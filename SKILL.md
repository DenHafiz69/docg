---
name: docg
description: Generate consistent, branded PDF documents (invoices, service agreements, resumes, and formal/cover letters) using the docg CLI. Use whenever the user asks to create an invoice, agreement, resume/CV, or letter.
---

# `docg` — AI-Friendly Document Generator

Use `docg` to generate clean, consistently styled PDF documents from structured YAML or JSON.

Global user directories (XDG-compliant):
- **Config & profiles**: `~/.config/docg/` (`default_brand.yaml`, `default_payment.yaml`, `profiles/*.yaml`) — override with `DOCG_CONFIG_DIR`
- **Data & SQLite ledger**: `~/.local/share/docg/ledger.db` — override with `DOCG_DATA_DIR`
- **Unified workspace override**: Set `DOCG_HOME=/path/to/folder` (or pass `--home`) to store both `config/` and `data/` in one synced folder.

Run `docg init` once to create starter configs, or `docg paths --json` to inspect resolved paths.

## Quick Discovery Commands

Before generating a document, inspect the available types, profiles, and exact JSON schema so you never guess field names:

```bash
docg types                    # List document types (invoice, agreement, resume, letter)
docg profiles --json          # List profiles in ~/.config/docg/profiles/
docg paths --json             # Show resolved config, profile, and ledger paths
docg schema <type>            # Print exact Pydantic JSON Schema for <type>
docg example <type>           # Print a valid sample YAML for <type>
```

## Generating Documents

Pass a YAML/JSON file or pipe JSON/YAML directly via stdin (`-`), and pass `--json` for structured output:

```bash
# From a saved YAML/JSON file
docg generate invoice inv.yaml -o invoice.pdf --json

# Directly from stdin (great for one-off resumes or cover letters)
docg generate resume - -o resume.pdf --profile personal --json << 'EOF'
headline: "Full-Stack Developer"
summary: "..."
experience:
  - role: "Software Engineer"
    company: "Example Co"
    period: "2024 – Present"
    highlights:
      - "Built scalable APIs."
EOF
```

### Useful Flags
- `--profile <name>` / `-p`: Choose a profile in `~/.config/docg/profiles/` (`business` is default for `invoice`/`agreement`; `personal` is default for `resume`/`letter`).
- `--brand <file>` / `-b`: Override brand settings with a custom YAML/JSON file.
- `--validate`: Validate input against the Pydantic schema without rendering a PDF.
- `--json`: Return structured JSON (`{"doc_type", "doc_number", "pdf", ...}`).
- `--no-record`: Skip writing to the SQLite ledger (useful for drafts/tests).
- `--home <dir>`: Override both config and data directories (or set `DOCG_HOME`).

## Numbering & Ledger Tracking

Invoices, agreements, and numbered letters are tracked in `~/.local/share/docg/ledger.db`:
- Omit `invoice_number` / `agreement_number` or set it to `"AUTO"` to auto-assign the next sequential number (`INV-YYYY-NNN`, `AGR-YYYY-NNN`, `LTR-YYYY-NNN`).
- Use ledger commands to check history and update payment status:

```bash
docg list --json                     # List all recorded documents
docg next-number invoice             # Check next invoice number
docg status INV-2026-001 PAID        # Mark paid (sets balance_due to 0.0)
```

## Best Practices for AI Agents
1. Run `docg profiles --json` and `docg schema <type>` if unsure about profiles or field names.
2. Always pass `--json` when calling `docg` programmatically so you can verify the exact output PDF path and assigned document number.
3. Use `--validate` before rendering when building complex invoices or agreements.
4. For one-off documents (`resume`, `letter`), piping YAML/JSON via stdin (`-`) avoids temporary files.
