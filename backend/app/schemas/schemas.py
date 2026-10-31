from pydantic import BaseModel, Field
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
    pass

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
    pass

class LeadResponse(LeadBase):
    id: int
    customer_id: Optional[int] = None
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
    roof_area: float
    roof_direction: str # South, North, East, West, etc.
    roof_tilt: float
    shading_level: str # None, Low, Medium, High
    cable_distance: float
    grid_suitability: str # Suitable, Needs Upgrade, Unsuitable
    recommended_capacity: float
    survey_notes: Optional[str] = None
    status: str = "Draft" # Draft, Submitted, Approved, Rejected

class SiteSurveyCreate(SiteSurveyBase):
    pass

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
    amount: float
    payment_type: str = "advance" # advance, full
    reference_notes: Optional[str] = None

class PaymentResponse(BaseModel):
    id: int
    order_id: Optional[int] = None
    quotation_id: Optional[int] = None
    customer_id: int
    amount: float
    payment_date: datetime
    payment_type: str
    status: str
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
    serial_numbers: List[str]

# ----------------- Installation Schemas -----------------
class InstallationCompleteRequest(BaseModel):
    confirmed_system_size: float
    serial_numbers: List[str] = []
    finish_time: Optional[datetime] = None
    notes: Optional[str] = None

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
    description: str
    quantity: int = 1
    unit_price: float

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
    equipment_serial: str
    title: str
    description: str
    priority: str = "Medium" # Low, Medium, High, Urgent

class ServiceTicketResponse(BaseModel):
    id: int
    customer_id: int
    customer_name: Optional[str] = None
    equipment_serial: str
    installation_id: Optional[int] = None
    title: str
    description: str
    priority: str
    status: str # Open, Assigned, In Progress, Resolved, Customer Confirmed, Closed
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
    material_cost: float
    labour_cost: float
    total_cost: float
    profit: float
    profit_margin_pct: float
    status: str

# ----------------- Dashboard Metrics -----------------
class DashboardMetricsResponse(BaseModel):
    total_leads: int
    pending_surveys: int
    confirmed_orders: int
    open_tickets: int
    active_warranties: int
