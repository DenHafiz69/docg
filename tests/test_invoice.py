from __future__ import annotations

from pathlib import Path

from docg.core.renderer import load_data_file
from docg.tools.invoice.generator import generate_invoice


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_BRAND = REPO_ROOT / "config" / "default_brand.example.yaml"


def test_generate_invoice_from_sample(tmp_path: Path) -> None:
    sample = REPO_ROOT / "examples" / "invoice_sample.yaml"
    out_pdf = tmp_path / "invoice.pdf"
    out_html = tmp_path / "invoice.html"

    result = generate_invoice(
        load_data_file(sample), output_pdf=out_pdf, output_html=out_html, brand_path=EXAMPLE_BRAND
    )

    assert Path(result["pdf"]) == out_pdf.resolve()
    assert out_pdf.exists() and out_pdf.stat().st_size > 1000
    html = out_html.read_text(encoding="utf-8")
    assert "INV-2026-001" in html
    assert "Klinik Medisave KL" in html
    assert "RM 3,350.00" in html
    assert "RM 2,350.00" in html
    assert "#0284C7" in html


def test_invoice_tax_and_discount(tmp_path: Path) -> None:
    out_pdf = tmp_path / "tax_invoice.pdf"
    out_html = tmp_path / "tax_invoice.html"

    result = generate_invoice(
        {
            "invoice_number": "INV-2026-002",
            "currency": "USD",
            "client": {"name": "Alice Tan"},
            "items": [
                {"title": "Consulting", "quantity": 2, "unit": "hrs", "unit_price": 100.0},
            ],
            "discount_percent": 10.0,
            "tax_rate": 8.0,
            "tax_label": "SST",
        },
        output_pdf=out_pdf,
        output_html=out_html,
        brand_path=EXAMPLE_BRAND,
    )

    assert out_pdf.exists()
    assert result["total"] == 194.4
    html = out_html.read_text(encoding="utf-8")
    assert "$ 200.00" in html
    assert "-$ 20.00" in html
    assert "$ 14.40" in html
    assert "$ 194.40" in html
