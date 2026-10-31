from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Invoice, InvoiceItem
from backend.app.schemas.schemas import InvoiceResponse, InvoiceItemCreate

router = APIRouter(prefix="/invoices", tags=["Invoices"])

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
    new_items: List[InvoiceItemCreate],
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

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

    tax = round(subtotal * 0.18, 2)
    total = round(subtotal + tax, 2)

    inv.subtotal = subtotal
    inv.tax = tax
    inv.total = total

    db.commit()
    db.refresh(inv)
    return _format_invoice(inv)

@router.post("/{id}/pay", response_model=InvoiceResponse)
def mark_invoice_paid(id: int, db: Session = Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.id == id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    inv.status = "Paid"
    db.commit()
    db.refresh(inv)
    return _format_invoice(inv)
