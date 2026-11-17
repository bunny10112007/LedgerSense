from __future__ import annotations

from ledgersense.domain.models import Receipt

# Balance Sheet Accounts (Assets, Liabilities, Equity)
BANK = "1000-Bank"
CASH = "1010-Cash in Hand"
INPUT_CGST = "1200-Input CGST"
INPUT_SGST = "1210-Input SGST"
INPUT_IGST = "1220-Input IGST"
SUNDRY_CREDITORS = "2000-Sundry Creditors"
DRAWINGS_INSURANCE = "3100-Insurance / Drawings"

BALANCE_SHEET_ACCOUNTS = frozenset(
    {
        BANK,
        CASH,
        INPUT_CGST,
        INPUT_SGST,
        INPUT_IGST,
        SUNDRY_CREDITORS,
        DRAWINGS_INSURANCE,
    }
)

# Revenue Accounts
CLIENT_REVENUE = "4000-Client Revenue"

REVENUE_ACCOUNTS = frozenset({CLIENT_REVENUE})

# Expense Accounts
EXP_OFFICE = "5000-Office & Stationery Expense"
EXP_FUEL = "5010-Fuel Expense"
EXP_SOFTWARE = "5020-Software & IT Expense"
EXP_DINING = "5030-Food & Beverage Expense"
EXP_TRAVEL = "5040-Travel & Cab Expense"
EXP_HARDWARE = "5050-Hardware & Repairs Expense"
EXP_PRINTING = "5060-Printing Expense"
EXP_MOTOR = "5070-Motor Vehicle Expense"
EXP_INSURANCE = "5080-Insurance Expense"
EXP_GENERAL = "5090-General / Petty Expense"

EXPENSE_ACCOUNTS = frozenset(
    {
        EXP_OFFICE,
        EXP_FUEL,
        EXP_SOFTWARE,
        EXP_DINING,
        EXP_TRAVEL,
        EXP_HARDWARE,
        EXP_PRINTING,
        EXP_MOTOR,
        EXP_INSURANCE,
        EXP_GENERAL,
    }
)


def is_expense_account(account_code: str) -> bool:
    """Return True if the account code represents an expense."""
    return account_code in EXPENSE_ACCOUNTS or account_code.startswith("5")


def is_income_account(account_code: str) -> bool:
    """Return True if the account code represents revenue or income."""
    return account_code in REVENUE_ACCOUNTS or account_code.startswith("4")


def map_expense_account(receipt: Receipt) -> str:
    """Map a receipt deterministically to its designated expense account code."""
    # 1. Primary classification by doc_type
    doc_type = getattr(receipt, "doc_type", "")
    if doc_type == "fuel_slip":
        return EXP_FUEL
    if doc_type == "dining_bill":
        return EXP_DINING
    if doc_type == "fare":
        return EXP_TRAVEL
    if doc_type == "premium_receipt":
        return EXP_INSURANCE

    # 2. Text-based keyword classification
    text_corpus = (
        f"{receipt.vendor_name or ''} {receipt.vendor_key or ''} "
        + " ".join(item.description for item in receipt.line_items if item.description)
    ).lower()

    if any(
        k in text_corpus
        for k in ("stationer", "stationery", "paper", "pen", "notebook")
    ):
        return EXP_OFFICE
    if any(k in text_corpus for k in ("fuel", "petrol", "diesel")):
        return EXP_FUEL
    if any(
        k in text_corpus
        for k in (
            "software",
            "cloud",
            "aws",
            "github",
            "hosting",
            "saas",
            "subscription",
        )
    ):
        return EXP_SOFTWARE
    if any(
        k in text_corpus
        for k in (
            "restaurant",
            "dining",
            "cater",
            "canteen",
            "cafe",
            "food",
            "beverage",
        )
    ):
        return EXP_DINING
    if any(
        k in text_corpus
        for k in ("cab", "taxi", "fare", "travel", "uber", "ola", "mobility")
    ):
        return EXP_TRAVEL
    if any(
        k in text_corpus for k in ("furniture", "hardware", "desk", "chair", "repair")
    ):
        return EXP_HARDWARE
    if any(k in text_corpus for k in ("print", "printing", "press")):
        return EXP_PRINTING
    if any(
        k in text_corpus
        for k in ("motor", "vehicle", "car service", "car repair", "spare parts")
    ):
        return EXP_MOTOR
    if any(k in text_corpus for k in ("insurance", "premium", "policy")):
        return EXP_INSURANCE

    return EXP_GENERAL
