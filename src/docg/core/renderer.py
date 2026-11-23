from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from docg.core.models import BrandConfig
from docg.core.paths import default_brand_path, profiles_dir

CORE_TEMPLATES_DIR = Path(__file__).parent / "templates"


def load_data_text(raw: str, source: str = "<stdin>") -> dict[str, Any]:
    """Parse YAML or JSON text into a dictionary."""
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping/object at root of {source}")
    return data


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


def list_profiles(home: Path | None = None) -> list[str]:
    """List available named profile files under config/profiles/."""
    pdir = profiles_dir(home)
    if not pdir.is_dir():
        return []
    return sorted(
        p.stem for p in pdir.iterdir() if p.is_file() and p.suffix.lower() in {".yaml", ".yml", ".json"}
    )


def resolve_profile_path(profile: str, home: Path | None = None) -> Path:
    """Resolve a profile name (e.g. 'nedays' or 'personal') to its file path."""
    pdir = profiles_dir(home)
    for ext in (".yaml", ".yml", ".json"):
        candidate = pdir / f"{profile}{ext}"
        if candidate.exists():
            return candidate
    available = ", ".join(list_profiles(home)) or "none"
    raise FileNotFoundError(f"Profile '{profile}' not found in {pdir}. Available: {available}")


def resolve_brand(
    inline_brand: dict[str, Any] | BrandConfig | None = None,
    profile: str | None = None,
    brand_path: Path | None = None,
    home: Path | None = None,
) -> BrandConfig:
    """Resolve BrandConfig by merging profile/default brand, optional --brand file, and inline overrides."""
    merged: dict[str, Any] = {}

    if profile is not None:
        merged.update(load_data_file(resolve_profile_path(profile, home=home)))
    else:
        fallback = default_brand_path(home)
        if fallback.exists():
            merged.update(load_data_file(fallback))

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

    footer_text = brand.footer_note or f"{brand.name}"

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
