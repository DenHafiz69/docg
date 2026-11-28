from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from docg.core.models import BrandConfig, Party
from docg.tools.invoice.models import LineItem, PaymentInfo


class QuotationData(BaseModel):
    """Complete input schema for generating a business quotation / estimate."""

    quotation_number: Optional[str] = Field(
        None, description="Quotation number (omit or set 'AUTO' to auto-generate via ledger)"
    )
    issue_date: str = Field(default_factory=lambda: date.today().isoformat())
    valid_until: Optional[str] = Field(
        None, description="Expiration date of the quotation, e.g. 2026-12-31"
    )
    currency: str = "MYR"
    currency_symbol: Optional[str] = None
    project_title: Optional[str] = None
    status: Optional[str] = Field(
        None, description="Optional status badge e.g. DRAFT, ISSUED, ACCEPTED, EXPIRED"
    )

    client: Party
    items: list[LineItem] = Field(..., min_length=1)

    discount_percent: float = Field(0.0, ge=0, le=100)
    discount_amount: float = Field(0.0, ge=0)
    tax_rate: float = Field(0.0, ge=0, le=100, description="Tax percentage, e.g. 8.0 for 8%")
    tax_label: str = "Tax"
    deposit_percent: Optional[float] = Field(
        None, ge=0, le=100, description="Optional upfront deposit percentage required to commence"
    )

    terms: list[str] = Field(
        default_factory=list,
        description="Quotation terms and conditions bullets",
    )
    payment: Optional[PaymentInfo] = Field(
        None, description="Optional payment instructions carried over when converting to invoice"
    )
    notes: Optional[str] = None
    brand: Optional[BrandConfig] = None
