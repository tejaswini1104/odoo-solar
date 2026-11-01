from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.api.deps import get_current_user, require_roles
from backend.app.core.database import get_db
from backend.app.core.roles import SALES, TECHNICIAN
from backend.app.models.models import SiteSurvey, Technician, User
from backend.app.schemas.schemas import SiteSurveyCreate, SiteSurveyResponse, TechnicianResponse
from backend.app.schemas.survey_schemas import SurveyCompleteRequest, SurveyReassignRequest, SurveyScheduleRequest
from backend.app.services.survey_service import SurveyService, is_measured

# Access by role is set where this router is included (api_router.py).
router = APIRouter(tags=["Site Surveys"])


def _visible_to(user: User, survey: SiteSurvey) -> bool:
    """A technician sees only their own surveys. Other roles with survey access see all of them."""
    return user.role != TECHNICIAN or survey.technician_id == user.technician_id


def _get_survey(db: Session, user: User, survey_id: int) -> SiteSurvey:
    survey = db.query(SiteSurvey).filter(SiteSurvey.id == survey_id).first()
    if not survey or not _visible_to(user, survey):
        raise HTTPException(status_code=404, detail="Site survey not found")
    return survey


@router.get("/surveys", response_model=List[SiteSurveyResponse])
def list_surveys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(SiteSurvey)
    if user.role == TECHNICIAN:
        query = query.filter(SiteSurvey.technician_id == user.technician_id)
    return query.order_by(SiteSurvey.created_at.desc()).all()

@router.post("/surveys", response_model=SiteSurveyResponse)
def create_survey(survey_in: SiteSurveyCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = survey_in.dict()
    if user.role == TECHNICIAN:
        # A technician's surveys are always recorded under their own name
        data["technician_id"] = user.technician_id
        data["technician_name"] = user.name
    survey = SiteSurvey(**data)
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey

@router.post("/surveys/schedule", response_model=SiteSurveyResponse, status_code=201)
def schedule_survey(
    payload: SurveyScheduleRequest,
    _user: User = Depends(require_roles(SALES)),  # Sales book the visit; the system picks the technician
    db: Session = Depends(get_db),
):
    return SurveyService.schedule(db, payload)

@router.get("/surveys/{id}", response_model=SiteSurveyResponse)
def get_survey(id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_survey(db, user, id)

@router.put("/surveys/{id}/complete", response_model=SiteSurveyResponse)
def complete_survey(
    id: int,
    payload: SurveyCompleteRequest,
    user: User = Depends(require_roles(TECHNICIAN)),  # only the technician on the visit records the findings
    db: Session = Depends(get_db),
):
    survey = _get_survey(db, user, id)
    return SurveyService.complete(db, survey, payload)

@router.post("/surveys/{id}/reassign", response_model=SiteSurveyResponse)
def reassign_survey(
    id: int,
    payload: SurveyReassignRequest,
    _user: User = Depends(require_roles(SALES)),
    db: Session = Depends(get_db),
):
    survey = db.query(SiteSurvey).filter(SiteSurvey.id == id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Site survey not found")
    return SurveyService.reassign(db, survey, payload.technician_id)

# Who may approve or reject a survey is on hold for now: it follows the survey access rule for the router.
@router.post("/surveys/{id}/approve", response_model=SiteSurveyResponse)
def approve_survey(id: int, db: Session = Depends(get_db)):
    survey = db.query(SiteSurvey).filter(SiteSurvey.id == id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Site survey not found")
    if survey.status == "Scheduled" or not is_measured(survey):
        raise HTTPException(
            status_code=400,
            detail="The technician has not recorded this survey yet, so it cannot be approved.",
        )

    survey.status = "Approved"
    db.commit()
    db.refresh(survey)
    return survey

@router.post("/surveys/{id}/reject", response_model=SiteSurveyResponse)
def reject_survey(id: int, db: Session = Depends(get_db)):
    survey = db.query(SiteSurvey).filter(SiteSurvey.id == id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Site survey not found")

    survey.status = "Rejected"
    db.commit()
    db.refresh(survey)
    return survey

@router.get("/technicians", response_model=List[TechnicianResponse])
def list_technicians(db: Session = Depends(get_db)):
    return db.query(Technician).all()
