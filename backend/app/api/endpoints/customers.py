from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.clock import business_today
from backend.app.models.models import Customer, EquipmentSerial, SalesOrder, Warranty
from backend.app.schemas.schemas import CustomerCreate, CustomerResponse

router = APIRouter(prefix="/customers", tags=["Customers"])

@router.get("", response_model=List[CustomerResponse])
def list_customers(db: Session = Depends(get_db)):
    return db.query(Customer).order_by(Customer.created_at.desc()).all()

@router.get("/search")
def search_customers(q: str, db: Session = Depends(get_db)):
    """Find a customer by name, phone, email, city or address, or by the serial number on their equipment."""
    term = q.strip()
    if len(term) < 2:
        return []
    like = f"%{term}%"
    by_serial = (
        db.query(SalesOrder.customer_id)
        .join(EquipmentSerial, EquipmentSerial.order_id == SalesOrder.id)
        .filter(EquipmentSerial.serial_number.ilike(like))
    )
    customers = (
        db.query(Customer)
        .filter(or_(
            Customer.name.ilike(like), Customer.phone.ilike(like), Customer.email.ilike(like),
            Customer.city.ilike(like), Customer.address.ilike(like), Customer.id.in_(by_serial),
        ))
        .order_by(Customer.name)
        .limit(15)
        .all()
    )
    today = business_today()
    result = []
    for customer in customers:
        equipment = []
        serials = (
            db.query(EquipmentSerial)
            .join(SalesOrder, EquipmentSerial.order_id == SalesOrder.id)
            .filter(SalesOrder.customer_id == customer.id)
            .all()
        )
        for serial in serials:
            if serial.status == "Replaced":
                continue  # swapped out in a repair; its replacement is listed instead
            warranty = (
                db.query(Warranty).filter(Warranty.serial_number == serial.serial_number)
                .order_by(Warranty.created_at.desc()).first()
            )
            equipment.append({
                "serial_number": serial.serial_number,
                "product_name": serial.product.name,
                "category": serial.product.category,
                "status": serial.status,
                "warranty_end": warranty.end_date if warranty else None,
                "under_warranty": bool(warranty and warranty.start_date <= today <= warranty.end_date),
            })
        # The panels have no serial numbers, so each order's panels are claimed through their bulk warranty
        for panel in db.query(Warranty).filter(Warranty.customer_id == customer.id, Warranty.warranty_type == "bulk").all():
            equipment.append({
                "serial_number": None,
                "warranty_id": panel.id,
                "product_name": f"{panel.product.name} (order SO-{panel.order_id:04d})",
                "category": panel.product.category,
                "status": "Installed",
                "warranty_end": panel.end_date,
                "under_warranty": panel.start_date <= today <= panel.end_date,
            })
        result.append({
            "id": customer.id, "name": customer.name, "phone": customer.phone,
            "address": f"{customer.address}, {customer.city}", "equipment": equipment,
        })
    return result

@router.post("", response_model=CustomerResponse)
def create_customer(customer_in: CustomerCreate, db: Session = Depends(get_db)):
    phone = customer_in.phone.strip()
    email = customer_in.email.strip().lower()
    duplicate = db.query(Customer).filter(
        (Customer.phone == phone) | (func.lower(Customer.email) == email)
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail=f"A customer with this phone or email already exists: {duplicate.name} (customer #{duplicate.id}).",
        )
    data = customer_in.dict()
    data["phone"], data["email"] = phone, email
    customer = Customer(**data)
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
