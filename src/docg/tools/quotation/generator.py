from __future__ import annotations

from pathlib import Path
from typing import Any

from docg.core.ledger import Ledger
from docg.core.renderer import render_document, resolve_brand, resolve_template
from docg.tools.invoice.generator import CURRENCY_SYMBOLS, format_money
from docg.tools.quotation.models import QuotationData

TEMPLATE_DIR = Path(__file__).parent


def generate_quotation(
    data: QuotationData | dict[str, Any],
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
    """Validate quotation data, compute totals, and render a PDF quotation."""
    quotation = data if isinstance(data, QuotationData) else QuotationData.model_validate(data)
    if not quotation.quotation_number or quotation.quotation_number.strip().upper() == "AUTO":
        if ledger is None:
            raise ValueError("quotation_number is required when no ledger is provided.")
        quotation.quotation_number = ledger.next_number("quotation")

    brand = resolve_brand(
        inline_brand=quotation.brand, profile=profile, brand_path=brand_path, home=home
    )

    symbol = quotation.currency_symbol or CURRENCY_SYMBOLS.get(quotation.currency.upper(), quotation.currency)

    subtotal = round(sum(item.total for item in quotation.items), 2)

    discount = round(quotation.discount_amount, 2)
    if quotation.discount_percent > 0:
        discount = round(discount + subtotal * (quotation.discount_percent / 100.0), 2)
    discount = min(discount, subtotal)

    taxable = round(subtotal - discount, 2)
    tax_amount = round(taxable * (quotation.tax_rate / 100.0), 2) if quotation.tax_rate > 0 else 0.0
    grand_total = round(taxable + tax_amount, 2)

    deposit_amount = (
        round(grand_total * (quotation.deposit_percent / 100.0), 2)
        if quotation.deposit_percent
        else None
    )

    meta_rows = [
        {"label": "Quotation No.", "value": quotation.quotation_number},
        {"label": "Issue Date", "value": quotation.issue_date},
    ]
    if quotation.valid_until:
        meta_rows.append({"label": "Valid Until", "value": quotation.valid_until})
    if quotation.status:
        meta_rows.append({"label": "Status", "value": quotation.status.upper()})

    formatted_items = [
        {
            "title": item.title,
            "description": item.description,
            "quantity": f"{item.quantity:g}" + (f" {item.unit}" if item.unit else ""),
            "unit_price": format_money(item.unit_price, symbol),
            "total": format_money(item.total, symbol),
        }
        for item in quotation.items
    ]

    totals = {
        "subtotal": format_money(subtotal, symbol),
        "discount": format_money(discount, symbol) if discount > 0 else None,
        "tax_label": f"{quotation.tax_label} ({quotation.tax_rate:g}%)",
        "tax_amount": format_money(tax_amount, symbol) if tax_amount > 0 else None,
        "grand_total": format_money(grand_total, symbol),
        "deposit_percent": f"{quotation.deposit_percent:g}%" if quotation.deposit_percent else None,
        "deposit_amount": format_money(deposit_amount, symbol) if deposit_amount is not None else None,
    }

    context = {
        "doc_type": "QUOTATION",
        "doc_number": quotation.quotation_number,
        "brand": brand,
        "meta_rows": meta_rows,
        "quotation": quotation,
        "items": formatted_items,
        "totals": totals,
    }

    tdir, tname = resolve_template(
        "quotation", template, default_dir=TEMPLATE_DIR, default_name="template.html", home=home
    )
    rendered = render_document(
        template_dir=tdir,
        template_name=tname,
        context=context,
        output_pdf=output_pdf,
        output_html=output_html,
    )

    status_val = quotation.status or "ISSUED"
    if ledger is not None:
        ledger.record(
            doc_number=quotation.quotation_number,
            doc_type="quotation",
            client_name=quotation.client.company or quotation.client.name,
            project_title=quotation.project_title,
            currency=quotation.currency,
            total_amount=grand_total,
            balance_due=None,
            status=status_val,
            issue_date=quotation.issue_date,
            input_path=input_path,
            output_path=rendered,
            payload=quotation.model_dump(mode="json"),
        )

    return {
        "doc_type": "quotation",
        "doc_number": quotation.quotation_number,
        "pdf": str(rendered.resolve()),
        "currency": quotation.currency,
        "total": grand_total,
        "status": status_val.upper(),
    }
