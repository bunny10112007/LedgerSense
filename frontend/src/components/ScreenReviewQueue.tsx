import React, { useState } from 'react';
import type { RiskFlag, Receipt, BankLine, Run } from '../types/api';
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  FileText,
  Lock,
  Unlock,
  UserCheck,
  Building,
  Info,
} from 'lucide-react';
import { formatINR } from '../utils/money';

interface ScreenReviewQueueProps {
  flags: RiskFlag[];
  receipts: Receipt[];
  bankLines: BankLine[];
  run: Run;
  onDecideFlag: (
    flagId: string,
    auditorId: string,
    decision: 'approve' | 'reject',
    reason: string
  ) => Promise<void>;
  onCommitBooks: () => Promise<void>;
  isCommitting: boolean;
}

export const ScreenReviewQueue: React.FC<ScreenReviewQueueProps> = ({
  flags,
  receipts,
  bankLines,
  run,
  onDecideFlag,
  onCommitBooks,
  isCommitting,
}) => {
  const [selectedFlagId, setSelectedFlagId] = useState<string>(flags[0]?.id || '');
  const [filter, setFilter] = useState<'all' | 'open_high' | 'resolved'>('all');
  const [auditorId, setAuditorId] = useState<'auditor-a' | 'auditor-b'>('auditor-a');
  const [decisionReason, setDecisionReason] = useState<string>('');
  const [commitError, setCommitError] = useState<string | null>(null);

  // Sorting: HIGH first, then MEDIUM, then LOW
  const severityOrder: Record<string, number> = { HIGH: 1, MEDIUM: 2, LOW: 3 };
  const sortedFlags = [...flags].sort(
    (a, b) => (severityOrder[a.severity] || 99) - (severityOrder[b.severity] || 99)
  );

  const openHighFlags = flags.filter((f) => f.severity === 'HIGH' && f.status === 'OPEN');
  const isGateBlocked = openHighFlags.length > 0;
  const isCommitted = run.status === 'COMMITTED';

  const filteredFlags = sortedFlags.filter((f) => {
    if (filter === 'open_high') return f.severity === 'HIGH' && f.status === 'OPEN';
    if (filter === 'resolved') return f.status === 'APPROVED' || f.status === 'REJECTED';
    return true;
  });

  const selectedFlag = flags.find((f) => f.id === selectedFlagId) || filteredFlags[0];

  // Find linked receipt or bank line
  const linkedReceipt = receipts.find((r) =>
    selectedFlag?.entity_ids.some((eid) => eid === r.id || eid === r.id.replace('rcpt:', ''))
  );
  const linkedBankLine = bankLines.find((b) =>
    selectedFlag?.entity_ids.some((eid) => eid === b.id || eid.includes(b.id))
  );

  const handleDecision = async (decision: 'approve' | 'reject') => {
    if (!selectedFlag) return;
    if (decisionReason.trim().length < 10) return;
    try {
      await onDecideFlag(selectedFlag.id, auditorId, decision, decisionReason.trim());
      setDecisionReason('');
    } catch (err: unknown) {
      alert((err as Error).message || 'Failed to submit decision');
    }
  };

  const handleCommit = async () => {
    setCommitError(null);
    try {
      await onCommitBooks();
    } catch (err: unknown) {
      setCommitError((err as Error).message || 'Gate blocked: HIGH severity flags remaining');
    }
  };

  return (
    <div className="space-y-6">
      {/* Human Gate Banner & Commit Action Bar */}
      <div
        className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all shadow-sm ${
          isCommitted
            ? 'bg-emerald-50 border-emerald-300 text-emerald-950'
            : isGateBlocked
            ? 'bg-red-50 border-red-200 text-red-950'
            : 'bg-emerald-50 border-emerald-300 text-emerald-950'
        }`}
      >
        <div className="flex items-start sm:items-center space-x-3">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
              isCommitted
                ? 'bg-emerald-600 text-white'
                : isGateBlocked
                ? 'bg-red-600 text-white'
                : 'bg-emerald-600 text-white'
            }`}
          >
            {isCommitted ? (
              <CheckCircle className="w-5 h-5" />
            ) : isGateBlocked ? (
              <Lock className="w-5 h-5" />
            ) : (
              <Unlock className="w-5 h-5" />
            )}
          </div>

          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-sm font-bold">
                {isCommitted
                  ? 'Ledger Committed — Books Frozen & Finalized'
                  : isGateBlocked
                  ? `Commit Gate Blocked (${openHighFlags.length} OPEN HIGH Flags)`
                  : 'Commit Gate Cleared — Ready to Commit Books'}
              </h2>
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase tracking-wider ${
                  isCommitted
                    ? 'bg-emerald-200 text-emerald-900'
                    : isGateBlocked
                    ? 'bg-red-200 text-red-900'
                    : 'bg-emerald-200 text-emerald-900'
                }`}
              >
                {run.status}
              </span>
            </div>
            <p className="text-xs opacity-90 mt-0.5">
              {isCommitted
                ? '14 double-entry journal entries committed to immutable SQLite ledger with audit signatures.'
                : isGateBlocked
                ? `Section 6.4 gate rule: All ${openHighFlags.length} HIGH-severity risk flags must receive auditor approval or rejection before commit.`
                : 'All statutory risk exceptions signed off. Double-entry entries will be committed into financial statements.'}
            </p>
          </div>
        </div>

        {/* Commit Action Button */}
        <div className="flex items-center space-x-3 shrink-0">
          <button
            type="button"
            onClick={handleCommit}
            disabled={isGateBlocked || isCommitting || isCommitted}
            className={`px-5 py-2.5 rounded-xl font-bold text-xs flex items-center space-x-2 shadow-md transition-all ${
              isCommitted
                ? 'bg-emerald-700 text-white cursor-default'
                : isGateBlocked
                ? 'bg-slate-300 text-slate-500 cursor-not-allowed opacity-80'
                : 'bg-emerald-600 hover:bg-emerald-700 text-white hover:shadow-lg'
            }`}
          >
            {isCommitted ? (
              <>
                <CheckCircle className="w-4 h-4" />
                <span>Books Committed</span>
              </>
            ) : isCommitting ? (
              <span>Committing...</span>
            ) : (
              <>
                <CheckCircle className="w-4 h-4" />
                <span>Commit Books ({flags.length - openHighFlags.length}/{flags.length} Signed)</span>
              </>
            )}
          </button>
        </div>
      </div>

      {commitError && (
        <div className="p-3 bg-red-100 border border-red-300 rounded-lg text-xs font-semibold text-red-800 flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{commitError}</span>
        </div>
      )}

      {/* Main Split Review Pane */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Flag Queue (5 cols) */}
        <div className="lg:col-span-5 space-y-3">
          {/* Filters Bar */}
          <div className="bg-[var(--surface)] p-2 rounded-xl border border-slate-200 flex items-center space-x-1 text-xs">
            <button
              onClick={() => setFilter('all')}
              className={`flex-1 py-1.5 px-3 rounded-lg font-medium transition-colors ${
                filter === 'all'
                  ? 'bg-slate-100 text-slate-900 font-bold'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              All ({flags.length})
            </button>
            <button
              onClick={() => setFilter('open_high')}
              className={`flex-1 py-1.5 px-3 rounded-lg font-medium transition-colors ${
                filter === 'open_high'
                  ? 'bg-red-50 text-red-700 font-bold border border-red-200'
                  : 'text-slate-500 hover:text-red-700'
              }`}
            >
              Open HIGH ({openHighFlags.length})
            </button>
            <button
              onClick={() => setFilter('resolved')}
              className={`flex-1 py-1.5 px-3 rounded-lg font-medium transition-colors ${
                filter === 'resolved'
                  ? 'bg-emerald-50 text-emerald-800 font-bold border border-emerald-200'
                  : 'text-slate-500 hover:text-emerald-800'
              }`}
            >
              Resolved ({flags.length - openHighFlags.length})
            </button>
          </div>

          {/* Flags List */}
          <div className="space-y-2.5 max-h-[750px] overflow-y-auto pr-1">
            {filteredFlags.map((flag) => {
              const isSelected = selectedFlag?.id === flag.id;
              const isHigh = flag.severity === 'HIGH';
              const isMedium = flag.severity === 'MEDIUM';

              return (
                <div
                  key={flag.id}
                  onClick={() => setSelectedFlagId(flag.id)}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all text-xs space-y-2 shadow-2xs ${
                    isSelected
                      ? 'border-[var(--accent)] ring-2 ring-cyan-100 bg-cyan-50/20'
                      : 'border-slate-200 bg-[var(--surface)] hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                          isHigh
                            ? 'bg-red-100 text-red-800 border border-red-200'
                            : isMedium
                            ? 'bg-amber-100 text-amber-800 border border-amber-200'
                            : 'bg-slate-100 text-slate-700 border border-slate-200'
                        }`}
                      >
                        {flag.severity}
                      </span>
                      <span className="font-bold text-slate-900">{flag.rule_id}</span>
                    </div>

                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                        flag.status === 'OPEN'
                          ? isHigh
                            ? 'bg-red-50 text-red-700 border border-red-200 font-bold'
                            : 'bg-amber-50 text-amber-700 border border-amber-200'
                          : flag.status === 'APPROVED'
                          ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                          : 'bg-slate-100 text-slate-600 border border-slate-200'
                      }`}
                    >
                      {flag.status}
                    </span>
                  </div>

                  <p className="text-slate-600 line-clamp-2 text-xs">
                    {flag.suggested_action}
                  </p>

                  <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100 font-mono">
                    <span>
                      Entities: {flag.entity_ids.join(', ')}
                    </span>
                    {flag.legal_ref && (
                      <span className="truncate max-w-[140px]" title={flag.legal_ref}>
                        {flag.legal_ref}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Flag Detail & Auditor Action (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {selectedFlag ? (
            <div className="bg-[var(--surface)] rounded-xl border border-slate-200 p-6 shadow-2xs space-y-6">
              {/* Header */}
              <div className="border-b border-slate-100 pb-4 flex items-start justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span
                      className={`px-2.5 py-0.5 rounded text-xs font-bold font-mono ${
                        selectedFlag.severity === 'HIGH'
                          ? 'bg-red-100 text-red-800 border border-red-200'
                          : selectedFlag.severity === 'MEDIUM'
                          ? 'bg-amber-100 text-amber-800 border border-amber-200'
                          : 'bg-slate-100 text-slate-700 border border-slate-200'
                      }`}
                    >
                      {selectedFlag.severity} SEVERITY
                    </span>
                    <h3 className="text-base font-bold text-slate-900">
                      {selectedFlag.rule_id}
                    </h3>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 mt-2">
                    {/* Legal Ref Pill */}
                    {selectedFlag.legal_ref === 'mapping pending' ? (
                      <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">
                        Statutory Mapping: mapping pending (ITA_2025)
                      </span>
                    ) : selectedFlag.legal_ref ? (
                      <span className="text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200">
                        Ref: {selectedFlag.legal_ref}
                      </span>
                    ) : null}

                    {/* Unverified rule badge */}
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
                      UNVERIFIED RULE (YAML v1)
                    </span>
                  </div>
                </div>

                <div className="text-right">
                  <span
                    className={`text-xs font-bold px-3 py-1 rounded-full ${
                      selectedFlag.status === 'OPEN'
                        ? 'bg-red-50 text-red-700 border border-red-200'
                        : selectedFlag.status === 'APPROVED'
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : 'bg-slate-100 text-slate-700 border border-slate-200'
                    }`}
                  >
                    {selectedFlag.status}
                  </span>
                </div>
              </div>

              {/* Suggested Action Callout */}
              <div className="p-3.5 bg-cyan-50/60 border border-cyan-200 rounded-xl text-xs space-y-1">
                <div className="font-bold text-cyan-950 flex items-center space-x-1.5">
                  <Info className="w-3.5 h-3.5 text-[var(--accent)]" />
                  <span>Suggested Auditor Action:</span>
                </div>
                <p className="text-cyan-900 pl-5">{selectedFlag.suggested_action}</p>
              </div>

              {/* Evidence Key-Value Table */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Auditable Evidence & Telemetry
                </h4>
                <div className="bg-slate-50 rounded-xl border border-slate-200 p-3 space-y-1.5 text-xs font-mono">
                  {Object.entries(selectedFlag.evidence).map(([key, val]) => (
                    <div key={key} className="flex justify-between py-1 border-b border-slate-200/60 last:border-0">
                      <span className="text-slate-500">{key}:</span>
                      <span className="font-semibold text-slate-800">
                        {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Linked Document Preview */}
              {linkedReceipt && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center space-x-1.5">
                    <FileText className="w-3.5 h-3.5 text-slate-500" />
                    <span>Linked Document Preview ({linkedReceipt.id})</span>
                  </h4>
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs grid grid-cols-2 gap-3">
                    <div>
                      <div className="text-slate-400 text-[11px]">Vendor</div>
                      <div className="font-bold text-slate-800">{linkedReceipt.vendor_name || 'N/A'}</div>
                    </div>
                    <div>
                      <div className="text-slate-400 text-[11px]">Invoice Total</div>
                      <div className="font-bold font-mono text-[var(--ink)] text-sm">
                        {formatINR(linkedReceipt.total)}
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-400 text-[11px]">Vendor GSTIN</div>
                      <div className="font-mono text-slate-700">{linkedReceipt.vendor_gstin || 'None / Invalid'}</div>
                    </div>
                    <div>
                      <div className="text-slate-400 text-[11px]">Document Type / Mode</div>
                      <div className="capitalize text-slate-700">
                        {linkedReceipt.doc_type} • {linkedReceipt.payment_mode}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Linked Bank Line Preview */}
              {linkedBankLine && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center space-x-1.5">
                    <Building className="w-3.5 h-3.5 text-slate-500" />
                    <span>Linked Bank Statement Debit ({linkedBankLine.id})</span>
                  </h4>
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs grid grid-cols-2 gap-3">
                    <div>
                      <div className="text-slate-400 text-[11px]">Narration</div>
                      <div className="font-mono text-slate-800 font-semibold">{linkedBankLine.narration}</div>
                    </div>
                    <div>
                      <div className="text-slate-400 text-[11px]">Debit Amount</div>
                      <div className="font-bold font-mono text-red-700 text-sm">
                        {formatINR(linkedBankLine.debit)}
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-400 text-[11px]">Txn Date</div>
                      <div className="font-mono text-slate-700">{linkedBankLine.txn_date}</div>
                    </div>
                    <div>
                      <div className="text-slate-400 text-[11px]">Ref No</div>
                      <div className="font-mono text-slate-700">{linkedBankLine.ref_no || 'N/A'}</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Auditor Decision Section */}
              <div className="pt-4 border-t border-slate-200 space-y-4">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center space-x-1.5">
                  <UserCheck className="w-4 h-4 text-[var(--accent)]" />
                  <span>Auditor Sign-off & Override</span>
                </h4>

                {/* If already decided, display previous decision */}
                {selectedFlag.decided_by && (
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1">
                    <div className="flex items-center justify-between text-slate-600">
                      <span>
                        Decided as <strong className="uppercase font-bold text-slate-900">{selectedFlag.status}</strong> by{' '}
                        <strong className="text-slate-900">{selectedFlag.decided_by}</strong>
                      </span>
                      {selectedFlag.decided_at && (
                        <span className="font-mono text-slate-400 text-[11px]">
                          {new Date(selectedFlag.decided_at).toLocaleString('en-IN', {
                            timeZone: 'Asia/Kolkata',
                            hour12: false,
                          })}
                        </span>
                      )}
                    </div>
                    {selectedFlag.decision_reason && (
                      <p className="text-slate-800 italic bg-white p-2 rounded border border-slate-100">
                        "{selectedFlag.decision_reason}"
                      </p>
                    )}
                  </div>
                )}

                {/* Auditor Selector */}
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Auditor Identity
                    </label>
                    <select
                      value={auditorId}
                      onChange={(e) => setAuditorId(e.target.value as 'auditor-a' | 'auditor-b')}
                      className="text-xs p-2 rounded-lg border border-slate-200 bg-white font-mono"
                    >
                      <option value="auditor-a">auditor-a (Senior Statutory Auditor)</option>
                      <option value="auditor-b">auditor-b (Tax Audit Reviewer)</option>
                    </select>
                  </div>

                  {/* Mandatory Reason with Counter */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="block text-xs font-semibold text-slate-700">
                        Statutory Audit Justification (Min 10 characters)
                      </label>
                      <span
                        className={`text-[10px] font-mono ${
                          decisionReason.trim().length >= 10
                            ? 'text-emerald-600 font-bold'
                            : 'text-slate-400'
                        }`}
                      >
                        {decisionReason.trim().length} / 10 chars
                      </span>
                    </div>
                    <textarea
                      rows={2}
                      value={decisionReason}
                      onChange={(e) => setDecisionReason(e.target.value)}
                      placeholder="e.g. Verified emergency fuel purchase voucher with original driver logsheet"
                      className="w-full text-xs p-2.5 rounded-lg border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-[var(--accent)]"
                    />
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center space-x-3 pt-1">
                    <button
                      type="button"
                      onClick={() => handleDecision('approve')}
                      disabled={decisionReason.trim().length < 10}
                      className="flex-1 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold text-xs shadow-sm transition-all flex items-center justify-center space-x-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <CheckCircle className="w-3.5 h-3.5" />
                      <span>Approve Exception</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleDecision('reject')}
                      disabled={decisionReason.trim().length < 10}
                      className="flex-1 py-2.5 px-4 bg-red-600 hover:bg-red-700 text-white rounded-xl font-bold text-xs shadow-sm transition-all flex items-center justify-center space-x-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Reject Document</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-[var(--surface)] p-12 text-center rounded-xl border border-slate-200 text-slate-400 text-xs">
              Select an audit exception to review telemetry and record decision.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
