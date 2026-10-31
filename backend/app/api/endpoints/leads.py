from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Lead, Customer
from backend.app.schemas.schemas import LeadCreate, LeadResponse, CustomerResponse

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
