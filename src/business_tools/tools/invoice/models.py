from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from business_tools.core.models import BrandConfig, Party


class LineItem(BaseModel):
    """Single billable line item on an invoice."""

    title: str
    description: Optional[str] = None
    quantity: float = Field(1.0, gt=0)
    unit: Optional[str] = Field(None, description="e.g. hrs, pcs, package")
    unit_price: float = Field(..., ge=0)

    @property
    def total(self) -> float:
        return round(self.quantity * self.unit_price, 2)


class PaymentInfo(BaseModel):
    """Payment instructions shown on the invoice."""

    method: str = "Bank Transfer"
    bank_name: Optional[str] = None
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    reference: Optional[str] = None
    terms: Optional[str] = Field(
        "Payment due within 14 days of invoice date.",
        description="Payment terms summary",
    )


class InvoiceData(BaseModel):
    """Complete input schema for generating an invoice."""

    invoice_number: Optional[str] = Field(
        None, description="Invoice number (omit or set 'AUTO' to auto-generate via ledger)"
    )
    issue_date: str = Field(default_factory=lambda: date.today().isoformat())
    due_date: Optional[str] = None
    currency: str = "MYR"
    currency_symbol: Optional[str] = None
    project_title: Optional[str] = None
    status: Optional[str] = Field(None, description="Optional status badge e.g. UNPAID, PAID")

    client: Party
    items: list[LineItem] = Field(..., min_length=1)

    discount_percent: float = Field(0.0, ge=0, le=100)
    discount_amount: float = Field(0.0, ge=0)
    tax_rate: float = Field(0.0, ge=0, le=100, description="Tax percentage, e.g. 8.0 for 8%")
    tax_label: str = "Tax"
    amount_paid: float = Field(0.0, ge=0)

    payment: Optional[PaymentInfo] = None
    notes: Optional[str] = None
    brand: Optional[BrandConfig] = None
