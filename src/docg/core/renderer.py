from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from docg.core.models import BrandConfig, Party
from docg.core.paths import clients_dir, default_brand_path, profiles_dir, templates_dir

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


def list_clients(home: Path | None = None) -> list[str]:
    """List available saved client files under config/clients/."""
    cdir = clients_dir(home)
    if not cdir.is_dir():
        return []
    return sorted(
        p.stem for p in cdir.iterdir() if p.is_file() and p.suffix.lower() in {".yaml", ".yml", ".json"}
    )


def resolve_client_path(client: str | Path, home: Path | None = None) -> Path:
    """Resolve a saved client slug or direct file path to its Party file."""
    raw = Path(client).expanduser()
    if raw.is_file():
        return raw.resolve()

    cdir = clients_dir(home)
    slug = str(client).strip()
    for ext in (".yaml", ".yml", ".json"):
        candidate = cdir / f"{slug}{ext}"
        if candidate.exists():
            return candidate
    available = ", ".join(list_clients(home)) or "none"
    raise FileNotFoundError(
        f"Client '{client}' not found in {cdir}. Available: {available}."
    )


def load_client(client: str | Path, home: Path | None = None) -> Party:
    """Load and validate a saved client Party record."""
    data = load_data_file(resolve_client_path(client, home=home))
    return Party.model_validate(data)


def save_client(
    slug: str,
    party: Party | dict[str, Any],
    home: Path | None = None,
    *,
    overwrite: bool = False,
) -> Path:
    """Save a client Party record to ~/.config/docg/clients/<slug>.yaml."""
    clean_slug = slug.strip()
    if not clean_slug or "/" in clean_slug or "\\" in clean_slug or clean_slug in {".", ".."}:
        raise ValueError(f"Invalid client slug '{slug}'.")
    validated = party if isinstance(party, Party) else Party.model_validate(party)
    cdir = clients_dir(home)
    cdir.mkdir(parents=True, exist_ok=True)
    target = cdir / f"{clean_slug}.yaml"
    if target.exists() and not overwrite:
        raise FileExistsError(f"Client '{clean_slug}' already exists at {target}. Use --force to overwrite.")
    payload = validated.model_dump(exclude_none=True)
    if not payload.get("address"):
        payload.pop("address", None)
    target.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return target


def merge_client_into_data(
    data: dict[str, Any],
    *,
    field_name: str,
    client_override: str | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    """Merge a saved client record into data[field_name] (CLI --client or string shorthand in YAML)."""
    existing = data.get(field_name)
    slug = client_override
    inline: dict[str, Any] = {}

    if isinstance(existing, str):
        if slug is None:
            slug = existing
    elif isinstance(existing, dict):
        inline = existing

    if slug is None:
        return data

    saved = load_client(slug, home=home).model_dump(exclude_none=True)
    if not saved.get("address"):
        saved.pop("address", None)
    merged = {**saved, **{k: v for k, v in inline.items() if v is not None}}
    return {**data, field_name: merged}


def list_templates(doc_type: str | None = None, home: Path | None = None) -> dict[str, list[str]]:
    """List saved custom HTML templates under ~/.config/docg/templates/<doc_type>/."""
    if doc_type is not None:
        key = doc_type.strip().lower()
        tdir = templates_dir(home, key)
        if not tdir.is_dir():
            return {key: []}
        return {
            key: sorted(p.stem for p in tdir.iterdir() if p.is_file() and p.suffix.lower() == ".html")
        }

    root = templates_dir(home)
    if not root.is_dir():
        return {}
    result: dict[str, list[str]] = {}
    for sub in sorted(root.iterdir()):
        if sub.is_dir():
            names = sorted(p.stem for p in sub.iterdir() if p.is_file() and p.suffix.lower() == ".html")
            if names:
                result[sub.name] = names
    return result


def resolve_template(
    doc_type: str,
    template: str | Path | None,
    *,
    default_dir: Path,
    default_name: str = "template.html",
    home: Path | None = None,
) -> tuple[Path, str]:
    """Resolve a custom template by file path or saved name in ~/.config/docg/templates/<doc_type>/."""
    if template is None:
        return default_dir, default_name

    raw = Path(template).expanduser()
    if raw.is_file():
        resolved = raw.resolve()
        return resolved.parent, resolved.name

    tdir = templates_dir(home, doc_type)
    name = str(template).strip()
    candidates = [tdir / name]
    if not name.lower().endswith(".html"):
        candidates.insert(0, tdir / f"{name}.html")

    for candidate in candidates:
        if candidate.is_file():
            resolved = candidate.resolve()
            return resolved.parent, resolved.name

    available = ", ".join(list_templates(doc_type, home=home).get(doc_type.strip().lower(), [])) or "none"
    raise FileNotFoundError(
        f"Template '{template}' not found for '{doc_type}' in {tdir}. Available: {available}."
    )


def resolve_profile_path(profile: str, home: Path | None = None) -> Path:
    """Resolve a profile name (e.g. 'business' or 'personal') to its file path."""
    pdir = profiles_dir(home)
    for ext in (".yaml", ".yml", ".json"):
        candidate = pdir / f"{profile}{ext}"
        if candidate.exists():
            return candidate
    available = ", ".join(list_profiles(home)) or "none"
    raise FileNotFoundError(
        f"Profile '{profile}' not found in {pdir}. Available: {available}. "
        "Run 'docg init' to create starter profiles."
    )


def resolve_brand(
    inline_brand: dict[str, Any] | BrandConfig | None = None,
    profile: str | None = None,
    brand_path: Path | None = None,
    home: Path | None = None,
    strict_profile: bool = False,
) -> BrandConfig:
    """Resolve BrandConfig by merging profile/default brand, optional --brand file, and inline overrides."""
    merged: dict[str, Any] = {}

    if profile is not None:
        try:
            merged.update(load_data_file(resolve_profile_path(profile, home=home)))
        except FileNotFoundError:
            if strict_profile:
                raise
            fallback = default_brand_path(home)
            if fallback.exists():
                merged.update(load_data_file(fallback))
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
