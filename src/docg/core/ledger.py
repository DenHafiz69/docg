from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from docg.core.paths import default_ledger_path

DOC_PREFIXES: dict[str, str] = {
    "invoice": "INV",
    "agreement": "AGR",
    "letter": "LTR",
    "quotation": "QUO",
    "receipt": "REC",
}

_NUMBER_RE = re.compile(r"^[A-Z]+-(\d{4})-(\d+)$")


class Ledger:
    """Lightweight SQLite ledger for tracking document numbers, clients, amounts, and statuses."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or default_ledger_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_number TEXT UNIQUE NOT NULL,
                    doc_type TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    seq INTEGER NOT NULL,
                    client_name TEXT NOT NULL,
                    project_title TEXT,
                    currency TEXT,
                    total_amount REAL,
                    balance_due REAL,
                    status TEXT NOT NULL,
                    issue_date TEXT NOT NULL,
                    input_path TEXT,
                    output_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    @staticmethod
    def prefix_for(doc_type: str) -> str:
        return DOC_PREFIXES.get(doc_type.lower(), doc_type[:3].upper())

    @staticmethod
    def parse_year_seq(doc_number: str, fallback_year: int) -> tuple[int, int]:
        match = _NUMBER_RE.match(doc_number.strip().upper())
        if match:
            return int(match.group(1)), int(match.group(2))
        return fallback_year, 0

    def next_number(self, doc_type: str, year: Optional[int] = None) -> str:
        """Return the next sequential document number (e.g. INV-2026-002)."""
        target_year = year or date.today().year
        prefix = self.prefix_for(doc_type)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(seq), 0) AS max_seq FROM documents WHERE doc_type = ? AND year = ?",
                (doc_type.lower(), target_year),
            ).fetchone()
            next_seq = int(row["max_seq"]) + 1
        return f"{prefix}-{target_year}-{next_seq:03d}"

    def record(
        self,
        *,
        doc_number: str,
        doc_type: str,
        client_name: str,
        issue_date: str,
        status: str,
        project_title: Optional[str] = None,
        currency: Optional[str] = None,
        total_amount: Optional[float] = None,
        balance_due: Optional[float] = None,
        input_path: Optional[Path] = None,
        output_path: Optional[Path] = None,
    ) -> None:
        """Insert or update a document record in the ledger."""
        now = datetime.now(timezone.utc).isoformat()
        year, seq = self.parse_year_seq(doc_number, date.today().year)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents (
                    doc_number, doc_type, year, seq, client_name, project_title,
                    currency, total_amount, balance_due, status, issue_date,
                    input_path, output_path, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(doc_number) DO UPDATE SET
                    doc_type = excluded.doc_type,
                    year = excluded.year,
                    seq = excluded.seq,
                    client_name = excluded.client_name,
                    project_title = excluded.project_title,
                    currency = excluded.currency,
                    total_amount = excluded.total_amount,
                    balance_due = excluded.balance_due,
                    status = excluded.status,
                    issue_date = excluded.issue_date,
                    input_path = excluded.input_path,
                    output_path = excluded.output_path,
                    updated_at = excluded.updated_at
                """,
                (
                    doc_number,
                    doc_type.lower(),
                    year,
                    seq,
                    client_name,
                    project_title,
                    currency,
                    total_amount,
                    balance_due,
                    status.upper(),
                    issue_date,
                    str(input_path) if input_path else None,
                    str(output_path) if output_path else None,
                    now,
                    now,
                ),
            )

    def list_documents(
        self,
        doc_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List recorded documents ordered by most recent."""
        query = "SELECT * FROM documents WHERE 1=1"
        params: list[Any] = []
        if doc_type:
            query += " AND doc_type = ?"
            params.append(doc_type.lower())
        if status:
            query += " AND UPPER(status) = ?"
            params.append(status.upper())
        query += " ORDER BY year DESC, seq DESC, id DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def update_status(
        self,
        doc_number: str,
        status: str,
        balance_due: Optional[float] = None,
    ) -> bool:
        """Update document status (and optionally balance_due; sets 0.0 when PAID)."""
        normalized = status.upper()
        if balance_due is None and normalized == "PAID":
            balance_due = 0.0

        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            if balance_due is not None:
                cur = conn.execute(
                    "UPDATE documents SET status = ?, balance_due = ?, updated_at = ? WHERE doc_number = ?",
                    (normalized, balance_due, now, doc_number),
                )
            else:
                cur = conn.execute(
                    "UPDATE documents SET status = ?, updated_at = ? WHERE doc_number = ?",
                    (normalized, now, doc_number),
                )
        return cur.rowcount > 0
