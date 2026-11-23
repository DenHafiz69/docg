from __future__ import annotations

from pathlib import Path

from docg.core.ledger import Ledger
from docg.tools.agreement.generator import generate_agreement
from docg.tools.invoice.generator import generate_invoice


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_BRAND = REPO_ROOT / "config" / "default_brand.example.yaml"


def test_ledger_auto_numbering_and_status(tmp_path: Path) -> None:
    db_path = tmp_path / "ledger.db"
    ledger = Ledger(db_path)

    assert ledger.next_number("invoice", year=2026) == "INV-2026-001"

    generate_invoice(
        {
            "issue_date": "2026-11-20",
            "currency": "MYR",
            "client": {"name": "Client A"},
            "items": [{"title": "Setup", "quantity": 1, "unit_price": 500.0}],
        },
        output_pdf=tmp_path / "inv1.pdf",
        brand_path=EXAMPLE_BRAND,
        ledger=ledger,
    )

    assert ledger.next_number("invoice", year=2026) == "INV-2026-002"

    generate_agreement(
        {
            "agreement_number": "AUTO",
            "effective_date": "2026-11-20",
            "title": "Test Agreement",
            "client": {"name": "Client A"},
        },
        output_pdf=tmp_path / "agr1.pdf",
        brand_path=EXAMPLE_BRAND,
        ledger=ledger,
    )

    docs = ledger.list_documents()
    assert len(docs) == 2
    assert {d["doc_number"] for d in docs} == {"INV-2026-001", "AGR-2026-001"}

    assert ledger.update_status("INV-2026-001", "PAID") is True
    inv_rows = ledger.list_documents(doc_type="invoice", status="PAID")
    assert len(inv_rows) == 1
    assert inv_rows[0]["balance_due"] == 0.0
