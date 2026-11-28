from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from docg.cli import app
from docg.core.converter import convert_document
from docg.core.ledger import Ledger
from docg.core.renderer import load_data_file
from docg.tools.quotation.generator import generate_quotation
from docg.tools.receipt.generator import generate_receipt

runner = CliRunner()
REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_BRAND = REPO_ROOT / "config" / "default_brand.example.yaml"


def _setup_xdg(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    cfg_dir = tmp_path / "xdg_config" / "docg"
    dat_dir = tmp_path / "xdg_data" / "docg"
    monkeypatch.setenv("DOCG_CONFIG_DIR", str(cfg_dir))
    monkeypatch.setenv("DOCG_DATA_DIR", str(dat_dir))
    monkeypatch.delenv("DOCG_HOME", raising=False)
    assert runner.invoke(app, ["init"]).exit_code == 0
    return cfg_dir, dat_dir


def test_generate_quotation_and_receipt_from_samples(tmp_path: Path) -> None:
    quo_pdf = tmp_path / "quotation.pdf"
    quo_html = tmp_path / "quotation.html"
    quo_res = generate_quotation(
        load_data_file(REPO_ROOT / "examples" / "quotation_sample.yaml"),
        output_pdf=quo_pdf,
        output_html=quo_html,
        brand_path=EXAMPLE_BRAND,
    )
    assert quo_pdf.exists() and quo_pdf.stat().st_size > 1000
    assert quo_res["doc_number"] == "QUO-2026-001"
    assert quo_res["total"] == 3350.0
    html = quo_html.read_text(encoding="utf-8")
    assert "QUOTATION" in html
    assert "QUO-2026-001" in html
    assert "RM 3,350.00" in html
    assert "RM 1,675.00" in html

    rec_pdf = tmp_path / "receipt.pdf"
    rec_html = tmp_path / "receipt.html"
    rec_res = generate_receipt(
        load_data_file(REPO_ROOT / "examples" / "receipt_sample.yaml"),
        output_pdf=rec_pdf,
        output_html=rec_html,
        brand_path=EXAMPLE_BRAND,
    )
    assert rec_pdf.exists() and rec_pdf.stat().st_size > 1000
    assert rec_res["doc_number"] == "REC-2026-001"
    assert rec_res["amount_paid"] == 3350.0
    assert rec_res["balance_due"] == 0.0
    assert rec_res["status"] == "PAID"
    rhtml = rec_html.read_text(encoding="utf-8")
    assert "RECEIPT" in rhtml
    assert "REC-2026-001" in rhtml
    assert "DN-20261128-88412" in rhtml


def test_client_directory_cli_and_generate_merge(tmp_path: Path, monkeypatch) -> None:
    cfg_dir, _ = _setup_xdg(tmp_path, monkeypatch)

    res_add = runner.invoke(
        app,
        [
            "clients",
            "add",
            "acme",
            "--name",
            "Jane Doe",
            "--company",
            "Acme Sdn Bhd",
            "--email",
            "jane@acme.my",
            "--address",
            "Level 10, Menara Acme",
            "--address",
            "50450 Kuala Lumpur",
            "--reg",
            "202401001234",
            "--json",
        ],
    )
    assert res_add.exit_code == 0
    assert (cfg_dir / "clients" / "acme.yaml").exists()

    res_list = runner.invoke(app, ["clients", "--json"])
    assert res_list.exit_code == 0
    assert json.loads(res_list.stdout)["clients"] == ["acme"]

    res_show = runner.invoke(app, ["clients", "show", "acme", "--json"])
    assert res_show.exit_code == 0
    assert json.loads(res_show.stdout)["company"] == "Acme Sdn Bhd"

    # Generate invoice using --client acme without specifying client in payload
    inv_pdf = tmp_path / "acme_inv.pdf"
    inv_html = tmp_path / "acme_inv.html"
    payload = json.dumps(
        {
            "invoice_number": "AUTO",
            "currency": "MYR",
            "project_title": "Monthly Retainer",
            "items": [{"title": "Engineering Support", "quantity": 1, "unit_price": 1500.0}],
        }
    )
    res_gen = runner.invoke(
        app,
        [
            "generate",
            "invoice",
            "-",
            "--client",
            "acme",
            "-o",
            str(inv_pdf),
            "--html",
            str(inv_html),
            "--json",
        ],
        input=payload,
    )
    assert res_gen.exit_code == 0, res_gen.stdout + res_gen.stderr
    assert inv_pdf.exists()
    html = inv_html.read_text(encoding="utf-8")
    assert "Acme Sdn Bhd" in html
    assert "Jane Doe" in html
    assert "202401001234" in html

    # Also test string shorthand `recipient: "acme"` for letter
    ltr_pdf = tmp_path / "acme_letter.pdf"
    ltr_html = tmp_path / "acme_letter.html"
    letter_payload = json.dumps(
        {
            "recipient": "acme",
            "subject": "Project Kickoff",
            "paragraphs": ["We are excited to start working together."],
        }
    )
    res_ltr = runner.invoke(
        app,
        ["generate", "letter", "-", "-o", str(ltr_pdf), "--html", str(ltr_html), "--json"],
        input=letter_payload,
    )
    assert res_ltr.exit_code == 0, res_ltr.stdout + res_ltr.stderr
    assert "Acme Sdn Bhd" in ltr_html.read_text(encoding="utf-8")

    # Remove client
    res_rm = runner.invoke(app, ["clients", "rm", "acme"])
    assert res_rm.exit_code == 0
    assert json.loads(runner.invoke(app, ["clients", "--json"]).stdout)["clients"] == []


def test_convert_quotation_to_invoice_to_receipt_lifecycle(tmp_path: Path, monkeypatch) -> None:
    _setup_xdg(tmp_path, monkeypatch)

    # 1. Generate Quotation
    quo_pdf = tmp_path / "quo.pdf"
    quo_payload = json.dumps(
        {
            "quotation_number": "AUTO",
            "currency": "MYR",
            "project_title": "API Integration",
            "client": {"name": "Ali Hassan", "company": "Bintang Tech"},
            "items": [{"title": "Backend API", "quantity": 1, "unit_price": 2000.0}],
            "tax_rate": 8.0,
            "tax_label": "SST",
        }
    )
    res_quo = runner.invoke(
        app, ["generate", "quotation", "-", "-o", str(quo_pdf), "--json"], input=quo_payload
    )
    assert res_quo.exit_code == 0, res_quo.stdout + res_quo.stderr
    quo_data = json.loads(res_quo.stdout)
    quo_num = quo_data["doc_number"]
    assert quo_num.startswith("QUO-")
    assert quo_data["total"] == 2160.0

    # 2. Convert Quotation -> Invoice
    inv_pdf = tmp_path / "inv.pdf"
    inv_html = tmp_path / "inv.html"
    res_inv = runner.invoke(
        app,
        [
            "convert",
            quo_num,
            "--to",
            "invoice",
            "--due-date",
            "2026-12-15",
            "-o",
            str(inv_pdf),
            "--html",
            str(inv_html),
            "--json",
        ],
    )
    assert res_inv.exit_code == 0, res_inv.stdout + res_inv.stderr
    inv_data = json.loads(res_inv.stdout)
    inv_num = inv_data["doc_number"]
    assert inv_num.startswith("INV-")
    assert inv_data["converted_from"] == quo_num
    assert inv_data["total"] == 2160.0
    assert "Bintang Tech" in inv_html.read_text(encoding="utf-8")

    # 3. Convert Invoice -> Receipt via `docg status <inv> PAID --receipt`
    rec_pdf = tmp_path / "rec.pdf"
    res_paid = runner.invoke(
        app,
        [
            "status",
            inv_num,
            "PAID",
            "--receipt",
            "--payment-method",
            "DuitNow",
            "--reference",
            "TXN-999",
            "-o",
            str(rec_pdf),
            "--json",
        ],
    )
    assert res_paid.exit_code == 0, res_paid.stdout + res_paid.stderr
    paid_data = json.loads(res_paid.stdout)
    assert paid_data["status"] == "PAID"
    assert paid_data["receipt"]["doc_number"].startswith("REC-")
    assert paid_data["receipt"]["amount_paid"] == 2160.0
    assert rec_pdf.exists()

    # Verify ledger states
    res_list = runner.invoke(app, ["list", "--json"])
    docs = {d["doc_number"]: d for d in json.loads(res_list.stdout)}
    assert docs[quo_num]["status"] == "ACCEPTED"
    assert docs[inv_num]["status"] == "PAID"
    assert docs[inv_num]["balance_due"] == 0.0
    assert docs[paid_data["receipt"]["doc_number"]]["status"] == "PAID"


def test_convert_direct_helper_partial_payment(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "ledger.db")
    quo = generate_quotation(
        {
            "quotation_number": "AUTO",
            "client": {"name": "Bob"},
            "items": [{"title": "Design", "quantity": 1, "unit_price": 1000.0}],
        },
        output_pdf=tmp_path / "q.pdf",
        brand_path=EXAMPLE_BRAND,
        ledger=ledger,
    )
    inv = convert_document(
        ledger, quo["doc_number"], "invoice", output_pdf=tmp_path / "i.pdf", brand_path=EXAMPLE_BRAND
    )
    rec = convert_document(
        ledger,
        inv["doc_number"],
        "receipt",
        output_pdf=tmp_path / "r.pdf",
        brand_path=EXAMPLE_BRAND,
        amount_paid=400.0,
    )
    assert rec["status"] == "PARTIAL"
    assert rec["balance_due"] == 600.0
    inv_row = ledger.get_document(inv["doc_number"])
    assert inv_row is not None
    assert inv_row["status"] == "PARTIAL"
    assert inv_row["balance_due"] == 600.0
