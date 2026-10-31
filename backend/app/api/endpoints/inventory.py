from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import InventoryItem, EquipmentSerial, Product
from backend.app.schemas.schemas import InventoryItemResponse, EquipmentSerialResponse

router = APIRouter(prefix="/inventory", tags=["Inventory & Serials"])

@router.get("", response_model=List[InventoryItemResponse])
def get_inventory(db: Session = Depends(get_db)):
    items = db.query(InventoryItem).join(Product).order_by(Product.id.asc()).all()
    results = []
    for item in items:
        results.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": item.product.name,
            "category": item.product.category,
            "quantity_on_hand": item.quantity_on_hand,
            "reserved_quantity": item.reserved_quantity,
            "available_quantity": max(0, item.quantity_on_hand - item.reserved_quantity),
            "is_serialized": item.product.is_serialized
        })
    return results

@router.get("/serials", response_model=List[EquipmentSerialResponse])
def get_serials(
    status: Optional[str] = None,
    product_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(EquipmentSerial).join(Product)
    if status:
        query = query.filter(EquipmentSerial.status == status)
    if product_id:
        query = query.filter(EquipmentSerial.product_id == product_id)

    serials = query.order_by(EquipmentSerial.created_at.desc()).all()
    return [
        {
            "id": s.id,
            "product_id": s.product_id,
            "product_name": s.product.name,
            "category": s.product.category,
            "serial_number": s.serial_number,
            "status": s.status,
            "order_id": s.order_id,
            "installation_id": s.installation_id,
            "created_at": s.created_at
        }
        for s in serials
    ]
