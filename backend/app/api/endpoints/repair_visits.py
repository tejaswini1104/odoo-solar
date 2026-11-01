from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.models.models import ServiceTicket, User
from backend.app.schemas.schemas import TicketInspectRequest
from backend.app.services.ticket_service import TicketService

# Access is set where this router is included (api_router.py): technicians only.
router = APIRouter(prefix="/repair-visits", tags=["Repair Visits"])


def _visit(t: ServiceTicket) -> dict:
    c = t.customer
    return {
        "id": t.id,
        "reference": f"TCK-{t.id:04d}",
        "title": t.title,
        "description": t.description,
        "priority": t.priority,
        "status": t.status,
        "service_type": t.service_type,
        "equipment_serial": t.equipment_serial,
        "customer_name": c.name if c else None,
        "customer_phone": c.phone if c else None,
        "customer_address": f"{c.address}, {c.city}" if c else None,
        "needs_replacement": t.needs_replacement,
        "inspection_notes": t.inspection_notes,
        "quote_status": t.quote_status,
        "customer_charge": t.customer_charge,
        "dispatch_serial": t.dispatch_serial,
        "created_at": t.created_at,
    }


def _own_ticket(db: Session, user: User, ticket_id: int) -> ServiceTicket:
    ticket = db.query(ServiceTicket).filter(ServiceTicket.id == ticket_id).first()
    if not ticket or not user.technician_id or ticket.technician_id != user.technician_id:
        raise HTTPException(status_code=404, detail="This repair visit is not assigned to you.")
    return ticket


@router.get("")
def my_repair_visits(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The tickets assigned to the signed-in technician, newest first."""
    if not user.technician_id:
        return []
    tickets = (
        db.query(ServiceTicket)
        .filter(ServiceTicket.technician_id == user.technician_id)
        .order_by(ServiceTicket.created_at.desc())
        .all()
    )
    return [_visit(t) for t in tickets]


@router.post("/{ticket_id}/report")
def report_visit(
    ticket_id: int, payload: TicketInspectRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """The technician's finding at the site: repairable on the spot, or a replacement is needed. Support are told."""
    ticket = _own_ticket(db, user, ticket_id)
    updated = TicketService.record_inspection(db, ticket.id, payload.needs_replacement, (payload.notes or "").strip() or None)
    return _visit(updated)
