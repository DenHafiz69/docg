# `docg` — AI-Friendly Document Generator

A `uv`-managed Python CLI for generating consistently formatted PDF documents (**invoices**, **service agreements**, **resumes**, and **letters**) designed to pair seamlessly with AI coding tools (Claude Code, OpenCode, Codex, Antigravity).

## Install

### Quick Install (`curl`)

```bash
curl -fsSL https://raw.githubusercontent.com/DenHafiz69/docg/main/install.sh | bash
```

This installs `docg` globally via `uv tool` and runs `docg init` to seed starter configs in `~/.config/docg/`.

Optional environment variables:
- `DOCG_REF` — git branch or tag to install (defaults to `main`)
- `DOCG_REPO` — git repository URL

### Or Install Directly with `uv`

```bash
uv tool install git+https://github.com/DenHafiz69/docg.git
docg init
```

### Local Development Checkout

```bash
./install.sh
# or:
uv sync
uv run docg --help
```

## Global Configuration & Storage (XDG)

`docg` stores user configuration and ledger data globally so it works from any directory (especially when invoked by AI agents):

- **Config, profiles & custom templates**: `~/.config/docg/` (`default_brand.yaml`, `default_payment.yaml`, `profiles/*.yaml`, `resume_master.yaml`, `templates/<type>/*.html`) — override with `DOCG_CONFIG_DIR`
- **Data & SQLite ledger**: `~/.local/share/docg/ledger.db` — override with `DOCG_DATA_DIR`
- **Unified synced folder override**: Set `DOCG_HOME=/path/to/folder` (or pass `--home`) to store both `config/` and `data/` in one folder

Inspect resolved paths anytime with `docg paths`.

## Commands

```bash
# Initialize or inspect global paths, profiles & custom templates
docg init
docg paths
docg profiles
docg templates

# Discover types, schemas, and examples
docg types
docg schema invoice
docg example resume

# Generate from file (optionally using a saved custom template with -t/--template)
docg generate invoice invoice.yaml -o invoice.pdf
docg generate agreement agreement.yaml -o agreement.pdf
docg generate resume resume.yaml -o resume.pdf
docg generate resume resume.yaml -o resume.pdf --template modern-sidebar
docg generate letter letter.yaml -o letter.pdf

# Generate from stdin with JSON output (ideal for AI agents)
docg example resume | docg generate resume - -o resume.pdf --json

# Ledger commands (SQLite at ~/.local/share/docg/ledger.db)
docg list
docg next-number invoice
docg status INV-2026-001 PAID
```

## Pairing with AI Coding Tools

Drop [SKILL.md](SKILL.md) into your AI tool's skills directory (or print it anytime with `docg skill`). Agents can introspect `docg paths --json`, `docg profiles --json`, and `docg schema <type>`, validate with `--validate`, and generate PDFs via stdin or YAML files.

## Project Layout

- `src/docg/core/`: Shared models, XDG paths, SQLite ledger, Jinja2 + WeasyPrint renderer, and tool registry
- `src/docg/tools/`: Document generators (`invoice`, `agreement`, `resume`, `letter`)
- `src/docg/assets/`: Bundled example YAML files, starter config templates, and `SKILL.md`
