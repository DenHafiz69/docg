from __future__ import annotations

from pathlib import Path
from typing import Any

from docg.core.ledger import Ledger
from docg.core.renderer import render_document, resolve_brand, resolve_template
from docg.tools.letter.models import LetterData

TEMPLATE_DIR = Path(__file__).parent


def generate_letter(
    data: LetterData | dict[str, Any],
    output_pdf: Path,
    *,
    profile: str | None = "personal",
    brand_path: Path | None = None,
    output_html: Path | None = None,
    ledger: Ledger | None = None,
    input_path: Path | None = None,
    home: Path | None = None,
    template: str | Path | None = None,
) -> dict[str, Any]:
    """Validate letter data and render a PDF using the shared design system."""
    letter = data if isinstance(data, LetterData) else LetterData.model_validate(data)
    if letter.letter_number and letter.letter_number.strip().upper() == "AUTO":
        if ledger is None:
            raise ValueError("Cannot auto-generate letter_number when no ledger is provided.")
        letter.letter_number = ledger.next_number("letter")

    brand = resolve_brand(
        inline_brand=letter.brand, profile=profile, brand_path=brand_path, home=home
    )

    meta_rows = [{"label": "Date", "value": letter.issue_date}]
    if letter.letter_number:
        meta_rows.insert(0, {"label": "Ref. No.", "value": letter.letter_number})

    salutation = letter.salutation or f"Dear {letter.recipient.name},"
    sender_name = letter.sender_name or brand.signatory_name or brand.name
    sender_title = letter.sender_title if letter.sender_title is not None else brand.signatory_title

    context = {
        "doc_type": letter.doc_label.upper(),
        "doc_number": letter.letter_number or letter.subject or "",
        "brand": brand,
        "meta_rows": meta_rows,
        "letter": letter,
        "salutation": salutation,
        "sender_name": sender_name,
        "sender_title": sender_title,
    }

    tdir, tname = resolve_template(
        "letter", template, default_dir=TEMPLATE_DIR, default_name="template.html", home=home
    )
    rendered = render_document(
        template_dir=tdir,
        template_name=tname,
        context=context,
        output_pdf=output_pdf,
        output_html=output_html,
    )

    if ledger is not None and letter.letter_number:
        ledger.record(
            doc_number=letter.letter_number,
            doc_type="letter",
            client_name=letter.recipient.company or letter.recipient.name,
            project_title=letter.subject,
            status="ISSUED",
            issue_date=letter.issue_date,
            input_path=input_path,
            output_path=rendered,
            payload=letter.model_dump(mode="json"),
        )

    result: dict[str, Any] = {
        "doc_type": "letter",
        "pdf": str(rendered.resolve()),
    }
    if letter.letter_number:
        result["doc_number"] = letter.letter_number
    return result
