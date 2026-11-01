from datetime import date
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend.app.models.models import Installation, Technician, TechnicianPayout, User
from backend.app.services.profitability_service import day_bounds, job_hours


def _completed_jobs(db: Session, technician_id: int, start: date, end: date, paid: bool) -> List[Installation]:
    """Completed jobs the technician finished in the range, that have (paid) or have not (unpaid) been paid for."""
    low, high = day_bounds(start, end)
    query = db.query(Installation).filter(
        Installation.technician_id == technician_id,
        Installation.status == "Completed",
        Installation.finish_time.isnot(None),
        Installation.finish_time >= low,
        Installation.finish_time <= high,
    )
    query = query.filter(Installation.payout_id.isnot(None)) if paid else query.filter(Installation.payout_id.is_(None))
    return query.order_by(Installation.finish_time).all()


def _hours(jobs: List[Installation]) -> float:
    return round(sum(job_hours(job) or 0 for job in jobs), 2)


class PayrollService:
    @staticmethod
    def summary(db: Session, start: date, end: date) -> List[dict]:
        """For each technician: the hours and pay still owed for jobs finished in the range, and what was already paid."""
        rows = []
        for tech in db.query(Technician).order_by(Technician.name).all():
            unpaid = _completed_jobs(db, tech.id, start, end, paid=False)
            paid = _completed_jobs(db, tech.id, start, end, paid=True)
            if not unpaid and not paid:
                continue
            unpaid_hours = _hours(unpaid)
            paid_hours = _hours(paid)
            rows.append({
                "technician_id": tech.id,
                "technician_name": tech.name,
                "hourly_rate": tech.hourly_rate,
                "unpaid_jobs": len(unpaid),
                "unpaid_hours": unpaid_hours,
                "amount_due": round(unpaid_hours * tech.hourly_rate, 2),
                "paid_jobs": len(paid),
                "paid_hours": paid_hours,
                "jobs_without_hours": sum(1 for job in unpaid if job_hours(job) is None),
            })
        return rows

    @staticmethod
    def pay(db: Session, technician_id: int, start: date, end: date, reference: Optional[str], user: User) -> TechnicianPayout:
        """Record a payment for every unpaid completed job in the range. Each job is marked, so it cannot be paid twice."""
        tech = db.get(Technician, technician_id)
        if not tech:
            raise HTTPException(status_code=404, detail="Technician not found.")
        jobs = _completed_jobs(db, technician_id, start, end, paid=False)
        if not jobs:
            raise HTTPException(status_code=400, detail="There are no unpaid completed jobs in that period.")

        hours = _hours(jobs)
        amount = round(hours * tech.hourly_rate, 2)
        if amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="These jobs have no recorded hours, so there is nothing to pay. Check the start and finish times.",
            )

        payout = TechnicianPayout(
            technician_id=tech.id,
            period_start=start,
            period_end=end,
            jobs_count=len(jobs),
            hours=hours,
            hourly_rate=tech.hourly_rate,  # the rate is kept, so a later change does not rewrite what was paid
            amount=amount,
            reference=(reference or "").strip() or None,
            paid_by=user.id,
        )
        db.add(payout)
        db.flush()
        for job in jobs:
            job.payout_id = payout.id
        db.commit()
        db.refresh(payout)
        return payout
