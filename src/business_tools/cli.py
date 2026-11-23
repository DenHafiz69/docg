from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from business_tools.core.ledger import DEFAULT_LEDGER_PATH, Ledger
from business_tools.tools.agreement.generator import generate_agreement_from_file
from business_tools.tools.invoice.generator import generate_invoice_from_file

app = typer.Typer(
    name="biz",
    help="Unified CLI for generating consistent business documents.",
    no_args_is_help=True,
)
console = Console()


def _default_output_path(input_file: Path, doc_kind: str) -> Path:
    return Path("output") / f"{input_file.stem}_{doc_kind}.pdf"


@app.command("invoice")
def invoice_cmd(
    input_file: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=False,
        help="Path to invoice data (.yaml, .yml, or .json)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output PDF path (defaults to output/<name>_invoice.pdf)",
    ),
    brand: Optional[Path] = typer.Option(
        None,
        "--brand",
        "-b",
        exists=True,
        dir_okay=False,
        help="Optional brand/sender YAML/JSON file overriding config/default_brand.yaml",
    ),
    html: Optional[Path] = typer.Option(
        None,
        "--html",
        help="Optional path to also save the rendered HTML",
    ),
    db: Path = typer.Option(
        DEFAULT_LEDGER_PATH,
        "--db",
        help="Path to SQLite ledger database",
    ),
    no_record: bool = typer.Option(
        False,
        "--no-record",
        help="Skip recording this document in the SQLite ledger",
    ),
) -> None:
    """Generate a PDF invoice from a YAML or JSON file."""
    out_pdf = output or _default_output_path(input_file, "invoice")
    ledger = None if no_record else Ledger(db)
    result = generate_invoice_from_file(
        input_path=input_file,
        output_pdf=out_pdf,
        brand_path=brand,
        output_html=html,
        ledger=ledger,
    )
    typer.echo(f"Generated invoice: {result}")


@app.command("agreement")
def agreement_cmd(
    input_file: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=False,
        help="Path to agreement letter data (.yaml, .yml, or .json)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output PDF path (defaults to output/<name>_agreement.pdf)",
    ),
    brand: Optional[Path] = typer.Option(
        None,
        "--brand",
        "-b",
        exists=True,
        dir_okay=False,
        help="Optional brand/sender YAML/JSON file overriding config/default_brand.yaml",
    ),
    html: Optional[Path] = typer.Option(
        None,
        "--html",
        help="Optional path to also save the rendered HTML",
    ),
    db: Path = typer.Option(
        DEFAULT_LEDGER_PATH,
        "--db",
        help="Path to SQLite ledger database",
    ),
    no_record: bool = typer.Option(
        False,
        "--no-record",
        help="Skip recording this document in the SQLite ledger",
    ),
) -> None:
    """Generate a PDF agreement letter from a YAML or JSON file."""
    out_pdf = output or _default_output_path(input_file, "agreement")
    ledger = None if no_record else Ledger(db)
    result = generate_agreement_from_file(
        input_path=input_file,
        output_pdf=out_pdf,
        brand_path=brand,
        output_html=html,
        ledger=ledger,
    )
    typer.echo(f"Generated agreement letter: {result}")


@app.command("next-number")
def next_number_cmd(
    doc_type: str = typer.Argument(..., help="Document type, e.g. invoice or agreement"),
    year: Optional[int] = typer.Option(None, "--year", "-y", help="Year (defaults to current year)"),
    db: Path = typer.Option(DEFAULT_LEDGER_PATH, "--db", help="Path to SQLite ledger database"),
) -> None:
    """Print the next sequential document number from the ledger."""
    ledger = Ledger(db)
    typer.echo(ledger.next_number(doc_type, year=year))


@app.command("list")
def list_cmd(
    doc_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by document type"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    db: Path = typer.Option(DEFAULT_LEDGER_PATH, "--db", help="Path to SQLite ledger database"),
) -> None:
    """List all tracked documents in the SQLite ledger."""
    ledger = Ledger(db)
    rows = ledger.list_documents(doc_type=doc_type, status=status)
    if not rows:
        typer.echo("No documents found in ledger.")
        return

    table = Table(title="Business Documents Ledger")
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
    db: Path = typer.Option(DEFAULT_LEDGER_PATH, "--db", help="Path to SQLite ledger database"),
) -> None:
    """Update the status of a document in the SQLite ledger."""
    ledger = Ledger(db)
    updated = ledger.update_status(doc_number, new_status, balance_due=balance_due)
    if not updated:
        typer.echo(f"Document '{doc_number}' not found in ledger.", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Updated {doc_number} -> {new_status.upper()}")


if __name__ == "__main__":
    app()
