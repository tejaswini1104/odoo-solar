from datetime import datetime, timedelta, date
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.core.config import settings
from backend.app.services.assignment_service import pick_technician
from backend.app.core.roles import SALES, WAREHOUSE
from backend.app.services.notification_service import notify
from backend.app.services.subsidy_service import SubsidyService
from backend.app.models.models import (
    SalesOrder, Quotation, Payment, InventoryItem, Installation, Technician, SiteSurvey,
    SolarPackage, EquipmentSerial, SubsidyApplication
)

# "Recorded" is the status of payments entered before verification existed; they count as verified.
VERIFIED_STATUSES = ("Verified", "Recorded")

def is_service(product) -> bool:
    """Installation is work done on site. It is never packed, so it never needs stock, a reservation or a dispatch."""
    return product.category == "Installation Service"


class OrderService:
    @staticmethod
    def create_or_get_order_from_quotation(db: Session, quotation_id: int) -> SalesOrder:
        quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
        if not quotation:
            raise HTTPException(status_code=404, detail="Quotation not found")
        
        # Check if order already exists
        existing_order = db.query(SalesOrder).filter(SalesOrder.quotation_id == quotation_id).first()
        if existing_order:
            return existing_order
        
        # Create SalesOrder in Draft / Pending Confirmation
        order = SalesOrder(
            quotation_id=quotation.id,
            customer_id=quotation.customer_id,
            package_id=quotation.package_id,
            total_amount=quotation.total,
            status="Pending Confirmation",
            flat_labour_cost=5000.0
        )
        quotation.status = "Accepted"
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    @staticmethod
    def confirm_order(db: Session, order_id: int) -> SalesOrder:
        order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail=f"Sales Order #{order_id} not found.")

        if order.status in ["Confirmed", "Dispatched", "Completed"]:
            return order # Already confirmed

        # 1. Check linked survey approval
        quotation = order.quotation
        if not quotation:
            raise HTTPException(status_code=400, detail="Order has no linked quotation.")
        
        survey = quotation.survey
        if not survey or survey.status != "Approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order confirmation failed: Linked site survey is not Approved."
            )

        # 2. Verified advance: at least ADVANCE_PERCENT of the total including GST must be confirmed by staff.
        # Payments can be linked to either order_id or quotation_id. Customer-reported payments that staff
        # have not verified yet ("Pending Verification") do not count.
        payments = db.query(Payment).filter(
            (Payment.order_id == order.id) | (Payment.quotation_id == quotation.id)
        ).all()

        verified_total = round(sum(p.amount for p in payments if p.status in VERIFIED_STATUSES), 2)
        required_advance = round(order.total_amount * settings.ADVANCE_PERCENT / 100, 2)

        if verified_total + 0.005 < required_advance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Order confirmation failed: a verified advance of ₹{required_advance:,.2f} "
                    f"({settings.ADVANCE_PERCENT:g}% of the total including GST) is required. "
                    f"Verified so far: ₹{verified_total:,.2f}."
                )
            )

        # 3. Stock availability check (before any writes, so a shortage never reserves anything)
        package = order.package
        shortages = OrderService._find_stock_shortages(db, package)
        if shortages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order confirmation failed: insufficient stock for " + "; ".join(shortages) + "."
            )

        # Link any unlinked quotation payments directly to this order
        for p in payments:
            if p.order_id is None:
                p.order_id = order.id

        # 4. ATOMIC TRANSACTION:
        # a) Mark order Confirmed
        # b) Reserve inventory quantities
        # c) Create Installation Job & assign technician
        try:
            order.status = "Confirmed"

            # Reserve inventory for each BOM component (stock existence was checked above)
            for comp in package.components:
                if is_service(comp.product):
                    continue
                inv = db.query(InventoryItem).filter(InventoryItem.product_id == comp.product_id).first()
                inv.reserved_quantity += comp.quantity

            tech_id = OrderService._pick_technician(db)

            # Create Installation job record
            existing_job = db.query(Installation).filter(Installation.sales_order_id == order.id).first()
            if not existing_job:
                scheduled = date.today() + timedelta(days=2)
                installation_job = Installation(
                    sales_order_id=order.id,
                    customer_id=order.customer_id,
                    technician_id=tech_id,
                    scheduled_date=scheduled,
                    system_capacity=package.capacity_kw,
                    status="Scheduled",
                    notes=f"Auto-generated installation for {package.name}"
                )
                db.add(installation_job)

            # Customers who asked for the government subsidy get a file to track it, opened in the same transaction
            SubsidyService.open_for_order(db, order)

            ref = f"SO-{order.id:04d}"
            notify(
                db, f"Pack order {ref}", f"{package.name} for {order.customer.name}. Open Dispatch for the pick list.",
                link="dispatch", role=WAREHOUSE,
            )
            if tech_id:
                notify(
                    db, f"New installation job {ref}", f"{package.name} for {order.customer.name}, scheduled for the job date.",
                    link="installations", technician_id=tech_id,
                )
            notify(
                db, f"Order {ref} confirmed", "Your advance is verified. We will pack and schedule the installation.",
                link="quotes", customer_id=order.customer_id,
            )

            db.commit()
            db.refresh(order)
            return order
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Transaction failed during order confirmation: {str(e)}"
            )

    @staticmethod
    def cancel_order(db: Session, order_id: int, reason: str) -> SalesOrder:
        """Cancel an order that has not left the warehouse: free its reserved stock and drop the installation job.

        Money already received is not touched. The alert to Sales says how much is now due back to the customer.
        """
        order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail=f"Sales Order #{order_id} not found.")
        if order.status == "Cancelled":
            return order
        if order.status not in ("Pending Confirmation", "Confirmed"):
            raise HTTPException(
                status_code=400,
                detail=f"An order that is '{order.status}' cannot be cancelled, because the hardware has already left the warehouse.",
            )
        try:
            if order.status == "Confirmed":
                for comp in order.package.components:
                    if is_service(comp.product):
                        continue
                    inv = db.query(InventoryItem).filter(InventoryItem.product_id == comp.product_id).first()
                    if inv:
                        inv.reserved_quantity = max(0, inv.reserved_quantity - comp.quantity)
                if order.installation:
                    db.delete(order.installation)
            order.status = "Cancelled"
            if order.quotation:
                order.quotation.status = "Cancelled"
            subsidy = db.query(SubsidyApplication).filter(SubsidyApplication.order_id == order.id).first()
            if subsidy and subsidy.status not in ("Disbursed", "Rejected"):
                subsidy.status = "Rejected"
                subsidy.notes = f"Order cancelled: {reason}"
            received = round(sum(p.amount for p in order.payments if p.status in VERIFIED_STATUSES), 2)
            notify(
                db, f"Order SO-{order.id:04d} cancelled", f"{reason}. Refund due to the customer: ₹{received:,.0f}.",
                link="orders", role=SALES,
            )
            notify(db, f"Order SO-{order.id:04d} was cancelled", reason, link="quotes", customer_id=order.customer_id)
            db.commit()
            db.refresh(order)
            return order
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Cancelling the order failed: {str(e)}")

    @staticmethod
    def _find_stock_shortages(db: Session, package: SolarPackage) -> List[str]:
        """Return a message for every BOM component that cannot be reserved.

        Serialized products are counted from physically In Stock serial numbers;
        bulk products from quantity_on_hand. Both subtract existing reservations.
        """
        shortages = []
        for comp in package.components:
            product = comp.product
            if is_service(product):
                continue
            inv = db.query(InventoryItem).filter(InventoryItem.product_id == comp.product_id).first()
            reserved = inv.reserved_quantity if inv else 0
            if product.is_serialized:
                physical = db.query(EquipmentSerial).filter(
                    EquipmentSerial.product_id == comp.product_id,
                    EquipmentSerial.status == "In Stock"
                ).count()
            else:
                physical = inv.quantity_on_hand if inv else 0
            available = physical - reserved
            if available < comp.quantity:
                shortages.append(
                    f"{product.name} (need {comp.quantity}, available {max(available, 0)})"
                )
        return shortages

    @staticmethod
    def _pick_technician(db: Session) -> Optional[int]:
        """Assign the technician with the least open work (surveys and installations) who can sign in."""
        technician = pick_technician(db)
        return technician.id if technician else None
