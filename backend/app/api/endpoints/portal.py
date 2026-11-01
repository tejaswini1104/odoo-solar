from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.api.deps import require_customer
from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.core.roles import SALES
from backend.app.services.notification_service import notify
from backend.app.models.models import Customer, Lead, SolarPackage, User
from backend.app.schemas.portal_schemas import CatalogPackage, EnquiryCreate, EnquiryResponse

router = APIRouter(prefix="/portal", tags=["Customer Portal"])

def _enquiry_out(lead: Lead) -> EnquiryResponse:
    return EnquiryResponse(
        id=lead.id,
        reference=f"ENQ-{lead.id:05d}",
        required_capacity=lead.required_capacity,
        grid_type=lead.grid_type,
        monthly_electricity_bill=lead.monthly_electricity_bill,
        roof_area=lead.roof_area,
        subsidy_requirement=lead.subsidy_requirement,
        lead_status=lead.lead_status,
        enquiry_source=lead.enquiry_source,
        created_at=lead.created_at,
    )


@router.get("/packages", response_model=List[CatalogPackage])
def list_packages_for_customers(db: Session = Depends(get_db)):
    """Public package catalogue. Shows the customer price (BOM at unit price + GST), never cost_price."""
    packages = db.query(SolarPackage).order_by(SolarPackage.capacity_kw, SolarPackage.system_type).all()
    result = []
    for pkg in packages:
        subtotal = sum(comp.quantity * comp.product.unit_price for comp in pkg.components)
        result.append(CatalogPackage(
            id=pkg.id,
            name=pkg.name,
            capacity_kw=pkg.capacity_kw,
            system_type=pkg.system_type,
            description=pkg.description,
            price_incl_gst=round(subtotal * (1 + settings.GST_PERCENT / 100), 2),
        ))
    return result


@router.get("/enquiries", response_model=List[EnquiryResponse])
def my_enquiries(user: User = Depends(require_customer), db: Session = Depends(get_db)):
    leads = (
        db.query(Lead)
        .filter(Lead.customer_id == user.customer_id)
        .order_by(Lead.created_at.desc())
        .all()
    )
    return [_enquiry_out(lead) for lead in leads]


@router.post("/enquiries", response_model=EnquiryResponse, status_code=201)
def create_enquiry(
    payload: EnquiryCreate,
    user: User = Depends(require_customer),
    db: Session = Depends(get_db),
):
    customer = db.query(Customer).filter(Customer.id == user.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Your customer record could not be found.")

    # The lead is built from the signed-in customer's own record. The request cannot set the name, email or source.
    lead = Lead(
        name=customer.name,
        phone=customer.phone,
        email=customer.email,
        address=customer.address,
        city=customer.city,
        enquiry_source="Web",
        required_capacity=payload.required_capacity,
        monthly_electricity_bill=payload.monthly_electricity_bill,
        roof_area=payload.roof_area,
        grid_type=payload.grid_type,
        subsidy_requirement=payload.subsidy_requirement,
        lead_status="New",
        customer_id=customer.id,
    )
    db.add(lead)
    notify(
        db, f"New enquiry from {customer.name}",
        f"{payload.required_capacity:g} kW, {customer.city}. Call them to check roof space, bill and grid.",
        link="leads", role=SALES,
    )
    db.commit()
    db.refresh(lead)
    return _enquiry_out(lead)
