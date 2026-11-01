from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Quotation
from backend.app.schemas.schemas import QuotationCreate, QuotationResponse, SalesOrderResponse
from backend.app.services.quotation_service import QuotationService
from backend.app.services.order_service import OrderService
from backend.app.api.endpoints.orders import _format_order

from backend.app.services.notification_service import notify

router = APIRouter(prefix="/quotations", tags=["Quotations"])

def _format_quotation(q: Quotation) -> dict:
    return {
        "id": q.id,
        "customer_id": q.customer_id,
        "customer_name": q.customer.name if q.customer else None,
        "survey_id": q.survey_id,
        "package_id": q.package_id,
        "package_name": q.package.name if q.package else None,
        "subtotal": q.subtotal,
        "tax": q.tax,
        "total": q.total,
        "status": q.status,
        "items": [
            {
                "id": it.id,
                "product_id": it.product_id,
                "product_name": it.product.name if it.product else None,
                "quantity": it.quantity,
                "unit_price": it.unit_price,
                "total_price": it.total_price
            }
            for it in q.items
        ],
        "created_at": q.created_at,
        "updated_at": q.updated_at
    }

@router.get("", response_model=List[QuotationResponse])
def list_quotations(db: Session = Depends(get_db)):
    quotes = db.query(Quotation).order_by(Quotation.created_at.desc()).all()
    return [_format_quotation(q) for q in quotes]

@router.post("", response_model=QuotationResponse)
def create_quotation(quotation_in: QuotationCreate, db: Session = Depends(get_db)):
    # Explicit service call enforcing the hard gate
    quotation = QuotationService.create_quotation(db, quotation_in)
    return _format_quotation(quotation)

@router.get("/{id}", response_model=QuotationResponse)
def get_quotation(id: int, db: Session = Depends(get_db)):
    q = db.query(Quotation).filter(Quotation.id == id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found")
    return _format_quotation(q)

@router.post("/{id}/send", response_model=dict)
def send_quotation(id: int, db: Session = Depends(get_db)):
    """Mark a draft quotation as sent. Only sent quotations are visible to the customer in the portal."""
    quotation = db.query(Quotation).filter(Quotation.id == id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if quotation.status != "Draft":
        raise HTTPException(status_code=400, detail=f"Only draft quotations can be sent. Current status: '{quotation.status}'.")
    quotation.status = "Sent"
    notify(
        db, f"Your quotation QTN-{quotation.id:05d} is ready",
        f"Total ₹{quotation.total:,.0f} including GST. Review and accept it in the portal.",
        link="quotes", customer_id=quotation.customer_id,
    )
    db.commit()
    return {"id": quotation.id, "status": quotation.status}

@router.post("/{id}/confirm", response_model=SalesOrderResponse)
def convert_and_confirm_quotation(id: int, db: Session = Depends(get_db)):
    # Accepts quotation and generates a SalesOrder
    order = OrderService.create_or_get_order_from_quotation(db, id)
    return _format_order(order)
