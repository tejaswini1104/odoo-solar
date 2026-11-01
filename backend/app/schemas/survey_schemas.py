from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class SurveyScheduleRequest(BaseModel):
    customer_id: int
    lead_id: Optional[int] = None  # the enquiry this visit follows up, if any
    scheduled_date: date
    notes: Optional[str] = Field(default=None, max_length=1000)


class SurveyCompleteRequest(BaseModel):
    """What the technician records on site."""
    roof_area: float = Field(gt=0, le=100000, description="Shadow-free roof area, sq.ft")
    roof_direction: str = Field(pattern="^(North|North-East|East|South-East|South|South-West|West|North-West)$")
    roof_tilt: float = Field(ge=0, le=90, description="degrees")
    shading_level: str = Field(pattern="^(None|Low|Medium|High)$")
    cable_distance: float = Field(ge=0, le=1000, description="metres from panels to the inverter and meter")
    grid_suitability: str = Field(pattern="^(Suitable|Needs Upgrade|Unsuitable)$")
    recommended_capacity: float = Field(ge=1, le=5, description="kW")
    recommended_system_type: str = Field(pattern="^(On-Grid|Off-Grid)$")
    survey_notes: Optional[str] = Field(default=None, max_length=2000)


class SurveyReassignRequest(BaseModel):
    technician_id: int


class LeadStatusRequest(BaseModel):
    status: str = Field(pattern="^(New|Contacted|Lost)$")
    # The first call: roof space without shadow and whether the grid connection is suitable
    shadow_free_area: Optional[float] = Field(default=None, gt=0, description="sq.ft")
    grid_connection_ok: Optional[bool] = None
    call_notes: Optional[str] = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def contacted_needs_the_basics(self):
        if self.status == "Contacted" and (self.shadow_free_area is None or self.grid_connection_ok is None):
            raise ValueError("To mark a lead Contacted, record the shadow-free roof area and whether the grid connection is suitable.")
        return self
