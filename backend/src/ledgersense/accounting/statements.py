from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from ledgersense.accounting.chart import (
    BALANCE_SHEET_ACCOUNTS,
    is_expense_account,
    is_income_account,
)
from ledgersense.domain.models import (
    JournalEntry,
    PnL,
    TrialBalance,
    TrialBalanceRow,
    quantize_money,
)


def trial_balance(entries: list[JournalEntry]) -> TrialBalance:
    """Compute the Trial Balance from committed journal entries.

    Aggregates net debits and credits per account code.
    Enforces total_debit == total_credit strictly.
    """
    committed = [e for e in entries if e.status == "COMMITTED"]
    target_entries = committed if committed else entries

    debit_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    credit_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))

    for entry in target_entries:
        for line in entry.lines:
            debit_totals[line.account_code] += line.debit
            credit_totals[line.account_code] += line.credit

    all_accounts = sorted(set(debit_totals.keys()) | set(credit_totals.keys()))
    rows: list[TrialBalanceRow] = []
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    for acct in all_accounts:
        d = quantize_money(debit_totals[acct])
        c = quantize_money(credit_totals[acct])
        rows.append(TrialBalanceRow(account_code=acct, debit=d, credit=c))
        total_debit += d
        total_credit += c

    total_debit = quantize_money(total_debit)
    total_credit = quantize_money(total_credit)
    balanced = total_debit == total_credit

    if not balanced:
        raise ValueError(
            f"Trial Balance out of balance: total debit ({total_debit}) != total credit ({total_credit})"
        )

    return TrialBalance(
        accounts=rows,
        total_debit=total_debit,
        total_credit=total_credit,
        balanced=balanced,
    )


def profit_and_loss(entries: list[JournalEntry]) -> PnL:
    """Compute Profit & Loss statement from income and expense accounts.

    Excludes Balance Sheet accounts (Bank, Cash, Creditors, Input GST, Drawings).
    Net Profit = Total Income - Total Expenses.
    """
    committed = [e for e in entries if e.status == "COMMITTED"]
    target_entries = committed if committed else entries

    income_dict: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    expense_dict: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))

    for entry in target_entries:
        for line in entry.lines:
            acct = line.account_code
            if acct in BALANCE_SHEET_ACCOUNTS:
                continue

            if is_income_account(acct):
                # Income increases with credit
                income_dict[acct] += (line.credit - line.debit)
            elif is_expense_account(acct):
                # Expenses increase with debit
                expense_dict[acct] += (line.debit - line.credit)
            else:
                # Default: accounts starting with 5 are expenses, 4 are income
                if acct.startswith("4"):
                    income_dict[acct] += (line.credit - line.debit)
                else:
                    expense_dict[acct] += (line.debit - line.credit)

    formatted_income = {k: quantize_money(v) for k, v in income_dict.items() if v != Decimal("0.00")}
    formatted_expenses = {k: quantize_money(v) for k, v in expense_dict.items() if v != Decimal("0.00")}

    total_income = quantize_money(sum(formatted_income.values(), Decimal("0.00")))
    total_expenses = quantize_money(sum(formatted_expenses.values(), Decimal("0.00")))
    net_profit = quantize_money(total_income - total_expenses)

    return PnL(
        income=formatted_income,
        expenses=formatted_expenses,
        total_income=total_income,
        total_expenses=total_expenses,
        net_profit=net_profit,
    )
