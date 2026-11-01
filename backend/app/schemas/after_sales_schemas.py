from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field

BANK_REFERENCE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9/\-_. ]*$"


class PortalWarranty(BaseModel):
    id: int
    product_name: str
    category: str
    serial_number: Optional[str] = None  # empty for the bulk solar panel warranty
    warranty_type: str
    duration_months: int
    start_date: date
    end_date: date
    status: str                          # Active or Expired, worked out from today's date
    days_left: int


class PortalTicketCreate(BaseModel):
    equipment_serial: Optional[str] = Field(default=None, min_length=3, max_length=100)
    warranty_id: Optional[int] = None    # for a claim on the solar panels, which have no serial numbers
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=5)
    priority: str = Field(default="Medium", pattern="^(Low|Medium|High|Urgent)$")


class PortalQuoteDecision(BaseModel):
    approved: bool


class PortalInvoiceLine(BaseModel):
    description: str
    quantity: int
    unit_price: float
    total: float


class PortalTicket(BaseModel):
    id: int
    reference: str
    equipment_serial: str
    replacement_serial: Optional[str] = None
    technician_name: Optional[str] = None
    needs_replacement: Optional[bool] = None
    quote_status: Optional[str] = None
    quote_lines: List[PortalInvoiceLine] = []
    title: str
    description: str
    priority: str
    status: str
    service_type: str                    # COVERED or BILLABLE
    customer_charge: float
    customer_confirmed: bool
    invoice_id: Optional[int] = None
    created_at: datetime


class PortalInvoice(BaseModel):
    id: int
    invoice_number: str
    origin: str                          # for example "Service ticket TCK-0003" or "Installation order SO-0001"
    status: str                          # Sent or Paid
    items: List[PortalInvoiceLine]
    subtotal: float
    gst: float
    total: float
    paid_verified: float
    paid_pending: float
    payable_now: float


class InvoicePaymentSubmit(BaseModel):
    amount: float = Field(gt=0, le=10_000_000)
    reference_number: str = Field(min_length=4, max_length=100, pattern=BANK_REFERENCE_PATTERN)


class PortalInstallationPhoto(BaseModel):
    id: int
    caption: Optional[str] = None
    url: str


class PortalInstallation(BaseModel):
    id: int
    reference: str
    package_name: str
    status: str
    technician_name: Optional[str] = None
    scheduled_date: date
    start_time: Optional[datetime] = None
    finish_time: Optional[datetime] = None
    confirmed_system_size: Optional[float] = None
    delivered_at: Optional[datetime] = None
    signed_by_name: Optional[str] = None
    signed_at: Optional[datetime] = None
    signature_url: Optional[str] = None
    photos: List[PortalInstallationPhoto]
