from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Payment, SalesOrder, Quotation, Customer
from backend.app.schemas.schemas import PaymentCreate, PaymentResponse

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.get("", response_model=List[PaymentResponse])
def list_payments(db: Session = Depends(get_db)):
    return db.query(Payment).order_by(Payment.payment_date.desc()).all()

@router.post("", response_model=PaymentResponse)
def create_payment(payment_in: PaymentCreate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == payment_in.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if payment_in.order_id:
        order = db.query(SalesOrder).filter(SalesOrder.id == payment_in.order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        if not payment_in.quotation_id and order.quotation_id:
            payment_in.quotation_id = order.quotation_id
    elif payment_in.quotation_id:
        quotation = db.query(Quotation).filter(Quotation.id == payment_in.quotation_id).first()
        if not quotation:
            raise HTTPException(status_code=404, detail="Quotation not found")
        if quotation.sales_order:
            payment_in.order_id = quotation.sales_order.id

    payment = Payment(
        order_id=payment_in.order_id,
        quotation_id=payment_in.quotation_id,
        customer_id=payment_in.customer_id,
        amount=payment_in.amount,
        payment_date=datetime.utcnow(),
        payment_type=payment_in.payment_type,
        status="Recorded",
        reference_notes=payment_in.reference_notes
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment
