from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.api.deps import require_customer
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.roles import SALES
from backend.app.services.notification_service import notify
from backend.app.models.models import Invoice, Payment, Quotation, User
from backend.app.schemas.billing_schemas import BankDetails, PaymentSubmit, PortalPayment, PortalQuote, QuoteLine
from backend.app.services.order_service import VERIFIED_STATUSES, OrderService

router = APIRouter(prefix="/portal", tags=["Customer Portal - Billing"])


def _payment_state(q: Quotation, total: float, db: Session):
    """Return (verified, pending, advance_required, order_completed, payable_now) for a quotation.

    The customer may pay the advance or the full amount before work starts, or settle the balance later. The
    order needs at least the advance verified before it is confirmed. Payments waiting for verification count
    towards the limit, so the same money cannot be reported twice.
    """
    payments = db.query(Payment).filter(Payment.quotation_id == q.id).all()
    verified = round(sum(p.amount for p in payments if p.status in VERIFIED_STATUSES), 2)
    pending = round(sum(p.amount for p in payments if p.status == "Pending Verification"), 2)
    required = round(total * settings.ADVANCE_PERCENT / 100, 2)
    completed = bool(q.sales_order and q.sales_order.status == "Completed")
    payable_now = round(max(total - verified - pending, 0), 2)
    return verified, pending, required, completed, payable_now


def _quote_out(q: Quotation, db: Session) -> PortalQuote:
    items = [
        QuoteLine(
            product_name=item.product.name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.total_price,
        )
        for item in q.items
    ]
    # Use the totals stored on the quotation, so the portal always matches what was issued
    subtotal, gst, total = q.subtotal, q.tax, q.total

    verified, pending, required, completed, payable_now = _payment_state(q, total, db)

    return PortalQuote(
        id=q.id,
        reference=f"QTN-{q.id:05d}",
        package_name=q.package.name,
        status=q.status,
        items=items,
        subtotal=subtotal,
        gst=gst,
        total=total,
        order_id=q.sales_order.id if q.sales_order else None,
        order_status=q.sales_order.status if q.sales_order else None,
        advance_percent=settings.ADVANCE_PERCENT,
        advance_required=required,
        advance_verified=verified,
        advance_pending=pending,
        advance_outstanding=round(max(required - verified, 0), 2),
        balance_required=round(total - required, 2),
        order_completed=completed,
        payable_now=payable_now,
    )


def _own_quotation(db: Session, user: User, quotation_id: int) -> Quotation:
    q = db.query(Quotation).filter(Quotation.id == quotation_id, Quotation.customer_id == user.customer_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found.")
    return q


@router.get("/quotations", response_model=List[PortalQuote])
def my_quotations(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    quotes = (
        db.query(Quotation)
        .filter(Quotation.customer_id == user.customer_id, Quotation.status.in_(["Sent", "Accepted"]))
        .order_by(Quotation.created_at.desc())
        .all()
    )
    return [_quote_out(q, db) for q in quotes]


@router.post("/quotations/{quotation_id}/accept", response_model=PortalQuote)
def accept_quotation(quotation_id: int, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    q = _own_quotation(db, user, quotation_id)
    if q.status == "Accepted":
        return _quote_out(q, db)
    if q.status != "Sent":
        raise HTTPException(status_code=400, detail="This quotation is not available to accept.")
    # Accepting creates the sales order; installation is scheduled only after the verified advance is confirmed.
    OrderService.create_or_get_order_from_quotation(db, q.id)
    notify(db, f"Quotation QTN-{q.id:05d} accepted", "Waiting for the advance payment.", link="orders", role=SALES)
    db.commit()
    db.refresh(q)
    return _quote_out(q, db)


@router.get("/bank-details", response_model=BankDetails)
def bank_details(user: User = Depends(require_customer)):
    return BankDetails(**settings.BANK_DETAILS, advance_percent=settings.ADVANCE_PERCENT)


@router.post("/payments", response_model=PortalPayment, status_code=201)
def report_payment(payload: PaymentSubmit, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    q = _own_quotation(db, user, payload.quotation_id)
    if q.status != "Accepted" or q.sales_order is None:
        raise HTTPException(status_code=400, detail="Accept the quotation before paying the advance.")

    verified, pending, required, completed, payable_now = _payment_state(q, q.total, db)
    if payable_now <= 0:
        raise HTTPException(
            status_code=400,
            detail="This quotation is fully paid, or the payments you reported are waiting to be verified.",
        )
    if payload.amount > payable_now + 0.005:
        raise HTTPException(
            status_code=400,
            detail=f"You can pay at most ₹{payable_now:,.2f} on this quotation.",
        )

    reference = payload.reference_number.strip()
    if db.query(Payment).filter(Payment.reference_number == reference).first():
        raise HTTPException(status_code=409, detail="This reference number has already been reported.")

    payment = Payment(
        order_id=q.sales_order.id,
        quotation_id=q.id,
        customer_id=user.customer_id,
        amount=round(payload.amount, 2),
        payment_date=datetime.utcnow(),
        payment_type=(
            "full" if verified + pending == 0 and payload.amount + 0.005 >= q.total
            else "balance" if completed
            else "advance"
        ),
        status="Pending Verification",
        reference_number=reference,
    )
    db.add(payment)
    notify(
        db, f"Payment of ₹{payment.amount:,.0f} reported for QTN-{q.id:05d}",
        f"Reference {reference}. Check the bank statement and verify it.", link="orders", role=SALES,
    )
    db.commit()
    db.refresh(payment)
    return PortalPayment(
        id=payment.id,
        quotation_reference=f"QTN-{q.id:05d}",
        amount=payment.amount,
        reference_number=payment.reference_number,
        status=payment.status,
        payment_date=payment.payment_date,
    )


@router.get("/payments", response_model=List[PortalPayment])
def my_payments(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    payments = (
        db.query(Payment)
        .filter(Payment.customer_id == user.customer_id)
        .order_by(Payment.payment_date.desc())
        .all()
    )
    return [
        PortalPayment(
            id=p.id,
            quotation_reference=(
                f"QTN-{p.quotation_id:05d}" if p.quotation_id
                else (db.get(Invoice, p.invoice_id).invoice_number if p.invoice_id else "-")
            ),
            amount=p.amount,
            reference_number=p.reference_number,
            status=p.status,
            payment_date=p.payment_date,
        )
        for p in payments
    ]
