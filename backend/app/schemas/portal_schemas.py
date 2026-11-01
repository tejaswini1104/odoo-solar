from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from backend.app.core.validators import MAX_MONEY, clean_phone, strong_password, text_rule


# ----------------- Auth -----------------
class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(max_length=50)
    password: str = Field(min_length=8, max_length=128)
    address: str = Field(min_length=5)
    city: str = Field(min_length=2, max_length=100)

    _phone = field_validator("phone")(clean_phone)
    _password = field_validator("password")(strong_password)
    _name = field_validator("name")(text_rule("Name", 2, 255))
    _address = field_validator("address")(text_rule("Address", 5, 500))
    _city = field_validator("city")(text_rule("City", 2, 100))


class LoginRequest(BaseModel):
    # Plain text on purpose: the sign-in lookup decides whether the account exists, not an email-format check
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    customer_id: Optional[int] = None


# ----------------- Portal catalogue -----------------
class CatalogPackage(BaseModel):
    id: int
    name: str
    capacity_kw: float
    system_type: str
    description: Optional[str] = None
    price_incl_gst: float  # customer price only; product cost prices are never exposed


# ----------------- Portal enquiries -----------------
class EnquiryCreate(BaseModel):
    required_capacity: float = Field(ge=1, le=5, description="kW, between 1 and 5")
    grid_type: str = Field(pattern="^(On-Grid|Off-Grid)$")
    monthly_electricity_bill: float = Field(ge=0, le=MAX_MONEY)
    roof_area: float = Field(gt=0, le=100000, description="sq.ft")
    subsidy_requirement: bool = False


class EnquiryResponse(BaseModel):
    id: int
    reference: str
    required_capacity: float
    grid_type: str
    monthly_electricity_bill: float
    roof_area: float
    subsidy_requirement: bool
    lead_status: str
    enquiry_source: str
    created_at: datetime


class EnquiryList(BaseModel):
    items: List[EnquiryResponse]
