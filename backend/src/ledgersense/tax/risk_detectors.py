from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from ledgersense.domain.models import (
    BankLine,
    Match,
    Receipt,
    RiskFlag,
    RunConfig,
    Severity,
)
from ledgersense.tax.gstin import validate_gstin
from ledgersense.tax.rules_engine import RuleSet, load_rules

SEVERITY_ORDER: dict[Severity, int] = {
    "HIGH": 0,
    "MEDIUM": 1,
    "LOW": 2,
}


def _get_run_id(
    receipts: list[Receipt],
    matches: list[Match],
    bank_lines: list[BankLine],
) -> str:
    """Extract run_id from available entities or fallback to default."""
    if receipts and receipts[0].run_id:
        return receipts[0].run_id
    if matches and matches[0].run_id:
        return matches[0].run_id
    if bank_lines and bank_lines[0].run_id:
        return bank_lines[0].run_id
    return "run:default"


# --- 1. DUP_FARE / DUP_DOC Detector ---


def detect_duplicates(
    receipts: list[Receipt], run_id: str = "run:default"
) -> list[RiskFlag]:
    """Detect exact and near duplicate receipts.

    - Exact: two receipts share (vendor_key, total, invoice_date, invoice_no) when invoice_no present.
    - Near: two receipts share (vendor_key, total) and abs(date delta) <= 1 day when invoice_no missing.
    Keeps the earlier receipt clean and flags subsequent duplicate occurrences.
    """
    flags: list[RiskFlag] = []
    seen: list[Receipt] = []

    for rcpt in receipts:
        if rcpt.total is None or rcpt.invoice_date is None:
            seen.append(rcpt)
            continue

        duplicate_of: Receipt | None = None
        dup_kind: str | None = None

        for prev in seen:
            if prev.total is None or prev.invoice_date is None:
                continue
            if prev.vendor_key != rcpt.vendor_key or prev.total != rcpt.total:
                continue

            # Exact duplicate: matching invoice_no and invoice_date
            if rcpt.invoice_no and prev.invoice_no:
                if (
                    rcpt.invoice_no.strip() == prev.invoice_no.strip()
                    and rcpt.invoice_date == prev.invoice_date
                ):
                    duplicate_of = prev
                    dup_kind = "exact"
                    break
            else:
                # Near duplicate: invoice_no missing on either, date delta <= 1 day
                delta_days = abs((rcpt.invoice_date - prev.invoice_date).days)
                if delta_days <= 1:
                    duplicate_of = prev
                    dup_kind = "near"
                    break

        if duplicate_of:
            is_fare = (
                rcpt.doc_type == "fare" or "cab" in (rcpt.vendor_name or "").lower()
            )
            rule_id = "DUP_FARE" if is_fare else "DUP_DOC"
            severity: Severity = "HIGH" if is_fare else "MEDIUM"
            legal_ref = (
                "Internal Audit Control — Duplicate Claim"
                if is_fare
                else "Internal Audit Control — Duplicate Document"
            )

            flags.append(
                RiskFlag(
                    id=f"flag:dup:{rcpt.id}",
                    run_id=run_id,
                    rule_id=rule_id,
                    severity=severity,
                    entity_ids=[rcpt.id],
                    legal_ref=legal_ref,
                    evidence={
                        "duplicate_of": duplicate_of.id,
                        "kind": dup_kind,
                        "vendor_key": rcpt.vendor_key,
                        "vendor_name": rcpt.vendor_name,
                        "total": str(rcpt.total),
                        "invoice_date": str(rcpt.invoice_date),
                        "invoice_no": rcpt.invoice_no,
                        "reason": f"Duplicate of {duplicate_of.id} ({dup_kind} duplicate)",
                    },
                    suggested_action="Reject the later document",
                    status="OPEN",
                )
            )
        else:
            seen.append(rcpt)

    return flags


# --- 2. OUT_OF_PERIOD Detector ---


def detect_out_of_period(
    receipts: list[Receipt],
    cfg: RunConfig,
    run_id: str = "run:default",
) -> list[RiskFlag]:
    """Flag receipts with invoice_date falling outside [cfg.period_start, cfg.period_end]."""
    flags: list[RiskFlag] = []

    for rcpt in receipts:
        if rcpt.invoice_date is None:
            continue

        if rcpt.invoice_date < cfg.period_start or rcpt.invoice_date > cfg.period_end:
            flags.append(
                RiskFlag(
                    id=f"flag:period:{rcpt.id}",
                    run_id=run_id,
                    rule_id="OUT_OF_PERIOD",
                    severity="HIGH",
                    entity_ids=[rcpt.id],
                    legal_ref="Matching & Cut-off Principle (FY Boundary)",
                    evidence={
                        "vendor_name": rcpt.vendor_name,
                        "invoice_date": str(rcpt.invoice_date),
                        "period_start": str(cfg.period_start),
                        "period_end": str(cfg.period_end),
                        "total": str(rcpt.total) if rcpt.total is not None else None,
                        "reason": (
                            f"Invoice date {rcpt.invoice_date} falls outside "
                            f"reconciliation period {cfg.period_start} to {cfg.period_end}"
                        ),
                    },
                    suggested_action="Move to correct period or approve with reason",
                    status="OPEN",
                )
            )

    return flags


# --- 3. CASH_LIMIT Detector ---


def detect_cash_limit(
    receipts: list[Receipt],
    cfg: RunConfig,
    rules: RuleSet,
    run_id: str = "run:default",
) -> list[RiskFlag]:
    """Flag cash transactions exceeding statutory limit per vendor per day (s.40A(3))."""
    flags: list[RiskFlag] = []

    # Group cash receipts by (vendor_key, invoice_date)
    cash_groups: dict[tuple[str, Any], list[Receipt]] = defaultdict(list)
    for rcpt in receipts:
        if rcpt.payment_mode == "cash" and rcpt.invoice_date and rcpt.total:
            cash_groups[(rcpt.vendor_key, rcpt.invoice_date)].append(rcpt)

    legal_ref = rules.cash_limit_ref(cfg.regime)

    for (vkey, idate), group in cash_groups.items():
        total_cash = sum(r.total for r in group if r.total is not None)
        if total_cash > cfg.cash_limit:
            entity_ids = [r.id for r in group]
            flags.append(
                RiskFlag(
                    id=f"flag:cash:{group[0].id}",
                    run_id=run_id,
                    rule_id="CASH_LIMIT",
                    severity="HIGH",
                    entity_ids=entity_ids,
                    legal_ref=legal_ref,
                    evidence={
                        "vendor_key": vkey,
                        "vendor_name": group[0].vendor_name,
                        "invoice_date": str(idate),
                        "cash_total": str(total_cash),
                        "cash_limit": str(cfg.cash_limit),
                        "receipt_ids": entity_ids,
                        "reason": f"Cash expense {total_cash} exceeds statutory limit {cfg.cash_limit}",
                    },
                    suggested_action="Treat as disallowed or obtain evidence of exception",
                    status="OPEN",
                )
            )

    return flags


# --- 4. GSTIN_INVALID Detector ---


def detect_invalid_gstin(
    receipts: list[Receipt],
    run_id: str = "run:default",
) -> list[RiskFlag]:
    """Flag invalid GSTIN on invoices or tax invoices claiming GST without valid GSTIN."""
    flags: list[RiskFlag] = []

    for rcpt in receipts:
        tax_claimed = (
            (rcpt.cgst or Decimal(0))
            + (rcpt.sgst or Decimal(0))
            + (rcpt.igst or Decimal(0))
        )

        # Check if GSTIN present or tax claimed
        if rcpt.vendor_gstin:
            res = validate_gstin(rcpt.vendor_gstin)
            if not res.ok:
                flags.append(
                    RiskFlag(
                        id=f"flag:gstin:{rcpt.id}",
                        run_id=run_id,
                        rule_id="GSTIN_INVALID",
                        severity="HIGH",
                        entity_ids=[rcpt.id],
                        legal_ref="CGST Act s.16(2)(aa) — Valid Tax Invoice / GSTIN",
                        evidence={
                            "vendor_name": rcpt.vendor_name,
                            "vendor_gstin": rcpt.vendor_gstin,
                            "reason": res.reason,
                            "expected_check_char": res.expected_check_char,
                            "tax_claimed": str(tax_claimed),
                        },
                        suggested_action="Deny ITC until corrected",
                        status="OPEN",
                    )
                )
        elif tax_claimed > Decimal("0.00"):
            # Tax claimed but missing GSTIN entirely
            flags.append(
                RiskFlag(
                    id=f"flag:gstin_missing:{rcpt.id}",
                    run_id=run_id,
                    rule_id="GSTIN_INVALID",
                    severity="HIGH",
                    entity_ids=[rcpt.id],
                    legal_ref="CGST Act s.16(2)(aa) — Valid Tax Invoice / GSTIN",
                    evidence={
                        "vendor_name": rcpt.vendor_name,
                        "vendor_gstin": None,
                        "reason": "missing_gstin_on_tax_invoice",
                        "tax_claimed": str(tax_claimed),
                    },
                    suggested_action="Deny ITC until corrected",
                    status="OPEN",
                )
            )

    return flags


# --- 5. ITC_BLOCKED Detector ---


def detect_blocked_itc(
    receipts: list[Receipt],
    rules: RuleSet,
    run_id: str = "run:default",
) -> list[RiskFlag]:
    """Flag input tax credit claims blocked under CGST Act s.17(5) based on keywords."""
    flags: list[RiskFlag] = []

    for rcpt in receipts:
        tax_claimed = (
            (rcpt.cgst or Decimal(0))
            + (rcpt.sgst or Decimal(0))
            + (rcpt.igst or Decimal(0))
        )
        if tax_claimed <= Decimal("0.00"):
            continue  # No ITC claimed to block

        # Aggregate text tokens from vendor name and line item descriptions
        text_parts = [rcpt.vendor_name or ""]
        for item in rcpt.line_items:
            if item.description:
                text_parts.append(item.description)
        full_text = " ".join(text_parts).lower()

        for category in rules.gst.categories:
            matched_keyword = next(
                (kw for kw in category.keywords if kw.lower() in full_text), None
            )
            if matched_keyword:
                flags.append(
                    RiskFlag(
                        id=f"flag:itc:{rcpt.id}",
                        run_id=run_id,
                        rule_id="ITC_BLOCKED",
                        severity=category.severity,
                        entity_ids=[rcpt.id],
                        legal_ref=category.ref,
                        evidence={
                            "category": category.id,
                            "matched_keyword": matched_keyword,
                            "vendor_name": rcpt.vendor_name,
                            "tax_claimed": str(tax_claimed),
                            "total": str(rcpt.total)
                            if rcpt.total is not None
                            else None,
                            "reason": f"Blocked ITC under {category.ref} for {category.id.lower()}",
                        },
                        suggested_action="Book tax as expense; ITC = 0",
                        status="OPEN",
                    )
                )
                break  # One blocked category match per receipt is sufficient

    return flags


# --- 6. UNMATCHED_RECEIPT Detector ---


def detect_unmatched_receipts(
    matches: list[Match],
    run_id: str = "run:default",
) -> list[RiskFlag]:
    """Flag vouchers that have no matching bank entry."""
    flags: list[RiskFlag] = []

    for m in matches:
        if m.kind == "UNMATCHED_RECEIPT" and m.receipt_id:
            flags.append(
                RiskFlag(
                    id=f"flag:unmatched_rcpt:{m.receipt_id}",
                    run_id=run_id,
                    rule_id="UNMATCHED_RECEIPT",
                    severity="MEDIUM",
                    entity_ids=[m.receipt_id],
                    legal_ref="Bank Reconciliation — Unmatched Expense Voucher",
                    evidence={
                        "receipt_id": m.receipt_id,
                        "score": m.score,
                        "reason": "Expense voucher has no matching bank debit",
                    },
                    suggested_action="Obtain matching bank entry or confirm cash transaction",
                    status="OPEN",
                )
            )

    return flags


# --- 7. UNMATCHED_BANK Detector ---


def detect_unmatched_bank(
    matches: list[Match],
    bank_lines: list[BankLine],
    run_id: str = "run:default",
) -> list[RiskFlag]:
    """Flag unexplained bank debit lines that have no matching receipt."""
    flags: list[RiskFlag] = []
    bank_lines_by_id = {b.id: b for b in bank_lines}

    for m in matches:
        if m.kind == "UNMATCHED_BANK" and m.bank_line_id:
            bank_line = bank_lines_by_id.get(m.bank_line_id)
            evidence: dict[str, Any] = {
                "bank_line_id": m.bank_line_id,
                "reason": "Bank debit has no matching receipt",
            }
            if bank_line:
                evidence.update(
                    {
                        "amount": str(bank_line.debit),
                        "txn_date": str(bank_line.txn_date),
                        "narration": bank_line.narration,
                    }
                )

            flags.append(
                RiskFlag(
                    id=f"flag:unmatched_bank:{m.bank_line_id}",
                    run_id=run_id,
                    rule_id="UNMATCHED_BANK",
                    severity="MEDIUM",
                    entity_ids=[m.bank_line_id],
                    legal_ref="Bank Reconciliation — Unexplained Bank Debit",
                    evidence=evidence,
                    suggested_action="Obtain document or classify",
                    status="OPEN",
                )
            )

    return flags


# --- 8. ARITH_MISMATCH Detector ---


def detect_arithmetic_mismatches(
    receipts: list[Receipt],
    run_id: str = "run:default",
) -> list[RiskFlag]:
    """Flag receipts where subtotal, tax components, and total arithmetic do not add up."""
    flags: list[RiskFlag] = []

    for rcpt in receipts:
        if rcpt.check_messages:
            flags.append(
                RiskFlag(
                    id=f"flag:arith:{rcpt.id}",
                    run_id=run_id,
                    rule_id="ARITH_MISMATCH",
                    severity="MEDIUM",
                    entity_ids=[rcpt.id],
                    legal_ref="Invoice Arithmetic Integrity",
                    evidence={
                        "vendor_name": rcpt.vendor_name,
                        "check_messages": rcpt.check_messages,
                        "total": str(rcpt.total) if rcpt.total is not None else None,
                        "reason": "; ".join(rcpt.check_messages),
                    },
                    suggested_action="Verify line items and recalculate tax/total",
                    status="OPEN",
                )
            )

    return flags


# --- 9. LOW_CONFIDENCE Detector ---


def detect_low_confidence(
    receipts: list[Receipt],
    run_id: str = "run:default",
) -> list[RiskFlag]:
    """Flag receipts whose extraction confidence falls below the confidence threshold."""
    flags: list[RiskFlag] = []

    for rcpt in receipts:
        if rcpt.extraction_status == "LOW_CONFIDENCE":
            flags.append(
                RiskFlag(
                    id=f"flag:conf:{rcpt.id}",
                    run_id=run_id,
                    rule_id="LOW_CONFIDENCE",
                    severity="LOW",
                    entity_ids=[rcpt.id],
                    legal_ref="OCR / Vision Extraction Confidence Threshold",
                    evidence={
                        "vendor_name": rcpt.vendor_name,
                        "extraction_status": rcpt.extraction_status,
                        "field_confidence": rcpt.field_confidence,
                        "reason": "One or more critical fields below confidence threshold",
                    },
                    suggested_action="Manually inspect and verify extracted fields",
                    status="OPEN",
                )
            )

    return flags


# --- Top-Level Coordinator: detect_all ---


def detect_all(
    receipts: list[Receipt],
    matches: list[Match],
    bank_lines: list[BankLine],
    cfg: RunConfig,
    rules: RuleSet | None = None,
) -> list[RiskFlag]:
    """Run all 9 statutory and audit risk detectors.

    Returns risk flags ordered by severity (HIGH first, then MEDIUM, then LOW),
    with canonical sequential IDs ('flag:0001', 'flag:0002', etc.).
    """
    effective_rules = rules if rules is not None else load_rules()
    run_id = _get_run_id(receipts, matches, bank_lines)

    raw_flags: list[RiskFlag] = []

    # 1. Duplicate detection
    raw_flags.extend(detect_duplicates(receipts, run_id=run_id))

    # 2. Cut-off / Out of period
    raw_flags.extend(detect_out_of_period(receipts, cfg=cfg, run_id=run_id))

    # 3. Cash limit
    raw_flags.extend(
        detect_cash_limit(receipts, cfg=cfg, rules=effective_rules, run_id=run_id)
    )

    # 4. GSTIN validation
    raw_flags.extend(detect_invalid_gstin(receipts, run_id=run_id))

    # 5. Blocked ITC
    raw_flags.extend(detect_blocked_itc(receipts, rules=effective_rules, run_id=run_id))

    # 6. Unmatched receipts
    raw_flags.extend(detect_unmatched_receipts(matches, run_id=run_id))

    # 7. Unmatched bank debits
    raw_flags.extend(
        detect_unmatched_bank(matches, bank_lines=bank_lines, run_id=run_id)
    )

    # 8. Arithmetic integrity
    raw_flags.extend(detect_arithmetic_mismatches(receipts, run_id=run_id))

    # 9. Low extraction confidence
    raw_flags.extend(detect_low_confidence(receipts, run_id=run_id))

    # Sort flags by severity (HIGH -> MEDIUM -> LOW) then by rule_id and entity_ids
    raw_flags.sort(
        key=lambda f: (
            SEVERITY_ORDER.get(f.severity, 3),
            f.rule_id,
            f.entity_ids[0] if f.entity_ids else "",
        )
    )

    # Renumber sequentially to canonical IDs: flag:0001, flag:0002, ...
    final_flags: list[RiskFlag] = []
    for idx, flag in enumerate(raw_flags, start=1):
        final_flags.append(flag.model_copy(update={"id": f"flag:{idx:04d}"}))

    return final_flags
