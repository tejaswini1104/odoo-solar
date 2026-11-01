from datetime import date, datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from backend.app.api.deps import require_customer
from backend.app.core.database import get_db
from backend.app.models.models import Installation, Invoice, Payment, ServiceTicket, SubsidyApplication, User, Warranty
from backend.app.schemas.after_sales_schemas import (
    InvoicePaymentSubmit, PortalInstallation, PortalInstallationPhoto, PortalInvoice, PortalInvoiceLine,
    PortalTicket, PortalTicketCreate, PortalWarranty
)
from backend.app.schemas.billing_schemas import PortalPayment
from backend.app.schemas.schemas import ServiceTicketCreate
from backend.app.services.installation_proof_service import resolve_file
from backend.app.services.order_service import VERIFIED_STATUSES
from backend.app.services.ticket_service import TicketService

router = APIRouter(prefix="/portal", tags=["Customer Portal - After-sales"])


# ----------------- Warranties -----------------
@router.get("/warranties", response_model=List[PortalWarranty])
def my_warranties(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    today = date.today()
    warranties = (
        db.query(Warranty)
        .filter(Warranty.customer_id == user.customer_id)
        .order_by(Warranty.end_date)
        .all()
    )
    result = []
    for w in warranties:
        active = w.start_date <= today <= w.end_date
        result.append(PortalWarranty(
            id=w.id,
            product_name=w.product.name,
            category=w.product.category,
            serial_number=w.serial_number,
            warranty_type=w.warranty_type,
            duration_months=w.duration_months,
            start_date=w.start_date,
            end_date=w.end_date,
            status="Active" if active else "Expired",
            days_left=max((w.end_date - today).days, 0),
        ))
    return result


# ----------------- Service tickets -----------------
def _ticket_out(t: ServiceTicket) -> PortalTicket:
    return PortalTicket(
        id=t.id,
        reference=f"TCK-{t.id:04d}",
        equipment_serial=t.equipment_serial,
        title=t.title,
        description=t.description,
        priority=t.priority,
        status=t.status,
        service_type=t.service_type,
        customer_charge=t.customer_charge,
        customer_confirmed=t.customer_confirmed,
        invoice_id=t.invoice_id,
        created_at=t.created_at,
    )


@router.get("/tickets", response_model=List[PortalTicket])
def my_tickets(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    tickets = (
        db.query(ServiceTicket)
        .filter(ServiceTicket.customer_id == user.customer_id)
        .order_by(ServiceTicket.created_at.desc())
        .all()
    )
    return [_ticket_out(t) for t in tickets]


@router.post("/tickets", response_model=PortalTicket, status_code=201)
def raise_ticket(payload: PortalTicketCreate, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    serial = payload.equipment_serial.strip()
    # A customer can only raise a ticket for equipment registered to their own account
    owns_serial = (
        db.query(Warranty)
        .filter(Warranty.customer_id == user.customer_id, Warranty.serial_number == serial)
        .first()
    )
    if not owns_serial:
        raise HTTPException(status_code=403, detail="This serial number is not registered to your account.")

    ticket = TicketService.create_ticket(
        db,
        ServiceTicketCreate(
            customer_id=user.customer_id,
            equipment_serial=serial,
            title=payload.title.strip(),
            description=payload.description.strip(),
            priority=payload.priority,
        ),
    )
    return _ticket_out(ticket)


@router.post("/tickets/{ticket_id}/confirm", response_model=PortalTicket)
def confirm_ticket(ticket_id: int, user: User = Depends(require_customer), db: Session = Depends(get_db)):
    ticket = (
        db.query(ServiceTicket)
        .filter(ServiceTicket.id == ticket_id, ServiceTicket.customer_id == user.customer_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
    if ticket.status != "Resolved":
        raise HTTPException(
            status_code=400,
            detail="You can confirm the fix once our technician has marked the ticket as resolved.",
        )
    return _ticket_out(TicketService.customer_confirm_ticket(db, ticket.id))


# ----------------- Invoices -----------------
def _invoice_origin(inv: Invoice) -> str:
    if inv.ticket_id:
        return f"Service ticket TCK-{inv.ticket_id:04d}"
    if inv.order_id:
        return f"Installation order SO-{inv.order_id:04d}"
    return "Direct"


def _invoice_out(inv: Invoice, db: Session) -> PortalInvoice:
    payments = db.query(Payment).filter(Payment.invoice_id == inv.id).all()
    verified = round(sum(p.amount for p in payments if p.status in VERIFIED_STATUSES), 2)
    pending = round(sum(p.amount for p in payments if p.status == "Pending Verification"), 2)
    if inv.status == "Paid":
        # The project invoice is issued after the order's own payments cleared, so it is fully paid
        verified = max(verified, inv.total)
        payable = 0.0
    else:
        payable = round(max(inv.total - verified - pending, 0), 2)
    return PortalInvoice(
        id=inv.id,
        invoice_number=inv.invoice_number,
        origin=_invoice_origin(inv),
        status=inv.status,
        items=[
            PortalInvoiceLine(description=i.description, quantity=i.quantity, unit_price=i.unit_price, total=i.total)
            for i in inv.items
        ],
        subtotal=inv.subtotal,
        gst=inv.tax,
        total=inv.total,
        paid_verified=verified,
        paid_pending=pending,
        payable_now=payable,
    )


@router.get("/invoices", response_model=List[PortalInvoice])
def my_invoices(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    # Draft invoices are internal until staff send them
    invoices = (
        db.query(Invoice)
        .filter(Invoice.customer_id == user.customer_id, Invoice.status.in_(["Sent", "Paid"]))
        .order_by(Invoice.created_at.desc())
        .all()
    )
    return [_invoice_out(inv, db) for inv in invoices]


@router.post("/invoices/{invoice_id}/payments", response_model=PortalPayment, status_code=201)
def pay_invoice(
    invoice_id: int,
    payload: InvoicePaymentSubmit,
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.customer_id == user.customer_id).first()
    if not inv or inv.status not in ("Sent", "Paid"):
        raise HTTPException(status_code=404, detail="Invoice not found.")
    if inv.status == "Paid":
        raise HTTPException(status_code=400, detail="This invoice is already paid.")

    payable = _invoice_out(inv, db).payable_now
    if payload.amount > payable + 0.005:
        raise HTTPException(status_code=400, detail=f"You can pay at most ₹{payable:,.2f} on this invoice right now.")

    reference = payload.reference_number.strip()
    if db.query(Payment).filter(Payment.reference_number == reference).first():
        raise HTTPException(status_code=409, detail="This reference number has already been reported.")

    payment = Payment(
        invoice_id=inv.id,
        customer_id=user.customer_id,
        amount=round(payload.amount, 2),
        payment_date=datetime.utcnow(),
        payment_type="service",
        status="Pending Verification",
        reference_number=reference,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return PortalPayment(
        id=payment.id,
        quotation_reference=inv.invoice_number,
        amount=payment.amount,
        reference_number=payment.reference_number,
        status=payment.status,
        payment_date=payment.payment_date,
    )


# ----------------- Installation progress and proof -----------------
def _installation_out(inst: Installation) -> PortalInstallation:
    return PortalInstallation(
        id=inst.id,
        reference=f"JOB-{inst.id:04d}",
        package_name=inst.sales_order.package.name if inst.sales_order and inst.sales_order.package else "Solar system",
        status=inst.status,
        technician_name=inst.technician.name if inst.technician else None,
        scheduled_date=inst.scheduled_date,
        start_time=inst.start_time,
        finish_time=inst.finish_time,
        confirmed_system_size=inst.confirmed_system_size,
        delivered_at=inst.sales_order.delivered_at if inst.sales_order else None,
        signed_by_name=inst.signed_by_name,
        signed_at=inst.signed_at,
        signature_url=f"/api/portal/installations/{inst.id}/signature/file" if inst.signature_path else None,
        photos=[
            PortalInstallationPhoto(
                id=p.id,
                caption=p.caption,
                url=f"/api/portal/installations/{inst.id}/photos/{p.id}/file",
            )
            for p in sorted(inst.photos, key=lambda p: p.id)
        ],
    )


def _own_installation(db: Session, user: User, installation_id: int) -> Installation:
    inst = (
        db.query(Installation)
        .filter(Installation.id == installation_id, Installation.customer_id == user.customer_id)
        .first()
    )
    if not inst:
        raise HTTPException(status_code=404, detail="Installation not found.")
    return inst


@router.get("/installations", response_model=List[PortalInstallation])
def my_installations(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    jobs = (
        db.query(Installation)
        .filter(Installation.customer_id == user.customer_id)
        .order_by(Installation.scheduled_date.desc())
        .all()
    )
    return [_installation_out(inst) for inst in jobs]


@router.get("/installations/{installation_id}/photos/{photo_id}/file")
def my_installation_photo(
    installation_id: int, photo_id: int, user: User = Depends(require_customer), db: Session = Depends(get_db)
):
    inst = _own_installation(db, user, installation_id)
    photo = next((p for p in inst.photos if p.id == photo_id), None)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found.")
    return FileResponse(resolve_file(photo.file_path), headers={"Cache-Control": "private, max-age=3600"})


@router.get("/installations/{installation_id}/signature/file")
def my_installation_signature(
    installation_id: int, user: User = Depends(require_customer), db: Session = Depends(get_db)
):
    inst = _own_installation(db, user, installation_id)
    if not inst.signature_path:
        raise HTTPException(status_code=404, detail="No signature has been recorded.")
    return FileResponse(resolve_file(inst.signature_path), media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


# ----------------- Subsidy progress -----------------
def _status_steps(events):
    """One entry each time the file moved to a new status. Internal notes added on the same status are not steps."""
    steps = []
    for event in sorted(events, key=lambda e: e.id):
        if not steps or steps[-1]["status"] != event.status:
            steps.append({"status": event.status, "at": event.created_at})
    return steps



@router.get("/subsidies")
def my_subsidies(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    """The customer's own subsidy files: where each stands, and its history. Internal notes are not shown."""
    apps = (
        db.query(SubsidyApplication)
        .filter(SubsidyApplication.customer_id == user.customer_id)
        .order_by(SubsidyApplication.created_at.desc())
        .all()
    )
    return [
        {
            "id": a.id,
            "order_reference": f"SO-{a.order_id:04d}",
            "package_name": a.order.package.name if a.order and a.order.package else None,
            "status": a.status,
            "reference_number": a.reference_number,
            "expected_amount": a.expected_amount,
            "received_amount": a.received_amount,
            "applied_on": a.applied_on,
            "approved_on": a.approved_on,
            "disbursed_on": a.disbursed_on,
            "steps": _status_steps(a.events),
        }
        for a in apps
    ]
