---
name: docg
description: Generate consistent, branded PDF documents (invoices, service agreements, resumes, and formal/cover letters) using the docg CLI. Use whenever the user asks to create an invoice, agreement, resume/CV, or letter.
---

# `docg` — AI-Friendly Document Generator

Use `docg` to generate clean, consistently styled PDF documents from structured YAML or JSON. All profiles, payment defaults, and the SQLite ledger (`data/ledger.db`) live inside the synced `docg` workspace (`DOCG_HOME`, defaulting to `/home/denhafiz/Coding/business-tools`).

## Quick Discovery Commands

Before generating a document, inspect the available types, profiles, and exact JSON schema so you never guess field names:

```bash
docg types                    # List document types (invoice, agreement, resume, letter)
docg profiles                 # List profiles (e.g. nedays, personal)
docg schema <type>            # Print exact Pydantic JSON Schema for <type>
docg example <type>           # Print a valid sample YAML for <type>
```

## Generating Documents

You can either pass a YAML/JSON file or pipe JSON/YAML directly via stdin (`-`), and pass `--json` for structured output:

```bash
# From a saved YAML/JSON file
docg generate invoice data/client/inv.yaml -o output/client/inv.pdf --json

# Directly from stdin (great for one-off resumes or cover letters)
docg generate resume - -o output/resume.pdf --profile personal --json << 'EOF'
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
- `--profile <name>` / `-p`: Choose a profile in `config/profiles/` (`nedays` is default for `invoice`/`agreement`; `personal` is default for `resume`/`letter`).
- `--validate`: Validate input against the Pydantic schema without rendering a PDF.
- `--json`: Return structured JSON (`{"doc_type", "doc_number", "pdf", ...}`).
- `--no-record`: Skip writing to the SQLite ledger (useful for drafts/tests).
- `--home <dir>`: Override the synced workspace directory (or set `DOCG_HOME`).

## Numbering & Ledger Tracking

Invoices and agreements (and numbered letters) are tracked in `data/ledger.db`:
- Omit `invoice_number` / `agreement_number` or set it to `"AUTO"` to auto-assign the next sequential number (`INV-YYYY-NNN`, `AGR-YYYY-NNN`, `LTR-YYYY-NNN`).
- Use ledger commands to check history and update payment status:

```bash
docg list --json                     # List all recorded documents
docg next-number invoice             # Check next invoice number
docg status INV-2026-001 PAID        # Mark paid (sets balance_due to 0.0)
```

## Best Practices for AI Agents
1. Run `docg schema <type>` if unsure about optional or nested fields.
2. For client work (`invoice`, `agreement`), save the source YAML under `data/<client>/` so it stays synced and editable, then render to `output/<client>/`.
3. For one-off documents (`resume`, `letter`), piping via stdin or saving to the requested output folder both work cleanly.
4. Always pass `--json` when calling `docg` programmatically so you can verify the exact output PDF path and assigned document number.
