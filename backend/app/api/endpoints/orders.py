from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import SalesOrder, Payment
from backend.app.schemas.schemas import SalesOrderResponse
from backend.app.core.config import settings
from backend.app.services.order_service import OrderService, VERIFIED_STATUSES

router = APIRouter(prefix="/orders", tags=["Sales Orders"])

def _format_order(o: SalesOrder) -> dict:
    # Only money that staff have verified counts. A payment the customer has reported but nobody has checked does not.
    verified_payments = [p for p in o.payments if p.status in VERIFIED_STATUSES]
    advance_paid = round(sum(p.amount for p in verified_payments), 2)
    required_advance = round(o.total_amount * settings.ADVANCE_PERCENT / 100, 2)
    is_advance_paid = advance_paid + 0.005 >= required_advance and advance_paid > 0
    survey_approved = o.quotation.survey.status == "Approved" if o.quotation and o.quotation.survey else False

    return {
        "id": o.id,
        "quotation_id": o.quotation_id,
        "customer_id": o.customer_id,
        "customer_name": o.customer.name if o.customer else None,
        "package_id": o.package_id,
        "package_name": o.package.name if o.package else None,
        "total_amount": o.total_amount,
        "status": o.status,
        "flat_labour_cost": o.flat_labour_cost,
        "advance_paid": advance_paid,
        "is_advance_paid": is_advance_paid,
        "survey_approved": survey_approved,
        "delivered_at": o.delivered_at,
        "created_at": o.created_at,
        "updated_at": o.updated_at
    }

@router.get("", response_model=List[SalesOrderResponse])
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(SalesOrder).order_by(SalesOrder.created_at.desc()).all()
    return [_format_order(o) for o in orders]

@router.get("/{id}", response_model=SalesOrderResponse)
def get_order(id: int, db: Session = Depends(get_db)):
    order = db.query(SalesOrder).filter(SalesOrder.id == id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Sales Order not found")
    return _format_order(order)

@router.post("/{id}/confirm", response_model=SalesOrderResponse)
def confirm_order(id: int, db: Session = Depends(get_db)):
    # Invokes the strict confirmation checks and atomic transaction
    confirmed = OrderService.confirm_order(db, id)
    return _format_order(confirmed)


class CancelRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)

@router.post("/{id}/cancel", response_model=SalesOrderResponse)
def cancel_order(id: int, payload: CancelRequest, db: Session = Depends(get_db)):
    """Cancel an order before dispatch. Stock is released and the installation job is removed."""
    return _format_order(OrderService.cancel_order(db, id, payload.reason.strip()))
