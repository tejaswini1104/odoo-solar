from typing import List
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.core.roles import SALES, SUPPORT
from backend.app.models.models import Invoice, InvoiceItem, ServiceTicket, User
from backend.app.schemas.schemas import InvoiceResponse, InvoiceItemCreate

router = APIRouter(prefix="/invoices", tags=["Invoices"])


def _require_invoice_owner(user: User, inv: Invoice) -> None:
    """Repair invoices (tied to a ticket) are handled by Support. Installation invoices are handled by Sales."""
    owner = SUPPORT if inv.ticket_id else SALES
    if user.role != owner:
        raise HTTPException(
            status_code=403,
            detail="Repair invoices are handled by Support. Installation invoices are handled by Sales.",
        )

def _format_invoice(inv: Invoice) -> dict:
    return {
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "customer_id": inv.customer_id,
        "customer_name": inv.customer.name if inv.customer else None,
        "order_id": inv.order_id,
        "ticket_id": inv.ticket_id,
        "subtotal": inv.subtotal,
        "tax": inv.tax,
        "total": inv.total,
        "status": inv.status,
        "items": [
            {
                "id": it.id,
                "description": it.description,
                "quantity": it.quantity,
                "unit_price": it.unit_price,
                "total": it.total
            }
            for it in inv.items
        ],
        "created_at": inv.created_at,
        "updated_at": inv.updated_at
    }

@router.get("", response_model=List[InvoiceResponse])
def list_invoices(db: Session = Depends(get_db)):
    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).all()
    return [_format_invoice(inv) for inv in invoices]

@router.get("/{id}", response_model=InvoiceResponse)
def get_invoice(id: int, db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.id == id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _format_invoice(inv)

@router.put("/{id}/items", response_model=InvoiceResponse)
def update_invoice_items(
    id: int,
    new_items: List[InvoiceItemCreate] = Body(min_length=1, max_length=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    _require_invoice_owner(user, inv)
    if inv.status != "Draft":
        raise HTTPException(
            status_code=400,
            detail=f"Only a draft invoice can be edited. This one is '{inv.status}', so the customer may already have seen it.",
        )

    # Clear existing items
    db.query(InvoiceItem).filter(InvoiceItem.invoice_id == inv.id).delete()

    subtotal = 0.0
    for it in new_items:
        tot = round(it.quantity * it.unit_price, 2)
        subtotal += tot
        db.add(InvoiceItem(
            invoice_id=inv.id,
            description=it.description,
            quantity=it.quantity,
            unit_price=it.unit_price,
            total=tot
        ))

    tax = round(subtotal * settings.GST_PERCENT / 100, 2)
    total = round(subtotal + tax, 2)

    inv.subtotal = subtotal
    inv.tax = tax
    inv.total = total

    db.commit()
    db.refresh(inv)
    return _format_invoice(inv)

@router.post("/{id}/send", response_model=InvoiceResponse)
def send_invoice(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Make a draft invoice visible to the customer. A service invoice can be sent only once its ticket is resolved."""
    inv = db.query(Invoice).filter(Invoice.id == id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    _require_invoice_owner(user, inv)
    if inv.status != "Draft":
        raise HTTPException(status_code=400, detail=f"Only draft invoices can be sent. Current status: '{inv.status}'.")
    if inv.ticket_id:
        ticket = db.query(ServiceTicket).filter(ServiceTicket.id == inv.ticket_id).first()
        if ticket and ticket.status not in ("Resolved", "Customer Confirmed", "Closed"):
            raise HTTPException(
                status_code=400,
                detail="Resolve the service ticket before sending this invoice."
            )
    inv.status = "Sent"
    db.commit()
    db.refresh(inv)
    return _format_invoice(inv)

@router.post("/{id}/pay", response_model=InvoiceResponse)
def mark_invoice_paid(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.id == id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    _require_invoice_owner(user, inv)
    
    inv.status = "Paid"
    db.commit()
    db.refresh(inv)
    return _format_invoice(inv)
