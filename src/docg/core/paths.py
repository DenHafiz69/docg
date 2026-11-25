from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PACKAGE_ROOT / "assets"
REPO_ROOT = Path(__file__).resolve().parents[3]


def _xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")).expanduser().resolve()


def _xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")).expanduser().resolve()


def resolve_config_dir(home: Path | None = None) -> Path:
    """Resolve the global configuration directory holding profiles and defaults.

    Priority:
    1. Explicit --home argument (<home>/config)
    2. DOCG_HOME environment variable (<DOCG_HOME>/config)
    3. DOCG_CONFIG_DIR environment variable
    4. XDG config directory (~/.config/docg)
    """
    if home is not None:
        return home.expanduser().resolve() / "config"

    env_home = os.environ.get("DOCG_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve() / "config"

    env_config = os.environ.get("DOCG_CONFIG_DIR")
    if env_config:
        return Path(env_config).expanduser().resolve()

    return _xdg_config_home() / "docg"


def resolve_data_dir(home: Path | None = None) -> Path:
    """Resolve the global data directory holding the SQLite ledger.

    Priority:
    1. Explicit --home argument (<home>/data)
    2. DOCG_HOME environment variable (<DOCG_HOME>/data)
    3. DOCG_DATA_DIR environment variable
    4. XDG data directory (~/.local/share/docg)
    """
    if home is not None:
        return home.expanduser().resolve() / "data"

    env_home = os.environ.get("DOCG_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve() / "data"

    env_data = os.environ.get("DOCG_DATA_DIR")
    if env_data:
        return Path(env_data).expanduser().resolve()

    return _xdg_data_home() / "docg"


def resolve_home(home: Path | None = None) -> Path:
    """Resolve the unified workspace root when --home or DOCG_HOME is set, otherwise config dir."""
    if home is not None:
        return home.expanduser().resolve()
    env_home = os.environ.get("DOCG_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()
    return resolve_config_dir()


def profiles_dir(home: Path | None = None) -> Path:
    return resolve_config_dir(home) / "profiles"


def default_brand_path(home: Path | None = None) -> Path:
    return resolve_config_dir(home) / "default_brand.yaml"


def default_payment_path(home: Path | None = None) -> Path:
    return resolve_config_dir(home) / "default_payment.yaml"


def resume_master_path(home: Path | None = None) -> Path:
    return resolve_config_dir(home) / "resume_master.yaml"


def templates_dir(home: Path | None = None, doc_type: str | None = None) -> Path:
    base = resolve_config_dir(home) / "templates"
    if doc_type:
        return base / doc_type.strip().lower()
    return base


def default_ledger_path(home: Path | None = None) -> Path:
    return resolve_data_dir(home) / "ledger.db"


def examples_dir(home: Path | None = None) -> Path:
    if home is not None:
        candidate = home.expanduser().resolve() / "examples"
        if candidate.is_dir():
            return candidate
    if (ASSETS_DIR / "examples").is_dir():
        return ASSETS_DIR / "examples"
    return REPO_ROOT / "examples"


def skill_file_path(home: Path | None = None) -> Path:
    if home is not None:
        candidate = home.expanduser().resolve() / "SKILL.md"
        if candidate.exists():
            return candidate
    bundled = ASSETS_DIR / "SKILL.md"
    if bundled.exists():
        return bundled
    return REPO_ROOT / "SKILL.md"


def init_global_dirs(home: Path | None = None, *, force: bool = False) -> dict[str, Any]:
    """Initialize global config and data directories with starter config files."""
    cfg_dir = resolve_config_dir(home)
    prof_dir = profiles_dir(home)
    tmpl_dir = templates_dir(home)
    dat_dir = resolve_data_dir(home)

    cfg_dir.mkdir(parents=True, exist_ok=True)
    prof_dir.mkdir(parents=True, exist_ok=True)
    (tmpl_dir / "resume").mkdir(parents=True, exist_ok=True)
    dat_dir.mkdir(parents=True, exist_ok=True)

    template_root = ASSETS_DIR / "config"
    if not template_root.is_dir():
        template_root = REPO_ROOT / "config"

    starter_map = [
        (template_root / "default_brand.example.yaml", default_brand_path(home)),
        (template_root / "default_payment.example.yaml", default_payment_path(home)),
        (template_root / "profiles" / "business.example.yaml", prof_dir / "business.yaml"),
        (template_root / "profiles" / "personal.example.yaml", prof_dir / "personal.yaml"),
    ]

    created: list[str] = []
    skipped: list[str] = []
    for src, dst in starter_map:
        if not src.exists():
            continue
        if dst.exists() and not force:
            skipped.append(str(dst))
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        created.append(str(dst))

    return {
        "config_dir": str(cfg_dir),
        "profiles_dir": str(prof_dir),
        "templates_dir": str(tmpl_dir),
        "data_dir": str(dat_dir),
        "ledger_path": str(default_ledger_path(home)),
        "created": created,
        "skipped": skipped,
    }
