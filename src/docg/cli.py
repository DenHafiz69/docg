from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from docg.core.converter import convert_document
from docg.core.ledger import Ledger
from docg.core.models import Party
from docg.core.paths import (
    clients_dir,
    default_brand_path,
    default_ledger_path,
    default_payment_path,
    examples_dir,
    init_global_dirs,
    profiles_dir,
    resolve_config_dir,
    resolve_data_dir,
    resume_master_path,
    skill_file_path,
    templates_dir,
)
from docg.core.registry import REGISTRY, get_tool
from docg.core.renderer import (
    list_clients,
    list_profiles,
    list_templates,
    load_client,
    load_data_file,
    load_data_text,
    merge_client_into_data,
    resolve_client_path,
    resolve_profile_path,
    save_client,
)

app = typer.Typer(
    name="docg",
    help="AI-friendly CLI for generating consistent PDF documents (invoices, quotations, receipts, agreements, resumes, letters).",
    no_args_is_help=True,
)
clients_app = typer.Typer(
    help="Manage reusable client/recipient records in ~/.config/docg/clients/.",
)
app.add_typer(clients_app, name="clients")
console = Console()


def _load_input(input_source: Optional[str]) -> tuple[dict, Optional[Path]]:
    if input_source is None or input_source == "-":
        if sys.stdin.isatty():
            typer.echo("Error: Provide an input file path or pipe YAML/JSON via stdin.", err=True)
            raise typer.Exit(code=2)
        raw = sys.stdin.read()
        return load_data_text(raw, source="<stdin>"), None

    path = Path(input_source)
    return load_data_file(path), path


def _default_output_path(doc_type: str, input_path: Optional[Path]) -> Path:
    stem = input_path.stem if input_path else doc_type
    return Path("output") / f"{stem}_{doc_type}.pdf"


@app.command("generate")
@app.command("gen", hidden=True)
def generate_cmd(
    doc_type: str = typer.Argument(
        ..., help="Document type: invoice, quotation, receipt, agreement, resume, letter"
    ),
    input_file: Optional[str] = typer.Argument(
        None,
        help="Path to YAML/JSON data file, or '-' / omitted to read from stdin",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output PDF path (defaults to output/<name>_<type>.pdf)"
    ),
    profile: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Named profile in ~/.config/docg/profiles/ (e.g. business, personal)"
    ),
    client: Optional[str] = typer.Option(
        None,
        "--client",
        "-c",
        help="Saved client slug in ~/.config/docg/clients/ (or path to client YAML/JSON)",
    ),
    brand: Optional[Path] = typer.Option(
        None, "--brand", "-b", exists=True, dir_okay=False, help="Custom brand YAML/JSON override"
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        "-t",
        help="Custom HTML template name in ~/.config/docg/templates/<type>/ or path to .html file",
    ),
    html: Optional[Path] = typer.Option(None, "--html", help="Optional path to also save rendered HTML"),
    home: Optional[Path] = typer.Option(
        None, "--home", help="Override synced workspace directory (or set DOCG_HOME)"
    ),
    db: Optional[Path] = typer.Option(None, "--db", help="Override SQLite ledger database path"),
    no_record: bool = typer.Option(False, "--no-record", help="Skip recording in SQLite ledger"),
    validate_only: bool = typer.Option(
        False, "--validate", help="Validate input against schema without rendering PDF"
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output"),
) -> None:
    """Generate a PDF document from a YAML/JSON file or stdin."""
    try:
        tool = get_tool(doc_type)
    except KeyError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc

    data, input_path = _load_input(input_file)

    if client is not None and tool.client_field is None:
        typer.echo(f"Document type '{tool.name}' does not support --client.", err=True)
        raise typer.Exit(code=2)

    if tool.client_field is not None:
        try:
            data = merge_client_into_data(
                data, field_name=tool.client_field, client_override=client, home=home
            )
        except (FileNotFoundError, ValidationError, ValueError) as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=2) from exc

    if validate_only:
        try:
            tool.model.model_validate(data)
        except ValidationError as exc:
            if as_json:
                typer.echo(json.dumps({"valid": False, "errors": exc.errors()}, indent=2))
            else:
                typer.echo(f"Validation failed:\n{exc}", err=True)
            raise typer.Exit(code=1) from exc

        if as_json:
            typer.echo(json.dumps({"valid": True, "doc_type": tool.name}))
        else:
            typer.echo(f"Valid {tool.name} input.")
        return

    if profile is not None:
        try:
            resolve_profile_path(profile, home=home)
        except FileNotFoundError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=2) from exc

    out_pdf = output or _default_output_path(tool.name, input_path)
    selected_profile = profile or tool.default_profile
    ledger: Ledger | None = None
    if tool.uses_ledger and not no_record:
        ledger = Ledger(db or default_ledger_path(home))

    try:
        result = tool.generator(
            data,
            output_pdf=out_pdf,
            profile=selected_profile,
            brand_path=brand,
            output_html=html,
            ledger=ledger,
            input_path=input_path,
            home=home,
            template=template,
        )
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc

    if as_json:
        typer.echo(json.dumps(result, indent=2))
    else:
        num = f" ({result['doc_number']})" if result.get("doc_number") else ""
        typer.echo(f"Generated {tool.name}{num}: {result['pdf']}")


@app.command("types")
def types_cmd(
    as_json: bool = typer.Option(False, "--json", help="Emit JSON list of document types"),
) -> None:
    """List available document types."""
    if as_json:
        payload = [
            {
                "name": t.name,
                "description": t.description,
                "default_profile": t.default_profile,
                "uses_ledger": t.uses_ledger,
            }
            for t in REGISTRY.values()
        ]
        typer.echo(json.dumps(payload, indent=2))
        return

    table = Table(title="Available Document Types")
    table.add_column("Type", style="cyan", no_wrap=True)
    table.add_column("Default Profile")
    table.add_column("Ledger")
    table.add_column("Description")
    for t in REGISTRY.values():
        table.add_row(t.name, t.default_profile, "yes" if t.uses_ledger else "no", t.description)
    console.print(table)


@app.command("schema")
def schema_cmd(
    doc_type: str = typer.Argument(..., help="Document type to inspect"),
) -> None:
    """Print the JSON Schema for a document type (useful for AI coding tools)."""
    try:
        tool = get_tool(doc_type)
    except KeyError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc

    typer.echo(json.dumps(tool.model.model_json_schema(), indent=2))


@app.command("example")
def example_cmd(
    doc_type: str = typer.Argument(..., help="Document type to show a sample YAML for"),
    home: Optional[Path] = typer.Option(None, "--home", help="Override synced workspace directory"),
) -> None:
    """Print a sample YAML input for a document type."""
    try:
        tool = get_tool(doc_type)
    except KeyError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc

    sample_path = examples_dir(home) / tool.example_file
    if not sample_path.exists():
        typer.echo(f"Example file not found: {sample_path}", err=True)
        raise typer.Exit(code=1)
    typer.echo(sample_path.read_text(encoding="utf-8").rstrip())


@app.command("profiles")
def profiles_cmd(
    home: Optional[Path] = typer.Option(None, "--home", help="Override workspace directory"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """List available brand/personal profiles in ~/.config/docg/profiles/."""
    names = list_profiles(home)
    pdir = profiles_dir(home)
    if as_json:
        typer.echo(
            json.dumps(
                {
                    "config_dir": str(resolve_config_dir(home)),
                    "profiles_dir": str(pdir),
                    "profiles": names,
                },
                indent=2,
            )
        )
        return

    if not names:
        typer.echo(f"No profiles found in {pdir}. Run 'docg init' to create starter profiles.")
        return
    for name in names:
        typer.echo(name)


@app.command("templates")
def templates_cmd(
    doc_type: Optional[str] = typer.Argument(
        None, help="Optional document type to filter (e.g. resume, invoice, agreement, letter)"
    ),
    home: Optional[Path] = typer.Option(None, "--home", help="Override workspace directory"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """List saved custom HTML templates in ~/.config/docg/templates/."""
    if doc_type is not None:
        try:
            doc_type = get_tool(doc_type).name
        except KeyError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=2) from exc

    found = list_templates(doc_type=doc_type, home=home)
    tdir = templates_dir(home, doc_type)
    if as_json:
        typer.echo(json.dumps({"templates_dir": str(tdir), "templates": found}, indent=2))
        return

    if not any(found.values()):
        typer.echo(f"No custom templates found in {tdir}.")
        return
    for dtype, names in found.items():
        for name in names:
            typer.echo(f"{dtype}/{name}")


@app.command("init")
def init_cmd(
    force: bool = typer.Option(False, "--force", help="Overwrite existing starter config files"),
    home: Optional[Path] = typer.Option(None, "--home", help="Override workspace directory"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Initialize global ~/.config/docg and ~/.local/share/docg directories with starter configs."""
    result = init_global_dirs(home, force=force)
    if as_json:
        typer.echo(json.dumps(result, indent=2))
        return

    typer.echo(f"Config dir: {result['config_dir']}")
    typer.echo(f"Data dir:   {result['data_dir']}")
    if result["created"]:
        typer.echo("Created:")
        for path in result["created"]:
            typer.echo(f"  + {path}")
    if result["skipped"]:
        typer.echo("Already exists (kept):")
        for path in result["skipped"]:
            typer.echo(f"  = {path}")


@app.command("paths")
def paths_cmd(
    home: Optional[Path] = typer.Option(None, "--home", help="Override workspace directory"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Show resolved global config, profile, and ledger paths."""
    info = {
        "config_dir": str(resolve_config_dir(home)),
        "profiles_dir": str(profiles_dir(home)),
        "clients_dir": str(clients_dir(home)),
        "default_brand": str(default_brand_path(home)),
        "default_payment": str(default_payment_path(home)),
        "resume_master": str(resume_master_path(home)),
        "templates_dir": str(templates_dir(home)),
        "data_dir": str(resolve_data_dir(home)),
        "ledger_path": str(default_ledger_path(home)),
        "examples_dir": str(examples_dir(home)),
        "skill_file": str(skill_file_path(home)),
    }
    if as_json:
        typer.echo(json.dumps(info, indent=2))
        return

    table = Table(title="docg Paths")
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Path")
    for k, v in info.items():
        table.add_row(k, v)
    console.print(table)


@app.command("skill")
def skill_cmd(
    home: Optional[Path] = typer.Option(None, "--home", help="Override synced workspace directory"),
) -> None:
    """Print SKILL.md instructions for AI coding agents."""
    path = skill_file_path(home)
    if not path.exists():
        typer.echo(f"SKILL.md not found at {path}", err=True)
        raise typer.Exit(code=1)
    typer.echo(path.read_text(encoding="utf-8").rstrip())


@app.command("next-number")
def next_number_cmd(
    doc_type: str = typer.Argument(..., help="Document type, e.g. invoice, agreement, letter"),
    year: Optional[int] = typer.Option(None, "--year", "-y", help="Year (defaults to current year)"),
    home: Optional[Path] = typer.Option(None, "--home", help="Override synced workspace directory"),
    db: Optional[Path] = typer.Option(None, "--db", help="Override SQLite ledger database path"),
) -> None:
    """Print the next sequential document number from the ledger."""
    ledger = Ledger(db or default_ledger_path(home))
    typer.echo(ledger.next_number(doc_type, year=year))


@app.command("list")
def list_cmd(
    doc_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by document type"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    home: Optional[Path] = typer.Option(None, "--home", help="Override synced workspace directory"),
    db: Optional[Path] = typer.Option(None, "--db", help="Override SQLite ledger database path"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON list of documents"),
) -> None:
    """List all tracked documents in the SQLite ledger."""
    ledger = Ledger(db or default_ledger_path(home))
    rows = ledger.list_documents(doc_type=doc_type, status=status)
    if as_json:
        typer.echo(json.dumps(rows, indent=2))
        return

    if not rows:
        typer.echo("No documents found in ledger.")
        return

    table = Table(title="Document Ledger")
    table.add_column("Number", style="cyan", no_wrap=True)
    table.add_column("Type")
    table.add_column("Client")
    table.add_column("Issue Date")
    table.add_column("Total", justify="right")
    table.add_column("Balance", justify="right")
    table.add_column("Status", style="bold")
    table.add_column("PDF")

    for r in rows:
        cur = r["currency"] or ""
        total_str = f"{cur} {r['total_amount']:,.2f}".strip() if r["total_amount"] is not None else "-"
        bal_str = f"{cur} {r['balance_due']:,.2f}".strip() if r["balance_due"] is not None else "-"
        table.add_row(
            r["doc_number"],
            r["doc_type"],
            r["client_name"],
            r["issue_date"],
            total_str,
            bal_str,
            r["status"],
            r["output_path"] or "-",
        )

    console.print(table)


@clients_app.callback(invoke_without_command=True)
def clients_list_cmd(
    ctx: typer.Context,
    home: Optional[Path] = typer.Option(None, "--home", help="Override workspace directory"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """List saved clients in ~/.config/docg/clients/."""
    if ctx.invoked_subcommand is not None:
        return

    names = list_clients(home)
    cdir = clients_dir(home)
    if as_json:
        typer.echo(
            json.dumps(
                {
                    "clients_dir": str(cdir),
                    "clients": names,
                },
                indent=2,
            )
        )
        return

    if not names:
        typer.echo(f"No clients found in {cdir}. Add one with 'docg clients add <slug> --name ...'.")
        return
    for name in names:
        typer.echo(name)


@clients_app.command("show")
def clients_show_cmd(
    slug: str = typer.Argument(..., help="Saved client slug"),
    home: Optional[Path] = typer.Option(None, "--home", help="Override workspace directory"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Show details of a saved client."""
    try:
        party = load_client(slug, home=home)
    except (FileNotFoundError, ValidationError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc

    data = party.model_dump(exclude_none=True)
    if as_json:
        typer.echo(json.dumps(data, indent=2))
        return

    table = Table(title=f"Client: {slug}")
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value")
    for k, v in data.items():
        if isinstance(v, list):
            v_str = "\n".join(v) if v else "-"
        else:
            v_str = str(v)
        table.add_row(k, v_str)
    console.print(table)


@clients_app.command("add")
def clients_add_cmd(
    slug: str = typer.Argument(..., help="Client slug (filename without extension, e.g. acme)"),
    name: str = typer.Option(..., "--name", "-n", help="Contact person name"),
    company: Optional[str] = typer.Option(None, "--company", help="Company or organization name"),
    role: Optional[str] = typer.Option(None, "--role", help="Contact role/title"),
    email: Optional[str] = typer.Option(None, "--email", help="Email address"),
    phone: Optional[str] = typer.Option(None, "--phone", help="Phone number"),
    address: Optional[list[str]] = typer.Option(
        None, "--address", "-a", help="Address line (repeat flag for multiple lines)"
    ),
    registration_no: Optional[str] = typer.Option(None, "--reg", help="Company registration number"),
    tax_id: Optional[str] = typer.Option(None, "--tax-id", help="Tax / SST / VAT ID"),
    force: bool = typer.Option(False, "--force", help="Overwrite if client already exists"),
    home: Optional[Path] = typer.Option(None, "--home", help="Override workspace directory"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Save a reusable client record under ~/.config/docg/clients/."""
    party = Party(
        name=name,
        company=company,
        role=role,
        address=address or [],
        email=email,
        phone=phone,
        registration_no=registration_no,
        tax_id=tax_id,
    )
    try:
        saved_path = save_client(slug, party, home=home, overwrite=force)
    except (FileExistsError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    if as_json:
        typer.echo(
            json.dumps(
                {"slug": slug, "path": str(saved_path), "client": party.model_dump(exclude_none=True)},
                indent=2,
            )
        )
    else:
        typer.echo(f"Saved client '{slug}': {saved_path}")


@clients_app.command("rm")
def clients_rm_cmd(
    slug: str = typer.Argument(..., help="Saved client slug to delete"),
    home: Optional[Path] = typer.Option(None, "--home", help="Override workspace directory"),
) -> None:
    """Delete a saved client record."""
    try:
        path = resolve_client_path(slug, home=home)
    except FileNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    path.unlink()
    typer.echo(f"Removed client '{slug}': {path}")


@app.command("convert")
def convert_cmd(
    doc_number: str = typer.Argument(..., help="Source document number in ledger, e.g. QUO-2026-001 or INV-2026-001"),
    to: str = typer.Option(..., "--to", help="Target document type: invoice or receipt"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output PDF path (defaults to output/<source>_<to>.pdf)"
    ),
    profile: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Named profile in ~/.config/docg/profiles/"
    ),
    brand: Optional[Path] = typer.Option(
        None, "--brand", "-b", exists=True, dir_okay=False, help="Custom brand YAML/JSON override"
    ),
    template: Optional[str] = typer.Option(
        None, "--template", "-t", help="Custom HTML template name or path"
    ),
    html: Optional[Path] = typer.Option(None, "--html", help="Optional path to also save rendered HTML"),
    due_date: Optional[str] = typer.Option(None, "--due-date", help="Due date (when converting to invoice)"),
    payment_date: Optional[str] = typer.Option(None, "--payment-date", help="Payment date (when converting to receipt)"),
    payment_method: Optional[str] = typer.Option(
        None, "--payment-method", help="Payment method (when converting to receipt)"
    ),
    reference: Optional[str] = typer.Option(
        None, "--reference", help="Payment/transaction reference (when converting to receipt)"
    ),
    amount: Optional[float] = typer.Option(
        None, "--amount", help="Amount paid (when converting to receipt; defaults to full total)"
    ),
    keep_status: bool = typer.Option(
        False, "--keep-status", help="Do not update the source document's status in the ledger"
    ),
    home: Optional[Path] = typer.Option(
        None, "--home", help="Override synced workspace directory (or set DOCG_HOME)"
    ),
    db: Optional[Path] = typer.Option(None, "--db", help="Override SQLite ledger database path"),
    no_record: bool = typer.Option(False, "--no-record", help="Skip recording the new document in the ledger"),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output"),
) -> None:
    """Convert a tracked ledger document (quotation -> invoice, invoice -> receipt)."""
    ledger = Ledger(db or default_ledger_path(home))
    target = to.strip().lower()
    out_pdf = output or (Path("output") / f"{doc_number.lower()}_{target}.pdf")

    if profile is not None:
        try:
            resolve_profile_path(profile, home=home)
        except FileNotFoundError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=2) from exc

    try:
        result = convert_document(
            ledger,
            doc_number,
            target,
            output_pdf=out_pdf,
            profile=profile or "business",
            brand_path=brand,
            output_html=html,
            home=home,
            template=template,
            due_date=due_date,
            payment_date=payment_date,
            payment_method=payment_method,
            payment_reference=reference,
            amount_paid=amount,
            record_in_ledger=not no_record,
            update_source_status=not keep_status,
        )
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc

    if as_json:
        typer.echo(json.dumps(result, indent=2))
    else:
        typer.echo(
            f"Converted {doc_number} -> {result['doc_type']} ({result['doc_number']}): {result['pdf']}"
        )


@app.command("status")
def status_cmd(
    doc_number: str = typer.Argument(..., help="Document number, e.g. INV-2026-001"),
    new_status: str = typer.Argument(..., help="New status, e.g. PAID, SIGNED, VOID"),
    balance_due: Optional[float] = typer.Option(
        None, "--balance", help="Optional updated balance due (automatically 0.0 when PAID)"
    ),
    receipt: bool = typer.Option(
        False, "--receipt", help="Automatically generate a receipt PDF when marking an invoice PAID"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output PDF path for --receipt (defaults to output/<doc>_receipt.pdf)"
    ),
    payment_method: Optional[str] = typer.Option(None, "--payment-method", help="Payment method for --receipt"),
    reference: Optional[str] = typer.Option(None, "--reference", help="Transaction reference for --receipt"),
    home: Optional[Path] = typer.Option(None, "--home", help="Override synced workspace directory"),
    db: Optional[Path] = typer.Option(None, "--db", help="Override SQLite ledger database path"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON output"),
) -> None:
    """Update the status of a document in the SQLite ledger."""
    ledger = Ledger(db or default_ledger_path(home))
    updated = ledger.update_status(doc_number, new_status, balance_due=balance_due)
    if not updated:
        typer.echo(f"Document '{doc_number}' not found in ledger.", err=True)
        raise typer.Exit(code=1)

    receipt_result: dict | None = None
    if receipt:
        out_pdf = output or (Path("output") / f"{doc_number.lower()}_receipt.pdf")
        try:
            receipt_result = convert_document(
                ledger,
                doc_number,
                "receipt",
                output_pdf=out_pdf,
                home=home,
                payment_method=payment_method,
                payment_reference=reference,
                update_source_status=False,
            )
        except (FileNotFoundError, ValueError) as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=2) from exc

    if as_json:
        payload: dict = {"doc_number": doc_number, "status": new_status.upper()}
        if receipt_result is not None:
            payload["receipt"] = receipt_result
        typer.echo(json.dumps(payload, indent=2))
        return

    typer.echo(f"Updated {doc_number} -> {new_status.upper()}")
    if receipt_result is not None:
        typer.echo(f"Generated receipt ({receipt_result['doc_number']}): {receipt_result['pdf']}")


if __name__ == "__main__":
    app()
