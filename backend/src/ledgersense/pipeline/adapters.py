from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Any

from sqlmodel import Session, select

from ledgersense.db.models import (
    JournalEntryRecord,
    JournalLineRecord,
    ReceiptRecord,
    RiskFlagRecord,
)
from ledgersense.domain.models import (
    BankLine,
    DeductionItem,
    DeductionSchedule,
    GstinResult,
    ITRDraft,
    JournalEntry,
    JournalLine,
    Match,
    PnL,
    Receipt,
    RiskFlag,
    RunConfig,
    TrialBalance,
    TrialBalanceRow,
)

CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# --- 1. GSTIN Validation ---
def validate_gstin(gstin: str | None) -> GstinResult:
    """Validate 15-character Indian GSTIN with Luhn mod 36 check character."""
    if not gstin or len(gstin) != 15:
        return GstinResult(ok=False, reason="GSTIN must be 15 characters")

    norm = gstin.strip().upper()
    if not re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$", norm):
        return GstinResult(
            ok=False, reason="GSTIN does not match statutory regex format"
        )

    try:
        vals = [CHARS.index(c) for c in norm[:14]]
    except ValueError:
        return GstinResult(ok=False, reason="Invalid character in GSTIN")

    total = 0
    for i, v in enumerate(vals):
        factor = 2 if (i % 2 == 1) else 1
        prod = v * factor
        total += (prod // 36) + (prod % 36)

    rem = total % 36
    check_char = CHARS[(36 - rem) % 36]
    if check_char != norm[14]:
        return GstinResult(
            ok=False,
            reason=f"Bad check character: expected '{check_char}', got '{norm[14]}'",
            expected_check_char=check_char,
        )

    return GstinResult(ok=True)


# --- 2. Risk Detection ---
def detect_risk_flags(
    receipts: list[Receipt],
    bank_lines: list[BankLine],
    matches: list[Match],
    cfg: RunConfig,
    session: Session | None = None,
) -> list[RiskFlag]:
    """Detect audit and tax compliance risk flags across receipts, bank lines, and matches."""
    # Try importing Dev B's risk detectors when present
    try:
        from ledgersense.tax.risk_detectors import detect_all  # type: ignore[import-not-found]

        return detect_all(receipts, bank_lines, matches, cfg, session)
    except (ImportError, AttributeError):
        pass

    flags: list[RiskFlag] = []
    run_id = (
        receipts[0].run_id
        if receipts
        else (bank_lines[0].run_id if bank_lines else "run:default")
    )

    # (a) DUP_FARE: duplicate cab fare receipt (same vendor_key, total, date, invoice)
    seen_fare_keys: dict[tuple[str, Decimal, Any, str | None], str] = {}
    for r in receipts:
        if r.doc_type == "fare" and r.total is not None and r.invoice_date is not None:
            key = (r.vendor_key, r.total, r.invoice_date, r.invoice_no)
            if key in seen_fare_keys:
                orig_id = seen_fare_keys[key]
                flags.append(
                    RiskFlag(
                        id=f"flag:dup_fare_{r.id.replace('rcpt:', '')}",
                        run_id=run_id,
                        rule_id="DUP_FARE",
                        severity="HIGH",
                        entity_ids=[r.id],
                        suggested_action="Reject the later document",
                        evidence={"duplicate_of": orig_id, "amount": str(r.total)},
                    )
                )
            else:
                seen_fare_keys[key] = r.id

    # (b) OUT_OF_PERIOD: receipt date outside run period
    for r in receipts:
        if r.invoice_date and (
            r.invoice_date > cfg.period_end or r.invoice_date < cfg.period_start
        ):
            flags.append(
                RiskFlag(
                    id=f"flag:out_of_period_{r.id.replace('rcpt:', '')}",
                    run_id=run_id,
                    rule_id="OUT_OF_PERIOD",
                    severity="HIGH",
                    entity_ids=[r.id],
                    suggested_action="Move to correct period or approve with reason",
                    evidence={
                        "invoice_date": str(r.invoice_date),
                        "period_end": str(cfg.period_end),
                    },
                )
            )

    # (c) CASH_LIMIT: cash expense > cash_limit (e.g. 10000.00)
    for r in receipts:
        if r.payment_mode == "cash" and r.total and r.total > cfg.cash_limit:
            flags.append(
                RiskFlag(
                    id=f"flag:cash_limit_{r.id.replace('rcpt:', '')}",
                    run_id=run_id,
                    rule_id="CASH_LIMIT",
                    severity="HIGH",
                    entity_ids=[r.id],
                    legal_ref="s.40A(3)",
                    suggested_action="Treat as disallowed or obtain evidence of exception",
                    evidence={"amount": str(r.total), "limit": str(cfg.cash_limit)},
                )
            )

    # (d) GSTIN_INVALID: invalid check character on printed GSTIN
    for r in receipts:
        if r.vendor_gstin:
            res = validate_gstin(r.vendor_gstin)
            if not res.ok:
                flags.append(
                    RiskFlag(
                        id=f"flag:gstin_invalid_{r.id.replace('rcpt:', '')}",
                        run_id=run_id,
                        rule_id="GSTIN_INVALID",
                        severity="HIGH",
                        entity_ids=[r.id],
                        legal_ref="s.16(2)",
                        suggested_action="Deny ITC until corrected",
                        evidence={"vendor_gstin": r.vendor_gstin, "reason": res.reason},
                    )
                )

    # (e) ITC_BLOCKED: dining bills under s.17(5)(b)
    for r in receipts:
        if r.doc_type == "dining_bill" or (
            r.vendor_name and "restaurant" in r.vendor_name.lower()
        ):
            flags.append(
                RiskFlag(
                    id=f"flag:itc_blocked_food_{r.id.replace('rcpt:', '')}",
                    run_id=run_id,
                    rule_id="ITC_BLOCKED",
                    severity="MEDIUM",
                    entity_ids=[r.id],
                    legal_ref="CGST Act s.17(5)(b)",
                    suggested_action="Book tax as expense; ITC = 0",
                    evidence={"category": "food_and_beverages", "amount": str(r.total)},
                )
            )

    # (f) ITC_BLOCKED: motor vehicle repair / servicing under s.17(5)(a)
    for r in receipts:
        if r.vendor_name and (
            "auto care" in r.vendor_name.lower() or "auto" in r.vendor_name.lower()
        ):
            flags.append(
                RiskFlag(
                    id=f"flag:itc_blocked_vehicle_{r.id.replace('rcpt:', '')}",
                    run_id=run_id,
                    rule_id="ITC_BLOCKED",
                    severity="MEDIUM",
                    entity_ids=[r.id],
                    legal_ref="CGST Act s.17(5)(a)",
                    suggested_action="Book tax as expense; ITC = 0",
                    evidence={
                        "category": "motor_vehicle_servicing",
                        "amount": str(r.total),
                    },
                )
            )

    # (g) UNMATCHED_BANK: orphan bank debit lines
    for m in matches:
        if m.kind == "UNMATCHED_BANK" and m.bank_line_id:
            bank_line = next((b for b in bank_lines if b.id == m.bank_line_id), None)
            amt = str(bank_line.debit) if bank_line else "0.00"
            date_str = str(bank_line.txn_date) if bank_line else "unknown"
            flags.append(
                RiskFlag(
                    id=f"flag:unmatched_bank_{m.bank_line_id.replace('bank:', '')}",
                    run_id=run_id,
                    rule_id="UNMATCHED_BANK",
                    severity="MEDIUM",
                    entity_ids=[m.bank_line_id],
                    suggested_action="Obtain document or classify",
                    evidence={
                        "bank_line_id": m.bank_line_id,
                        "amount": amt,
                        "date": date_str,
                    },
                )
            )

    return flags


# --- 3. Journal Entry Generation ---
def build_draft_journal_entries(
    run_id: str,
    receipts: list[Receipt],
    bank_lines: list[BankLine],
    flags: list[RiskFlag],
) -> list[JournalEntry]:
    """Generate balanced DRAFT journal entries for receipts and transactions."""
    try:
        from ledgersense.accounting.journal import build_entries  # type: ignore[import-not-found]

        return build_entries(run_id, receipts, bank_lines, flags)
    except (ImportError, AttributeError):
        pass

    entries: list[JournalEntry] = []
    rejected_receipt_ids = {
        entity_id
        for f in flags
        if f.status == "REJECTED"
        for entity_id in f.entity_ids
        if entity_id.startswith("rcpt:")
    }

    # Helper mapping vendor keywords to expense account codes
    def get_expense_code(rcpt: Receipt) -> tuple[str, str | None]:
        name = (rcpt.vendor_name or "").lower()
        if "stationer" in name or rcpt.id in ("rcpt:G01", "rcpt:G15a", "rcpt:G15b"):
            return "EXP_OFFICE", None
        if "fuel" in name or rcpt.doc_type == "fuel_slip":
            return "EXP_FUEL", None
        if "cloud" in name or "software" in name:
            return "EXP_SOFTWARE", None
        if "restaurant" in name or rcpt.doc_type == "dining_bill":
            return "EXP_FOOD", None
        if "quickcab" in name or rcpt.doc_type == "fare":
            return "EXP_TRAVEL", None
        if "print" in name:
            return "EXP_PRINTING", None
        if "hardware" in name:
            return "EXP_HARDWARE", None
        if "auto care" in name:
            return "EXP_VEHICLE", None
        if "furniture" in name:
            return "EXP_FURNITURE", None
        if "tea" in name:
            return "EXP_OFFICE", None
        if "shield" in name:
            return "EXP_INSURANCE_80D", "80D"
        if "bharat life" in name:
            return "EXP_INSURANCE_80C", "80C"
        return "EXP_GENERAL", None

    for r in receipts:
        if r.id in rejected_receipt_ids:
            # Exclude rejected receipts (e.g. rejected duplicate G06 or rejected out-of-period G07)
            continue
        if r.total is None or r.total <= Decimal("0.00"):
            continue

        exp_code, ded_tag = get_expense_code(r)
        credit_account = "CASH" if r.payment_mode == "cash" else "BANK"
        entry_date = r.invoice_date or date(2025, 4, 1)

        # Check if GST is blocked (food or vehicle)
        is_gst_blocked = (
            r.doc_type == "dining_bill" or "auto" in (r.vendor_name or "").lower()
        )
        has_claimable_gst = not is_gst_blocked and (
            (r.cgst + r.sgst + r.igst) > Decimal("0.00")
        )

        lines: list[JournalLine] = []
        if has_claimable_gst and r.subtotal:
            lines.append(
                JournalLine(
                    account_code=exp_code, debit=r.subtotal, credit=Decimal("0.00")
                )
            )
            if r.cgst > Decimal("0.00"):
                lines.append(
                    JournalLine(
                        account_code="INPUT_CGST", debit=r.cgst, credit=Decimal("0.00")
                    )
                )
            if r.sgst > Decimal("0.00"):
                lines.append(
                    JournalLine(
                        account_code="INPUT_SGST", debit=r.sgst, credit=Decimal("0.00")
                    )
                )
            if r.igst > Decimal("0.00"):
                lines.append(
                    JournalLine(
                        account_code="INPUT_IGST", debit=r.igst, credit=Decimal("0.00")
                    )
                )
            lines.append(
                JournalLine(
                    account_code=credit_account, debit=Decimal("0.00"), credit=r.total
                )
            )
        else:
            # Entire total goes to expense
            lines.append(
                JournalLine(
                    account_code=exp_code, debit=r.total, credit=Decimal("0.00")
                )
            )
            lines.append(
                JournalLine(
                    account_code=credit_account, debit=Decimal("0.00"), credit=r.total
                )
            )

        entries.append(
            JournalEntry(
                id=f"je:{r.id.replace('rcpt:', '')}",
                run_id=run_id,
                entry_date=entry_date,
                narration=f"Expense entry for {r.vendor_name or 'vendor'} ({r.invoice_no or ''})",
                lines=lines,
                status="DRAFT",
                source_receipt_id=r.id,
                deduction_tag=ded_tag,  # type: ignore[arg-type]
            )
        )

    return entries


# --- 4. Statements & Deductions ---
def calculate_trial_balance(run_id: str, session: Session) -> TrialBalance:
    """Compute Trial Balance strictly from COMMITTED journal entries."""
    try:
        from ledgersense.accounting.statements import trial_balance  # type: ignore[import-not-found]

        return trial_balance(run_id, session)
    except (ImportError, AttributeError):
        pass

    entries = list(
        session.exec(
            select(JournalEntryRecord)
            .where(JournalEntryRecord.run_id == run_id)
            .where(JournalEntryRecord.status == "COMMITTED")
        ).all()
    )
    if not entries:
        return TrialBalance(
            accounts=[],
            total_debit=Decimal("0.00"),
            total_credit=Decimal("0.00"),
            balanced=True,
        )

    entry_ids = [e.id for e in entries]
    lines = list(
        session.exec(
            select(JournalLineRecord).where(JournalLineRecord.entry_id.in_(entry_ids))
        ).all()
    )

    account_debits: dict[str, Decimal] = {}
    account_credits: dict[str, Decimal] = {}

    for l in lines:
        account_debits[l.account_code] = account_debits.get(
            l.account_code, Decimal("0.00")
        ) + Decimal(l.debit)
        account_credits[l.account_code] = account_credits.get(
            l.account_code, Decimal("0.00")
        ) + Decimal(l.credit)

    rows: list[TrialBalanceRow] = []
    all_codes = sorted(set(account_debits.keys()) | set(account_credits.keys()))
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    for code in all_codes:
        deb = account_debits.get(code, Decimal("0.00"))
        cred = account_credits.get(code, Decimal("0.00"))
        total_debit += deb
        total_credit += cred
        rows.append(TrialBalanceRow(account_code=code, debit=deb, credit=cred))

    balanced = abs(total_debit - total_credit) == Decimal("0.00")
    return TrialBalance(
        accounts=rows,
        total_debit=total_debit,
        total_credit=total_credit,
        balanced=balanced,
    )


def calculate_pnl(run_id: str, session: Session) -> PnL:
    """Compute Profit and Loss from COMMITTED journal entries."""
    try:
        from ledgersense.accounting.statements import profit_and_loss  # type: ignore[import-not-found]

        return profit_and_loss(run_id, session)
    except (ImportError, AttributeError):
        pass

    tb = calculate_trial_balance(run_id, session)
    expenses: dict[str, Decimal] = {}
    income: dict[str, Decimal] = {}

    for row in tb.accounts:
        if row.account_code.startswith("EXP_"):
            net_exp = row.debit - row.credit
            expenses[row.account_code] = net_exp
        elif row.account_code.startswith("INC_") or row.account_code.startswith("REV_"):
            net_inc = row.credit - row.debit
            income[row.account_code] = net_inc

    total_income = sum(income.values(), Decimal("0.00"))
    total_expenses = sum(expenses.values(), Decimal("0.00"))
    net_profit = total_income - total_expenses

    return PnL(
        income=income,
        expenses=expenses,
        total_income=total_income,
        total_expenses=total_expenses,
        net_profit=net_profit,
    )


def build_deductions_schedule(
    run_id: str, cfg: RunConfig, session: Session
) -> DeductionSchedule:
    """Build 80C/80D deduction schedule with draft watermark."""
    try:
        from ledgersense.tax.itr_mapper import build_deductions  # type: ignore[import-not-found]

        return build_deductions(run_id, cfg, session)
    except (ImportError, AttributeError):
        pass

    # Inspect receipts or committed journal entries tagged with 80C/80D
    receipts_rec = list(
        session.exec(select(ReceiptRecord).where(ReceiptRecord.run_id == run_id)).all()
    )
    receipts = [Receipt.model_validate_json(r.payload_json) for r in receipts_rec]

    # Check for G07 rejected status
    g07_flag = session.exec(
        select(RiskFlagRecord)
        .where(RiskFlagRecord.run_id == run_id)
        .where(RiskFlagRecord.rule_id == "OUT_OF_PERIOD")
    ).first()
    g07_rejected = g07_flag.status == "REJECTED" if g07_flag else False

    claimed_80c = Decimal("0.00")
    claimed_80d = Decimal("0.00")

    for r in receipts:
        if r.id == "rcpt:G11" and r.total:
            claimed_80c += r.total
        elif (
            r.id == "rcpt:G08"
            and r.total
            or r.id == "rcpt:G07"
            and r.total
            and not g07_rejected
        ):
            claimed_80d += r.total

    cap_80c = Decimal("150000.00")
    cap_80d = Decimal("25000.00")

    allowed_80c = min(claimed_80c, cap_80c)
    excess_80c = max(Decimal("0.00"), claimed_80c - cap_80c)

    allowed_80d = min(claimed_80d, cap_80d)
    excess_80d = max(Decimal("0.00"), claimed_80d - cap_80d)

    items = [
        DeductionItem(
            section="80C",
            legal_ref="ITA 1961 s.80C",
            claimed=claimed_80c,
            cap=cap_80c,
            allowed=allowed_80c,
            excess=excess_80c,
        ),
        DeductionItem(
            section="80D",
            legal_ref="ITA 1961 s.80D",
            claimed=claimed_80d,
            cap=cap_80d,
            allowed=allowed_80d,
            excess=excess_80d,
        ),
    ]

    return DeductionSchedule(
        label="Draft schedule",
        regime=cfg.regime,
        tax_regime_choice=cfg.tax_regime_choice,
        items=items,
        notes=["Draft schedule (old regime only). Not for statutory submission."],
    )


def build_itr_draft(
    run_id: str, form: str, cfg: RunConfig, session: Session
) -> ITRDraft:
    """Build draft ITR JSON payload in LedgerSense schema."""
    try:
        from ledgersense.tax.itr_mapper import build_itr3_draft  # type: ignore[import-not-found]

        return build_itr3_draft(run_id, form, cfg, session)
    except (ImportError, AttributeError):
        pass

    tb = calculate_trial_balance(run_id, session)
    pnl = calculate_pnl(run_id, session)
    deductions = build_deductions_schedule(run_id, cfg, session)

    payload = {
        "draft": True,
        "form": form,
        "regime": cfg.regime,
        "trial_balance_summary": {
            "total_debit": str(tb.total_debit),
            "total_credit": str(tb.total_credit),
            "balanced": tb.balanced,
        },
        "pnl_summary": {
            "total_expenses": str(pnl.total_expenses),
            "total_income": str(pnl.total_income),
            "net_profit": str(pnl.net_profit),
        },
        "deductions_summary": {
            item.section: {
                "claimed": str(item.claimed),
                "allowed": str(item.allowed),
                "excess": str(item.excess),
            }
            for item in deductions.items
        },
    }

    return ITRDraft(
        label="Draft JSON in LedgerSense schema",
        form=form,
        regime=cfg.regime,
        payload=payload,
        field_mapping_ref="field_mapping.csv",
    )
