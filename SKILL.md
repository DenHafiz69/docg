---
name: docg
description: Generate consistent, branded PDF documents (invoices, quotations, receipts, service agreements, resumes, and formal/cover letters) using the docg CLI. Use whenever the user asks to create an invoice, quotation, receipt, agreement, resume/CV, or letter.
---

# `docg` — AI-Friendly Document Generator

Use `docg` to generate clean, consistently styled PDF documents from structured YAML or JSON.

Global user directories (XDG-compliant):
- **Config, profiles & clients**: `~/.config/docg/` (`default_brand.yaml`, `default_payment.yaml`, `profiles/*.yaml`, `clients/*.yaml`, `resume_master.yaml`, `templates/<type>/*.html`) — override with `DOCG_CONFIG_DIR`
- **Data & SQLite ledger**: `~/.local/share/docg/ledger.db` — override with `DOCG_DATA_DIR`
- **Unified workspace override**: Set `DOCG_HOME=/path/to/folder` (or pass `--home`) to store both `config/` and `data/` in one synced folder.

Run `docg init` once to create starter configs, or `docg paths --json` to inspect resolved paths.

## Quick Discovery Commands

Before generating a document, inspect the available types, profiles, and exact JSON schema so you never guess field names:

```bash
docg types                    # List document types (invoice, quotation, receipt, agreement, resume, letter)
docg profiles --json          # List profiles in ~/.config/docg/profiles/
docg clients --json           # List saved clients in ~/.config/docg/clients/
docg templates --json         # List saved custom HTML templates in ~/.config/docg/templates/
docg paths --json             # Show resolved config, profile, template, and ledger paths
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
- `--profile <name>` / `-p`: Choose a profile in `~/.config/docg/profiles/` (`business` is default for `invoice`/`quotation`/`receipt`/`agreement`; `personal` is default for `resume`/`letter`).
- `--client <slug>` / `-c`: Load a saved client from `~/.config/docg/clients/<slug>.yaml` (or use `client: "<slug>"` / `recipient: "<slug>"` directly in YAML/JSON).
- `--template <name-or-path>` / `-t`: Use a saved custom HTML template in `~/.config/docg/templates/<type>/<name>.html` or a direct path to an `.html` file.
- `--brand <file>` / `-b`: Override brand settings with a custom YAML/JSON file.
- `--validate`: Validate input against the Pydantic schema without rendering a PDF.
- `--json`: Return structured JSON (`{"doc_type", "doc_number", "pdf", ...}`).
- `--no-record`: Skip writing to the SQLite ledger (useful for drafts/tests).
- `--home <dir>`: Override both config and data directories (or set `DOCG_HOME`).

## Resume Workflow (Ask, Store Locally, and Tailor per Role)

When the user asks to create or update a resume/CV, follow this workflow instead of guessing or inventing details:

1. **Inspect locally stored data first**:
   - Run `docg paths --json` to locate `profiles_dir` and `resume_master` (defaults to `~/.config/docg/profiles/personal.yaml` and `~/.config/docg/resume_master.yaml`).
   - Check whether `personal.yaml` exists and has real user details (not placeholder values like `Alex Morgan` / `example.com`).
   - Check whether `resume_master.yaml` exists with the user's career history.
2. **Ask the user first for any missing information**:
   - If `personal.yaml` is missing or still uses placeholders, ask the user for their contact details (full name, location/address, email, phone, website) and save them to `~/.config/docg/profiles/personal.yaml`.
   - If `resume_master.yaml` is missing (or lacks sections needed), ask the user to provide their work experience, education, projects, skills, certifications, languages, and links (`github`, `linkedin`), then save the full, unmodified master record to `~/.config/docg/resume_master.yaml` (matching `docg schema resume`).
   - If the user has not specified a **target role / job description**, ask what role they are targeting before generating.
3. **Tailor for the target role (without overwriting the master file)**:
   - Use `~/.config/docg/resume_master.yaml` as the factual source of truth—never fabricate employers, dates, degrees, or metrics.
   - Tailor `headline`, `summary`, bullet phrasing, ordering, and which `experience`, `projects`, and `skills` to highlight based on the target role.
   - Pipe the tailored YAML/JSON via stdin into `docg generate resume - -o <output.pdf> --profile personal --json` so `resume_master.yaml` stays intact as the master career bank.
4. **Keep local records up to date**:
   - Whenever the user shares new experience, projects, education, skills, or updated contact info, update `~/.config/docg/resume_master.yaml` or `~/.config/docg/profiles/personal.yaml` so future resumes reuse it automatically.

## Creating a Reusable Resume Template from an Image or PDF Sample

When the user provides a reference resume **image** (PNG/JPG/WebP) or **PDF** and asks you to match its layout/style and generate their resume:

1. **Inspect the reference sample visually**:
   - View the image or PDF directly (if it is a multi-page PDF or cannot be viewed directly, render its pages to PNG first) and extract its visual design:
     - Page size, margins, and column structure (single-column, two-column sidebar, header banner, etc.)
     - Color palette (background, sidebar fill, primary text, muted text, accent color, divider lines)
     - Typography (serif vs sans-serif, heading sizes, uppercase/letter-spacing, bold/italic hierarchy, bullet style, right-aligned dates)
     - Section order and spacing density
2. **Build and save a reusable Jinja2 HTML+CSS template**:
   - Run `docg paths --json` to get `templates_dir` (`~/.config/docg/templates`).
   - Choose a clean kebab-case template name (e.g. `modern-sidebar`, `classic-serif`, or the name the user requested) and save the template to:
     `~/.config/docg/templates/resume/<template_name>.html`
   - Write a **100% data-driven** Jinja2 template compatible with WeasyPrint (`@page { size: A4; margin: ...; }`, CSS flexbox/grid, `break-inside: avoid` on items). You may either `{% extends "base.html" %}` or write a standalone `<!DOCTYPE html>` document for full layout control.
   - Never hardcode the sample's or user's personal text into the template. Guard every optional section with `{% if ... %}` and use the exact `docg` resume context variables:
     - Top-level: `full_name`, `headline`, `contact_parts` (list of strings), `footer_text`
     - `brand`: `name`, `tagline`, `address` (list), `email`, `phone`, `website`, `primary_color`, `accent_color`, `muted_color`, `footer_note`
     - `resume`: `summary`, `github`, `linkedin`, `experience` (`role`, `company`, `location`, `period`, `highlights`), `projects` (`name`, `url`, `tech`, `period`, `highlights`), `skills` (`category`, `items`), `education` (`degree`, `institution`, `location`, `period`, `details`), `certifications` (list), `languages` (list)
3. **Gather and tailor the user's resume data**:
   - Follow the **Resume Workflow** above: check `~/.config/docg/profiles/personal.yaml` and `~/.config/docg/resume_master.yaml`, ask the user for any missing details and save them locally, then tailor the content for the user's target role.
4. **Render the resume with the saved template and verify**:
   - Generate the PDF using `--template <template_name>`:
     ```bash
     docg generate resume - -o <output.pdf> --profile personal --template <template_name> --json
     ```
   - Visually inspect the generated PDF (or render it to PNG and view it) to check alignment, contrast, margins, and page breaks against the user's sample; refine `~/.config/docg/templates/resume/<template_name>.html` if needed.
   - Tell the user the saved template name (`<template_name>`) and path so they can reuse it anytime via `docg generate resume ... --template <template_name>` or list saved templates with `docg templates resume`.

## Numbering & Ledger Tracking

Invoices, quotations, receipts, agreements, and numbered letters are tracked in `~/.local/share/docg/ledger.db`:
- Omit `invoice_number` / `quotation_number` / `receipt_number` / `agreement_number` or set it to `"AUTO"` to auto-assign the next sequential number (`INV-YYYY-NNN`, `QUO-YYYY-NNN`, `REC-YYYY-NNN`, `AGR-YYYY-NNN`, `LTR-YYYY-NNN`).
- Use ledger & conversion commands to check history, convert documents, and update payment status:

```bash
docg list --json                                      # List all recorded documents
docg next-number quotation                            # Check next quotation number
docg convert QUO-2026-001 --to invoice -o inv.pdf     # Convert quotation to invoice (marks quote ACCEPTED)
docg convert INV-2026-001 --to receipt -o rec.pdf     # Convert invoice to receipt (marks invoice PAID)
docg status INV-2026-001 PAID --receipt -o rec.pdf    # Mark paid & auto-generate receipt
```

## Best Practices for AI Agents
1. Run `docg profiles --json` and `docg schema <type>` if unsure about profiles or field names.
2. Always pass `--json` when calling `docg` programmatically so you can verify the exact output PDF path and assigned document number.
3. Use `--validate` before rendering when building complex invoices or agreements.
4. For one-off documents (`resume`, `letter`), piping YAML/JSON via stdin (`-`) avoids temporary files.
