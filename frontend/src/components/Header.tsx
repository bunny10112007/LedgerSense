import React from 'react';
import type { Run } from '../types/api';
import { ShieldCheck, FileText, Database, Eye } from 'lucide-react';

interface HeaderProps {
  run: Run;
  activeScreen: 'upload' | 'queue' | 'recon' | 'books';
  setActiveScreen: (screen: 'upload' | 'queue' | 'recon' | 'books') => void;
  openHighCount: number;
  auditCount: number;
  onOpenAuditDrawer: () => void;
  onOpenEgressDrawer: () => void;
  onResetMock: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  run,
  activeScreen,
  setActiveScreen,
  openHighCount,
  auditCount,
  onOpenAuditDrawer,
  onOpenEgressDrawer,
  onResetMock,
}) => {
  const isITA1961 = run.regime === 'ITA_1961';

  return (
    <header className="bg-[var(--surface)] border-b border-slate-200 sticky top-0 z-30 shadow-sm">
      <div className="px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">
        {/* Logo & Run Meta */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-[var(--accent)] flex items-center justify-center text-white font-bold text-lg shadow-sm">
            LS
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold tracking-tight text-[var(--ink)]">
                LedgerSense
              </h1>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono">
                {run.id}
              </span>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded border ${
                  isITA1961
                    ? 'bg-blue-50 text-blue-800 border-blue-200'
                    : 'bg-purple-50 text-purple-800 border-purple-200'
                }`}
                title={
                  isITA1961
                    ? 'Income-tax Act, 1961 (FY ending on or before 31 Mar 2026)'
                    : 'Income-tax Act, 2025 (FY ending 1 Apr 2026 onwards)'
                }
              >
                {run.regime}
              </span>
            </div>
            <div className="flex items-center space-x-2 text-xs text-[var(--muted)] mt-0.5">
              <span>
                Period: <strong className="font-mono text-slate-700">{run.period_start}</strong> to{' '}
                <strong className="font-mono text-slate-700">{run.period_end}</strong>
              </span>
              <span>•</span>
              <span className="flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="font-medium text-emerald-700">LLM: REPLAY</span>
              </span>
            </div>
          </div>
        </div>

        {/* Global Action Panels */}
        <div className="flex items-center space-x-2.5">
          <button
            onClick={onOpenAuditDrawer}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-medium text-slate-700 hover:bg-slate-50 transition-colors shadow-2xs"
            title="Open Immutable Audit Log"
          >
            <Database className="w-3.5 h-3.5 text-slate-500" />
            <span>Audit Trail</span>
            <span className="px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-600 font-mono text-[10px] border border-slate-200">
              {auditCount}
            </span>
          </button>

          <button
            onClick={onOpenEgressDrawer}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-emerald-200 bg-emerald-50 text-xs font-medium text-emerald-800 hover:bg-emerald-100 transition-colors shadow-2xs"
            title="Open Data Egress & Privacy Panel"
          >
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            <span>Data Privacy & Egress</span>
          </button>

          <button
            onClick={onResetMock}
            className="text-xs px-2.5 py-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-md transition-colors"
            title="Reset Mock State to Golden Baseline"
          >
            Reset Golden
          </button>
        </div>
      </div>

      {/* Navigation Tabs Bar */}
      <div className="px-6 flex space-x-1 border-t border-slate-100 overflow-x-auto">
        <button
          onClick={() => setActiveScreen('upload')}
          className={`py-3 px-4 text-xs font-semibold border-b-2 transition-colors flex items-center space-x-2 whitespace-nowrap ${
            activeScreen === 'upload'
              ? 'border-[var(--accent)] text-[var(--accent)]'
              : 'border-transparent text-[var(--muted)] hover:text-[var(--ink)]'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>1. Upload & Run Setup</span>
        </button>

        <button
          onClick={() => setActiveScreen('queue')}
          className={`py-3 px-4 text-xs font-semibold border-b-2 transition-colors flex items-center space-x-2 whitespace-nowrap ${
            activeScreen === 'queue'
              ? 'border-[var(--accent)] text-[var(--accent)]'
              : 'border-transparent text-[var(--muted)] hover:text-[var(--ink)]'
          }`}
        >
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>2. Statutory Review Queue</span>
          {openHighCount > 0 ? (
            <span className="px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 text-[10px] font-bold border border-red-200 animate-pulse">
              {openHighCount} Open HIGH
            </span>
          ) : (
            <span className="px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-medium border border-emerald-200">
              Resolved
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveScreen('recon')}
          className={`py-3 px-4 text-xs font-semibold border-b-2 transition-colors flex items-center space-x-2 whitespace-nowrap ${
            activeScreen === 'recon'
              ? 'border-[var(--accent)] text-[var(--accent)]'
              : 'border-transparent text-[var(--muted)] hover:text-[var(--ink)]'
          }`}
        >
          <Database className="w-3.5 h-3.5" />
          <span>3. Bank Reconciliation</span>
        </button>

        <button
          onClick={() => setActiveScreen('books')}
          className={`py-3 px-4 text-xs font-semibold border-b-2 transition-colors flex items-center space-x-2 whitespace-nowrap ${
            activeScreen === 'books'
              ? 'border-[var(--accent)] text-[var(--accent)]'
              : 'border-transparent text-[var(--muted)] hover:text-[var(--ink)]'
          }`}
        >
          <Eye className="w-3.5 h-3.5" />
          <span>4. Books & Tax Drafts</span>
        </button>
      </div>
    </header>
  );
};
