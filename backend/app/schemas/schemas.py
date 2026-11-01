from pydantic import BaseModel, Field, field_validator, model_validator
from backend.app.core.validators import MAX_MONEY, SERIAL_PATTERN, clean_email, clean_phone, text_rule
from typing import List, Optional
from datetime import datetime, date

# ----------------- Customer Schemas -----------------
class CustomerBase(BaseModel):
    name: str
    phone: str
    email: str
    address: str
    city: str

class CustomerCreate(CustomerBase):
    _phone = field_validator("phone")(clean_phone)
    _email = field_validator("email")(clean_email)
    _name = field_validator("name")(text_rule("Name", 2, 255))
    _address = field_validator("address")(text_rule("Address", 5, 500))
    _city = field_validator("city")(text_rule("City", 2, 100))

class CustomerResponse(CustomerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------- Lead Schemas -----------------
class LeadBase(BaseModel):
    name: str
    phone: str
    email: str
    address: str
    city: str
    enquiry_source: str = "Web" # Web, WhatsApp, Call, Manual
    required_capacity: float
    monthly_electricity_bill: float
    roof_area: float
    grid_type: str = "On-Grid" # On-Grid, Off-Grid, Hybrid
    subsidy_requirement: bool = False
    lead_status: str = "New"

class LeadCreate(LeadBase):
    enquiry_source: str = Field(default="Manual", pattern="^(Web|WhatsApp|Call|Manual)$")
    required_capacity: float = Field(ge=1, le=5, description="kW, between 1 and 5")
    monthly_electricity_bill: float = Field(ge=0, le=MAX_MONEY)
    roof_area: float = Field(gt=0, le=100000, description="sq.ft")
    grid_type: str = Field(default="On-Grid", pattern="^(On-Grid|Off-Grid|Hybrid)$")
    lead_status: str = Field(default="New", pattern="^New$")  # a new enquiry always starts as New

    _phone = field_validator("phone")(clean_phone)
    _email = field_validator("email")(clean_email)
    _name = field_validator("name")(text_rule("Name", 2, 255))
    _address = field_validator("address")(text_rule("Address", 5, 500))
    _city = field_validator("city")(text_rule("City", 2, 100))

class LeadResponse(LeadBase):
    id: int
    customer_id: Optional[int] = None
    shadow_free_area: Optional[float] = None
    grid_connection_ok: Optional[bool] = None
    call_notes: Optional[str] = None
    contacted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------- Technician Schemas -----------------
class TechnicianBase(BaseModel):
    name: str
    phone: Optional[str] = None

class TechnicianCreate(TechnicianBase):
    pass

class TechnicianResponse(TechnicianBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------- Site Survey Schemas -----------------
class SiteSurveyBase(BaseModel):
    customer_id: Optional[int] = None
    lead_id: Optional[int] = None
    technician_id: Optional[int] = None
    technician_name: str
    # Empty while a visit is only scheduled. The technician fills these in on site.
    roof_area: Optional[float] = None
    roof_direction: Optional[str] = None # South, North, East, West, etc.
    roof_tilt: Optional[float] = None
    shading_level: Optional[str] = None # None, Low, Medium, High
    cable_distance: Optional[float] = None
    grid_suitability: Optional[str] = None # Suitable, Needs Upgrade, Unsuitable
    recommended_capacity: Optional[float] = None
    recommended_system_type: Optional[str] = None # On-Grid or Off-Grid
    scheduled_date: Optional[date] = None
    survey_notes: Optional[str] = None
    status: str = "Draft" # Scheduled, Draft, Submitted, Approved, Rejected

class SiteSurveyCreate(SiteSurveyBase):
    # A survey entered by hand is already measured, so these are required here, within believable ranges
    technician_name: str = Field(min_length=2, max_length=255)
    roof_area: float = Field(gt=0, le=100000)
    roof_direction: str = Field(pattern="^(North|North-East|East|South-East|South|South-West|West|North-West)$")
    roof_tilt: float = Field(ge=0, le=90)
    shading_level: str = Field(pattern="^(None|Low|Medium|High)$")
    cable_distance: float = Field(ge=0, le=1000)
    grid_suitability: str = Field(pattern="^(Suitable|Needs Upgrade|Unsuitable)$")
    recommended_capacity: float = Field(ge=1, le=5)
    recommended_system_type: Optional[str] = Field(default=None, pattern="^(On-Grid|Off-Grid)$")
    survey_notes: Optional[str] = Field(default=None, max_length=2000)
    # Approval is a separate step by someone else, so a survey cannot be created already approved
    status: str = Field(default="Draft", pattern="^(Draft|Submitted)$")

class SiteSurveyResponse(SiteSurveyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------- Product & Package Schemas -----------------
class ProductResponse(BaseModel):
    id: int
    name: str
    category: str
    unit: str
    cost_price: float
    unit_price: float
    is_serialized: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PackageComponentResponse(BaseModel):
    id: int
    product_id: int
    product: ProductResponse
    quantity: int

    class Config:
        from_attributes = True

class SolarPackageResponse(BaseModel):
    id: int
    name: str
    capacity_kw: float
    system_type: str
    description: Optional[str] = None
    base_price: float
    components: List[PackageComponentResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class BOMItemResponse(BaseModel):
    product_id: int
    product_name: str
    category: str
    unit: str
    quantity: int
    cost_price: float
    unit_price: float
    total_price: float
    is_serialized: bool

class BOMResponse(BaseModel):
    package_id: int
    package_name: str
    capacity_kw: float
    system_type: str
    items: List[BOMItemResponse]
    subtotal: float
    tax: float
    total: float

# ----------------- Quotation Schemas -----------------
class QuotationItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    quantity: int
    unit_price: float
    total_price: float

    class Config:
        from_attributes = True

class QuotationCreate(BaseModel):
    customer_id: int
    survey_id: int # Hard check: survey must be Approved!
    package_id: int
    # Needed only when the package differs from what the survey recommended
    override_reason: Optional[str] = Field(default=None, max_length=500)

class QuotationResponse(BaseModel):
    id: int
    customer_id: int
    customer_name: Optional[str] = None
    survey_id: int
    package_id: int
    package_name: Optional[str] = None
    subtotal: float
    tax: float
    total: float
    status: str
    items: List[QuotationItemResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------- Payment Schemas -----------------
class PaymentCreate(BaseModel):
    order_id: Optional[int] = None
    quotation_id: Optional[int] = None
    customer_id: int
    amount: float = Field(gt=0, le=MAX_MONEY)
    payment_type: str = Field(default="advance", pattern="^(advance|full|balance)$")
    reference_notes: Optional[str] = Field(default=None, max_length=500)

class PaymentResponse(BaseModel):
    id: int
    order_id: Optional[int] = None
    quotation_id: Optional[int] = None
    customer_id: int
    amount: float
    payment_date: datetime
    payment_type: str
    status: str
    invoice_id: Optional[int] = None
    reference_number: Optional[str] = None
    reference_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# ----------------- Sales Order Schemas -----------------
class SalesOrderResponse(BaseModel):
    id: int
    quotation_id: int
    customer_id: int
    customer_name: Optional[str] = None
    package_id: int
    package_name: Optional[str] = None
    total_amount: float
    status: str
    flat_labour_cost: float
    advance_paid: float = 0.0
    is_advance_paid: bool = False
    survey_approved: bool = False
    delivered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------- Inventory & Dispatch Schemas -----------------
class InventoryItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    category: str
    quantity_on_hand: int
    reserved_quantity: int
    available_quantity: int
    is_serialized: bool

    class Config:
        from_attributes = True

class EquipmentSerialResponse(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    category: Optional[str] = None
    serial_number: str
    status: str # In Stock, Reserved, Dispatched, Installed
    order_id: Optional[int] = None
    installation_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DispatchSerialsRequest(BaseModel):
    # Mapping of product_id -> list of serial numbers, or simply list of serial numbers
    serial_numbers: List[str] = Field(min_length=1, max_length=50)

# ----------------- Installation Schemas -----------------
class InstallationCompleteRequest(BaseModel):
    confirmed_system_size: float = Field(gt=0, le=50, description="kW")
    serial_numbers: List[str] = Field(default=[], max_length=50)
    start_time: Optional[datetime] = None
    finish_time: Optional[datetime] = None
    notes: Optional[str] = Field(default=None, max_length=2000)

class InstallationResponse(BaseModel):
    id: int
    sales_order_id: int
    customer_id: int
    customer_name: Optional[str] = None
    technician_id: Optional[int] = None
    technician_name: Optional[str] = None
    scheduled_date: date
    system_capacity: float
    confirmed_system_size: Optional[float] = None
    status: str # Scheduled, In Progress, Completed
    start_time: Optional[datetime] = None
    finish_time: Optional[datetime] = None
    notes: Optional[str] = None
    photo_count: int = 0
    signed_by_name: Optional[str] = None
    signed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------- Warranty Schemas -----------------
class WarrantyResponse(BaseModel):
    id: int
    customer_id: int
    customer_name: Optional[str] = None
    installation_id: int
    order_id: int
    product_id: int
    product_name: Optional[str] = None
    category: Optional[str] = None
    serial_number: Optional[str] = None
    warranty_type: str # serialized, bulk
    duration_months: int
    start_date: date
    end_date: date
    status: str # Active, Expired
    is_currently_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True

# ----------------- Invoice Schemas -----------------
class InvoiceItemResponse(BaseModel):
    id: int
    description: str
    quantity: int
    unit_price: float
    total: float

    class Config:
        from_attributes = True

class InvoiceItemCreate(BaseModel):
    description: str = Field(max_length=255)
    quantity: int = Field(default=1, ge=1, le=1000)
    unit_price: float = Field(ge=0, le=MAX_MONEY)

    _description = field_validator("description")(text_rule("Description", 2, 255))

class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    customer_id: int
    customer_name: Optional[str] = None
    order_id: Optional[int] = None
    ticket_id: Optional[int] = None
    subtotal: float
    tax: float
    total: float
    status: str # Draft, Sent, Paid
    items: List[InvoiceItemResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------- Service Ticket Schemas -----------------
class ServiceTicketCreate(BaseModel):
    customer_id: int
    # A serial-numbered unit is identified by its serial. The solar panels have no serial numbers, so a claim on them
    # names the bulk panel warranty instead.
    equipment_serial: Optional[str] = Field(default=None, min_length=3, max_length=100)
    warranty_id: Optional[int] = None
    title: str = Field(max_length=255)
    description: str = Field(max_length=2000)
    priority: str = Field(default="Medium", pattern="^(Low|Medium|High|Urgent)$")

    _serial = field_validator("equipment_serial")(text_rule("Serial number", 3, 100))
    _title = field_validator("title")(text_rule("Title", 3, 255))
    _description = field_validator("description")(text_rule("Description", 5, 2000))

    @model_validator(mode="after")
    def _one_identifier(self):
        if bool(self.equipment_serial) == (self.warranty_id is not None):
            raise ValueError("Give either the equipment serial number or the panel warranty, not both and not neither.")
        return self


class TicketAssignRequest(BaseModel):
    technician_id: int


class TicketInspectRequest(BaseModel):
    needs_replacement: bool
    notes: Optional[str] = Field(default=None, max_length=2000)


class TicketQuoteDecision(BaseModel):
    approved: bool


class TicketDispatchRequest(BaseModel):
    serial_number: Optional[str] = Field(default=None, min_length=3, max_length=100)

    _serial = field_validator("serial_number")(text_rule("Serial number", 3, 100))

class ServiceTicketResponse(BaseModel):
    id: int
    customer_id: int
    customer_name: Optional[str] = None
    equipment_serial: str
    installation_id: Optional[int] = None
    warranty_id: Optional[int] = None
    replacement_serial: Optional[str] = None
    technician_id: Optional[int] = None
    technician_name: Optional[str] = None
    inspection_notes: Optional[str] = None
    needs_replacement: Optional[bool] = None
    quote_status: Optional[str] = None
    dispatch_serial: Optional[str] = None
    title: str
    description: str
    priority: str
    status: str # Open, Assigned, Quotation Sent, In Progress, Dispatched, Resolved, Customer Confirmed, Closed
    service_type: str # COVERED, BILLABLE
    customer_charge: float
    customer_confirmed: bool
    invoice_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ----------------- Profitability Schemas -----------------
class OrderProfitabilityResponse(BaseModel):
    order_id: int
    customer_name: str
    package_name: str
    revenue: float
    amount_paid: float = 0.0
    balance_due: float = 0.0
    material_cost: float
    labour_cost: float
    total_cost: float
    profit: float
    profit_margin_pct: float
    status: str
    finished_on: Optional[date] = None
    labour_hours: Optional[float] = None
    labour_basis: str = ""

# ----------------- Dashboard Metrics -----------------
class DashboardMetricsResponse(BaseModel):
    total_leads: int
    pending_surveys: int
    confirmed_orders: int
    open_tickets: int
    active_warranties: int
