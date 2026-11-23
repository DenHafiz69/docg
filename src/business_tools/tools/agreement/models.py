from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from business_tools.core.models import BrandConfig, Party, SignatureParty


class SubClause(BaseModel):
    """Optional nested sub-section inside a clause."""

    title: str
    bullets: list[str] = Field(default_factory=list)


class AgreementClause(BaseModel):
    """Numbered clause or section inside an agreement letter."""

    title: str
    body: str = ""
    bullets: list[str] = Field(default_factory=list)
    subclauses: list[SubClause] = Field(default_factory=list)


class KeyTerm(BaseModel):
    """Key commercial summary row (e.g. Project Fee, Timeline, Payment Schedule)."""

    label: str
    value: str


class AgreementData(BaseModel):
    """Complete input schema for generating an agreement letter."""

    agreement_number: Optional[str] = Field(
        None, description="Agreement number (omit or set 'AUTO' to auto-generate via ledger)"
    )
    effective_date: str = Field(default_factory=lambda: date.today().isoformat())
    title: str = Field(..., description="Subject / title of the agreement letter")
    doc_label: str = Field("AGREEMENT LETTER", description="Top-right document badge")

    client: Party
    salutation: Optional[str] = None
    intro_paragraphs: list[str] = Field(default_factory=list)
    key_terms: list[KeyTerm] = Field(default_factory=list)
    clauses: list[AgreementClause] = Field(default_factory=list)
    closing_paragraphs: list[str] = Field(default_factory=list)

    signatures: list[SignatureParty] = Field(default_factory=list)
    provider_signatory_name: Optional[str] = None
    provider_signatory_title: Optional[str] = None
    notes: Optional[str] = None
    brand: Optional[BrandConfig] = None
