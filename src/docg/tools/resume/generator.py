from __future__ import annotations

from pathlib import Path
from typing import Any

from docg.core.ledger import Ledger
from docg.core.renderer import render_document, resolve_brand, resolve_template
from docg.tools.resume.models import ResumeData

TEMPLATE_DIR = Path(__file__).parent


def generate_resume(
    data: ResumeData | dict[str, Any],
    output_pdf: Path,
    *,
    profile: str | None = "personal",
    brand_path: Path | None = None,
    output_html: Path | None = None,
    ledger: Ledger | None = None,  # noqa: ARG001 - resumes are not tracked in ledger
    input_path: Path | None = None,  # noqa: ARG001
    home: Path | None = None,
    template: str | Path | None = None,
) -> dict[str, Any]:
    """Validate resume data and render an ATS-friendly PDF resume."""
    resume = data if isinstance(data, ResumeData) else ResumeData.model_validate(data)
    brand = resolve_brand(
        inline_brand=resume.brand, profile=profile, brand_path=brand_path, home=home
    )

    full_name = resume.name or brand.name
    headline = resume.headline or brand.tagline
    location = resume.location or (", ".join(brand.address) if brand.address else None)
    email = resume.email or brand.email
    phone = resume.phone or brand.phone
    website = resume.website or brand.website

    contact_parts = [
        p for p in [location, email, phone, website, resume.github, resume.linkedin] if p
    ]

    context = {
        "doc_type": "RESUME",
        "doc_number": full_name,
        "brand": brand,
        "resume": resume,
        "full_name": full_name,
        "headline": headline,
        "contact_parts": contact_parts,
    }

    tdir, tname = resolve_template(
        "resume", template, default_dir=TEMPLATE_DIR, default_name="template.html", home=home
    )
    rendered = render_document(
        template_dir=tdir,
        template_name=tname,
        context=context,
        output_pdf=output_pdf,
        output_html=output_html,
    )

    return {
        "doc_type": "resume",
        "name": full_name,
        "pdf": str(rendered.resolve()),
    }
