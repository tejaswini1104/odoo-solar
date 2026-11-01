from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user
from backend.app.core.database import get_db
from backend.app.models.models import SalesOrder, SubsidyApplication, User
from backend.app.services.subsidy_service import SubsidyService

# Access by role is set where this router is included (api_router.py).
router = APIRouter(prefix="/subsidies", tags=["Subsidy tracking"])


class SubsidyOpen(BaseModel):
    order_id: int


class SubsidyUpdate(BaseModel):
    status: Optional[str] = Field(default=None, pattern="^(Documents collected|Applied|Approved|Disbursed|Rejected)$")
    reference_number: Optional[str] = Field(default=None, max_length=100)
    expected_amount: Optional[float] = Field(default=None, ge=0, le=10_000_000)
    received_amount: Optional[float] = Field(default=None, ge=0, le=10_000_000)
    note: Optional[str] = Field(default=None, max_length=1000)


def _out(app: SubsidyApplication) -> dict:
    return {
        "id": app.id,
        "order_id": app.order_id,
        "customer_id": app.customer_id,
        "customer_name": app.customer.name if app.customer else None,
        "package_name": app.order.package.name if app.order and app.order.package else None,
        "status": app.status,
        "reference_number": app.reference_number,
        "expected_amount": app.expected_amount,
        "received_amount": app.received_amount,
        "applied_on": app.applied_on,
        "approved_on": app.approved_on,
        "disbursed_on": app.disbursed_on,
        "created_at": app.created_at,
        "events": [
            {"status": e.status, "note": e.note, "at": e.created_at}
            for e in sorted(app.events, key=lambda e: e.id)
        ],
    }


@router.get("")
def list_subsidies(db: Session = Depends(get_db)) -> List[dict]:
    apps = db.query(SubsidyApplication).order_by(SubsidyApplication.created_at.desc()).all()
    return [_out(a) for a in apps]


@router.post("", status_code=201)
def open_subsidy(payload: SubsidyOpen, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    order = db.query(SalesOrder).filter(SalesOrder.id == payload.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    if db.query(SubsidyApplication).filter(SubsidyApplication.order_id == order.id).first():
        raise HTTPException(status_code=409, detail="This order already has a subsidy file.")
    application = SubsidyService.open_for_order(db, order, user=user, force=True)
    db.commit()
    db.refresh(application)
    return _out(application)


@router.put("/{subsidy_id}")
def update_subsidy(
    subsidy_id: int,
    payload: SubsidyUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    application = db.query(SubsidyApplication).filter(SubsidyApplication.id == subsidy_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Subsidy file not found.")
    updated = SubsidyService.update(
        db, application, user,
        status=payload.status,
        reference_number=payload.reference_number,
        expected_amount=payload.expected_amount,
        received_amount=payload.received_amount,
        note=payload.note,
    )
    return _out(updated)
