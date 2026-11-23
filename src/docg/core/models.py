from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class BrandConfig(BaseModel):
    """Consistent sender/profile identity and visual styling across all documents."""

    name: str = Field(..., description="Business or personal sender name")
    tagline: Optional[str] = Field(None, description="Short subtitle, headline, or tagline")
    address: list[str] = Field(default_factory=list, description="Address or location lines")
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    registration_no: Optional[str] = Field(None, description="Company/business registration number")
    tax_id: Optional[str] = Field(None, description="Tax / SST / VAT ID")
    logo_path: Optional[Path] = Field(None, description="Optional path to PNG/SVG logo")
    primary_color: str = Field("#0F172A", description="Deep ink/primary hex color")
    accent_color: str = Field("#0284C7", description="Cerulean accent hex color")
    muted_color: str = Field("#64748B", description="Secondary muted hex color")
    footer_note: Optional[str] = Field(
        None, description="Optional persistent footer text across documents"
    )
    signatory_name: Optional[str] = Field(
        None, description="Default authorized signatory name for agreements and letters"
    )
    signatory_title: Optional[str] = Field(
        None, description="Default authorized signatory title for agreements and letters"
    )

    @field_validator("address", mode="before")
    @classmethod
    def normalize_address(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [line.strip() for line in value.splitlines() if line.strip()]
        return value


class Party(BaseModel):
    """Represents a recipient, client, or counterparty."""

    name: str
    company: Optional[str] = None
    role: Optional[str] = None
    address: list[str] = Field(default_factory=list)
    email: Optional[str] = None
    phone: Optional[str] = None
    registration_no: Optional[str] = None
    tax_id: Optional[str] = None

    @field_validator("address", mode="before")
    @classmethod
    def normalize_address(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [line.strip() for line in value.splitlines() if line.strip()]
        return value


class SignatureParty(BaseModel):
    """Represents a signatory block in formal documents."""

    label: str = Field(..., description="e.g. 'For and on behalf of Provider'")
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    date: Optional[str] = None
