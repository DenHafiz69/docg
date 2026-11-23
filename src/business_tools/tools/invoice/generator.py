from __future__ import annotations

from pathlib import Path
from typing import Any

from business_tools.core.ledger import Ledger
from business_tools.core.renderer import load_data_file, render_document, resolve_brand
from business_tools.tools.invoice.models import InvoiceData, PaymentInfo

TEMPLATE_DIR = Path(__file__).parent
DEFAULT_PAYMENT_PATH = Path(__file__).resolve().parents[4] / "config" / "default_payment.yaml"

CURRENCY_SYMBOLS: dict[str, str] = {
    "MYR": "RM",
    "USD": "$",
    "SGD": "S$",
    "EUR": "€",
    "GBP": "£",
    "AUD": "A$",
}


def format_money(amount: float, symbol: str) -> str:
    return f"{symbol} {amount:,.2f}"


def generate_invoice(
    data: InvoiceData | dict[str, Any],
    output_pdf: Path,
    brand_path: Path | None = None,
    output_html: Path | None = None,
    ledger: Ledger | None = None,
    input_path: Path | None = None,
) -> Path:
    """Validate invoice data, compute totals, and render a PDF invoice."""
    invoice = data if isinstance(data, InvoiceData) else InvoiceData.model_validate(data)
    if not invoice.invoice_number or invoice.invoice_number.strip().upper() == "AUTO":
        if ledger is None:
            raise ValueError("invoice_number is required when no ledger is provided.")
        invoice.invoice_number = ledger.next_number("invoice")

    brand = resolve_brand(inline_brand=invoice.brand, brand_path=brand_path)
    if DEFAULT_PAYMENT_PATH.exists():
        default_pay = load_data_file(DEFAULT_PAYMENT_PATH)
        if invoice.payment is None:
            invoice.payment = PaymentInfo.model_validate(default_pay)
        else:
            merged_pay = {**default_pay, **invoice.payment.model_dump(exclude_none=True)}
            invoice.payment = PaymentInfo.model_validate(merged_pay)
    symbol = invoice.currency_symbol or CURRENCY_SYMBOLS.get(invoice.currency.upper(), invoice.currency)

    subtotal = round(sum(item.total for item in invoice.items), 2)

    discount = round(invoice.discount_amount, 2)
    if invoice.discount_percent > 0:
        discount = round(discount + subtotal * (invoice.discount_percent / 100.0), 2)
    discount = min(discount, subtotal)

    taxable = round(subtotal - discount, 2)
    tax_amount = round(taxable * (invoice.tax_rate / 100.0), 2) if invoice.tax_rate > 0 else 0.0
    grand_total = round(taxable + tax_amount, 2)
    balance_due = round(max(grand_total - invoice.amount_paid, 0.0), 2)

    meta_rows = [
        {"label": "Invoice No.", "value": invoice.invoice_number},
        {"label": "Issue Date", "value": invoice.issue_date},
    ]
    if invoice.due_date:
        meta_rows.append({"label": "Due Date", "value": invoice.due_date})
    if invoice.status:
        meta_rows.append({"label": "Status", "value": invoice.status.upper()})

    formatted_items = [
        {
            "title": item.title,
            "description": item.description,
            "quantity": f"{item.quantity:g}" + (f" {item.unit}" if item.unit else ""),
            "unit_price": format_money(item.unit_price, symbol),
            "total": format_money(item.total, symbol),
        }
        for item in invoice.items
    ]

    totals = {
        "subtotal": format_money(subtotal, symbol),
        "discount": format_money(discount, symbol) if discount > 0 else None,
        "tax_label": f"{invoice.tax_label} ({invoice.tax_rate:g}%)",
        "tax_amount": format_money(tax_amount, symbol) if tax_amount > 0 else None,
        "grand_total": format_money(grand_total, symbol),
        "amount_paid": format_money(invoice.amount_paid, symbol) if invoice.amount_paid > 0 else None,
        "balance_due": format_money(balance_due, symbol),
        "has_partial_payment": invoice.amount_paid > 0,
    }

    context = {
        "doc_type": "INVOICE",
        "doc_number": invoice.invoice_number,
        "brand": brand,
        "meta_rows": meta_rows,
        "invoice": invoice,
        "items": formatted_items,
        "totals": totals,
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
            doc_number=invoice.invoice_number,
            doc_type="invoice",
            client_name=invoice.client.company or invoice.client.name,
            project_title=invoice.project_title,
            currency=invoice.currency,
            total_amount=grand_total,
            balance_due=balance_due,
            status=invoice.status or ("PAID" if balance_due == 0 else "UNPAID"),
            issue_date=invoice.issue_date,
            input_path=input_path,
            output_path=rendered,
        )

    return rendered


def generate_invoice_from_file(
    input_path: Path,
    output_pdf: Path,
    brand_path: Path | None = None,
    output_html: Path | None = None,
    ledger: Ledger | None = None,
) -> Path:
    """Load YAML/JSON invoice data from disk and render a PDF."""
    raw = load_data_file(input_path)
    return generate_invoice(
        raw,
        output_pdf=output_pdf,
        brand_path=brand_path,
        output_html=output_html,
        ledger=ledger,
        input_path=input_path,
    )
