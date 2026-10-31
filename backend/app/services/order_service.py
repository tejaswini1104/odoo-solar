from datetime import datetime, timedelta, date
from typing import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.models import (
    SalesOrder, Quotation, Payment, InventoryItem, Installation, Technician, SiteSurvey,
    SolarPackage, EquipmentSerial
)

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

        # 2. Check at least advance payment recorded
        # Payments can be linked to either order_id or quotation_id
        payments = db.query(Payment).filter(
            (Payment.order_id == order.id) | (Payment.quotation_id == quotation.id)
        ).all()
        
        total_paid = sum(p.amount for p in payments)
        has_advance_or_full = any(p.payment_type in ["advance", "full"] and p.amount > 0 for p in payments)

        if not has_advance_or_full or total_paid <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order confirmation failed: At least one advance or full payment must be recorded before confirming the order."
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
    def _find_stock_shortages(db: Session, package: SolarPackage) -> List[str]:
        """Return a message for every BOM component that cannot be reserved.

        Serialized products are counted from physically In Stock serial numbers;
        bulk products from quantity_on_hand. Both subtract existing reservations.
        """
        shortages = []
        for comp in package.components:
            product = comp.product
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
        """Assign the technician with the fewest open (not Completed) installations."""
        open_jobs = dict(
            db.query(Installation.technician_id, func.count(Installation.id))
            .filter(Installation.status != "Completed", Installation.technician_id.isnot(None))
            .group_by(Installation.technician_id)
            .all()
        )
        technicians = db.query(Technician).order_by(Technician.id).all()
        if not technicians:
            return None
        return min(technicians, key=lambda t: (open_jobs.get(t.id, 0), t.id)).id
