from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user
from backend.app.core.clock import business_today
from backend.app.core.csv_export import csv_response
from backend.app.core.database import get_db
from backend.app.models.models import Technician, TechnicianPayout, User
from backend.app.services.payroll_service import PayrollService

# Administrator only: the access rule is applied where the router is included (api_router.py)
router = APIRouter(prefix="/payroll", tags=["Payroll"])


class PayoutRequest(BaseModel):
    technician_id: int
    from_date: date
    to_date: date
    reference: Optional[str] = Field(default=None, max_length=100)


class RateRequest(BaseModel):
    hourly_rate: float = Field(gt=0, le=5000)


def _month_start(today: date) -> date:
    return today.replace(day=1)


def _range(start: Optional[date], end: Optional[date]):
    end = end or business_today()
    start = start or _month_start(end)
    if start > end:
        raise HTTPException(status_code=400, detail="The start date is after the end date.")
    if (end - start).days > 366:
        raise HTTPException(status_code=400, detail="Please choose a period of a year or less.")
    return start, end


def _payout_out(payout: TechnicianPayout) -> dict:
    return {
        "id": payout.id,
        "technician_id": payout.technician_id,
        "technician_name": payout.technician.name if payout.technician else None,
        "period_start": payout.period_start,
        "period_end": payout.period_end,
        "jobs_count": payout.jobs_count,
        "hours": payout.hours,
        "hourly_rate": payout.hourly_rate,
        "amount": payout.amount,
        "reference": payout.reference,
        "paid_on": payout.paid_on,
    }


@router.get("/summary")
def payroll_summary(
    from_date: Optional[date] = Query(default=None, alias="from"),
    to_date: Optional[date] = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
):
    start, end = _range(from_date, to_date)
    rows = PayrollService.summary(db, start, end)
    return {
        "from": start,
        "to": end,
        "rows": rows,
        "total_due": round(sum(r["amount_due"] for r in rows), 2),
        "total_hours": round(sum(r["unpaid_hours"] for r in rows), 2),
    }


@router.get("/summary.csv")
def payroll_summary_csv(
    from_date: Optional[date] = Query(default=None, alias="from"),
    to_date: Optional[date] = Query(default=None, alias="to"),
    db: Session = Depends(get_db),
):
    start, end = _range(from_date, to_date)
    rows = PayrollService.summary(db, start, end)
    return csv_response(
        f"technician-pay-{start}-to-{end}.csv",
        ["Technician", "Hourly rate", "Unpaid jobs", "Unpaid hours", "Amount due", "Paid jobs", "Paid hours"],
        [[r["technician_name"], r["hourly_rate"], r["unpaid_jobs"], r["unpaid_hours"], r["amount_due"], r["paid_jobs"], r["paid_hours"]] for r in rows],
    )


@router.post("/payouts", status_code=201)
def create_payout(payload: PayoutRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.from_date > payload.to_date:
        raise HTTPException(status_code=400, detail="The start date is after the end date.")
    payout = PayrollService.pay(db, payload.technician_id, payload.from_date, payload.to_date, payload.reference, user)
    return _payout_out(payout)


@router.get("/payouts")
def list_payouts(technician_id: Optional[int] = None, db: Session = Depends(get_db)) -> List[dict]:
    query = db.query(TechnicianPayout)
    if technician_id:
        query = query.filter(TechnicianPayout.technician_id == technician_id)
    return [_payout_out(p) for p in query.order_by(TechnicianPayout.paid_on.desc()).limit(200).all()]


@router.get("/payouts.csv")
def payouts_csv(db: Session = Depends(get_db)):
    payouts = db.query(TechnicianPayout).order_by(TechnicianPayout.paid_on.desc()).all()
    return csv_response(
        "technician-payouts.csv",
        ["Paid on", "Technician", "Period start", "Period end", "Jobs", "Hours", "Hourly rate", "Amount", "Reference"],
        [[p.paid_on.date(), p.technician.name, p.period_start, p.period_end, p.jobs_count, p.hours, p.hourly_rate, p.amount, p.reference or ""] for p in payouts],
    )


@router.put("/technicians/{technician_id}/rate")
def set_rate(technician_id: int, payload: RateRequest, db: Session = Depends(get_db)):
    tech = db.get(Technician, technician_id)
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found.")
    tech.hourly_rate = payload.hourly_rate
    db.commit()
    return {"technician_id": tech.id, "technician_name": tech.name, "hourly_rate": tech.hourly_rate}
