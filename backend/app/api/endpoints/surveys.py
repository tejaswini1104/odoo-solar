from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.models.models import SiteSurvey, Technician
from backend.app.schemas.schemas import SiteSurveyCreate, SiteSurveyResponse, TechnicianResponse

router = APIRouter(tags=["Site Surveys"])

@router.get("/surveys", response_model=List[SiteSurveyResponse])
def list_surveys(db: Session = Depends(get_db)):
    return db.query(SiteSurvey).order_by(SiteSurvey.created_at.desc()).all()

@router.post("/surveys", response_model=SiteSurveyResponse)
def create_survey(survey_in: SiteSurveyCreate, db: Session = Depends(get_db)):
    survey = SiteSurvey(**survey_in.dict())
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey

@router.get("/surveys/{id}", response_model=SiteSurveyResponse)
def get_survey(id: int, db: Session = Depends(get_db)):
    survey = db.query(SiteSurvey).filter(SiteSurvey.id == id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Site survey not found")
    return survey

@router.post("/surveys/{id}/approve", response_model=SiteSurveyResponse)
def approve_survey(id: int, db: Session = Depends(get_db)):
    survey = db.query(SiteSurvey).filter(SiteSurvey.id == id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Site survey not found")
    
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
