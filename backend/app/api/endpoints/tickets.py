from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import ServiceTicket
from backend.app.schemas.schemas import ServiceTicketCreate, ServiceTicketResponse
from backend.app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["Service Tickets"])

def _format_ticket(t: ServiceTicket) -> dict:
    return {
        "id": t.id,
        "customer_id": t.customer_id,
        "customer_name": t.customer.name if t.customer else None,
        "equipment_serial": t.equipment_serial,
        "installation_id": t.installation_id,
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

@router.post("/{id}/resolve", response_model=ServiceTicketResponse)
def resolve_ticket(id: int, db: Session = Depends(get_db)):
    ticket = TicketService.resolve_ticket(db, id)
    return _format_ticket(ticket)

@router.post("/{id}/customer-confirm", response_model=ServiceTicketResponse)
def customer_confirm_ticket(id: int, db: Session = Depends(get_db)):
    ticket = TicketService.customer_confirm_ticket(db, id)
    return _format_ticket(ticket)

@router.post("/{id}/close", response_model=ServiceTicketResponse)
def close_ticket(id: int, db: Session = Depends(get_db)):
    ticket = TicketService.close_ticket(db, id)
    return _format_ticket(ticket)
