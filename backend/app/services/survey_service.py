from datetime import date
from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend.app.core.clock import business_today
from backend.app.models.models import Customer, Lead, SiteSurvey, Technician
from backend.app.schemas.survey_schemas import SurveyCompleteRequest, SurveyScheduleRequest
from backend.app.core.roles import SALES
from backend.app.services.assignment_service import pick_technician
from backend.app.services.notification_service import notify

OPEN_SURVEY_STATUSES = ("Scheduled", "Draft", "Submitted")
MEASUREMENT_FIELDS = (
    "roof_area", "roof_direction", "roof_tilt", "shading_level",
    "cable_distance", "grid_suitability", "recommended_capacity",
)


def is_measured(survey: SiteSurvey) -> bool:
    return all(getattr(survey, field) is not None for field in MEASUREMENT_FIELDS)


class SurveyService:
    @staticmethod
    def schedule(db: Session, payload: SurveyScheduleRequest) -> SiteSurvey:
        """Book a site visit and give it to the technician with the least open work."""
        customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found.")
        if payload.scheduled_date < business_today():
            raise HTTPException(status_code=400, detail="The survey date cannot be in the past.")

        booked = (
            db.query(SiteSurvey)
            .filter(SiteSurvey.customer_id == customer.id, SiteSurvey.status == "Scheduled")
            .first()
        )
        if booked:
            raise HTTPException(
                status_code=409,
                detail=f"A survey is already scheduled for {customer.name} on {booked.scheduled_date}.",
            )

        lead = None
        if payload.lead_id:
            lead = db.query(Lead).filter(Lead.id == payload.lead_id).first()
            if not lead:
                raise HTTPException(status_code=404, detail="Lead not found.")
        else:
            lead = (
                db.query(Lead)
                .filter(Lead.customer_id == customer.id)
                .order_by(Lead.created_at.desc())
                .first()
            )

        if lead and lead.lead_status == "New":
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Call {lead.name} first. Mark the enquiry Contacted after checking the shadow-free roof space "
                    "and the grid connection, then book the survey."
                ),
            )
        if lead and lead.lead_status == "Lost":
            raise HTTPException(status_code=400, detail="This enquiry is marked Lost, so no survey can be booked for it.")
        if lead and lead.grid_connection_ok is False:
            raise HTTPException(
                status_code=400,
                detail="The grid connection was found unsuitable on the first call. Mark the enquiry Lost or update it before booking a survey.",
            )

        technician = pick_technician(db)
        if not technician:
            raise HTTPException(status_code=400, detail="No technician is available to take this survey.")

        survey = SiteSurvey(
            customer_id=customer.id,
            lead_id=lead.id if lead else None,
            technician_id=technician.id,
            technician_name=technician.name,
            scheduled_date=payload.scheduled_date,
            survey_notes=payload.notes,
            status="Scheduled",
        )
        db.add(survey)
        # A lead that is still being worked moves to "Survey Scheduled". A converted lead stays converted.
        if lead and lead.lead_status in ("New", "Contacted"):
            lead.lead_status = "Survey Scheduled"
        notify(
            db, f"Survey visit booked for {survey.scheduled_date}", f"{customer.name}, {customer.address}.",
            link="surveys", technician_id=technician.id,
        )
        db.commit()
        db.refresh(survey)
        return survey

    @staticmethod
    def complete(db: Session, survey: SiteSurvey, payload: SurveyCompleteRequest) -> SiteSurvey:
        """The technician records the measurements. The survey then waits for approval."""
        if survey.status not in ("Scheduled", "Draft"):
            raise HTTPException(
                status_code=400,
                detail=f"This survey is '{survey.status}' and can no longer be edited.",
            )
        for field, value in payload.model_dump().items():
            setattr(survey, field, value)
        survey.status = "Submitted"
        notify(
            db, f"Survey SURV-{survey.id:04d} is ready for approval", "The technician has recorded the measurements.",
            link="surveys", role=SALES,
        )
        db.commit()
        db.refresh(survey)
        return survey

    @staticmethod
    def reassign(db: Session, survey: SiteSurvey, technician_id: int) -> SiteSurvey:
        if survey.status != "Scheduled":
            raise HTTPException(status_code=400, detail="Only a scheduled survey can be reassigned.")
        technician = db.get(Technician, technician_id)
        if not technician:
            raise HTTPException(status_code=404, detail="Technician not found.")
        survey.technician_id = technician.id
        survey.technician_name = technician.name
        db.commit()
        db.refresh(survey)
        return survey
