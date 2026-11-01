from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Lead, Customer
from backend.app.schemas.schemas import LeadCreate, LeadResponse, CustomerResponse
from backend.app.schemas.survey_schemas import LeadStatusRequest

router = APIRouter(prefix="/leads", tags=["Leads"])

@router.get("", response_model=List[LeadResponse])
def list_leads(db: Session = Depends(get_db)):
    return db.query(Lead).order_by(Lead.created_at.desc()).all()

@router.post("", response_model=LeadResponse)
def create_lead(lead_in: LeadCreate, db: Session = Depends(get_db)):
    lead = Lead(**lead_in.dict())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead

@router.get("/{id}", response_model=LeadResponse)
def get_lead(id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.post("/{id}/convert", response_model=CustomerResponse)
def convert_lead_to_customer(id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.customer_id:
        existing_customer = db.query(Customer).filter(Customer.id == lead.customer_id).first()
        if existing_customer:
            return existing_customer

    # The same person may already be a customer (same phone or email): reuse that record instead of duplicating it
    customer = db.query(Customer).filter(
        (Customer.phone == lead.phone.strip()) | (func.lower(Customer.email) == lead.email.strip().lower())
    ).first()
    if customer:
        lead.customer_id = customer.id
        lead.lead_status = "Converted"
        db.commit()
        return customer

    # Create new customer from lead details
    customer = Customer(
        name=lead.name,
        phone=lead.phone,
        email=lead.email,
        address=lead.address,
        city=lead.city
    )
    db.add(customer)
    db.flush()

    lead.customer_id = customer.id
    lead.lead_status = "Converted"

    db.commit()
    db.refresh(customer)
    return customer


@router.post("/{id}/status", response_model=LeadResponse)
def set_lead_status(id: int, payload: LeadStatusRequest, db: Session = Depends(get_db)):
    """Sales note how far a lead has got: Contacted after the first call, Lost if it goes nowhere.

    Converting a lead to a customer, and scheduling a survey, set their own statuses.
    """
    lead = db.query(Lead).filter(Lead.id == id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.lead_status == "Converted":
        raise HTTPException(status_code=400, detail="This lead has already been converted to a customer.")
    lead.lead_status = payload.status
    if payload.status == "Contacted":
        lead.shadow_free_area = payload.shadow_free_area
        lead.grid_connection_ok = payload.grid_connection_ok
        lead.contacted_at = datetime.utcnow()
    if payload.call_notes is not None:
        lead.call_notes = payload.call_notes.strip() or None
    db.commit()
    db.refresh(lead)
    return lead
