from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from docg.core.models import BrandConfig, Party


class LetterData(BaseModel):
    """Complete input schema for generating a formal letter, cover letter, or official correspondence."""

    letter_number: Optional[str] = Field(
        None,
        description="Optional reference number (set 'AUTO' to auto-generate LTR-YYYY-NNN via ledger)",
    )
    issue_date: str = Field(default_factory=lambda: date.today().isoformat())
    doc_label: str = Field(
        "LETTER", description="Top-right document badge, e.g. LETTER, COVER LETTER, OFFICIAL LETTER"
    )
    subject: Optional[str] = Field(None, description="Subject line of the letter")

    recipient: Party
    salutation: Optional[str] = None
    paragraphs: list[str] = Field(..., min_length=1, description="Body paragraphs of the letter")
    bullets: list[str] = Field(
        default_factory=list, description="Optional bullet points rendered after the first paragraph"
    )
    closing_paragraphs: list[str] = Field(default_factory=list)

    sign_off: str = Field("Sincerely,", description="Closing phrase before signature")
    sender_name: Optional[str] = Field(None, description="Defaults to profile signatory_name or name")
    sender_title: Optional[str] = Field(None, description="Defaults to profile signatory_title")
    notes: Optional[str] = None
    brand: Optional[BrandConfig] = None
