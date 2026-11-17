from __future__ import annotations

from datetime import date
from decimal import Decimal

from ledgersense.accounting.chart import (
    BANK,
    CASH,
    INPUT_CGST,
    INPUT_IGST,
    INPUT_SGST,
    SUNDRY_CREDITORS,
    map_expense_account,
)
from ledgersense.domain.models import (
    BankLine,
    JournalEntry,
    JournalLine,
    Match,
    Receipt,
    RiskFlag,
    RunConfig,
)


def _determine_deduction_tag(receipt: Receipt) -> str | None:
    """Determine Chapter VI-A deduction tag (80C / 80D) for eligible premium receipts."""
    if receipt.doc_type != "premium_receipt":
        return None

    vendor_text = (receipt.vendor_name or "").lower()
    if "health" in vendor_text:
        return "80D"
    if "life" in vendor_text:
        return "80C"
    return None


def build_entries(
    receipts: list[Receipt],
    matches: list[Match],
    flags: list[RiskFlag],
    cfg: RunConfig,
    bank_lines: list[BankLine] | None = None,
) -> list[JournalEntry]:
    """Construct double-entry JournalEntry models from receipts, bank matches, and audit risk flags.

    Enforces:
    - Balanced debits and credits strictly preserved.
    - Blocking Input Tax Credit on ITC_BLOCKED and GSTIN_INVALID receipts (gross expense).
    - Unapproved duplicates and out-of-period items excluded when REJECTED.
    - OPEN high-risk entries held in DRAFT status.
    - Deduction tagging for 80C and 80D.
    """
    matches_by_receipt = {m.receipt_id: m for m in matches if m.receipt_id}
    flags_by_receipt: dict[str, list[RiskFlag]] = {}
    for f in flags:
        for eid in f.entity_ids:
            flags_by_receipt.setdefault(eid, []).append(f)

    entries: list[JournalEntry] = []
    entry_counter = 1

    for rcpt in receipts:
        if rcpt.total is None or rcpt.total <= Decimal("0.00"):
            continue

        rcpt_flags = flags_by_receipt.get(rcpt.id, [])
        rcpt_flag_ids = [f.id for f in rcpt_flags]

        # Exclude rejected duplicate or out-of-period receipts
        is_rejected_duplicate = any(
            f.rule_id in ("DUP_FARE", "DUP_DOC") and f.status == "REJECTED"
            for f in rcpt_flags
        )
        is_rejected_out_of_period = any(
            f.rule_id == "OUT_OF_PERIOD" and f.status == "REJECTED"
            for f in rcpt_flags
        )
        if is_rejected_duplicate or is_rejected_out_of_period:
            continue

        # Entries are generated in DRAFT status until committed by human gate
        entry_status = "DRAFT"

        # Determine ITC eligibility:
        # Blocked under s.17(5) or invalid GSTIN under s.16(2)(aa)
        itc_blocked = any(
            f.rule_id in ("ITC_BLOCKED", "GSTIN_INVALID") and f.status != "AUTO_RESOLVED"
            for f in rcpt_flags
        )

        expense_account = map_expense_account(rcpt)
        lines: list[JournalLine] = []

        cgst = rcpt.cgst or Decimal("0.00")
        sgst = rcpt.sgst or Decimal("0.00")
        igst = rcpt.igst or Decimal("0.00")
        tax_total = cgst + sgst + igst

        if itc_blocked or tax_total <= Decimal("0.00"):
            # Book gross total to Expense account; zero Input GST
            lines.append(
                JournalLine(
                    account_code=expense_account,
                    debit=rcpt.total,
                    credit=Decimal("0.00"),
                )
            )
        else:
            # ITC is eligible: debit net subtotal to expense, debit input GST accounts
            subtotal = rcpt.subtotal if rcpt.subtotal is not None else (rcpt.total - tax_total)
            lines.append(
                JournalLine(
                    account_code=expense_account,
                    debit=subtotal,
                    credit=Decimal("0.00"),
                )
            )
            if cgst > Decimal("0.00"):
                lines.append(JournalLine(account_code=INPUT_CGST, debit=cgst, credit=Decimal("0.00")))
            if sgst > Decimal("0.00"):
                lines.append(JournalLine(account_code=INPUT_SGST, debit=sgst, credit=Decimal("0.00")))
            if igst > Decimal("0.00"):
                lines.append(JournalLine(account_code=INPUT_IGST, debit=igst, credit=Decimal("0.00")))

        # Credit account resolution
        match = matches_by_receipt.get(rcpt.id)
        if rcpt.payment_mode == "cash":
            credit_account = CASH
        elif match and match.kind == "MATCHED":
            credit_account = BANK
        else:
            credit_account = SUNDRY_CREDITORS

        lines.append(
            JournalLine(
                account_code=credit_account,
                debit=Decimal("0.00"),
                credit=rcpt.total,
            )
        )

        narration = f"{rcpt.vendor_name or 'Expense'} - {rcpt.doc_type} (Invoice: {rcpt.invoice_no or 'N/A'})"
        deduction_tag = _determine_deduction_tag(rcpt)

        entries.append(
            JournalEntry(
                id=f"je:{entry_counter:04d}",
                run_id=rcpt.run_id,
                entry_date=rcpt.invoice_date or date.today(),
                narration=narration,
                lines=lines,
                status=entry_status,
                source_receipt_id=rcpt.id,
                flag_ids=rcpt_flag_ids,
                deduction_tag=deduction_tag,
            )
        )
        entry_counter += 1

    return entries


def commit_entries(
    entries: list[JournalEntry],
    flags: list[RiskFlag],
) -> list[JournalEntry]:
    """Commit draft journal entries after validating that no HIGH risk flags remain OPEN.

    Raises ValueError (Gate Rule) if any HIGH severity risk flag is OPEN.
    Filters out any entries whose source receipts have been REJECTED.
    Transitions all eligible entries to status="COMMITTED".
    """
    open_high_flags = [f for f in flags if f.severity == "HIGH" and f.status == "OPEN"]
    if open_high_flags:
        rule_ids = [f.rule_id for f in open_high_flags]
        raise ValueError(
            f"Gate Rule Blocked: Cannot commit journal entries while {len(open_high_flags)} "
            f"HIGH severity risk flags remain OPEN ({rule_ids})."
        )

    # Identify all entity IDs rejected by auditor
    rejected_entity_ids = {
        eid for f in flags if f.status == "REJECTED" for eid in f.entity_ids
    }

    committed: list[JournalEntry] = []
    for entry in entries:
        if entry.source_receipt_id and entry.source_receipt_id in rejected_entity_ids:
            continue  # Exclude rejected items

        committed.append(
            entry.model_copy(update={"status": "COMMITTED"})
        )

    return committed
