# LedgerSense — Statutory Rules Notes & Open Questions

> [!IMPORTANT]
> Every statutory number in LedgerSense (cash transaction limits, Chapter VI-A deduction caps, blocked-credit categories, and section references) is a configuration value read from versioned YAML files (`backend/src/ledgersense/tax/rules/`). Code must NEVER hardcode or guess values from memory. Unverified rules must maintain `verified_by: null`, which renders as an `"UNVERIFIED"` badge in the user interface.

---

## 1. Statutory Thresholds and Caps Status

| Rule ID / Section | Parameter | Value in YAML | Status | Notes |
|---|---|---|---|---|
| `CGST Act s.17(5)` | Blocked ITC Categories | `FOOD_BEVERAGE`, `MOTOR_VEHICLE`, `HEALTH_CLUB` | Unverified (`verified_by: null`) | Confirm if passenger vehicle motor repairs require separate confirmation versus strict block. |
| `ITA_1961 s.40A(3)` | Cash expense daily limit | ₹10,000 | Unverified (`verified_by: null`) | Limit is per person per day. Need CA verification on transport/plying exception (₹35,000 limit). |
| `ITA_1961 s.80C` | Overall limit | ₹1,50,000 | Unverified (`verified_by: null`) | Old regime only. Subject to sub-limits (e.g. term life vs EPF vs ELSS). |
| `ITA_1961 s.80D` | Self / family health limit | ₹25,000 | Unverified (`verified_by: null`) | Old regime only. Senior-citizen (₹50,000) and parents medical insurance/health checkup sub-limits pending CA confirmation. |

---

## 2. Statute Recodification Mappings (ITA 1961 vs ITA 2025)

The Income-tax Act, 2025 replaces the Income-tax Act, 1961 effective **1 April 2026**.

- **FY 2025–26 (AY 2026–27)**: Governed by `ITA_1961`.
- **FY 2026–27 onwards**: Governed by `ITA_2025`.

### Section Mapping Table

| Topic | ITA 1961 Reference (`ref_1961`) | ITA 2025 Reference (`ref_2025`) | Status |
|---|---|---|---|
| Cash payment limit | `s.40A(3)` | `null` | **Mapping pending**. Need official ICAI cross-reference table or CA confirmation. UI displays `"Mapping pending"`. |
| Life insurance / PF deduction | `s.80C` | `s.123` | Quoted from published mapping guides. Pending official Gazette cross-check. |
| Health insurance deduction | `s.80D` | `s.126` | Quoted from published mapping guides. Pending official Gazette cross-check. |
| GST Blocked ITC | `CGST Act s.17(5)` | N/A | GST is governed by CGST/SGST Acts and is unaffected by the Income-tax recodification. |

---

## 3. Action Items for Pre-Submission
1. Obtain review and sign-off from a chartered accountant (CA) or certified tax practitioner.
2. Fill the `verified_by` fields in `backend/src/ledgersense/tax/rules/*.yaml` with the CA's name, credentials, and verification date to clear the `"UNVERIFIED"` badges.
3. Validate official 2025-Act section for cash-payment disallowance (`s.40A(3)` equivalent).
