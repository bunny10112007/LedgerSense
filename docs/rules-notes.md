# LedgerSense — Statutory Rules Notes & Open Questions

> [!IMPORTANT]
> Every statutory number in LedgerSense (cash transaction limits, Chapter VI-A deduction caps, blocked-credit categories, and section references) is a configuration value read from versioned YAML files (`backend/src/ledgersense/tax/rules/`). Code must NEVER hardcode or guess values from memory. Unverified rules maintain `verified_by: null`, which renders as an `"UNVERIFIED"` status badge in the user interface. When `ref_2025` is `null`, the UI displays `"Mapping pending"`.

---

## 1. Statutory Thresholds and Caps Status

| Rule ID / Section | Parameter | Value in YAML | Status | Verification & Audit Notes |
|---|---|---|---|---|
| `CGST Act s.17(5)` | Blocked ITC Categories | `FOOD_BEVERAGE`, `MOTOR_VEHICLE`, `HEALTH_CLUB` | `UNVERIFIED` (`verified_by: null`) | Section 17(5)(b) strictly blocks ITC for food, beverages, outdoor catering, and health club memberships. Section 17(5)(a) restricts motor vehicles and related servicing/repairs unless used for taxable supplies of transportation. Flagged as `BLOCK_ITC_NEEDS_CONFIRMATION` pending CA verification. |
| `ITA_1961 s.40A(3)` | Cash expense daily limit | ₹10,000 | `UNVERIFIED` (`verified_by: null`) | Disallows business expenditure paid in cash exceeding ₹10,000 to a person in a single day. Rule 6DD exceptions (e.g., payment on bank holidays, plying/hire/leasing goods carriages limit of ₹35,000) require CA review. |
| `ITA_1961 s.80C` | Overall limit | ₹1,50,000 | `UNVERIFIED` (`verified_by: null`) | Old regime only. Aggregated ceiling for eligible life insurance premium, employee provident fund, ELSS, PPF, and tuition fees. |
| `ITA_1961 s.80D` | Self / family health limit | ₹25,000 | `UNVERIFIED` (`verified_by: null`) | Old regime only. Covers health insurance premiums and preventive checkups (up to ₹5,000 within cap) for self/spouse/children. Senior citizen threshold (₹50,000) and parents' medical expenditure provisions pending CA sign-off. |

---

## 2. Statute Recodification Mappings (ITA 1961 vs ITA 2025)

The Direct Taxes Code / Income-tax Act, 2025 recodifies direct tax provisions with an effective transition date of **1 April 2026**.

- **FY 2025–26 (AY 2026–27)**: Governed strictly by `ITA_1961`.
- **FY 2026–27 onwards**: Governed by `ITA_2025`.

### Section Mapping Table

| Business Topic | ITA 1961 Reference (`ref_1961`) | ITA 2025 Reference (`ref_2025`) | Status in LedgerSense |
|---|---|---|---|
| Cash payment disallowance (> ₹10k) | `s.40A(3)` | `null` | **Mapping pending**. Awaiting official ICAI / CBDT concordance table for corresponding 2025 section. UI renders `"Mapping pending"`. |
| Life insurance / PF deduction | `s.80C` | `s.123` | Draft reference from published recodification guides. Pending official Gazette publication cross-check. |
| Health insurance premium deduction | `s.80D` | `s.126` | Draft reference from published recodification guides. Pending official Gazette publication cross-check. |
| GST Blocked Input Tax Credit | `CGST Act s.17(5)` | N/A | GST is governed by the Central Goods and Services Tax Act, 2017 and is unaffected by the Income-tax recodification. |

---

## 3. UI Display & Auditor Gate Invariants

1. **Unverified Rule Badges**: Any rule whose YAML configuration has `verified_by: null` displays an `"UNVERIFIED"` badge in the Review Queue and Statutory Rules panel.
2. **Pending Section Notice**: Any statutory detector referencing an unmapped 2025 section displays `"Mapping pending"` rather than placeholder or guessed numbers.
3. **Watermarked Draft Outputs**: All generated financial statements, Chapter VI-A deduction schedules, and ITR-3 draft JSON exports carry explicit `"Draft schedule"` and `"Draft JSON in LedgerSense schema"` labels until verified and committed by an authenticated auditor.
4. **Action Items for Production Filing**:
   - Obtain formal review and written sign-off from a licensed chartered accountant (CA).
   - Update `verified_by` in `backend/src/ledgersense/tax/rules/*.yaml` with the practitioner's registration number and sign-off timestamp.
   - Update `ref_2025` for cash payments once the Ministry of Finance gazettes the final section concordance.
