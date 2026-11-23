from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def resolve_home(home: Path | None = None) -> Path:
    """Resolve the synced workspace directory holding config/ and data/.

    Priority:
    1. Explicit --home argument
    2. DOCG_HOME environment variable
    3. Current working directory if it contains config/profiles or config/default_brand.yaml
    4. Editable repo root fallback
    """
    if home is not None:
        return home.expanduser().resolve()

    env_home = os.environ.get("DOCG_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()

    cwd = Path.cwd()
    if (cwd / "config" / "profiles").is_dir() or (cwd / "config" / "default_brand.yaml").exists():
        return cwd

    return REPO_ROOT


def profiles_dir(home: Path | None = None) -> Path:
    return resolve_home(home) / "config" / "profiles"


def default_brand_path(home: Path | None = None) -> Path:
    return resolve_home(home) / "config" / "default_brand.yaml"


def default_payment_path(home: Path | None = None) -> Path:
    return resolve_home(home) / "config" / "default_payment.yaml"


def default_ledger_path(home: Path | None = None) -> Path:
    return resolve_home(home) / "data" / "ledger.db"


def examples_dir(home: Path | None = None) -> Path:
    base = resolve_home(home) / "examples"
    if base.is_dir():
        return base
    return REPO_ROOT / "examples"


def skill_file_path(home: Path | None = None) -> Path:
    candidate = resolve_home(home) / "SKILL.md"
    if candidate.exists():
        return candidate
    return REPO_ROOT / "SKILL.md"
