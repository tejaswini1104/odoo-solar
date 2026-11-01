import re
from datetime import date
from typing import List, Optional
from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.app.core.clock import business_today
from backend.app.models.models import EquipmentSerial, InventoryItem, Product, StockPurchase, StockPurchaseItem, User


from backend.app.core.validators import SERIAL_PATTERN  # noqa: E402


class PurchaseItemIn(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=100000)
    unit_cost: float = Field(ge=0, le=10_000_000)
    serial_numbers: List[str] = Field(default=[], max_length=100000)  # required, one per unit, for serialized products


class PurchaseIn(BaseModel):
    supplier: str = Field(min_length=2, max_length=255, pattern=r"^\S(.*\S)?$")
    invoice_reference: Optional[str] = Field(default=None, max_length=100)
    purchased_on: date
    items: List[PurchaseItemIn] = Field(min_length=1)


class StockService:
    @staticmethod
    def receive(db: Session, payload: PurchaseIn, user: User) -> StockPurchase:
        """Record a supplier purchase and add it to stock, in one transaction.

        Bulk items raise the quantity on hand. Serialized items must come with one unique serial number per unit,
        and each is added to the serial register as In Stock.
        """
        if payload.purchased_on > business_today():
            raise HTTPException(status_code=400, detail="The purchase date cannot be in the future.")

        seen_serials = set()
        prepared = []
        for line in payload.items:
            product = db.get(Product, line.product_id)
            if not product:
                raise HTTPException(status_code=404, detail=f"Product {line.product_id} not found.")
            serials = [s.strip() for s in line.serial_numbers if s and s.strip()]
            if product.is_serialized:
                if len(serials) != line.quantity:
                    raise HTTPException(
                        status_code=400,
                        detail=f"'{product.name}' needs one serial number per unit: {line.quantity} units, {len(serials)} serial numbers given.",
                    )
                bad = [s for s in serials if not re.fullmatch(SERIAL_PATTERN, s)]
                if bad:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Serial number '{bad[0]}' is not valid. Use 3 to 100 letters, digits, dashes, dots or slashes, starting with a letter or digit.",
                    )
                repeated = [s for s in serials if s in seen_serials or serials.count(s) > 1]
                if repeated:
                    raise HTTPException(status_code=400, detail=f"Serial number '{repeated[0]}' appears more than once.")
                seen_serials.update(serials)
            elif serials:
                raise HTTPException(status_code=400, detail=f"'{product.name}' is not serialized, so it takes no serial numbers.")
            prepared.append((product, line, serials))

        all_serials = [s for _, _, serials in prepared for s in serials]
        if all_serials:
            taken = [row[0] for row in db.query(EquipmentSerial.serial_number).filter(EquipmentSerial.serial_number.in_(all_serials)).all()]
            if taken:
                raise HTTPException(status_code=409, detail=f"Serial number '{taken[0]}' is already in the register.")

        purchase = StockPurchase(
            supplier=payload.supplier.strip(),
            invoice_reference=(payload.invoice_reference or "").strip() or None,
            purchased_on=payload.purchased_on,
            received_by=user.id,
        )
        db.add(purchase)
        db.flush()

        total = 0.0
        for product, line, serials in prepared:
            total += line.quantity * line.unit_cost
            db.add(StockPurchaseItem(purchase_id=purchase.id, product_id=product.id, quantity=line.quantity, unit_cost=line.unit_cost))
            inventory = db.query(InventoryItem).filter(InventoryItem.product_id == product.id).first()
            if inventory:
                inventory.quantity_on_hand += line.quantity
            else:
                db.add(InventoryItem(product_id=product.id, quantity_on_hand=line.quantity, reserved_quantity=0))
            for serial in serials:
                db.add(EquipmentSerial(product_id=product.id, serial_number=serial, status="In Stock"))
        purchase.total_cost = round(total, 2)

        try:
            db.commit()
        except IntegrityError:
            # Someone registered the same serial number a moment ago. The database constraint is the final check.
            db.rollback()
            raise HTTPException(status_code=409, detail="One of the serial numbers was registered a moment ago. Please check and try again.")
        db.refresh(purchase)
        return purchase
