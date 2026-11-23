from __future__ import annotations

from pathlib import Path

from docg.core.renderer import load_data_file
from docg.tools.agreement.generator import generate_agreement


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_BRAND = REPO_ROOT / "config" / "default_brand.example.yaml"


def test_generate_agreement_from_sample(tmp_path: Path) -> None:
    sample = REPO_ROOT / "examples" / "agreement_sample.yaml"
    out_pdf = tmp_path / "agreement.pdf"
    out_html = tmp_path / "agreement.html"

    result = generate_agreement(
        load_data_file(sample), output_pdf=out_pdf, output_html=out_html, brand_path=EXAMPLE_BRAND
    )

    assert Path(result["pdf"]) == out_pdf.resolve()
    assert out_pdf.exists() and out_pdf.stat().st_size > 1000
    html = out_html.read_text(encoding="utf-8")
    assert "AGR-2026-001" in html
    assert "AGREEMENT LETTER" in html
    assert "Klinik Medisave KL" in html
    assert "#0284C7" in html
