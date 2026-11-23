# `docg` — AI-Friendly Document Generator

A `uv`-managed Python CLI for generating consistently formatted PDF documents (**invoices**, **service agreements**, **resumes**, and **letters**) designed to pair seamlessly with AI coding tools (Claude Code, OpenCode, Codex, Antigravity).

## Install

### Quick Install (`curl`)

```bash
curl -fsSL https://raw.githubusercontent.com/DenHafiz69/docg/main/install.sh | bash
```

Optional environment variables:
- `DOCG_DIR` — install/clone location (defaults to `~/.local/share/docg`)
- `DOCG_REF` — git branch or tag to install (defaults to `main`)
- `DOCG_REPO` — git repository URL

### Install from a Local Checkout (Editable)

```bash
./install.sh
# or directly with uv:
uv tool install -e .
```

Or run locally inside the repo without installing globally:

```bash
uv sync
uv run docg --help
```

Set `DOCG_HOME=/path/to/your/synced/folder` if you move or sync the config/data directory elsewhere.

## Commands

```bash
# Discover types, profiles, schemas, and examples
docg types
docg profiles
docg schema invoice
docg example resume

# Generate from file
docg generate invoice examples/invoice_sample.yaml -o output/invoice.pdf
docg generate agreement examples/agreement_sample.yaml -o output/agreement.pdf
docg generate resume examples/resume_sample.yaml -o output/resume.pdf
docg generate letter examples/letter_sample.yaml -o output/letter.pdf

# Generate from stdin with JSON output (ideal for AI agents)
cat examples/resume_sample.yaml | docg generate resume - -o output/resume.pdf --json

# Ledger commands (SQLite at data/ledger.db)
docg list
docg next-number invoice
docg status INV-2026-001 PAID
```

## Pairing with AI Coding Tools

Drop [SKILL.md](SKILL.md) into your AI tool's skills directory (or print it anytime with `docg skill`). Agents can introspect `docg schema <type>`, pick a profile (`nedays` or `personal`), validate with `--validate`, and generate PDFs via stdin or YAML files.

## Project Layout

- `config/profiles/`: Named sender profiles (`nedays.yaml`, `personal.yaml`)
- `config/default_payment.yaml`: Default bank/payment details inherited by invoices
- `data/ledger.db`: SQLite ledger tracking sequential numbers, amounts, and payment statuses
- `src/docg/core/`: Shared models, paths, SQLite ledger, Jinja2 + WeasyPrint renderer, and tool registry
- `src/docg/tools/`: Document generators (`invoice`, `agreement`, `resume`, `letter`)
