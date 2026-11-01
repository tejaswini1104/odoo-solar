from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from backend.app.core.validators import clean_phone, strong_password, text_rule


class StaffCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(pattern="^(admin|sales|technician|support|warehouse)$")
    technician_id: Optional[int] = None  # technician role only: link to an existing technician record

    _password = field_validator("password")(strong_password)
    _name = field_validator("name")(text_rule("Name", 2, 255))

    @field_validator("phone")
    @classmethod
    def _phone(cls, value):
        # A blank phone box means "no phone"; anything typed must be a real number
        return clean_phone(value) if value and value.strip() else None


class StaffUserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    is_active: bool
    technician_id: Optional[int] = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    _new_password = field_validator("new_password")(strong_password)
