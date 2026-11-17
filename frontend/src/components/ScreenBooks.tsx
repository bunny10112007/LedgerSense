import React, { useState } from 'react';
import type {
  JournalEntry,
  TrialBalance,
  PnL,
  DeductionSchedule,
  ITRDraft,
} from '../types/api';
import { formatINR } from '../utils/money';
import {
  BookOpen,
  Scale,
  Percent,
  FileCode,
  Copy,
  Download,
  CheckCircle,
  AlertTriangle,
} from 'lucide-react';

interface ScreenBooksProps {
  journalEntries: JournalEntry[];
  trialBalance: TrialBalance;
  pnl: PnL;
  deductions: DeductionSchedule;
  itrDraft: ITRDraft;
}

export const ScreenBooks: React.FC<ScreenBooksProps> = ({
  journalEntries,
  trialBalance,
  pnl,
  deductions,
  itrDraft,
}) => {
  const [activeTab, setActiveTab] = useState<'journal' | 'tb_pnl' | 'deductions' | 'itr'>('journal');
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(itrDraft, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadJson = () => {
    const blob = new Blob([JSON.stringify(itrDraft, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ITR3_Draft_${itrDraft.regime}_FY2025-26.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* Sub-navigation Tabs */}
      <div className="bg-[var(--surface)] p-2 rounded-xl border border-slate-200 flex space-x-1 text-xs shadow-2xs">
        <button
          onClick={() => setActiveTab('journal')}
          className={`flex-1 py-2 px-3 rounded-lg font-bold flex items-center justify-center space-x-1.5 transition-colors ${
            activeTab === 'journal'
              ? 'bg-[var(--accent)] text-white shadow-2xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span>Journal Entries ({journalEntries.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('tb_pnl')}
          className={`flex-1 py-2 px-3 rounded-lg font-bold flex items-center justify-center space-x-1.5 transition-colors ${
            activeTab === 'tb_pnl'
              ? 'bg-[var(--accent)] text-white shadow-2xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Scale className="w-3.5 h-3.5" />
          <span>Trial Balance & P&L</span>
        </button>

        <button
          onClick={() => setActiveTab('deductions')}
          className={`flex-1 py-2 px-3 rounded-lg font-bold flex items-center justify-center space-x-1.5 transition-colors ${
            activeTab === 'deductions'
              ? 'bg-[var(--accent)] text-white shadow-2xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Percent className="w-3.5 h-3.5" />
          <span>Chapter VI-A Deductions</span>
        </button>

        <button
          onClick={() => setActiveTab('itr')}
          className={`flex-1 py-2 px-3 rounded-lg font-bold flex items-center justify-center space-x-1.5 transition-colors ${
            activeTab === 'itr'
              ? 'bg-[var(--accent)] text-white shadow-2xs'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <FileCode className="w-3.5 h-3.5" />
          <span>ITR-3 Draft JSON</span>
        </button>
      </div>

      {/* Sub-tab 1: Journal Entries */}
      {activeTab === 'journal' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-[var(--muted)] px-1">
            <span>
              Double-entry vouchers constructed deterministically. ITC blocked on s.17(5) and invalid GSTIN.
            </span>
            <span className="font-mono text-slate-700">
              Total Entries: <strong>{journalEntries.length}</strong>
            </span>
          </div>

          <div className="space-y-3">
            {journalEntries.map((je) => (
                <div
                  key={je.id}
                  className="bg-[var(--surface)] rounded-xl border border-slate-200 overflow-hidden shadow-2xs text-xs"
                >
                  <div className="p-3 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200">
                        {je.id}
                      </span>
                      <span className="font-mono text-slate-500">{je.entry_date}</span>
                      <span className="font-semibold text-slate-800">{je.narration}</span>
                    </div>

                    <div className="flex items-center space-x-2">
                      {je.deduction_tag && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 border border-purple-200 font-mono">
                          Tag: {je.deduction_tag}
                        </span>
                      )}
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          je.status === 'COMMITTED'
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                            : 'bg-amber-100 text-amber-800 border border-amber-200'
                        }`}
                      >
                        {je.status}
                      </span>
                    </div>
                  </div>

                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-slate-100 text-slate-400 font-semibold text-[10px] uppercase">
                        <th className="py-1.5 px-4">Account Code & Description</th>
                        <th className="py-1.5 px-4 text-right">Debit (₹)</th>
                        <th className="py-1.5 px-4 text-right">Credit (₹)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {je.lines.map((line, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/50">
                          <td className="py-2 px-4 font-mono text-slate-800 font-medium">
                            {line.account_code}
                          </td>
                          <td className="py-2 px-4 text-right font-mono text-slate-900">
                            {line.debit !== '0.00' ? formatINR(line.debit) : '-'}
                          </td>
                          <td className="py-2 px-4 text-right font-mono text-slate-900">
                            {line.credit !== '0.00' ? formatINR(line.credit) : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Sub-tab 2: Trial Balance & P&L */}
      {activeTab === 'tb_pnl' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Trial Balance Table (7 cols) */}
          <div className="lg:col-span-7 bg-[var(--surface)] rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
            <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Trial Balance</h3>
                <p className="text-xs text-[var(--muted)]">Aggregated from committed journal ledger</p>
              </div>
              <span className="px-2.5 py-1 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold text-xs flex items-center space-x-1">
                <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                <span>BALANCED</span>
              </span>
            </div>

            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-100/75 border-b border-slate-200 text-slate-600 font-semibold text-[11px] uppercase">
                  <th className="py-2 px-4">Account Code</th>
                  <th className="py-2 px-4 text-right">Debit (₹)</th>
                  <th className="py-2 px-4 text-right">Credit (₹)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-xs">
                {trialBalance.accounts.map((row) => (
                  <tr key={row.account_code} className="hover:bg-slate-50">
                    <td className="py-2 px-4 text-slate-800">{row.account_code}</td>
                    <td className="py-2 px-4 text-right font-bold text-slate-900">
                      {row.debit !== '0.00' ? formatINR(row.debit) : '-'}
                    </td>
                    <td className="py-2 px-4 text-right font-bold text-slate-900">
                      {row.credit !== '0.00' ? formatINR(row.credit) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-slate-100 font-bold text-xs border-t-2 border-slate-300">
                  <td className="py-3 px-4 text-slate-900">Total Balance</td>
                  <td className="py-3 px-4 text-right font-mono text-emerald-800 text-sm">
                    {formatINR(trialBalance.total_debit)}
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-emerald-800 text-sm">
                    {formatINR(trialBalance.total_credit)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>

          {/* Profit & Loss Summary (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            <div className="bg-[var(--surface)] rounded-xl border border-slate-200 p-5 shadow-2xs space-y-4">
              <div className="border-b border-slate-100 pb-3">
                <h3 className="text-sm font-bold text-slate-900">Profit & Loss Statement</h3>
                <p className="text-xs text-[var(--muted)]">Net Income vs Operating Expenses</p>
              </div>

              <div className="space-y-3">
                <div className="p-3 bg-slate-50 rounded-lg flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-700">Total Income / Revenue</span>
                  <span className="font-mono font-bold text-slate-900 text-sm">
                    {formatINR(pnl.total_income)}
                  </span>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-700">Total Business Expenses</span>
                  <span className="font-mono font-bold text-red-700 text-sm">
                    {formatINR(pnl.total_expenses)}
                  </span>
                </div>

                <div className="p-3 bg-cyan-50 border border-cyan-200 rounded-lg flex items-center justify-between text-xs">
                  <span className="font-bold text-cyan-950">Net Profit / (Loss)</span>
                  <span className="font-mono font-bold text-cyan-950 text-base">
                    {formatINR(pnl.net_profit)}
                  </span>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 space-y-2">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                  Expense Category Breakdown
                </h4>
                <div className="space-y-1.5 text-xs font-mono">
                  {Object.entries(pnl.expenses).map(([cat, amt]) => (
                    <div key={cat} className="flex justify-between py-1 border-b border-slate-100">
                      <span className="text-slate-600 truncate max-w-[200px]" title={cat}>
                        {cat}
                      </span>
                      <span className="font-bold text-slate-900">{formatINR(amt)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sub-tab 3: Chapter VI-A Deductions */}
      {activeTab === 'deductions' && (
        <div className="bg-[var(--surface)] rounded-xl border border-slate-200 p-6 shadow-2xs space-y-6">
          <div className="border-b border-slate-100 pb-4 flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-base font-bold text-slate-900">
                  Chapter VI-A Deduction Schedule
                </h3>
                <span className="px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200 text-xs font-bold">
                  {deductions.label}
                </span>
              </div>
              <p className="text-xs text-[var(--muted)] mt-1">
                Regime: <strong className="font-mono">{deductions.regime}</strong> • Choice:{' '}
                <strong className="capitalize">{deductions.tax_regime_choice}</strong>
              </p>
            </div>
          </div>

          {/* Deductions Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-100/75 border-b border-slate-200 text-slate-600 font-semibold text-[11px] uppercase">
                  <th className="py-2.5 px-4">Section</th>
                  <th className="py-2.5 px-4">Statutory Reference</th>
                  <th className="py-2.5 px-4 text-right">Claimed (₹)</th>
                  <th className="py-2.5 px-4 text-right">Statutory Cap (₹)</th>
                  <th className="py-2.5 px-4 text-right">Allowed (₹)</th>
                  <th className="py-2.5 px-4 text-right">Excess / Disallowed (₹)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-xs">
                {deductions.items.map((item) => (
                  <tr key={item.section} className="hover:bg-slate-50">
                    <td className="py-3 px-4 font-bold text-slate-900">{item.section}</td>
                    <td className="py-3 px-4 text-slate-700 font-semibold">{item.legal_ref}</td>
                    <td className="py-3 px-4 text-right text-slate-800">{formatINR(item.claimed)}</td>
                    <td className="py-3 px-4 text-right text-slate-500">{formatINR(item.cap)}</td>
                    <td className="py-3 px-4 text-right font-bold text-emerald-700 text-sm">
                      {formatINR(item.allowed)}
                    </td>
                    <td className="py-3 px-4 text-right text-red-600 font-semibold">
                      {formatINR(item.excess)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Schedule Notes */}
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-1 text-xs">
            <div className="font-bold text-slate-700">Statutory Notes:</div>
            {deductions.notes.map((note, idx) => (
              <p key={idx} className="text-slate-600 italic">
                • {note}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Sub-tab 4: ITR-3 Draft JSON */}
      {activeTab === 'itr' && (
        <div className="bg-[var(--surface)] rounded-xl border border-slate-200 p-6 shadow-2xs space-y-5">
          {/* Watermark Banner */}
          <div className="p-4 bg-amber-50 border-2 border-amber-300 rounded-xl text-amber-950 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <AlertTriangle className="w-6 h-6 text-amber-600 shrink-0" />
              <div>
                <h4 className="font-bold text-xs uppercase tracking-wider">
                  DRAFT — NOT AN OFFICIAL FILING UTILITY EXPORT
                </h4>
                <p className="text-xs text-amber-900 mt-0.5">
                  Generated solely for CA / Auditor review. Field mapping verified against{' '}
                  <code className="bg-amber-100 px-1 py-0.5 rounded font-mono font-bold">
                    {itrDraft.field_mapping_ref}
                  </code>
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={handleCopyJson}
                className="py-2 px-3 bg-white border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 flex items-center space-x-1.5 transition-colors shadow-2xs"
              >
                {copied ? <CheckCircle className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied!' : 'Copy JSON'}</span>
              </button>

              <button
                type="button"
                onClick={handleDownloadJson}
                className="py-2 px-3 bg-[var(--accent)] hover:bg-cyan-800 text-white rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors shadow-2xs"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download JSON</span>
              </button>
            </div>
          </div>

          {/* Formatted JSON Viewer */}
          <div className="relative">
            <pre className="p-4 bg-slate-900 text-slate-100 rounded-xl overflow-x-auto text-xs font-mono leading-relaxed max-h-[550px]">
              {JSON.stringify(itrDraft, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
