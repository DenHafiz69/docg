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


REGISTRY: dict[str, DocTool] = {
    "invoice": DocTool(
        name="invoice",
        description="Itemized business invoice with tax, discount, deposit, and payment details.",
        model=InvoiceData,
        generator=generate_invoice,
        default_profile="nedays",
        example_file="invoice_sample.yaml",
        uses_ledger=True,
    ),
    "agreement": DocTool(
        name="agreement",
        description="Service agreement or contract letter with commercial summary, clauses, and signatures.",
        model=AgreementData,
        generator=generate_agreement,
        default_profile="nedays",
        example_file="agreement_sample.yaml",
        uses_ledger=True,
    ),
    "resume": DocTool(
        name="resume",
        description="Clean, ATS-friendly single-column PDF resume.",
        model=ResumeData,
        generator=generate_resume,
        default_profile="personal",
        example_file="resume_sample.yaml",
        uses_ledger=False,
    ),
    "letter": DocTool(
        name="letter",
        description="Formal letter, cover letter, or official correspondence on consistent letterhead.",
        model=LetterData,
        generator=generate_letter,
        default_profile="personal",
        example_file="letter_sample.yaml",
        uses_ledger=True,
    ),
}


def get_tool(doc_type: str) -> DocTool:
    key = doc_type.strip().lower()
    if key not in REGISTRY:
        available = ", ".join(sorted(REGISTRY.keys()))
        raise KeyError(f"Unknown document type '{doc_type}'. Available: {available}")
    return REGISTRY[key]
