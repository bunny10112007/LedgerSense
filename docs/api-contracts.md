# LedgerSense — API Contracts (v1)

This specification defines the 18 HTTP endpoints and shared error contracts for LedgerSense, matching Section 8 of the Complete Engineering Blueprint.

---

## 1. Error Contract

Every HTTP error response adheres to the standard JSON structure with a stable machine-readable error code:

```json
{
  "code": "STRING_CODE",
  "message": "Human-readable description of what went wrong.",
  "details": {}
}
```

### Notable Error Codes
- `LLM_UNAVAILABLE` (HTTP 502): External Moonshot/Kimi provider unreachable or failed. Suggests switching to replay mode (`LLM_MODE=replay`).
- `GATE_BLOCKED_HIGH_RISK` (HTTP 409): Run commit rejected because one or more `HIGH` severity risk flags remain `OPEN`.
- `INVALID_AUDITOR_DECISION` (HTTP 422): Auditor decision missing required ID or reason is less than 10 characters.
- `VALIDATION_FAILED` (HTTP 422): Schema or arithmetic validation failure on incoming request data.
- `NOT_FOUND` (HTTP 404): Requested entity does not exist.

### CORS Configuration
CORS middleware reads `ALLOWED_ORIGINS` from environment/config (default: `http://localhost:5173`).

---

## 2. Endpoints (18 Routes)

### 2.1 System & Health
1. **`GET /api/v1/health`**
   - **Request**: None
   - **Response**:
     ```json
     {
       "status": "ok",
       "llm_mode": "replay",
       "model_id": "moonshot-v1-8k-vision-preview"
     }
     ```
   - **Notes**: Reports service status and whether LLM is running in `live` or `replay` mode.

---

### 2.2 Runs & Ingestion
2. **`POST /api/v1/runs`**
   - **Request**:
     ```json
     {
       "period_start": "2025-04-01",
       "period_end": "2026-03-31",
       "tax_regime_choice": "old"
     }
     ```
   - **Response**: `Run` object with derived `regime` (`"ITA_1961"` if `period_end <= 2026-03-31` else `"ITA_2025"`). Status initialized to `"CREATED"`.

3. **`POST /api/v1/runs/{id}/documents`**
   - **Request**: `multipart/form-data` with document file(s) (PNG, JPEG, PDF).
   - **Response**: `Document[]` with `id`, `filename`, `file_hash`, `mime`, and status.
   - **Notes**: Computes SHA-256 file hashes; persists uploaded originals in `data/uploads/{run_id}/`.

4. **`POST /api/v1/runs/{id}/bank-csv`**
   - **Request**: `multipart/form-data` containing bank statement CSV.
   - **Response**:
     ```json
     {
       "lines_parsed": 16,
       "errors": []
     }
     ```
   - **Notes**: Parses debit and credit rows deterministically using strict column mappings.

5. **`POST /api/v1/runs/{id}/process`**
   - **Request**: None
   - **Response**: `202 Accepted` `{ "status": "PROCESSING" }`
   - **Notes**: Triggers background pipeline execution: Extract -> Validate -> Match -> Risk detectors.

6. **`GET /api/v1/runs/{id}`**
   - **Request**: None
   - **Response**: `Run` object plus live stage progress counters (e.g. `{"status": "AWAITING_REVIEW", "extracted": 16, "total": 16, "flags_count": 7}`).
   - **Notes**: Polled by the UI stage stepper every 2 seconds.

---

### 2.3 Perceptions & Reconciliations
7. **`GET /api/v1/runs/{id}/receipts`**
   - **Request**: None
   - **Response**: `Receipt[]`
   - **Notes**: Returns extracted receipts with metadata, totals, taxes, vendor keys, and arithmetic check messages.

8. **`GET /api/v1/runs/{id}/matches`**
   - **Request**: None
   - **Response**: `Match[]`
   - **Notes**: Returns 1:1 receipt-to-bank line matches, deltas (amount, date), confidence scores, and unmatched/orphan lines.

---

### 2.4 Risk & Auditor Gate
9. **`GET /api/v1/runs/{id}/flags`**
   - **Request**: Optional query parameter `?status=OPEN`
   - **Response**: `RiskFlag[]`
   - **Notes**: Risk flags sorted by severity (`HIGH` first, then `MEDIUM`, then `LOW`).

10. **`POST /api/v1/flags/{id}/decision`**
    - **Request**:
      ```json
      {
        "auditor_id": "auditor-a",
        "decision": "approve",
        "reason": "Verified genuine client business lunch voucher."
      }
      ```
    - **Response**: Updated `RiskFlag` with `status`, `decided_by`, `decision_reason`, `decided_at`.
    - **Notes**: `decision` must be `"approve"` or `"reject"`. `reason` must be at least 10 characters. Automatically creates an immutable `AuditEvent`.

11. **`POST /api/v1/runs/{id}/commit`**
    - **Request**:
      ```json
      {
        "auditor_id": "auditor-a"
      }
      ```
    - **Response**:
      - `200 OK`: `{ "entries_committed": 14 }` if no `HIGH` risk flags are `OPEN`.
      - `409 Conflict`: `{ "open_high_flags": [...] }` if any `HIGH` risk flag remains `OPEN`.
    - **Notes**: The human sign-off gate. Prevents committing unverified high-risk journal entries.

---

### 2.5 Accounting & Statements
12. **`GET /api/v1/runs/{id}/journal`**
    - **Request**: Optional query parameter `?status=DRAFT|COMMITTED`
    - **Response**: `JournalEntry[]`
    - **Notes**: Invariant: $\sum debit == \sum credit$ and $\ge 2$ lines per entry.

13. **`GET /api/v1/runs/{id}/trial-balance`**
    - **Request**: None
    - **Response**:
      ```json
      {
        "accounts": [
          { "account_code": "EXP_OFFICE", "debit": "10000.00", "credit": "0.00" }
        ],
        "total_debit": "10000.00",
        "total_credit": "10000.00"
      }
      ```
    - **Notes**: Computed strictly from committed entries.

14. **`GET /api/v1/runs/{id}/pnl`**
    - **Request**: None
    - **Response**:
      ```json
      {
        "income": "0.00",
        "expenses": "45200.00",
        "net": "-45200.00"
      }
      ```
    - **Notes**: Income and expense accounts only; net profit/loss balancing figure.

---

### 2.6 Tax Outputs & Drafts
15. **`GET /api/v1/runs/{id}/tax/deductions`**
    - **Request**: None
    - **Response**:
      ```json
      {
        "80C": { "claimed": "30000.00", "allowed": "30000.00", "excess": "0.00" },
        "80D": { "claimed": "18000.00", "allowed": "18000.00", "excess": "0.00" },
        "notes": "Draft schedule (old regime only)."
      }
      ```
    - **Notes**: Available only when `tax_regime_choice = "old"`. Contains Draft watermark.

16. **`GET /api/v1/runs/{id}/tax/itr?form=ITR3`**
    - **Request**: Query parameter `form` (e.g. `ITR3` or `ITR4`)
    - **Response**: `ITRDraft JSON` object
    - **Notes**: Modelled draft JSON with field mapping references. Must carry `"draft": true`.

---

### 2.7 Audit & Privacy
17. **`GET /api/v1/runs/{id}/audit-log`**
    - **Request**: None
    - **Response**: `AuditEvent[]`
    - **Notes**: Read-only chronological trail of state transitions, decisions, and system actions.

18. **`GET /api/v1/runs/{id}/egress`**
    - **Request**: None
    - **Response**:
      ```json
      {
        "calls": 16,
        "bytes": 245000,
        "est_cost": "0.08",
        "entries": []
      }
      ```
    - **Notes**: Transparent log of all outbound calls to Kimi API. Confirms bank data was never transmitted.
