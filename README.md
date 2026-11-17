# LedgerSense — Autonomous Audit & Indian Tax-Compliance Copilot

LedgerSense is an autonomous audit and Indian tax-compliance copilot designed for Indian businesses, chartered accountants, and tax professionals. It pairs multimodal perception models (such as Argon Vision) with rigorous, deterministic Python accounting and statutory rules engines to ingest invoices and receipts, reconcile them against bank statement CSVs, detect compliance and audit anomalies, enforce a mandatory human auditor sign-off gate, and commit double-entry books into balanced financial statements and draft ITR-3 tax schedules.

---

## Privacy & Security Architecture

> [!IMPORTANT]
> **Core Privacy Guarantee**: LedgerSense operates with PII masking before any text leaves the system, a provider-agnostic LLM layer, a per-run data-egress log, and bank data that never reaches an LLM.

- **Bank Data Isolation**: Bank statement CSVs are parsed exclusively on local hardware using deterministic Python parsers. Bank transactions, narrations, account balances, and reference numbers are strictly forbidden from passing to any LLM interface.
- **Pre-Perception PII Masking**: Sensitive identifiers including Indian PAN, Aadhaar, phone numbers, and email addresses are masked or tokenized prior to any perception call.
- **Transparent Egress Telemetry**: Every outbound perception call is recorded in an append-only `egress_log` tracking model ID, payload size in bytes, estimated cost, and masking status.
- **Offline Replay Determinism**: A content-addressable SHA-256 fixture cache (`data/golden/cache/`) powers instantaneous offline runs (`LLM_MODE=replay`), guaranteeing reproducible audits with zero network dependencies.
- **Append-Only Immutability**: The SQLite `audit_events` ledger is guarded by database triggers that immediately abort any `UPDATE` or `DELETE` attempt. Committed journal vouchers are immutable; corrections require explicit reversing entries.

---

## Quickstart Guide (< 10 minutes)

### Prerequisites
- **Python 3.12+** and [**uv**](https://docs.astral.sh/uv/) package manager
- **Node.js 20+** and **npm**

### 1. Repository Setup & Environment
```bash
git clone https://github.com/your-org/ledgersense.git
cd LedgerSense

# Copy example environment configuration
cp .env.example .env
```
*(By default, `.env` configures `LLM_MODE=replay`, requiring zero API keys for offline testing.)*

### 2. Backend Installation & Dependency Sync
```bash
cd backend
uv sync --frozen
```

### 3. Run the Golden Demo Pipeline (< 20 seconds)
Seed and execute the 16-document golden benchmark corpus:
```bash
uv run python ../scripts/reset_demo.py
uv run python ../scripts/run_demo.py
```
*(Executes full document extraction, bank reconciliation, risk detection, and journal drafting in ~2 seconds.)*

### 4. Start the FastAPI Backend Server
```bash
uv run uvicorn ledgersense.api.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive OpenAPI documentation will be accessible at `http://localhost:8000/docs`.

### 5. Frontend Installation & Development Server
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser to interact with the LedgerSense user interface.

---

## Architectural Overview

```
                        ┌──────────────────────────────────────────────┐
                        │              Document Uploads                │
                        │    (16 Synthetic PNG / PDF Receipts)         │
                        └──────────────────────┬───────────────────────┘
                                               │
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │      Perception Layer (llm/, extraction/)     │
                        │  - PII Masking (PAN, Aadhaar, Phone scrub)   │
                        │  - SHA-256 Cache Lookup (Replay Mode)        │
                        │  - Argon Vision with Auto-Retry              │
                        │  - Structured ExtractedReceipt Parsing       │
                        │  - Arithmetic & GSTIN Mod-36 Cross-Checks    │
                        └──────────────────────┬───────────────────────┘
                                               │
┌───────────────────────────────┐              │
│       Bank Statement CSV      │              │
│  (Strictly Local / No LLM)    │              │
└──────────────┬────────────────┘              │
               │                               ▼
               └──────────────────────► ┌──────────────────────────────────────────────┐
                                        │        Matching Engine (matching/)           │
                                        │  - Exact Duplicate Detection (Cab Fare)      │
                                        │  - Date Window (±3 days) & Tolerance (£5.00) │
                                        │  - 1-to-1 Debit Reconciliation & Orphans     │
                                        └──────────────────────┬───────────────────────┘
                                                               │
                                                               ▼
                                        ┌──────────────────────────────────────────────┐
                                        │       Statutory Rules Engine (tax/)          │
                                        │  - Versioned YAML Rules (tax/rules/)         │
                                        │  - Cash Limit s.40A(3) > ₹10,000 (HIGH)      │
                                        │  - Out-of-Period Cutoff FY 2025-26 (HIGH)    │
                                        │  - GSTIN Mod-36 Checksum Validation (HIGH)   │
                                        │  - Exact Duplicate Detection (HIGH)          │
                                        │  - Blocked ITC s.17(5) Food & Auto (MEDIUM)  │
                                        │  - Unmatched Bank Debit ₹9,999 (MEDIUM)      │
                                        └──────────────────────┬───────────────────────┘
                                                               │
                                                               ▼
                                        ┌──────────────────────────────────────────────┐
                                        │        Human Gate & Commit (pipeline/)       │
                                        │  - Blocks Commit (HTTP 409) if HIGH is OPEN  │
                                        │  - Auditor Sign-off (min 10-char reason)     │
                                        │  - Auto-Transition: AWAITING_REVIEW->APPROVED│
                                        └──────────────────────┬───────────────────────┘
                                                               │
                                                               ▼
                                        ┌──────────────────────────────────────────────┐
                                        │      Accounting & Reporting (accounting/)    │
                                        │  - Balanced Double-Entry Journal (14 entries)│
                                        │  - Trial Balance (Debits = Credits = 131,880)│
                                        │  - Profit & Loss Statement                   │
                                        │  - Chapter VI-A Deductions (80C / 80D Draft) │
                                        │  - Draft ITR-3 Schedule JSON Export          │
                                        └──────────────────────────────────────────────┘
```

---

## Verification & Audit Suite

Run full automated checks across backend and frontend:

```bash
# Backend Lint & Type Sanity
cd backend
uv run ruff check .

# Backend Test Suite (72 tests: unit, golden, accounting, statutory)
uv run pytest -q

# Frontend Production Build (TypeScript compile + Vite asset bundling)
cd ../frontend
npm run build
```

---

## Repository Structure

```
LedgerSense/
├── backend/
│   ├── src/ledgersense/
│   │   ├── accounting/          # Double-entry voucher construction, statements, trial balance
│   │   ├── api/                 # FastAPI routes (18 endpoints matching Section 8)
│   │   ├── audit/               # Append-only audit logger and SHA-256 payload hasher
│   │   ├── core/                # Configuration and environment settings
│   │   ├── db/                  # SQLModel tables, session factory, repository
│   │   ├── domain/              # Frozen Pydantic domain models (models.py)
│   │   ├── extraction/          # Document perception normalizer, GSTIN checks
│   │   ├── llm/                 # Provider protocol, Argon provider, PII scrubber, cache
│   │   ├── matching/            # Bank CSV parser and deterministic reconciliation matcher
│   │   ├── pipeline/            # State machine orchestrator and human auditor gate
│   │   └── tax/                 # Statutory risk detectors, ITR mapper, YAML rules
│   └── tests/                   # 72 unit and golden acceptance tests
├── data/
│   ├── golden/                  # 16 benchmark receipts, bank.csv, cache fixtures, answer_key.json
│   └── uploads/                 # Runtime document upload staging directory
├── docs/
│   ├── api-contracts.md         # API route specifications and error definitions
│   └── rules-notes.md           # Statutory rule audit status and 1961 vs 2025 mappings
├── frontend/                    # Vite + React 18 + TypeScript + Tailwind CSS application
└── scripts/
    ├── make_golden.py           # Synthetic receipt image and bank CSV generator
    ├── reset_demo.py            # Clean demo reset utility
    └── run_demo.py              # End-to-end golden demo executor
```

---

## License & Compliance Notice

LedgerSense is open-source software provided under the Apache 2.0 License. All tax deduction schedules and ITR draft outputs carry explicitly watermarked `"Draft"` statuses and require professional sign-off by a certified chartered accountant prior to filing with tax authorities.
