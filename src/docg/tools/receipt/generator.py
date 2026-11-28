from __future__ import annotations

from pathlib import Path
from typing import Any

from docg.core.ledger import Ledger
from docg.core.renderer import render_document, resolve_brand, resolve_template
from docg.tools.invoice.generator import CURRENCY_SYMBOLS, format_money
from docg.tools.receipt.models import ReceiptData

TEMPLATE_DIR = Path(__file__).parent


def generate_receipt(
    data: ReceiptData | dict[str, Any],
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
    """Validate receipt data, compute payment totals, and render a PDF receipt."""
    receipt = data if isinstance(data, ReceiptData) else ReceiptData.model_validate(data)
    if not receipt.receipt_number or receipt.receipt_number.strip().upper() == "AUTO":
        if ledger is None:
            raise ValueError("receipt_number is required when no ledger is provided.")
        receipt.receipt_number = ledger.next_number("receipt")

    brand = resolve_brand(
        inline_brand=receipt.brand, profile=profile, brand_path=brand_path, home=home
    )

    symbol = receipt.currency_symbol or CURRENCY_SYMBOLS.get(receipt.currency.upper(), receipt.currency)

    subtotal = round(sum(item.total for item in receipt.items), 2)

    discount = round(receipt.discount_amount, 2)
    if receipt.discount_percent > 0:
        discount = round(discount + subtotal * (receipt.discount_percent / 100.0), 2)
    discount = min(discount, subtotal)

    taxable = round(subtotal - discount, 2)
    tax_amount = round(taxable * (receipt.tax_rate / 100.0), 2) if receipt.tax_rate > 0 else 0.0
    grand_total = round(taxable + tax_amount, 2)

    amount_paid = round(receipt.amount_paid, 2) if receipt.amount_paid is not None else grand_total
    balance_due = round(max(grand_total - amount_paid, 0.0), 2)
    status_val = "PAID" if balance_due == 0 else "PARTIAL"

    meta_rows = [
        {"label": "Receipt No.", "value": receipt.receipt_number},
        {"label": "Payment Date", "value": receipt.payment_date},
    ]
    if receipt.invoice_number:
        meta_rows.append({"label": "Invoice Ref.", "value": receipt.invoice_number})
    meta_rows.append({"label": "Status", "value": status_val})

    formatted_items = [
        {
            "title": item.title,
            "description": item.description,
            "quantity": f"{item.quantity:g}" + (f" {item.unit}" if item.unit else ""),
            "unit_price": format_money(item.unit_price, symbol),
            "total": format_money(item.total, symbol),
        }
        for item in receipt.items
    ]

    totals = {
        "subtotal": format_money(subtotal, symbol),
        "discount": format_money(discount, symbol) if discount > 0 else None,
        "tax_label": f"{receipt.tax_label} ({receipt.tax_rate:g}%)",
        "tax_amount": format_money(tax_amount, symbol) if tax_amount > 0 else None,
        "grand_total": format_money(grand_total, symbol),
        "amount_paid": format_money(amount_paid, symbol),
        "balance_due": format_money(balance_due, symbol),
        "has_balance": balance_due > 0,
    }

    context = {
        "doc_type": "RECEIPT",
        "doc_number": receipt.receipt_number,
        "brand": brand,
        "meta_rows": meta_rows,
        "receipt": receipt,
        "items": formatted_items,
        "totals": totals,
        "status_label": status_val,
    }

    tdir, tname = resolve_template(
        "receipt", template, default_dir=TEMPLATE_DIR, default_name="template.html", home=home
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
            doc_number=receipt.receipt_number,
            doc_type="receipt",
            client_name=receipt.client.company or receipt.client.name,
            project_title=receipt.project_title,
            currency=receipt.currency,
            total_amount=grand_total,
            balance_due=balance_due,
            status=status_val,
            issue_date=receipt.payment_date,
            input_path=input_path,
            output_path=rendered,
            payload=receipt.model_dump(mode="json"),
        )

    return {
        "doc_type": "receipt",
        "doc_number": receipt.receipt_number,
        "pdf": str(rendered.resolve()),
        "currency": receipt.currency,
        "total": grand_total,
        "amount_paid": amount_paid,
        "balance_due": balance_due,
        "status": status_val,
    }
