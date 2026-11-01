from typing import Dict, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.core.roles import TECHNICIAN
from backend.app.models.models import Installation, SiteSurvey, Technician, User

# An installation takes far longer than a survey visit, so it weighs more when sharing out work.
SURVEY_WEIGHT = 1
INSTALLATION_WEIGHT = 3
OPEN_SURVEY_STATUSES = ("Scheduled", "Draft")


def technician_workload(db: Session) -> Dict[int, int]:
    """Points of open work per technician: open surveys and open (not completed) installations."""
    load: Dict[int, int] = {}

    surveys = (
        db.query(SiteSurvey.technician_id, func.count(SiteSurvey.id))
        .filter(SiteSurvey.status.in_(OPEN_SURVEY_STATUSES), SiteSurvey.technician_id.isnot(None))
        .group_by(SiteSurvey.technician_id)
        .all()
    )
    for technician_id, count in surveys:
        load[technician_id] = load.get(technician_id, 0) + count * SURVEY_WEIGHT

    installations = (
        db.query(Installation.technician_id, func.count(Installation.id))
        .filter(Installation.status != "Completed", Installation.technician_id.isnot(None))
        .group_by(Installation.technician_id)
        .all()
    )
    for technician_id, count in installations:
        load[technician_id] = load.get(technician_id, 0) + count * INSTALLATION_WEIGHT

    return load


def technicians_with_login(db: Session):
    """Technician records whose account is active. Only they can see the work they are given."""
    return (
        db.query(Technician)
        .join(User, User.technician_id == Technician.id)
        .filter(User.role == TECHNICIAN, User.is_active.is_(True))
        .order_by(Technician.id)
        .all()
    )


def pick_technician(db: Session) -> Optional[Technician]:
    """The technician with the least open work. Ties go to the lower id.

    Technicians who can sign in are preferred, because someone without a login cannot see the job.
    If nobody has a login yet, every technician record is considered, so work is still assigned.
    """
    candidates = technicians_with_login(db) or db.query(Technician).order_by(Technician.id).all()
    if not candidates:
        return None
    load = technician_workload(db)
    return min(candidates, key=lambda t: (load.get(t.id, 0), t.id))
