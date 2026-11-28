from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from docg.core.ledger import Ledger
from docg.core.renderer import load_data_file
from docg.tools.invoice.generator import generate_invoice
from docg.tools.receipt.generator import generate_receipt

SUPPORTED_CONVERSIONS: set[tuple[str, str]] = {
    ("quotation", "invoice"),
    ("invoice", "receipt"),
}


def _load_source_payload(record: dict[str, Any]) -> dict[str, Any]:
    payload = record.get("payload")
    if isinstance(payload, dict):
        return payload

    input_path_str = record.get("input_path")
    if input_path_str:
        input_path = Path(input_path_str)
        if input_path.is_file():
            return load_data_file(input_path)

    raise ValueError(
        f"Document '{record['doc_number']}' does not have stored payload data or a readable input file to convert."
    )


def build_converted_payload(
    source_type: str,
    target_type: str,
    source_number: str,
    source_payload: dict[str, Any],
    *,
    due_date: str | None = None,
    payment_date: str | None = None,
    payment_method: str | None = None,
    payment_reference: str | None = None,
    amount_paid: float | None = None,
) -> dict[str, Any]:
    """Transform a source document payload into a target document payload."""
    pair = (source_type.lower(), target_type.lower())
    if pair not in SUPPORTED_CONVERSIONS:
        supported = ", ".join(f"{s} -> {t}" for s, t in sorted(SUPPORTED_CONVERSIONS))
        raise ValueError(
            f"Unsupported conversion '{source_type} -> {target_type}'. Supported: {supported}."
        )

    shared_keys = (
        "client",
        "items",
        "currency",
        "currency_symbol",
        "project_title",
        "discount_percent",
        "discount_amount",
        "tax_rate",
        "tax_label",
        "brand",
    )
    base: dict[str, Any] = {k: source_payload[k] for k in shared_keys if k in source_payload}

    if pair == ("quotation", "invoice"):
        notes = source_payload.get("notes")
        ref_note = f"Converted from Quotation {source_number}."
        if notes:
            notes = f"{notes}\n{ref_note}" if ref_note not in notes else notes
        else:
            notes = ref_note

        invoice_data: dict[str, Any] = {
            **base,
            "invoice_number": "AUTO",
            "issue_date": date.today().isoformat(),
            "status": "UNPAID",
            "notes": notes,
        }
        if due_date:
            invoice_data["due_date"] = due_date
        if source_payload.get("payment"):
            invoice_data["payment"] = source_payload["payment"]
        return invoice_data

    # ("invoice", "receipt")
    src_payment = source_payload.get("payment") or {}
    method = payment_method or src_payment.get("method") or "Bank Transfer"
    reference = payment_reference or src_payment.get("reference")

    receipt_data: dict[str, Any] = {
        **base,
        "receipt_number": "AUTO",
        "invoice_number": source_number,
        "payment_date": payment_date or date.today().isoformat(),
        "payment_method": method,
    }
    if reference:
        receipt_data["payment_reference"] = reference
    if amount_paid is not None:
        receipt_data["amount_paid"] = amount_paid
    if source_payload.get("notes"):
        receipt_data["notes"] = source_payload["notes"]
    return receipt_data


def convert_document(
    ledger: Ledger,
    source_number: str,
    target_type: str,
    output_pdf: Path,
    *,
    profile: str | None = "business",
    brand_path: Path | None = None,
    output_html: Path | None = None,
    home: Path | None = None,
    template: str | Path | None = None,
    due_date: str | None = None,
    payment_date: str | None = None,
    payment_method: str | None = None,
    payment_reference: str | None = None,
    amount_paid: float | None = None,
    record_in_ledger: bool = True,
    update_source_status: bool = True,
) -> dict[str, Any]:
    """Convert an existing tracked document in the ledger into a target document type."""
    record = ledger.get_document(source_number)
    if record is None:
        raise FileNotFoundError(f"Document '{source_number}' not found in ledger.")

    source_type = record["doc_type"].lower()
    target = target_type.strip().lower()
    source_payload = _load_source_payload(record)

    target_payload = build_converted_payload(
        source_type,
        target,
        source_number,
        source_payload,
        due_date=due_date,
        payment_date=payment_date,
        payment_method=payment_method,
        payment_reference=payment_reference,
        amount_paid=amount_paid,
    )

    gen_ledger = ledger if record_in_ledger else None
    if not record_in_ledger:
        if target == "invoice":
            target_payload["invoice_number"] = ledger.next_number("invoice")
        elif target == "receipt":
            target_payload["receipt_number"] = ledger.next_number("receipt")

    if target == "invoice":
        result = generate_invoice(
            target_payload,
            output_pdf=output_pdf,
            profile=profile,
            brand_path=brand_path,
            output_html=output_html,
            ledger=gen_ledger,
            home=home,
            template=template,
        )
        if record_in_ledger and update_source_status:
            ledger.update_status(source_number, "ACCEPTED")
    elif target == "receipt":
        result = generate_receipt(
            target_payload,
            output_pdf=output_pdf,
            profile=profile,
            brand_path=brand_path,
            output_html=output_html,
            ledger=gen_ledger,
            home=home,
            template=template,
        )
        if record_in_ledger and update_source_status:
            if result["balance_due"] == 0:
                ledger.update_status(source_number, "PAID", balance_due=0.0)
            else:
                ledger.update_status(source_number, "PARTIAL", balance_due=result["balance_due"])
    else:
        raise ValueError(f"Unsupported target type '{target_type}'.")

    result["converted_from"] = source_number
    return result
