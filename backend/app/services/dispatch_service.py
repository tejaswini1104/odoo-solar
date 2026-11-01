from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from backend.app.models.models import (
    SalesOrder, EquipmentSerial, InventoryItem, Product
)

class DispatchService:
    @staticmethod
    def get_order_serialized_requirements(db: Session, order: SalesOrder):
        """Returns dict of product_id -> {product: Product, required_quantity: int}"""
        requirements = {}
        for comp in order.package.components:
            product = comp.product
            if product.is_serialized:
                requirements[product.id] = {
                    "product": product,
                    "required_quantity": comp.quantity
                }
        return requirements

    @staticmethod
    def dispatch_serials(db: Session, order_id: int, serial_numbers: List[str]) -> SalesOrder:
        order = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail=f"Order #{order_id} not found.")

        if order.status != "Confirmed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot dispatch order with status '{order.status}'. Order must be 'Confirmed'."
            )

        # Get serialized requirements
        requirements = DispatchService.get_order_serialized_requirements(db, order)
        total_required_serials = sum(req["required_quantity"] for req in requirements.values())

        if len(serial_numbers) != total_required_serials:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dispatch rejected: Expected {total_required_serials} serial numbers for this order's serialized components, but received {len(serial_numbers)}."
            )

        # Clean serial number strings
        clean_serials = [s.strip() for s in serial_numbers if s.strip()]
        if len(clean_serials) != len(set(clean_serials)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dispatch rejected: Duplicate serial numbers detected in submission."
            )

        # Fetch serial entities
        matched_serials = db.query(EquipmentSerial).filter(
            EquipmentSerial.serial_number.in_(clean_serials)
        ).all()

        matched_dict = {s.serial_number: s for s in matched_serials}

        # Check all provided serials exist and are In Stock
        for sn in clean_serials:
            if sn not in matched_dict:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dispatch rejected: Serial number '{sn}' does not exist in inventory."
                )
            serial_obj = matched_dict[sn]
            if serial_obj.status != "In Stock":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dispatch rejected: Serial number '{sn}' is not 'In Stock' (Current status: '{serial_obj.status}')."
                )

        # Validate that serials match the required product categories and counts
        assigned_counts = {}
        for s in matched_serials:
            assigned_counts[s.product_id] = assigned_counts.get(s.product_id, 0) + 1

        for product_id, req in requirements.items():
            assigned = assigned_counts.get(product_id, 0)
            if assigned != req["required_quantity"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dispatch rejected: Product '{req['product'].name}' requires {req['required_quantity']} serial number(s), but {assigned} were assigned."
                )

        # ATOMIC DISPATCH TRANSACTION
        try:
            # 1. Update serial status
            for s in matched_serials:
                s.status = "Dispatched"
                s.order_id = order.id

            # 2. Deduct inventory: decrease on_hand and reserved
            for comp in order.package.components:
                if comp.product.category == "Installation Service":
                    continue  # work done on site, not stock
                inv = db.query(InventoryItem).filter(InventoryItem.product_id == comp.product_id).first()
                if inv:
                    inv.reserved_quantity = max(0, inv.reserved_quantity - comp.quantity)
                    inv.quantity_on_hand = max(0, inv.quantity_on_hand - comp.quantity)

            # 3. Update order status
            order.status = "Dispatched"

            # 4. Update installation job status to In Progress
            if order.installation:
                order.installation.status = "In Progress"

            db.commit()
            db.refresh(order)
            return order
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Dispatch transaction failed: {str(e)}"
            )
