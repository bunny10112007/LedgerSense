from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from ledgersense.domain.models import BankLine, Match, Receipt, RunConfig


def _extract_tokens(text: str | None) -> set[str]:
    """Extract lowercase alphanumeric tokens of length >= 2 from text."""
    if not text:
        return set()
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 2}


def _compute_narration_token_overlap(receipt: Receipt, bank_line: BankLine) -> float:
    """Compute token overlap ratio between bank narration and receipt vendor/invoice tokens."""
    bank_tokens = _extract_tokens(bank_line.narration)
    receipt_tokens = _extract_tokens(receipt.vendor_name)
    if receipt.invoice_no:
        receipt_tokens.update(_extract_tokens(receipt.invoice_no))
    if receipt.vendor_key:
        slug = receipt.vendor_key.split("|")[0]
        receipt_tokens.update(slug.split("-"))

    if not receipt_tokens:
        return 0.0

    common_tokens = bank_tokens & receipt_tokens
    return min(1.0, len(common_tokens) / len(receipt_tokens))


def _compute_score(
    receipt: Receipt,
    bank_line: BankLine,
    cfg: RunConfig,
) -> float:
    """Compute candidate match score (0.0 to 1.0) per Section 6.2."""
    assert receipt.total is not None
    assert receipt.invoice_date is not None

    amt_diff = abs(bank_line.debit - receipt.total)
    days_diff = abs((bank_line.txn_date - receipt.invoice_date).days)

    if cfg.amount_tolerance > Decimal("0.00"):
        amount_closeness = 1.0 - float(amt_diff / cfg.amount_tolerance)
    else:
        amount_closeness = 1.0 if amt_diff == Decimal("0.00") else 0.0
    amount_closeness = max(0.0, min(1.0, amount_closeness))

    if cfg.date_window_days > 0:
        date_closeness = 1.0 - (days_diff / cfg.date_window_days)
    else:
        date_closeness = 1.0 if days_diff == 0 else 0.0
    date_closeness = max(0.0, min(1.0, date_closeness))

    narration_overlap = _compute_narration_token_overlap(receipt, bank_line)

    score = (0.5 * amount_closeness) + (0.3 * date_closeness) + (0.2 * narration_overlap)
    return round(score, 4)


def match(
    receipts: list[Receipt],
    bank_lines: list[BankLine],
    cfg: RunConfig,
) -> list[Match]:
    """Execute deterministic 1:1 bank-to-receipt matching per Section 6.2."""
    run_id = receipts[0].run_id if receipts else (bank_lines[0].run_id if bank_lines else "run:default")

    # 1. Deduplicate receipts: exclude exact duplicate receipts
    # same vendor_key + total + invoice_date + invoice_no, keeping first occurrence
    seen_receipt_keys: set[tuple[str, Decimal, Any, str | None]] = set()
    eligible_receipts: list[Receipt] = []

    for rcpt in receipts:
        # Exclude cash receipts from bank matching
        if rcpt.payment_mode == "cash":
            continue

        if rcpt.total is None or rcpt.invoice_date is None:
            continue

        dedup_key = (rcpt.vendor_key, rcpt.total, rcpt.invoice_date, rcpt.invoice_no)
        if dedup_key in seen_receipt_keys:
            # Duplicate receipt (e.g. G06 duplicate of G05) -> exclude from bank matching
            continue

        seen_receipt_keys.add(dedup_key)
        eligible_receipts.append(rcpt)

    # 2. Filter bank debit lines: ignore credit lines during expense matching
    eligible_bank_debits: list[BankLine] = [
        b for b in bank_lines if b.debit > Decimal("0.00") and (b.credit == Decimal("0.00") or b.credit is None)
    ]

    # 3. Candidate generation: within amount_tolerance and date_window_days
    candidates: list[dict[str, Any]] = []
    for rcpt in eligible_receipts:
        assert rcpt.total is not None
        assert rcpt.invoice_date is not None

        for bank in eligible_bank_debits:
            amt_diff = abs(bank.debit - rcpt.total)
            days_diff = abs((bank.txn_date - rcpt.invoice_date).days)

            if amt_diff <= cfg.amount_tolerance and days_diff <= cfg.date_window_days:
                score = _compute_score(rcpt, bank, cfg)
                candidates.append(
                    {
                        "score": score,
                        "receipt": rcpt,
                        "bank_line": bank,
                        "txn_date": bank.txn_date,
                        "invoice_date": rcpt.invoice_date,
                    }
                )

    # 4. Check for ambiguous candidates:
    # If two distinct candidates for same receipt/bank line have identical dates and scores within 0.02
    ambiguous_receipts: set[str] = set()
    ambiguous_bank_lines: set[str] = set()

    # Group candidates by receipt
    rcpt_candidates: dict[str, list[dict[str, Any]]] = {}
    for c in candidates:
        rcpt_candidates.setdefault(c["receipt"].id, []).append(c)

    for r_id, c_list in rcpt_candidates.items():
        if len(c_list) > 1:
            for i in range(len(c_list)):
                for j in range(i + 1, len(c_list)):
                    c1, c2 = c_list[i], c_list[j]
                    if c1["bank_line"].txn_date == c2["bank_line"].txn_date and abs(c1["score"] - c2["score"]) <= 0.02:
                        ambiguous_receipts.add(r_id)

    # 5. Deterministic Greedy 1:1 Assignment
    # Sort candidates by:
    # 1. score descending
    # 2. bank txn_date ascending
    # 3. receipt invoice_date ascending
    # 4. receipt.id ascending
    # 5. bank.id ascending
    candidates.sort(
        key=lambda c: (
            -c["score"],
            c["txn_date"],
            c["invoice_date"],
            c["receipt"].id,
            c["bank_line"].id,
        )
    )

    assigned_receipt_ids: set[str] = set()
    assigned_bank_ids: set[str] = set()
    matches: list[Match] = []

    for c in candidates:
        rcpt = c["receipt"]
        bank = c["bank_line"]

        if rcpt.id in assigned_receipt_ids or bank.id in assigned_bank_ids:
            continue

        assigned_receipt_ids.add(rcpt.id)
        assigned_bank_ids.add(bank.id)

        is_ambiguous = rcpt.id in ambiguous_receipts or bank.id in ambiguous_bank_lines
        kind = "AMBIGUOUS" if is_ambiguous else "MATCHED"

        date_delta_days = (bank.txn_date - rcpt.invoice_date).days
        amount_delta = (bank.debit - rcpt.total).quantize(Decimal("0.01"))

        matches.append(
            Match(
                id=f"match:{rcpt.id.replace('rcpt:', '')}_{bank.id.replace('bank:', '')}",
                run_id=run_id,
                receipt_id=rcpt.id,
                bank_line_id=bank.id,
                score=c["score"],
                date_delta_days=date_delta_days,
                amount_delta=amount_delta,
                kind=kind,
            )
        )

    # 6. Reverse pass: unassigned bank debit lines
    for bank in eligible_bank_debits:
        if bank.id not in assigned_bank_ids:
            matches.append(
                Match(
                    id=f"match:bank:{bank.id.replace('bank:', '')}",
                    run_id=run_id,
                    receipt_id=None,
                    bank_line_id=bank.id,
                    score=0.0,
                    date_delta_days=None,
                    amount_delta=None,
                    kind="UNMATCHED_BANK",
                )
            )

    # 7. Reverse pass: unassigned non-cash non-duplicate receipts
    for rcpt in eligible_receipts:
        if rcpt.id not in assigned_receipt_ids:
            matches.append(
                Match(
                    id=f"match:rcpt:{rcpt.id.replace('rcpt:', '')}",
                    run_id=run_id,
                    receipt_id=rcpt.id,
                    bank_line_id=None,
                    score=0.0,
                    date_delta_days=None,
                    amount_delta=None,
                    kind="UNMATCHED_RECEIPT",
                )
            )

    return matches
