from sqlalchemy.orm import Session
from backend.app.models.models import Invoice, InvoiceItem, Payment, SalesOrder
from backend.app.services.order_service import VERIFIED_STATUSES

EPSILON = 0.005


def _verified_sum(payments) -> float:
    return round(sum(p.amount for p in payments if p.status in VERIFIED_STATUSES), 2)


def sync_after_verification(db: Session, payment: Payment) -> None:
    """Update invoices after a payment is verified. The caller commits the session."""
    if payment.invoice_id:
        _mark_service_invoice_paid(db, payment.invoice_id)
    if payment.order_id:
        _create_project_invoice_if_paid(db, payment.order_id)


def _mark_service_invoice_paid(db: Session, invoice_id: int) -> None:
    invoice = db.get(Invoice, invoice_id)
    if not invoice or invoice.status == "Paid":
        return
    paid = _verified_sum(db.query(Payment).filter(Payment.invoice_id == invoice.id).all())
    if paid + EPSILON >= invoice.total:
        invoice.status = "Paid"


def _create_project_invoice_if_paid(db: Session, order_id: int) -> None:
    """Issue the order's tax invoice once verified payments cover the full order total including GST."""
    order = db.get(SalesOrder, order_id)
    if not order or not order.quotation:
        return

    already = db.query(Invoice).filter(Invoice.order_id == order.id, Invoice.ticket_id.is_(None)).first()
    if already:
        return

    order_payments = db.query(Payment).filter(Payment.order_id == order.id, Payment.invoice_id.is_(None)).all()
    if _verified_sum(order_payments) + EPSILON < order.total_amount:
        return

    quotation = order.quotation
    invoice = Invoice(
        invoice_number=f"INV-PRJ-{order.id:04d}",
        customer_id=order.customer_id,
        order_id=order.id,
        subtotal=quotation.subtotal,
        tax=quotation.tax,
        total=quotation.total,
        status="Paid",
    )
    db.add(invoice)
    db.flush()
    for item in quotation.items:
        db.add(InvoiceItem(
            invoice_id=invoice.id,
            description=item.product.name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total=item.total_price,
        ))
