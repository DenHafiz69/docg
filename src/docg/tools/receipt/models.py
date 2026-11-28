from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from docg.core.models import BrandConfig, Party
from docg.tools.invoice.models import LineItem


class ReceiptData(BaseModel):
    """Complete input schema for generating a payment receipt."""

    receipt_number: Optional[str] = Field(
        None, description="Receipt number (omit or set 'AUTO' to auto-generate via ledger)"
    )
    payment_date: str = Field(default_factory=lambda: date.today().isoformat())
    invoice_number: Optional[str] = Field(
        None, description="Optional reference invoice number, e.g. INV-2026-001"
    )
    currency: str = "MYR"
    currency_symbol: Optional[str] = None
    project_title: Optional[str] = None
    payment_method: str = "Bank Transfer"
    payment_reference: Optional[str] = Field(
        None, description="Bank transfer reference, transaction ID, or cheque number"
    )

    client: Party
    items: list[LineItem] = Field(..., min_length=1)

    discount_percent: float = Field(0.0, ge=0, le=100)
    discount_amount: float = Field(0.0, ge=0)
    tax_rate: float = Field(0.0, ge=0, le=100, description="Tax percentage, e.g. 8.0 for 8%")
    tax_label: str = "Tax"
    amount_paid: Optional[float] = Field(
        None, ge=0, description="Amount received (defaults to full grand total)"
    )

    notes: Optional[str] = None
    brand: Optional[BrandConfig] = None
