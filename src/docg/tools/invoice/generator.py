from __future__ import annotations

from pathlib import Path
from typing import Any

from docg.core.ledger import Ledger
from docg.core.paths import default_payment_path
from docg.core.renderer import load_data_file, render_document, resolve_brand, resolve_template
from docg.tools.invoice.models import InvoiceData, PaymentInfo

TEMPLATE_DIR = Path(__file__).parent

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
    *,
    profile: str | None = "business",
    brand_path: Path | None = None,
    output_html: Path | None = None,
    ledger: Ledger | None = None,
    input_path: Path | None = None,
    home: Path | None = None,
    template: str | Path | None = None,
) -> dict[str, Any]:
    """Validate invoice data, compute totals, and render a PDF invoice."""
    invoice = data if isinstance(data, InvoiceData) else InvoiceData.model_validate(data)
    if not invoice.invoice_number or invoice.invoice_number.strip().upper() == "AUTO":
        if ledger is None:
            raise ValueError("invoice_number is required when no ledger is provided.")
        invoice.invoice_number = ledger.next_number("invoice")

    brand = resolve_brand(
        inline_brand=invoice.brand, profile=profile, brand_path=brand_path, home=home
    )

    pay_file = default_payment_path(home)
    if pay_file.exists():
        default_pay = load_data_file(pay_file)
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

    tdir, tname = resolve_template(
        "invoice", template, default_dir=TEMPLATE_DIR, default_name="template.html", home=home
    )
    rendered = render_document(
        template_dir=tdir,
        template_name=tname,
        context=context,
        output_pdf=output_pdf,
        output_html=output_html,
    )

    status_val = invoice.status or ("PAID" if balance_due == 0 else "UNPAID")
    if ledger is not None:
        ledger.record(
            doc_number=invoice.invoice_number,
            doc_type="invoice",
            client_name=invoice.client.company or invoice.client.name,
            project_title=invoice.project_title,
            currency=invoice.currency,
            total_amount=grand_total,
            balance_due=balance_due,
            status=status_val,
            issue_date=invoice.issue_date,
            input_path=input_path,
            output_path=rendered,
            payload=invoice.model_dump(mode="json"),
        )

    return {
        "doc_type": "invoice",
        "doc_number": invoice.invoice_number,
        "pdf": str(rendered.resolve()),
        "currency": invoice.currency,
        "total": grand_total,
        "balance_due": balance_due,
        "status": status_val.upper(),
    }
