from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Text, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    email = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)

    leads = relationship("Lead", back_populates="customer")
    surveys = relationship("SiteSurvey", back_populates="customer")
    quotations = relationship("Quotation", back_populates="customer")
    orders = relationship("SalesOrder", back_populates="customer")
    installations = relationship("Installation", back_populates="customer")
    warranties = relationship("Warranty", back_populates="customer")
    tickets = relationship("ServiceTicket", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")

class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    email = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    enquiry_source = Column(String(50), nullable=False) # Web, WhatsApp, Call, Manual
    required_capacity = Column(Float, nullable=False)   # in kW
    monthly_electricity_bill = Column(Float, nullable=False)
    roof_area = Column(Float, nullable=False)           # sq.ft
    grid_type = Column(String(50), nullable=False)      # On-Grid, Off-Grid, Hybrid
    subsidy_requirement = Column(Boolean, default=False, nullable=False)
    lead_status = Column(String(50), default="New", nullable=False) # New, Contacted, Survey Scheduled, Converted, Lost
    # What sales learn on the first call, before a technician is sent
    shadow_free_area = Column(Float, nullable=True)         # sq.ft of roof with no shadow
    grid_connection_ok = Column(Boolean, nullable=True)     # is the grid connection suitable
    call_notes = Column(Text, nullable=True)
    contacted_at = Column(DateTime, nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)

    customer = relationship("Customer", back_populates="leads")
    surveys = relationship("SiteSurvey", back_populates="lead")

class Technician(Base, TimestampMixin):
    __tablename__ = "technicians"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    hourly_rate = Column(Float, nullable=False, default=250.0) # rupees per hour worked on installations

    surveys = relationship("SiteSurvey", back_populates="technician")
    installations = relationship("Installation", back_populates="technician")
    payouts = relationship("TechnicianPayout", back_populates="technician")

class SiteSurvey(Base, TimestampMixin):
    __tablename__ = "site_surveys"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=True)
    technician_name = Column(String(255), nullable=False)
    # The measurements stay empty while a visit is only scheduled. The technician fills them in on site.
    roof_area = Column(Float, nullable=True)
    roof_direction = Column(String(50), nullable=True) # South, North, East, West, etc.
    roof_tilt = Column(Float, nullable=True)           # degrees
    shading_level = Column(String(50), nullable=True)  # None, Low, Medium, High
    cable_distance = Column(Float, nullable=True)      # meters
    grid_suitability = Column(String(50), nullable=True) # Suitable, Needs Upgrade, Unsuitable
    recommended_capacity = Column(Float, nullable=True)# in kW
    recommended_system_type = Column(String(50), nullable=True) # On-Grid or Off-Grid
    scheduled_date = Column(Date, nullable=True)
    survey_notes = Column(Text, nullable=True)
    status = Column(String(50), default="Draft", nullable=False) # Scheduled, Draft, Submitted, Approved, Rejected

    customer = relationship("Customer", back_populates="surveys")
    lead = relationship("Lead", back_populates="surveys")
    technician = relationship("Technician", back_populates="surveys")
    quotations = relationship("Quotation", back_populates="survey")

class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False) # Solar Panels, Inverter, Battery, Charge Controller, Wiring/Cables, Wiring Boxes/Switches, Mounting Stands, Earthing/Safety, Installation Service
    unit = Column(String(50), nullable=False, default="Nos") # Nos, Meters, Set
    cost_price = Column(Float, nullable=False, default=0.0)
    unit_price = Column(Float, nullable=False, default=0.0)
    is_serialized = Column(Boolean, default=False, nullable=False)

    package_components = relationship("PackageComponent", back_populates="product")
    inventory = relationship("InventoryItem", back_populates="product", uselist=False)
    serials = relationship("EquipmentSerial", back_populates="product")

class SolarPackage(Base, TimestampMixin):
    __tablename__ = "solar_packages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    capacity_kw = Column(Float, nullable=False)
    system_type = Column(String(50), nullable=False) # On-Grid, Off-Grid
    description = Column(Text, nullable=True)
    base_price = Column(Float, nullable=False, default=0.0)

    components = relationship("PackageComponent", back_populates="package", cascade="all, delete-orphan")
    quotations = relationship("Quotation", back_populates="package")
    orders = relationship("SalesOrder", back_populates="package")

class PackageComponent(Base, TimestampMixin):
    __tablename__ = "package_components"

    id = Column(Integer, primary_key=True, index=True)
    package_id = Column(Integer, ForeignKey("solar_packages.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)

    package = relationship("SolarPackage", back_populates="components")
    product = relationship("Product", back_populates="package_components")

class InventoryItem(Base, TimestampMixin):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), unique=True, nullable=False)
    quantity_on_hand = Column(Integer, nullable=False, default=0)
    reserved_quantity = Column(Integer, nullable=False, default=0)

    product = relationship("Product", back_populates="inventory")

class EquipmentSerial(Base, TimestampMixin):
    __tablename__ = "equipment_serials"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    # Unique constraint on serial numbers at DB level:
    serial_number = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(String(50), default="In Stock", nullable=False) # In Stock, Reserved, Dispatched, Installed, Replaced
    order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=True)
    installation_id = Column(Integer, ForeignKey("installations.id"), nullable=True)

    product = relationship("Product", back_populates="serials")
    order = relationship("SalesOrder", back_populates="dispatched_serials")
    installation = relationship("Installation", back_populates="serials")

class Quotation(Base, TimestampMixin):
    __tablename__ = "quotations"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    survey_id = Column(Integer, ForeignKey("site_surveys.id"), nullable=False) # REQUIRED! Checked in service layer
    package_id = Column(Integer, ForeignKey("solar_packages.id"), nullable=False)
    subtotal = Column(Float, nullable=False, default=0.0)
    tax = Column(Float, nullable=False, default=0.0) # GST 18% or calculated
    total = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), default="Draft", nullable=False) # Draft, Sent, Accepted, Cancelled
    override_reason = Column(Text, nullable=True) # why the package differs from the survey's recommendation

    customer = relationship("Customer", back_populates="quotations")
    survey = relationship("SiteSurvey", back_populates="quotations")
    package = relationship("SolarPackage", back_populates="quotations")
    items = relationship("QuotationItem", back_populates="quotation", cascade="all, delete-orphan")
    sales_order = relationship("SalesOrder", back_populates="quotation", uselist=False)
    payments = relationship("Payment", back_populates="quotation")

class QuotationItem(Base, TimestampMixin):
    __tablename__ = "quotation_items"

    id = Column(Integer, primary_key=True, index=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False, default=0.0)
    total_price = Column(Float, nullable=False, default=0.0)

    quotation = relationship("Quotation", back_populates="items")
    product = relationship("Product")

class SalesOrder(Base, TimestampMixin):
    __tablename__ = "sales_orders"

    id = Column(Integer, primary_key=True, index=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    package_id = Column(Integer, ForeignKey("solar_packages.id"), nullable=False)
    total_amount = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), default="Draft", nullable=False) # Draft, Pending Confirmation, Confirmed, Dispatched, Completed, Cancelled
    flat_labour_cost = Column(Float, nullable=False, default=5000.0) # Default labour cost for profitability
    delivered_at = Column(DateTime, nullable=True) # when the delivery was confirmed; the warranty clock starts here

    quotation = relationship("Quotation", back_populates="sales_order")
    customer = relationship("Customer", back_populates="orders")
    package = relationship("SolarPackage", back_populates="orders")
    payments = relationship("Payment", back_populates="order")
    installation = relationship("Installation", back_populates="sales_order", uselist=False)
    dispatched_serials = relationship("EquipmentSerial", back_populates="order")
    warranties = relationship("Warranty", back_populates="order")
    invoices = relationship("Invoice", back_populates="order")

class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=True)
    quotation_id = Column(Integer, ForeignKey("quotations.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    payment_type = Column(String(50), nullable=False) # advance, full
    status = Column(String(50), default="Recorded", nullable=False) # Pending Verification (customer reported), Verified, Recorded (legacy)
    reference_number = Column(String(100), unique=True, nullable=True, index=True) # bank transfer reference from the customer
    reference_notes = Column(Text, nullable=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True) # set when the payment is for a service invoice

    order = relationship("SalesOrder", back_populates="payments")
    quotation = relationship("Quotation", back_populates="payments")
    customer = relationship("Customer")

class Installation(Base, TimestampMixin):
    __tablename__ = "installations"

    id = Column(Integer, primary_key=True, index=True)
    sales_order_id = Column(Integer, ForeignKey("sales_orders.id"), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=True)
    scheduled_date = Column(Date, nullable=False)
    system_capacity = Column(Float, nullable=False) # from package kW
    confirmed_system_size = Column(Float, nullable=True) # captured on completion
    status = Column(String(50), default="Scheduled", nullable=False) # Scheduled, In Progress, Completed
    start_time = Column(DateTime, nullable=True)
    finish_time = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    # The homeowner accepts the finished work by signing on the technician's screen
    signed_by_name = Column(String(255), nullable=True)
    signed_at = Column(DateTime, nullable=True)
    signature_path = Column(String(500), nullable=True) # file under the private media folder
    payout_id = Column(Integer, ForeignKey("technician_payouts.id"), nullable=True) # set once the technician has been paid for this job

    sales_order = relationship("SalesOrder", back_populates="installation")
    customer = relationship("Customer", back_populates="installations")
    technician = relationship("Technician", back_populates="installations")
    serials = relationship("EquipmentSerial", back_populates="installation")
    warranties = relationship("Warranty", back_populates="installation")
    tickets = relationship("ServiceTicket", back_populates="installation")
    photos = relationship("InstallationPhoto", back_populates="installation", cascade="all, delete-orphan")

class InstallationPhoto(Base, TimestampMixin):
    __tablename__ = "installation_photos"

    id = Column(Integer, primary_key=True, index=True)
    installation_id = Column(Integer, ForeignKey("installations.id"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False) # relative to the private media folder
    original_name = Column(String(255), nullable=True)
    caption = Column(String(255), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    installation = relationship("Installation", back_populates="photos")

class Warranty(Base, TimestampMixin):
    __tablename__ = "warranties"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    installation_id = Column(Integer, ForeignKey("installations.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    serial_number = Column(String(100), nullable=True, index=True) # nullable for bulk solar panels
    warranty_type = Column(String(50), nullable=False) # serialized, bulk
    duration_months = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(50), default="Active", nullable=False) # Active, Expired

    customer = relationship("Customer", back_populates="warranties")
    installation = relationship("Installation", back_populates="warranties")
    order = relationship("SalesOrder", back_populates="warranties")
    product = relationship("Product")

class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(100), unique=True, nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("sales_orders.id"), nullable=True)
    ticket_id = Column(Integer, ForeignKey("service_tickets.id"), nullable=True)
    subtotal = Column(Float, nullable=False, default=0.0)
    tax = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), default="Draft", nullable=False) # Draft, Sent, Paid

    customer = relationship("Customer", back_populates="invoices")
    order = relationship("SalesOrder", back_populates="invoices")
    ticket = relationship("ServiceTicket", foreign_keys=[ticket_id])
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

class InvoiceItem(Base, TimestampMixin):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    description = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False, default=0.0)

    invoice = relationship("Invoice", back_populates="items")

class ServiceTicket(Base, TimestampMixin):
    __tablename__ = "service_tickets"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    equipment_serial = Column(String(100), nullable=False, index=True)
    installation_id = Column(Integer, ForeignKey("installations.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(50), default="Medium", nullable=False) # Low, Medium, High, Urgent
    # Open, Assigned, Quotation Sent, In Progress, Dispatched, Resolved, Customer Confirmed, Closed
    status = Column(String(50), default="Open", nullable=False)
    service_type = Column(String(50), nullable=False)              # COVERED, BILLABLE
    customer_charge = Column(Float, default=0.0, nullable=False)
    customer_confirmed = Column(Boolean, default=False, nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id", use_alter=True, name="fk_service_tickets_invoice_id"), nullable=True)
    warranty_id = Column(Integer, ForeignKey("warranties.id"), nullable=True)   # set for a claim on the bulk panel warranty
    replacement_serial = Column(String(100), nullable=True)                      # the unit that replaced the faulty one
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=True)  # who visits the customer
    inspection_notes = Column(Text, nullable=True)                               # the technician's finding at the site visit
    needs_replacement = Column(Boolean, nullable=True)                           # None until the technician has inspected
    quote_status = Column(String(20), nullable=True)                             # Pending, Approved, Rejected (billable tickets only)
    dispatch_serial = Column(String(100), nullable=True)                         # the unit sent out; becomes replacement_serial once fitted
    dispatched_at = Column(DateTime, nullable=True)

    customer = relationship("Customer", back_populates="tickets")
    technician = relationship("Technician")
    installation = relationship("Installation", back_populates="tickets")
    invoice = relationship("Invoice", foreign_keys=[invoice_id])

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="customer") # customer, admin, sales, technician, support, warehouse
    is_active = Column(Boolean, default=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), unique=True, nullable=True)      # set for customers
    technician_id = Column(Integer, ForeignKey("technicians.id"), unique=True, nullable=True)  # set for technician staff

    customer = relationship("Customer")
    technician = relationship("Technician")

class AuthSession(Base, TimestampMixin):
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True) # SHA-256 of the cookie value
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User")


class TechnicianPayout(Base, TimestampMixin):
    """One payment to a technician, covering the completed jobs it lists. Each job can be paid only once."""
    __tablename__ = "technician_payouts"

    id = Column(Integer, primary_key=True, index=True)
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=False, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    jobs_count = Column(Integer, nullable=False, default=0)
    hours = Column(Float, nullable=False, default=0.0)
    hourly_rate = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    reference = Column(String(100), nullable=True) # bank transfer or cash voucher reference
    paid_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    paid_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    technician = relationship("Technician", back_populates="payouts")


class SubsidyApplication(Base, TimestampMixin):
    """The government rooftop subsidy file for one order, from collecting documents to the money arriving."""
    __tablename__ = "subsidy_applications"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("sales_orders.id"), unique=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    status = Column(String(50), default="Documents pending", nullable=False)
    reference_number = Column(String(100), nullable=True) # the application number on the subsidy portal
    expected_amount = Column(Float, nullable=True)
    received_amount = Column(Float, nullable=True)
    applied_on = Column(Date, nullable=True)
    approved_on = Column(Date, nullable=True)
    disbursed_on = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    order = relationship("SalesOrder")
    customer = relationship("Customer")
    events = relationship("SubsidyEvent", back_populates="application", cascade="all, delete-orphan")


class SubsidyEvent(Base, TimestampMixin):
    """The history of a subsidy file: every step, who took it, and when."""
    __tablename__ = "subsidy_events"

    id = Column(Integer, primary_key=True, index=True)
    subsidy_id = Column(Integer, ForeignKey("subsidy_applications.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    note = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    application = relationship("SubsidyApplication", back_populates="events")


class StockPurchase(Base, TimestampMixin):
    """Stock bought from a supplier and received into the warehouse."""
    __tablename__ = "stock_purchases"

    id = Column(Integer, primary_key=True, index=True)
    supplier = Column(String(255), nullable=False)
    invoice_reference = Column(String(100), nullable=True) # the supplier's invoice or delivery note number
    purchased_on = Column(Date, nullable=False)
    total_cost = Column(Float, nullable=False, default=0.0)
    received_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    items = relationship("StockPurchaseItem", back_populates="purchase", cascade="all, delete-orphan")


class StockPurchaseItem(Base, TimestampMixin):
    __tablename__ = "stock_purchase_items"

    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("stock_purchases.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_cost = Column(Float, nullable=False)

    purchase = relationship("StockPurchase", back_populates="items")
    product = relationship("Product")


class Notification(Base, TimestampMixin):
    """An alert for everyone who holds a role (or for one customer), so nobody has to phone to pass work on."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(50), nullable=True, index=True)  # staff role that should see it
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)  # or one customer
    technician_id = Column(Integer, ForeignKey("technicians.id"), nullable=True, index=True)  # or one technician
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    link = Column(String(255), nullable=True)  # the app page to open, e.g. "dispatch"
    is_read = Column(Boolean, default=False, nullable=False)
