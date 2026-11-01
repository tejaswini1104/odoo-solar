from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import ServiceTicket, Technician
from backend.app.schemas.schemas import (
    ServiceTicketCreate, ServiceTicketResponse, TicketAssignRequest,
    TicketQuoteDecision,
)
from backend.app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["Service Tickets"])

def _format_ticket(t: ServiceTicket) -> dict:
    return {
        "id": t.id,
        "customer_id": t.customer_id,
        "customer_name": t.customer.name if t.customer else None,
        "equipment_serial": t.equipment_serial,
        "installation_id": t.installation_id,
        "warranty_id": t.warranty_id,
        "replacement_serial": t.replacement_serial,
        "technician_id": t.technician_id,
        "technician_name": t.technician.name if t.technician else None,
        "inspection_notes": t.inspection_notes,
        "needs_replacement": t.needs_replacement,
        "quote_status": t.quote_status,
        "dispatch_serial": t.dispatch_serial,
        "title": t.title,
        "description": t.description,
        "priority": t.priority,
        "status": t.status,
        "service_type": t.service_type,
        "customer_charge": t.customer_charge,
        "customer_confirmed": t.customer_confirmed,
        "invoice_id": t.invoice_id,
        "created_at": t.created_at,
        "updated_at": t.updated_at
    }

@router.get("", response_model=List[ServiceTicketResponse])
def list_tickets(db: Session = Depends(get_db)):
    tickets = db.query(ServiceTicket).order_by(ServiceTicket.created_at.desc()).all()
    return [_format_ticket(t) for t in tickets]

@router.get("/technicians")
def list_ticket_technicians(db: Session = Depends(get_db)):
    """The technicians support can send to a customer."""
    return [{"id": t.id, "name": t.name, "phone": t.phone} for t in db.query(Technician).order_by(Technician.name).all()]

@router.post("", response_model=ServiceTicketResponse)
def create_ticket(ticket_in: ServiceTicketCreate, db: Session = Depends(get_db)):
    ticket = TicketService.create_ticket(db, ticket_in)
    return _format_ticket(ticket)

@router.get("/{id}", response_model=ServiceTicketResponse)
def get_ticket(id: int, db: Session = Depends(get_db)):
    t = db.query(ServiceTicket).filter(ServiceTicket.id == id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Service ticket not found")
    return _format_ticket(t)

@router.post("/{id}/assign", response_model=ServiceTicketResponse)
def assign_technician(id: int, payload: TicketAssignRequest, db: Session = Depends(get_db)):
    """Send a technician to the customer."""
    return _format_ticket(TicketService.assign_technician(db, id, payload.technician_id))

@router.post("/{id}/quote", response_model=ServiceTicketResponse)
def decide_quote(id: int, payload: TicketQuoteDecision, db: Session = Depends(get_db)):
    """The customer's answer to the quotation, recorded by support (customers answer themselves in the portal)."""
    return _format_ticket(TicketService.decide_quote(db, id, payload.approved))

@router.post("/{id}/resolve", response_model=ServiceTicketResponse)
def resolve_ticket(id: int, db: Session = Depends(get_db)):
    """Mark the repair done. A dispatched replacement is recorded as fitted."""
    return _format_ticket(TicketService.resolve_ticket(db, id))

@router.post("/{id}/customer-confirm", response_model=ServiceTicketResponse)
def customer_confirm_ticket(id: int, db: Session = Depends(get_db)):
    ticket = TicketService.customer_confirm_ticket(db, id)
    return _format_ticket(ticket)

@router.post("/{id}/close", response_model=ServiceTicketResponse)
def close_ticket(id: int, db: Session = Depends(get_db)):
    ticket = TicketService.close_ticket(db, id)
    return _format_ticket(ticket)
