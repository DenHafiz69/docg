from __future__ import annotations

from pathlib import Path
from typing import Any

from business_tools.core.ledger import Ledger
from business_tools.core.models import SignatureParty
from business_tools.core.renderer import load_data_file, render_document, resolve_brand
from business_tools.tools.agreement.models import AgreementData

TEMPLATE_DIR = Path(__file__).parent


def generate_agreement(
    data: AgreementData | dict[str, Any],
    output_pdf: Path,
    brand_path: Path | None = None,
    output_html: Path | None = None,
    ledger: Ledger | None = None,
    input_path: Path | None = None,
) -> Path:
    """Validate agreement letter data and render a PDF using the shared design system."""
    agreement = data if isinstance(data, AgreementData) else AgreementData.model_validate(data)
    if not agreement.agreement_number or agreement.agreement_number.strip().upper() == "AUTO":
        if ledger is None:
            raise ValueError("agreement_number is required when no ledger is provided.")
        agreement.agreement_number = ledger.next_number("agreement")

    brand = resolve_brand(inline_brand=agreement.brand, brand_path=brand_path)

    meta_rows = [
        {"label": "Reference No.", "value": agreement.agreement_number},
        {"label": "Effective Date", "value": agreement.effective_date},
    ]

    salutation = agreement.salutation or f"Dear {agreement.client.name},"

    signatures = agreement.signatures
    if not signatures:
        signatures = [
            SignatureParty(
                label=f"For {brand.name}",
                name=agreement.provider_signatory_name or brand.signatory_name or brand.name,
                title=agreement.provider_signatory_title or brand.signatory_title or "Authorized Signatory",
                company=brand.name,
            ),
            SignatureParty(
                label="Accepted & Agreed By",
                name=agreement.client.name,
                title=agreement.client.role or "Client / Authorized Signatory",
                company=agreement.client.company,
            ),
        ]

    context = {
        "doc_type": agreement.doc_label.upper(),
        "doc_number": agreement.agreement_number,
        "brand": brand,
        "meta_rows": meta_rows,
        "agreement": agreement,
        "salutation": salutation,
        "signatures": signatures,
    }

    rendered = render_document(
        template_dir=TEMPLATE_DIR,
        template_name="template.html",
        context=context,
        output_pdf=output_pdf,
        output_html=output_html,
    )

    if ledger is not None:
        ledger.record(
            doc_number=agreement.agreement_number,
            doc_type="agreement",
            client_name=agreement.client.company or agreement.client.name,
            project_title=agreement.title,
            status="ISSUED",
            issue_date=agreement.effective_date,
            input_path=input_path,
            output_path=rendered,
        )

    return rendered


def generate_agreement_from_file(
    input_path: Path,
    output_pdf: Path,
    brand_path: Path | None = None,
    output_html: Path | None = None,
    ledger: Ledger | None = None,
) -> Path:
    """Load YAML/JSON agreement data from disk and render a PDF."""
    raw = load_data_file(input_path)
    return generate_agreement(
        raw,
        output_pdf=output_pdf,
        brand_path=brand_path,
        output_html=output_html,
        ledger=ledger,
        input_path=input_path,
    )
