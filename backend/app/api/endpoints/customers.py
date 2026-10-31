from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import Customer
from backend.app.schemas.schemas import CustomerCreate, CustomerResponse

router = APIRouter(prefix="/customers", tags=["Customers"])

@router.get("", response_model=List[CustomerResponse])
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).order_by(Customer.created_at.desc()).all()

@router.post("", response_model=CustomerResponse)
def create_customer(customer_in: CustomerCreate, db: Session = Depends(get_db)):
    customer = Customer(**customer_in.dict())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

@router.get("/{id}", response_model=CustomerResponse)
def get_customer(id: int, db: Session = Depends(get_db)):
    cust = db.query(Customer).filter(Customer.id == id).first()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    return cust
