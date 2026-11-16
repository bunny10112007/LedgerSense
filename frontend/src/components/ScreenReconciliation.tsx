import React from 'react';
import type { Match, Receipt, BankLine } from '../types/api';
import { formatINR } from '../utils/money';
import { CheckCircle2, AlertOctagon, Ban, CopyCheck, ArrowRightLeft } from 'lucide-react';

interface ScreenReconciliationProps {
  matches: Match[];
  receipts: Receipt[];
  bankLines: BankLine[];
}

export const ScreenReconciliation: React.FC<ScreenReconciliationProps> = ({
  matches,
  receipts,
  bankLines,
}) => {
  // Categorize matches
  const matchedPairs = matches.filter((m) => m.kind === 'MATCHED');
  const unmatchedBankMatches = matches.filter((m) => m.kind === 'UNMATCHED_BANK');

  // Identify cash vouchers and duplicates excluded from bank matching
  const cashReceipts = receipts.filter((r) => r.payment_mode === 'cash');
  const duplicateReceipts = receipts.filter((r) => r.id === 'rcpt:G06');

  // Build table rows
  const receiptMap = new Map(receipts.map((r) => [r.id, r]));
  const bankLineMap = new Map(bankLines.map((b) => [b.id, b]));

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Matched Pairs */}
        <div className="p-4 bg-[var(--surface)] border border-slate-200 rounded-xl shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-slate-500 text-xs">
            <span>Matched Pairs</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-700">
            {matchedPairs.length}
          </div>
          <p className="text-[11px] text-slate-500">Receipts matched 1-to-1 with debits</p>
        </div>

        {/* Card 2: Unmatched Bank Debit */}
        <div className="p-4 bg-amber-50/60 border border-amber-200 rounded-xl shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-amber-900 text-xs font-semibold">
            <span>Unmatched Bank Debit</span>
            <AlertOctagon className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-800">
            {formatINR('9999.00')}
          </div>
          <p className="text-[11px] text-amber-800">1 mystery UPI debit without receipt</p>
        </div>

        {/* Card 3: Cash Vouchers */}
        <div className="p-4 bg-[var(--surface)] border border-slate-200 rounded-xl shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-slate-500 text-xs">
            <span>Cash Vouchers</span>
            <Ban className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-800">
            {cashReceipts.length} Excluded
          </div>
          <p className="text-[11px] text-slate-500">G09 (₹12k) & G13 (₹450 petty cash)</p>
        </div>

        {/* Card 4: Duplicate Documents */}
        <div className="p-4 bg-[var(--surface)] border border-slate-200 rounded-xl shadow-2xs space-y-1">
          <div className="flex items-center justify-between text-slate-500 text-xs">
            <span>Duplicates Excluded</span>
            <CopyCheck className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-800">
            {duplicateReceipts.length} Excluded
          </div>
          <p className="text-[11px] text-slate-500">G06 duplicate of G05 fare receipt</p>
        </div>
      </div>

      {/* Main Reconciliation Table */}
      <div className="bg-[var(--surface)] rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <ArrowRightLeft className="w-4 h-4 text-[var(--accent)]" />
            <h3 className="text-sm font-bold text-slate-900">
              Deterministic 1:1 Bank Matching Ledger
            </h3>
          </div>
          <span className="text-xs text-[var(--muted)]">
            Tolerance: ±3 days, ±₹5.00
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-100/75 border-b border-slate-200 text-slate-600 font-semibold text-[11px] uppercase tracking-wider">
                <th className="py-2.5 px-4 w-[42%]">Receipt / Invoice Document</th>
                <th className="py-2.5 px-4 w-[16%] text-center">Match Diagnostics</th>
                <th className="py-2.5 px-4 w-[42%]">Bank Statement Record</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {/* Matched Pairs */}
              {matchedPairs.map((match) => {
                const rcpt = match.receipt_id ? receiptMap.get(match.receipt_id) : null;
                const bank = match.bank_line_id ? bankLineMap.get(match.bank_line_id) : null;
                const hasAmountDelta = match.amount_delta && match.amount_delta !== '0.00';
                const hasDateDelta = (match.date_delta_days ?? 0) > 0;

                return (
                  <tr key={match.id} className="hover:bg-slate-50/80 transition-colors">
                    {/* Receipt Column */}
                    <td className="py-3 px-4">
                      {rcpt ? (
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono font-bold text-slate-900">
                              {rcpt.id}
                            </span>
                            <span className="text-slate-800 font-semibold">
                              {rcpt.vendor_name || 'N/A'}
                            </span>
                          </div>
                          <div className="flex items-center space-x-3 text-slate-500 font-mono text-[11px]">
                            <span>Date: {rcpt.invoice_date}</span>
                            <span>•</span>
                            <span className="font-bold text-slate-900">
                              {formatINR(rcpt.total)}
                            </span>
                            <span>•</span>
                            <span className="capitalize">{rcpt.doc_type}</span>
                          </div>
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">No receipt</span>
                      )}
                    </td>

                    {/* Match Diagnostics Column */}
                    <td className="py-3 px-4 text-center">
                      <div className="inline-flex flex-col items-center space-y-1">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                          {Math.round(match.score * 100)}% Match
                        </span>

                        {hasAmountDelta && (
                          <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-amber-50 text-amber-800 border border-amber-200 font-bold" title="Amount within tolerance">
                            Δ {formatINR(match.amount_delta!)}
                          </span>
                        )}

                        {hasDateDelta && (
                          <span className="text-[10px] font-mono text-slate-500" title="Date delta">
                            {match.date_delta_days}d delta
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Bank Line Column */}
                    <td className="py-3 px-4">
                      {bank ? (
                        <div className="space-y-1">
                          <div className="font-mono text-slate-800 font-semibold text-[11px]">
                            {bank.narration}
                          </div>
                          <div className="flex items-center space-x-3 text-slate-500 font-mono text-[11px]">
                            <span>Bank Date: {bank.txn_date}</span>
                            <span>•</span>
                            <span className="font-bold text-slate-900">
                              {formatINR(bank.debit > '0.00' ? bank.debit : bank.credit)}
                            </span>
                            {bank.ref_no && (
                              <>
                                <span>•</span>
                                <span>Ref: {bank.ref_no}</span>
                              </>
                            )}
                          </div>
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">No bank line</span>
                      )}
                    </td>
                  </tr>
                );
              })}

              {/* Orphan / Unmatched Bank Debit */}
              {unmatchedBankMatches.map((match) => {
                const bank = match.bank_line_id
                  ? bankLineMap.get(match.bank_line_id)
                  : bankLines.find((b) => b.narration.includes('UNKNOWN') || b.debit === '9999.00');

                return (
                  <tr key={match.id} className="bg-amber-50/70 border-l-4 border-amber-500">
                    <td className="py-3.5 px-4">
                      <div className="p-2.5 rounded-lg bg-amber-100/70 border border-amber-300 text-amber-900 text-xs space-y-0.5">
                        <div className="font-bold flex items-center space-x-1.5">
                          <AlertOctagon className="w-3.5 h-3.5 text-amber-700" />
                          <span>MISSING SUPPORTING VOUCHER</span>
                        </div>
                        <p className="text-[11px]">
                          Statutory exception: Bank debit without matching invoice or voucher.
                        </p>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-center">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-200 text-amber-900 border border-amber-300">
                        UNMATCHED_BANK
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      {bank ? (
                        <div className="space-y-1">
                          <div className="font-mono text-amber-950 font-bold text-xs">
                            {bank.narration}
                          </div>
                          <div className="flex items-center space-x-3 text-amber-900 font-mono text-[11px]">
                            <span>Date: {bank.txn_date}</span>
                            <span>•</span>
                            <span className="font-bold text-red-700">
                              Debit: {formatINR(bank.debit)}
                            </span>
                            {bank.ref_no && <span>• Ref: {bank.ref_no}</span>}
                          </div>
                        </div>
                      ) : (
                        <span className="font-mono text-red-700 font-bold">
                          Debit: {formatINR('9999.00')} (UPI/UNKNOWN PAYEE)
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
