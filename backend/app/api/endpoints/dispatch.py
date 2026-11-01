from datetime import datetime
from backend.app.core.clock import business_today
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import SalesOrder, EquipmentSerial, InventoryItem, ServiceTicket
from backend.app.services.notification_service import notify
from backend.app.schemas.schemas import DispatchSerialsRequest, SalesOrderResponse, EquipmentSerialResponse, TicketDispatchRequest
from backend.app.services.dispatch_service import DispatchService
from backend.app.services.ticket_service import TicketService
from backend.app.services.warranty_service import WarrantyService
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

@router.get("/{id}/pick-list")
def get_pick_list(id: int, db: Session = Depends(get_db)):
    """Everything the warehouse packs for an order: panels, cables and stands as well as the serial-numbered units."""
    order = db.query(SalesOrder).filter(SalesOrder.id == id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    lines = []
    for comp in order.package.components:
        product = comp.product
        if product.category == "Installation Service":
            continue  # a service done on site, nothing to pack
        inv = db.query(InventoryItem).filter(InventoryItem.product_id == product.id).first()
        lines.append({
            "product_id": product.id,
            "product_name": product.name,
            "category": product.category,
            "unit": product.unit,
            "quantity": comp.quantity,
            "is_serialized": product.is_serialized,
            "on_hand": inv.quantity_on_hand if inv else 0,
            "reserved": inv.reserved_quantity if inv else 0,
        })
    lines.sort(key=lambda l: (not l["is_serialized"], l["category"], l["product_name"]))
    return {
        "order_id": order.id,
        "reference": f"SO-{order.id:04d}",
        "customer_name": order.customer.name if order.customer else None,
        "delivery_address": f"{order.customer.address}, {order.customer.city}" if order.customer else None,
        "package_name": order.package.name,
        "status": order.status,
        "lines": lines,
    }

@router.post("/{id}/serials", response_model=SalesOrderResponse)
def dispatch_order_serials(
    id: int,
    payload: DispatchSerialsRequest,
    db: Session = Depends(get_db)
):
    dispatched_order = DispatchService.dispatch_serials(db, id, payload.serial_numbers)
    return _format_order(dispatched_order)


@router.post("/{id}/delivered", response_model=SalesOrderResponse)
def mark_delivered(id: int, db: Session = Depends(get_db)):
    """The goods have reached the customer. This starts the warranty clock for every serial number and the panels."""
    order = db.query(SalesOrder).filter(SalesOrder.id == id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "Dispatched":
        raise HTTPException(
            status_code=400,
            detail=f"Only a dispatched order can be marked delivered. This order is '{order.status}'.",
        )
    if order.delivered_at:
        raise HTTPException(status_code=400, detail="This order has already been marked delivered.")

    order.delivered_at = datetime.utcnow()
    WarrantyService.create_warranties_for_delivery(db, order, business_today())
    ref = f"SO-{order.id:04d}"
    notify(
        db, f"Order {ref} delivered", "Your warranty clock has started for every serial number and the panels.",
        link="warranties", customer_id=order.customer_id,
    )
    if order.installation and order.installation.technician_id:
        notify(
            db, f"Hardware delivered for {ref}", f"Ready to install at {order.customer.address}, {order.customer.city}.",
            link="installations", technician_id=order.installation.technician_id,
        )
    db.commit()
    db.refresh(order)
    return _format_order(order)


# ----------------- Replacement units for repair tickets -----------------
def _replacement_request(t: ServiceTicket, db: Session) -> dict:
    serials, product_name = [], None
    if t.warranty_id is None:
        old = db.query(EquipmentSerial).filter(EquipmentSerial.serial_number == t.equipment_serial).first()
        if old:
            product_name = old.product.name
            serials = [
                r.serial_number for r in db.query(EquipmentSerial).filter(
                    EquipmentSerial.product_id == old.product_id, EquipmentSerial.status == "In Stock"
                ).order_by(EquipmentSerial.serial_number).all()
            ]
    return {
        "ticket_id": t.id,
        "reference": f"TCK-{t.id:04d}",
        "status": t.status,
        "customer_name": t.customer.name,
        "delivery_address": f"{t.customer.address}, {t.customer.city}",
        "faulty_serial": None if t.warranty_id is not None else t.equipment_serial,
        "is_panel": t.warranty_id is not None,
        "product_name": product_name,
        "available_serials": serials,
        "technician_name": t.technician.name if t.technician else None,
        "dispatch_serial": t.dispatch_serial,
        "dispatched_at": t.dispatched_at,
    }


@router.get("/replacements/list")
def replacement_requests(db: Session = Depends(get_db)):
    """Repair tickets waiting for the warehouse to send a replacement, and the ones already sent."""
    tickets = (
        db.query(ServiceTicket)
        .filter(ServiceTicket.status.in_(["Awaiting Dispatch", "Dispatched"]))
        .order_by(ServiceTicket.created_at)
        .all()
    )
    return [_replacement_request(t, db) for t in tickets]


@router.post("/replacements/{ticket_id}/send")
def send_replacement(ticket_id: int, payload: Optional[TicketDispatchRequest] = None, db: Session = Depends(get_db)):
    """Send the replacement for a repair ticket: pick the in-stock serial (panels have none)."""
    ticket = TicketService.dispatch_replacement(db, ticket_id, payload.serial_number if payload else None)
    return _replacement_request(ticket, db)
