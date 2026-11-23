from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from business_tools.core.models import BrandConfig

CORE_TEMPLATES_DIR = Path(__file__).parent / "templates"
DEFAULT_BRAND_PATH = Path(__file__).resolve().parents[3] / "config" / "default_brand.yaml"


def load_data_file(path: Path) -> dict[str, Any]:
    """Load structured document data from a YAML or JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    raw = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(raw)
    elif suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(raw)
    else:
        raise ValueError(f"Unsupported file extension '{suffix}'. Use .yaml, .yml, or .json.")

    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping/object at root of {path}")
    return data


def resolve_brand(
    inline_brand: dict[str, Any] | BrandConfig | None = None,
    brand_path: Path | None = None,
) -> BrandConfig:
    """Resolve BrandConfig by merging default brand file, optional --brand file, and inline overrides."""
    merged: dict[str, Any] = {}

    if DEFAULT_BRAND_PATH.exists():
        merged.update(load_data_file(DEFAULT_BRAND_PATH))

    if brand_path is not None:
        merged.update(load_data_file(brand_path))

    if inline_brand is not None:
        if isinstance(inline_brand, BrandConfig):
            merged.update(inline_brand.model_dump(exclude_none=True))
        else:
            merged.update({k: v for k, v in inline_brand.items() if v is not None})

    return BrandConfig.model_validate(merged)


def render_document(
    template_dir: Path,
    template_name: str,
    context: dict[str, Any],
    output_pdf: Path,
    output_html: Path | None = None,
) -> Path:
    """Render a document template extending core base.html into a PDF (and optional HTML)."""
    loader = ChoiceLoader(
        [
            FileSystemLoader(str(template_dir)),
            FileSystemLoader(str(CORE_TEMPLATES_DIR)),
        ]
    )
    env = Environment(
        loader=loader,
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    shared_css = (CORE_TEMPLATES_DIR / "styles.css").read_text(encoding="utf-8")
    brand: BrandConfig = context["brand"]

    logo_uri: str | None = None
    if brand.logo_path and brand.logo_path.exists():
        logo_uri = brand.logo_path.resolve().as_uri()

    footer_text = brand.footer_note or f"{brand.name} — Confidential"

    full_context = {
        **context,
        "shared_css": shared_css,
        "logo_uri": logo_uri,
        "footer_text": footer_text,
    }

    template = env.get_template(template_name)
    html_str = template.render(**full_context)

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    if output_html is not None:
        output_html.parent.mkdir(parents=True, exist_ok=True)
        output_html.write_text(html_str, encoding="utf-8")

    HTML(string=html_str, base_url=str(template_dir)).write_pdf(str(output_pdf))
    return output_pdf
