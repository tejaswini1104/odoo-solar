from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user, require_roles
from backend.app.core.database import get_db
from backend.app.core.roles import SALES, SUPPORT
from backend.app.models.models import Payment, SalesOrder, Quotation, Customer, User
from backend.app.schemas.schemas import PaymentCreate, PaymentResponse
from backend.app.services import billing_service

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.get("", response_model=List[PaymentResponse])
def list_payments(db: Session = Depends(get_db)):
    return db.query(Payment).order_by(Payment.payment_date.desc()).all()

@router.post("", response_model=PaymentResponse)
def create_payment(
    payment_in: PaymentCreate,
    _user: User = Depends(require_roles(SALES)),  # only Sales record order payments
    db: Session = Depends(get_db),
):
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

    # Never take more than is still owed on the order
    target = db.query(SalesOrder).filter(SalesOrder.id == payment_in.order_id).first() if payment_in.order_id else None
    if target:
        if target.status == "Cancelled":
            raise HTTPException(status_code=400, detail="This order was cancelled, so no payment can be recorded against it.")
        if target.customer_id != payment_in.customer_id:
            raise HTTPException(status_code=400, detail="This order belongs to a different customer.")
        held = round(sum(p.amount for p in target.payments if p.status in ("Verified", "Recorded", "Pending Verification")), 2)
        owed = round(target.total_amount - held, 2)
        if payment_in.amount > owed + 0.005:
            raise HTTPException(
                status_code=400,
                detail=f"This payment is more than the ₹{max(owed, 0):,.2f} still owed on the order (total ₹{target.total_amount:,.2f}, paid or reported ₹{held:,.2f}).",
            )

    payment = Payment(
        order_id=payment_in.order_id,
        quotation_id=payment_in.quotation_id,
        customer_id=payment_in.customer_id,
        amount=payment_in.amount,
        payment_date=datetime.utcnow(),
        payment_type=payment_in.payment_type,
        status="Verified",  # entered by staff, so it is verified when recorded
        reference_notes=payment_in.reference_notes
    )
    db.add(payment)
    db.flush()
    billing_service.sync_after_verification(db, payment)
    db.commit()
    db.refresh(payment)
    return payment

@router.post("/{id}/verify", response_model=PaymentResponse)
def verify_payment(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Staff confirm a payment that the customer reported (for example after checking the bank statement).

    Payments for a repair invoice are verified by Support. Payments for an order are verified by Sales.
    """
    payment = db.query(Payment).filter(Payment.id == id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    owner = SUPPORT if payment.invoice_id else SALES
    if user.role != owner:
        raise HTTPException(
            status_code=403,
            detail="Order payments are verified by Sales. Repair invoice payments are verified by Support.",
        )
    if payment.status != "Pending Verification":
        raise HTTPException(status_code=400, detail=f"Only pending payments can be verified. Current status: '{payment.status}'.")
    payment.status = "Verified"
    billing_service.sync_after_verification(db, payment)
    db.commit()
    db.refresh(payment)
    return payment
