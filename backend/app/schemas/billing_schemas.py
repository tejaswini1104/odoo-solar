from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class QuoteLine(BaseModel):
    product_name: str
    quantity: int
    unit_price: float
    line_total: float


class PortalQuote(BaseModel):
    id: int
    reference: str
    package_name: str
    status: str
    items: List[QuoteLine]
    subtotal: float
    gst: float
    total: float            # including GST
    order_id: Optional[int] = None
    order_status: Optional[str] = None
    advance_percent: float
    advance_required: float # advance_percent of total, including GST
    advance_verified: float # verified by staff so far
    advance_pending: float  # reported by customer, waiting for staff to check
    advance_outstanding: float
    balance_required: float  # total minus the advance, due after installation
    order_completed: bool
    payable_now: float       # the most the customer can report right now


class BankDetails(BaseModel):
    account_name: str
    bank_name: str
    account_number: str
    ifsc: str
    upi_id: str
    advance_percent: float


class PaymentSubmit(BaseModel):
    quotation_id: int
    amount: float = Field(gt=0, le=10_000_000)
    reference_number: str = Field(min_length=4, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9/\-_. ]*$")


class PortalPayment(BaseModel):
    id: int
    quotation_reference: str
    amount: float
    reference_number: Optional[str] = None
    status: str
    payment_date: datetime
