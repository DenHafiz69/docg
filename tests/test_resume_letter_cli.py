from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from docg.cli import app
from docg.core.renderer import load_data_file
from docg.tools.letter.generator import generate_letter
from docg.tools.resume.generator import generate_resume

runner = CliRunner()


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PERSONAL_BRAND = REPO_ROOT / "config" / "profiles" / "personal.example.yaml"


def test_generate_resume_from_sample(tmp_path: Path) -> None:
    sample = REPO_ROOT / "examples" / "resume_sample.yaml"
    out_pdf = tmp_path / "resume.pdf"
    out_html = tmp_path / "resume.html"

    result = generate_resume(
        load_data_file(sample),
        output_pdf=out_pdf,
        output_html=out_html,
        profile=None,
        brand_path=EXAMPLE_PERSONAL_BRAND,
    )

    assert Path(result["pdf"]) == out_pdf.resolve()
    assert out_pdf.exists() and out_pdf.stat().st_size > 1000
    html = out_html.read_text(encoding="utf-8")
    assert "Alex Morgan" in html
    assert "Full-Stack Web Developer" in html
    assert "#0284C7" in html


def test_generate_letter_from_sample(tmp_path: Path) -> None:
    sample = REPO_ROOT / "examples" / "letter_sample.yaml"
    out_pdf = tmp_path / "letter.pdf"
    out_html = tmp_path / "letter.html"

    result = generate_letter(
        load_data_file(sample),
        output_pdf=out_pdf,
        output_html=out_html,
        profile=None,
        brand_path=EXAMPLE_PERSONAL_BRAND,
    )

    assert Path(result["pdf"]) == out_pdf.resolve()
    assert out_pdf.exists() and out_pdf.stat().st_size > 1000
    html = out_html.read_text(encoding="utf-8")
    assert "COVER LETTER" in html
    assert "Acme Digital Sdn Bhd" in html
    assert "Alex Morgan" in html


def test_cli_schema_types_and_stdin_generate(tmp_path: Path) -> None:
    res_types = runner.invoke(app, ["types", "--json"])
    assert res_types.exit_code == 0
    names = {item["name"] for item in json.loads(res_types.stdout)}
    assert {"invoice", "agreement", "resume", "letter"} <= names

    res_schema = runner.invoke(app, ["schema", "resume"])
    assert res_schema.exit_code == 0
    schema = json.loads(res_schema.stdout)
    assert "experience" in schema["properties"]

    payload = json.dumps(
        {
            "brand": {"name": "Alex Morgan"},
            "headline": "Backend Engineer",
            "summary": "Building reliable Python CLIs.",
            "skills": [{"category": "Core", "items": ["Python", "SQLite"]}],
        }
    )

    res_val = runner.invoke(app, ["generate", "resume", "-", "--validate", "--json"], input=payload)
    assert res_val.exit_code == 0
    assert json.loads(res_val.stdout)["valid"] is True

    out_pdf = tmp_path / "stdin_resume.pdf"
    res_gen = runner.invoke(
        app,
        ["generate", "resume", "-", "-o", str(out_pdf), "--brand", str(EXAMPLE_PERSONAL_BRAND), "--json"],
        input=payload,
    )
    assert res_gen.exit_code == 0
    data = json.loads(res_gen.stdout)
    assert Path(data["pdf"]).exists()


def test_cli_init_and_paths_global_xdg(tmp_path: Path, monkeypatch) -> None:
    cfg_dir = tmp_path / "xdg_config" / "docg"
    dat_dir = tmp_path / "xdg_data" / "docg"
    monkeypatch.setenv("DOCG_CONFIG_DIR", str(cfg_dir))
    monkeypatch.setenv("DOCG_DATA_DIR", str(dat_dir))
    monkeypatch.delenv("DOCG_HOME", raising=False)

    res_init = runner.invoke(app, ["init", "--json"])
    assert res_init.exit_code == 0
    init_data = json.loads(res_init.stdout)
    assert Path(init_data["config_dir"]) == cfg_dir
    assert Path(init_data["data_dir"]) == dat_dir
    assert (cfg_dir / "default_brand.yaml").exists()
    assert (cfg_dir / "default_payment.yaml").exists()
    assert (cfg_dir / "profiles" / "business.yaml").exists()
    assert (cfg_dir / "profiles" / "personal.yaml").exists()

    res_paths = runner.invoke(app, ["paths", "--json"])
    assert res_paths.exit_code == 0
    paths_data = json.loads(res_paths.stdout)
    assert Path(paths_data["ledger_path"]) == dat_dir / "ledger.db"
    assert Path(paths_data["resume_master"]) == cfg_dir / "resume_master.yaml"
    assert Path(paths_data["examples_dir"]).is_dir()
    assert Path(paths_data["skill_file"]).exists()

    res_profiles = runner.invoke(app, ["profiles", "--json"])
    assert res_profiles.exit_code == 0
    prof_data = json.loads(res_profiles.stdout)
    assert set(prof_data["profiles"]) == {"business", "personal"}
