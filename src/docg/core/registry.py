from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel

from docg.tools.agreement.generator import generate_agreement
from docg.tools.agreement.models import AgreementData
from docg.tools.invoice.generator import generate_invoice
from docg.tools.invoice.models import InvoiceData
from docg.tools.letter.generator import generate_letter
from docg.tools.letter.models import LetterData
from docg.tools.quotation.generator import generate_quotation
from docg.tools.quotation.models import QuotationData
from docg.tools.receipt.generator import generate_receipt
from docg.tools.receipt.models import ReceiptData
from docg.tools.resume.generator import generate_resume
from docg.tools.resume.models import ResumeData


@dataclass(frozen=True)
class DocTool:
    name: str
    description: str
    model: type[BaseModel]
    generator: Callable[..., dict[str, Any]]
    default_profile: str
    example_file: str
    uses_ledger: bool = False
    client_field: str | None = None


REGISTRY: dict[str, DocTool] = {
    "invoice": DocTool(
        name="invoice",
        description="Itemized business invoice with tax, discount, deposit, and payment details.",
        model=InvoiceData,
        generator=generate_invoice,
        default_profile="business",
        example_file="invoice_sample.yaml",
        uses_ledger=True,
        client_field="client",
    ),
    "quotation": DocTool(
        name="quotation",
        description="Itemized business quotation / estimate with validity date, deposit, and terms.",
        model=QuotationData,
        generator=generate_quotation,
        default_profile="business",
        example_file="quotation_sample.yaml",
        uses_ledger=True,
        client_field="client",
    ),
    "receipt": DocTool(
        name="receipt",
        description="Payment receipt acknowledging full or partial payment against an invoice or order.",
        model=ReceiptData,
        generator=generate_receipt,
        default_profile="business",
        example_file="receipt_sample.yaml",
        uses_ledger=True,
        client_field="client",
    ),
    "agreement": DocTool(
        name="agreement",
        description="Service agreement or contract letter with commercial summary, clauses, and signatures.",
        model=AgreementData,
        generator=generate_agreement,
        default_profile="business",
        example_file="agreement_sample.yaml",
        uses_ledger=True,
        client_field="client",
    ),
    "resume": DocTool(
        name="resume",
        description="Clean, ATS-friendly single-column PDF resume.",
        model=ResumeData,
        generator=generate_resume,
        default_profile="personal",
        example_file="resume_sample.yaml",
        uses_ledger=False,
        client_field=None,
    ),
    "letter": DocTool(
        name="letter",
        description="Formal letter, cover letter, or official correspondence on consistent letterhead.",
        model=LetterData,
        generator=generate_letter,
        default_profile="personal",
        example_file="letter_sample.yaml",
        uses_ledger=True,
        client_field="recipient",
    ),
}


def get_tool(doc_type: str) -> DocTool:
    key = doc_type.strip().lower()
    if key not in REGISTRY:
        available = ", ".join(sorted(REGISTRY.keys()))
        raise KeyError(f"Unknown document type '{doc_type}'. Available: {available}")
    return REGISTRY[key]
