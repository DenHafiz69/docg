from __future__ import annotations

from pathlib import Path
from typing import Any

from docg.core.ledger import Ledger
from docg.core.models import SignatureParty
from docg.core.renderer import render_document, resolve_brand, resolve_template
from docg.tools.agreement.models import AgreementData

TEMPLATE_DIR = Path(__file__).parent


def generate_agreement(
    data: AgreementData | dict[str, Any],
    output_pdf: Path,
    *,
    profile: str | None = "business",
    brand_path: Path | None = None,
    output_html: Path | None = None,
    ledger: Ledger | None = None,
    input_path: Path | None = None,
    home: Path | None = None,
    template: str | Path | None = None,
) -> dict[str, Any]:
    """Validate agreement letter data and render a PDF using the shared design system."""
    agreement = data if isinstance(data, AgreementData) else AgreementData.model_validate(data)
    if not agreement.agreement_number or agreement.agreement_number.strip().upper() == "AUTO":
        if ledger is None:
            raise ValueError("agreement_number is required when no ledger is provided.")
        agreement.agreement_number = ledger.next_number("agreement")

    brand = resolve_brand(
        inline_brand=agreement.brand, profile=profile, brand_path=brand_path, home=home
    )

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

    tdir, tname = resolve_template(
        "agreement", template, default_dir=TEMPLATE_DIR, default_name="template.html", home=home
    )
    rendered = render_document(
        template_dir=tdir,
        template_name=tname,
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

    return {
        "doc_type": "agreement",
        "doc_number": agreement.agreement_number,
        "pdf": str(rendered.resolve()),
        "status": "ISSUED",
    }
