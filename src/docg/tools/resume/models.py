from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from docg.core.models import BrandConfig


class ExperienceItem(BaseModel):
    """Single work experience entry."""

    role: str
    company: str
    location: Optional[str] = None
    period: str = Field(..., description="e.g. 'Jan 2024 – Present'")
    highlights: list[str] = Field(default_factory=list)


class ProjectItem(BaseModel):
    """Highlighted project entry."""

    name: str
    url: Optional[str] = None
    tech: list[str] = Field(default_factory=list)
    period: Optional[str] = None
    highlights: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    """Education entry."""

    degree: str
    institution: str
    location: Optional[str] = None
    period: str
    details: list[str] = Field(default_factory=list)


class SkillGroup(BaseModel):
    """Categorized list of skills."""

    category: str
    items: list[str] = Field(default_factory=list)


class ResumeData(BaseModel):
    """Complete input schema for generating a clean, ATS-friendly PDF resume."""

    name: Optional[str] = Field(None, description="Full name (defaults to profile name)")
    headline: Optional[str] = Field(None, description="Role or professional headline (defaults to profile tagline)")
    location: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None

    summary: Optional[str] = None
    experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    skills: list[SkillGroup] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    brand: Optional[BrandConfig] = None
