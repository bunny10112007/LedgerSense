# LedgerSense — Engineering Rules

## Product
Autonomous audit and Indian tax-compliance copilot. Kimi reads documents; deterministic Python decides everything with legal or numeric consequences. Human gate before commit.

## Module ownership
Dev A: `db/`, `llm/`, `extraction/`, `matching/`, `pipeline/`, `api/`, `scripts/`, `data/golden` generation
Dev B: `tax/`, `accounting/`, `audit/`, `frontend/`, `rules` YAML, `README`, `docs/rules-notes.md`
Shared (PR from both): `domain/models.py`, `pyproject.toml`, `uv.lock`, `AGENTS.md`, `docs/api-contracts.md`, `data/golden/answer_key.json`

## Architecture rules
- `domain/models.py` is the contract. Never pass raw dicts across module boundaries.
- Money is `Decimal`, serialised as `str`. Never `float`. Quantize explicitly.
- ONLY `llm/` may import the Kimi client. `tax/`, `accounting/`, `matching/`, `audit/` must not.
- Bank data must never be passed to any LLM function. No exceptions.
- Tax thresholds, caps, section numbers and categories live in YAML under `tax/rules/`. NEVER hardcode or guess a number from memory. If unsure, leave the YAML value as `None` and add a note to `docs/rules-notes.md`.
- Every rule has `ref_1961` and `ref_2025` (null allowed). UI prints `"Mapping pending"` for null.
- Committed journal entries are immutable. Corrections are reversing entries.
- `audit_events` is append-only. No `UPDATE` or `DELETE`.
- Secrets only in `.env` (git-ignored). Never log API keys or full document text at `INFO`.

## Gate rule
Any `OPEN` risk flag with severity `HIGH` blocks commit (`HTTP 409`). Approval requires `auditor_id` and `reason` (min 10 chars) and writes an audit event.

## Work style
1. Read `AGENTS.md` and the relevant files in my scope.
2. State which files will change (must be in scope) and the acceptance test.
3. Write the failing test first (golden or unit), then the implementation.
4. Run: `cd backend && uv run ruff check . && uv run pytest -q`
5. Report exact commands and exact output. Never claim a test passed without running it.
6. I must be able to explain every changed line in review.

## Security
- Parameterised SQL only (`SQLModel`). Never execute uploaded content.
- Validate every upload: allowed MIME types, size limit, filename sanitised.
- No raw model output is displayed as a financial figure without validators.
