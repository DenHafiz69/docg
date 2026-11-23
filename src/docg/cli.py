from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from docg.core.ledger import Ledger
from docg.core.paths import (
    default_brand_path,
    default_ledger_path,
    default_payment_path,
    examples_dir,
    init_global_dirs,
    profiles_dir,
    resolve_config_dir,
    resolve_data_dir,
    skill_file_path,
)
from docg.core.registry import REGISTRY, get_tool
from docg.core.renderer import list_profiles, load_data_file, load_data_text, resolve_profile_path

app = typer.Typer(
    name="docg",
    help="AI-friendly CLI for generating consistent PDF documents (invoices, agreements, resumes, letters).",
    no_args_is_help=True,
)
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
    doc_type: str = typer.Argument(..., help="Document type: invoice, agreement, resume, letter"),
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
    brand: Optional[Path] = typer.Option(
        None, "--brand", "-b", exists=True, dir_okay=False, help="Custom brand YAML/JSON override"
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

    result = tool.generator(
        data,
        output_pdf=out_pdf,
        profile=selected_profile,
        brand_path=brand,
        output_html=html,
        ledger=ledger,
        input_path=input_path,
        home=home,
    )

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
        "default_brand": str(default_brand_path(home)),
        "default_payment": str(default_payment_path(home)),
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


@app.command("status")
def status_cmd(
    doc_number: str = typer.Argument(..., help="Document number, e.g. INV-2026-001"),
    new_status: str = typer.Argument(..., help="New status, e.g. PAID, SIGNED, VOID"),
    balance_due: Optional[float] = typer.Option(
        None, "--balance", help="Optional updated balance due (automatically 0.0 when PAID)"
    ),
    home: Optional[Path] = typer.Option(None, "--home", help="Override synced workspace directory"),
    db: Optional[Path] = typer.Option(None, "--db", help="Override SQLite ledger database path"),
) -> None:
    """Update the status of a document in the SQLite ledger."""
    ledger = Ledger(db or default_ledger_path(home))
    updated = ledger.update_status(doc_number, new_status, balance_due=balance_due)
    if not updated:
        typer.echo(f"Document '{doc_number}' not found in ledger.", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Updated {doc_number} -> {new_status.upper()}")


if __name__ == "__main__":
    app()
