from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import SalesOrder, EquipmentSerial
from backend.app.schemas.schemas import DispatchSerialsRequest, SalesOrderResponse, EquipmentSerialResponse
from backend.app.services.dispatch_service import DispatchService
from backend.app.api.endpoints.orders import _format_order

router = APIRouter(prefix="/dispatch", tags=["Dispatch & Inventory"])

@router.get("/{id}/requirements")
def get_dispatch_requirements(id: int, db: Session = Depends(get_db)):
    order = db.query(SalesOrder).filter(SalesOrder.id == id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    requirements = DispatchService.get_order_serialized_requirements(db, order)
    
    # Also fetch available in-stock serial numbers for these products
    req_list = []
    for product_id, req in requirements.items():
        in_stock_serials = db.query(EquipmentSerial).filter(
            EquipmentSerial.product_id == product_id,
            EquipmentSerial.status == "In Stock"
        ).all()

        req_list.append({
            "product_id": product_id,
            "product_name": req["product"].name,
            "category": req["product"].category,
            "required_quantity": req["required_quantity"],
            "available_serials": [s.serial_number for s in in_stock_serials]
        })

    return {
        "order_id": order.id,
        "package_name": order.package.name,
        "status": order.status,
        "requirements": req_list
    }

@router.post("/{id}/serials", response_model=SalesOrderResponse)
def dispatch_order_serials(
    id: int,
    payload: DispatchSerialsRequest,
    db: Session = Depends(get_db)
):
    dispatched_order = DispatchService.dispatch_serials(db, id, payload.serial_numbers)
    return _format_order(dispatched_order)
