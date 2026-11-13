from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from ledgersense.domain.models import BankLine

DEFAULT_COLUMN_MAPPING: dict[str, str] = {
    "date": "txn_date",
    "txn_date": "txn_date",
    "narration": "narration",
    "description": "narration",
    "particulars": "narration",
    "ref_no": "ref_no",
    "ref": "ref_no",
    "reference": "ref_no",
    "debit": "debit",
    "withdrawal": "debit",
    "credit": "credit",
    "deposit": "credit",
    "balance": "balance",
}


def _parse_date(date_str: str) -> date:
    """Parse common Indian bank CSV date formats."""
    clean_date = date_str.strip()
    try:
        return date.fromisoformat(clean_date)
    except ValueError:
        pass

    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(clean_date, fmt).date()
        except ValueError:
            pass

    raise ValueError(f"Unable to parse date from string: '{date_str}'")


def parse(
    path_or_bytes: Path | str | bytes,
    mapping: dict[str, str] | None = None,
    run_id: str = "run:2025-26-demo",
) -> list[BankLine]:
    """Parse bank statement CSV into validated BankLine domain models.

    Uses strict config-driven column mapping.
    """
    if isinstance(path_or_bytes, bytes):
        text_content = path_or_bytes.decode("utf-8-sig")
    elif isinstance(path_or_bytes, (str, Path)):
        with open(path_or_bytes, encoding="utf-8-sig") as f:
            text_content = f.read()
    else:
        raise TypeError(f"Unsupported input type for bank CSV: {type(path_or_bytes)}")

    csv_file = io.StringIO(text_content.strip())
    reader = csv.DictReader(csv_file)
    if not reader.fieldnames:
        return []

    # Build header-to-field resolution map
    effective_mapping = mapping if mapping is not None else DEFAULT_COLUMN_MAPPING
    field_to_col: dict[str, str] = {}
    for col in reader.fieldnames:
        norm_col = col.strip().lower()
        if norm_col in effective_mapping:
            field_to_col[effective_mapping[norm_col]] = col
        elif col in effective_mapping:
            field_to_col[effective_mapping[col]] = col

    required_fields = ["txn_date", "narration", "debit", "credit"]
    missing = [f for f in required_fields if f not in field_to_col]
    if missing:
        raise ValueError(f"Missing required bank CSV column mappings: {missing} (available: {reader.fieldnames})")

    bank_lines: list[BankLine] = []
    for idx, row in enumerate(reader):
        date_raw = row[field_to_col["txn_date"]]
        narration_raw = row[field_to_col["narration"]]
        debit_raw = row[field_to_col["debit"]]
        credit_raw = row[field_to_col["credit"]]

        ref_no = None
        if "ref_no" in field_to_col and row.get(field_to_col["ref_no"]):
            ref_no = str(row[field_to_col["ref_no"]]).strip()

        balance = None
        if "balance" in field_to_col and row.get(field_to_col["balance"]):
            bal_str = str(row[field_to_col["balance"]]).strip().replace(",", "")
            if bal_str:
                balance = Decimal(bal_str).quantize(Decimal("0.01"))

        debit_str = str(debit_raw or "0.00").strip().replace(",", "") or "0.00"
        credit_str = str(credit_raw or "0.00").strip().replace(",", "") or "0.00"

        bank_lines.append(
            BankLine(
                id=f"bank:{idx + 1:04d}",
                run_id=run_id,
                txn_date=_parse_date(date_raw),
                narration=str(narration_raw).strip(),
                debit=Decimal(debit_str).quantize(Decimal("0.01")),
                credit=Decimal(credit_str).quantize(Decimal("0.01")),
                balance=balance,
                ref_no=ref_no,
            )
        )

    return bank_lines
