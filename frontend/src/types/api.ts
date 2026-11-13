/**
 * Frozen API and domain types for LedgerSense frontend.
 * Mirrors backend/src/ledgersense/domain/models.py exactly.
 */

export type Money = string;

export type DocType =
  | 'gst_invoice'
  | 'receipt'
  | 'fuel_slip'
  | 'dining_bill'
  | 'fare'
  | 'premium_receipt'
  | 'other';

export type PayMode = 'cash' | 'upi' | 'card' | 'bank_transfer' | 'unknown';

export type Severity = 'LOW' | 'MEDIUM' | 'HIGH';

export type FlagStatus = 'OPEN' | 'APPROVED' | 'REJECTED' | 'AUTO_RESOLVED';

export type Regime = 'ITA_1961' | 'ITA_2025';

export type RunStatus =
  | 'CREATED'
  | 'EXTRACTED'
  | 'VALIDATED'
  | 'MATCHED'
  | 'RISK_DONE'
  | 'AWAITING_REVIEW'
  | 'APPROVED'
  | 'COMMITTED'
  | 'FAILED';

export const ID_PREFIXES: Record<string, string> = {
  run: 'run:',
  receipt: 'rcpt:',
  bank: 'bank:',
  match: 'match:',
  flag: 'flag:',
  journal: 'je:',
  event: 'evt:',
};

export const ALLOWED_TRANSITIONS: Record<RunStatus, RunStatus[]> = {
  CREATED: ['EXTRACTED', 'FAILED'],
  EXTRACTED: ['VALIDATED', 'FAILED'],
  VALIDATED: ['MATCHED', 'FAILED'],
  MATCHED: ['RISK_DONE', 'FAILED'],
  RISK_DONE: ['AWAITING_REVIEW', 'APPROVED', 'FAILED'],
  AWAITING_REVIEW: ['RISK_DONE', 'APPROVED', 'FAILED'],
  APPROVED: ['COMMITTED', 'FAILED'],
  COMMITTED: [],
  FAILED: [],
};

export interface LineItem {
  description: string;
  quantity?: string | null;
  unit_price?: Money | null;
  amount: Money;
  hsn_sac?: string | null;
  tax_rate_pct?: string | null;
}

export interface ExtractedReceipt {
  doc_type: DocType;
  vendor_name?: string | null;
  vendor_gstin?: string | null;
  invoice_no?: string | null;
  invoice_date?: string | null;
  line_items: LineItem[];
  subtotal?: Money | null;
  cgst: Money;
  sgst: Money;
  igst: Money;
  total?: Money | null;
  payment_mode: PayMode;
  field_confidence: Record<string, number>;
}

export interface Receipt extends ExtractedReceipt {
  id: string;
  run_id: string;
  source_file: string;
  file_hash: string;
  vendor_key: string;
  extraction_status: 'OK' | 'LOW_CONFIDENCE' | 'FAILED';
  check_messages: string[];
}

export interface BankLine {
  id: string;
  run_id: string;
  txn_date: string;
  narration: string;
  debit: Money;
  credit: Money;
  balance?: Money | null;
  ref_no?: string | null;
}

export interface Match {
  id: string;
  run_id: string;
  receipt_id?: string | null;
  bank_line_id?: string | null;
  score: number;
  date_delta_days?: number | null;
  amount_delta?: Money | null;
  kind: 'MATCHED' | 'UNMATCHED_RECEIPT' | 'UNMATCHED_BANK' | 'AMBIGUOUS';
}

export interface RiskFlag {
  id: string;
  run_id: string;
  rule_id: string;
  severity: Severity;
  entity_ids: string[];
  legal_ref?: string | null;
  evidence: Record<string, unknown>;
  suggested_action: string;
  status: FlagStatus;
  decided_by?: string | null;
  decision_reason?: string | null;
  decided_at?: string | null;
}

export interface JournalLine {
  account_code: string;
  debit: Money;
  credit: Money;
}

export interface JournalEntry {
  id: string;
  run_id: string;
  entry_date: string;
  narration: string;
  lines: JournalLine[];
  status: 'DRAFT' | 'COMMITTED';
  source_receipt_id?: string | null;
  flag_ids: string[];
  deduction_tag?: '80C' | '80D' | null;
}

export interface AuditEvent {
  id: string;
  ts: string;
  run_id: string;
  actor: string;
  action: string;
  entity_id?: string | null;
  reason?: string | null;
  payload_hash: string;
}

export interface RunConfig {
  period_start: string;
  period_end: string;
  date_window_days: number;
  amount_tolerance: Money;
  cash_limit: Money;
  tax_regime_choice: 'old' | 'new';
  regime: Regime;
}

export interface Run {
  id: string;
  period_start: string;
  period_end: string;
  regime: Regime;
  status: RunStatus;
  config: RunConfig;
  created_at: string;
}

// Section 9 pure function response models

export interface GstinResult {
  ok: boolean;
  reason?: string | null;
  expected_check_char?: string | null;
}

export interface TrialBalanceRow {
  account_code: string;
  debit: Money;
  credit: Money;
}

export interface TrialBalance {
  accounts: TrialBalanceRow[];
  total_debit: Money;
  total_credit: Money;
  balanced: boolean;
}

export interface PnL {
  income: Record<string, Money>;
  expenses: Record<string, Money>;
  total_income: Money;
  total_expenses: Money;
  net_profit: Money;
}

export interface DeductionItem {
  section: '80C' | '80D';
  legal_ref: string;
  claimed: Money;
  cap: Money;
  allowed: Money;
  excess: Money;
}

export interface DeductionSchedule {
  label: string;
  regime: Regime;
  tax_regime_choice: 'old' | 'new';
  items: DeductionItem[];
  notes: string[];
}

export interface ITRDraft {
  label: string;
  form: string;
  regime: Regime;
  payload: Record<string, unknown>;
  field_mapping_ref: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}
