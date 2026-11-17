import React, { useState } from 'react';
import type { Run, Regime } from '../types/api';
import { PipelineStepper } from './PipelineStepper';
import { UploadCloud, FileSpreadsheet, CheckCircle, ArrowRight, Calendar, Sparkles } from 'lucide-react';

interface ScreenUploadProps {
  run: Run;
  onUpdateConfig: (start: string, end: string, regimeChoice: 'old' | 'new') => void;
  onProcessRun: () => void;
  isProcessing: boolean;
  onNavigateToQueue: () => void;
}

export const ScreenUpload: React.FC<ScreenUploadProps> = ({
  run,
  onUpdateConfig,
  onProcessRun,
  isProcessing,
  onNavigateToQueue,
}) => {
  const [startDate, setStartDate] = useState(run.period_start);
  const [endDate, setEndDate] = useState(run.period_end);
  const [regimeChoice, setRegimeChoice] = useState<'old' | 'new'>(run.config.tax_regime_choice);

  // Live regime flip calculation
  const derivedRegime: Regime = endDate <= '2026-03-31' ? 'ITA_1961' : 'ITA_2025';

  const handleDateChange = (newStart: string, newEnd: string) => {
    setStartDate(newStart);
    setEndDate(newEnd);
    onUpdateConfig(newStart, newEnd, regimeChoice);
  };

  const handleRegimeChange = (newChoice: 'old' | 'new') => {
    setRegimeChoice(newChoice);
    onUpdateConfig(startDate, endDate, newChoice);
  };

  return (
    <div className="space-y-6">
      {/* Stepper Card */}
      <PipelineStepper currentStatus={run.status} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Configuration & Process Controls */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-[var(--surface)] p-5 rounded-xl border border-slate-200 shadow-2xs space-y-5">
            <div className="border-b border-slate-100 pb-3">
              <h2 className="text-base font-bold text-[var(--ink)]">Run Parameters</h2>
              <p className="text-xs text-[var(--muted)] mt-0.5">
                Financial period boundary determines active direct-tax statute.
              </p>
            </div>

            {/* Date Pickers */}
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1 flex items-center space-x-1.5">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  <span>Period Start Date</span>
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => handleDateChange(e.target.value, endDate)}
                  className="w-full text-xs font-mono p-2.5 rounded-lg border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-[var(--accent)]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1 flex items-center space-x-1.5">
                  <Calendar className="w-3.5 h-3.5 text-slate-400" />
                  <span>Period End Date</span>
                </label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => handleDateChange(startDate, e.target.value)}
                  className="w-full text-xs font-mono p-2.5 rounded-lg border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-[var(--accent)]"
                />
              </div>

              {/* Dynamic Statutory Regime Indicator */}
              <div
                className={`p-3 rounded-lg border text-xs space-y-1 transition-all ${
                  derivedRegime === 'ITA_1961'
                    ? 'bg-blue-50/70 border-blue-200 text-blue-900'
                    : 'bg-purple-50/70 border-purple-200 text-purple-900'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold">Derived Tax Regime:</span>
                  <span className="font-mono font-bold px-2 py-0.5 rounded bg-white text-[11px] shadow-2xs">
                    {derivedRegime}
                  </span>
                </div>
                <p className="text-[11px] leading-relaxed">
                  {derivedRegime === 'ITA_1961'
                    ? 'Income-tax Act, 1961 statutory sections active (e.g. s.40A(3), s.80C, s.80D).'
                    : 'Direct Tax Code / Income-tax Act, 2025 active (e.g. s.123, s.126; cash limit mapping pending).'}
                </p>
              </div>
            </div>

            {/* Tax Regime Choice (Old vs New) */}
            <div className="space-y-2 pt-2 border-t border-slate-100">
              <label className="block text-xs font-semibold text-slate-700">
                Chapter VI-A Tax Regime Choice
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => handleRegimeChange('old')}
                  className={`p-2.5 text-xs rounded-lg border text-left transition-all ${
                    regimeChoice === 'old'
                      ? 'border-[var(--accent)] bg-cyan-50/50 text-[var(--accent)] font-bold'
                      : 'border-slate-200 hover:bg-slate-50 text-slate-600'
                  }`}
                >
                  <div>Old Tax Regime</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">80C/80D Allowed</div>
                </button>

                <button
                  type="button"
                  onClick={() => handleRegimeChange('new')}
                  className={`p-2.5 text-xs rounded-lg border text-left transition-all ${
                    regimeChoice === 'new'
                      ? 'border-[var(--accent)] bg-cyan-50/50 text-[var(--accent)] font-bold'
                      : 'border-slate-200 hover:bg-slate-50 text-slate-600'
                  }`}
                >
                  <div>New Tax Regime</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">80C/80D Disallowed</div>
                </button>
              </div>
            </div>

            {/* Process Action */}
            <div className="pt-3 border-t border-slate-100 space-y-2">
              <button
                type="button"
                onClick={onProcessRun}
                disabled={isProcessing}
                className="w-full py-3 px-4 bg-[var(--accent)] hover:bg-cyan-800 text-white font-bold text-xs rounded-xl shadow-md transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                {isProcessing ? (
                  <span>Processing Statutory Reconciliation...</span>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Run Full Golden Reconciliation</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={onNavigateToQueue}
                className="w-full py-2.5 px-4 bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold text-xs rounded-xl transition-all flex items-center justify-center space-x-1.5"
              >
                <span>Jump to Review Queue</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Ingestion Dropzones & Seeded Dataset Overview */}
        <div className="lg:col-span-2 space-y-6">
          {/* Dropzones */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Receipts Dropzone */}
            <div className="border-2 border-dashed border-slate-300 rounded-xl p-6 bg-[var(--surface)] text-center flex flex-col items-center justify-center space-y-2 hover:border-[var(--accent)] transition-colors">
              <div className="w-12 h-12 rounded-full bg-cyan-50 text-[var(--accent)] flex items-center justify-center">
                <UploadCloud className="w-6 h-6" />
              </div>
              <h3 className="text-xs font-bold text-slate-800">Receipts & Invoices</h3>
              <p className="text-[11px] text-[var(--muted)]">
                Drop PNG / PDF invoice documents here
              </p>
              <span className="text-[10px] font-mono font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                16 Golden Documents Pre-loaded
              </span>
            </div>

            {/* Bank CSV Dropzone */}
            <div className="border-2 border-dashed border-slate-300 rounded-xl p-6 bg-[var(--surface)] text-center flex flex-col items-center justify-center space-y-2 hover:border-[var(--accent)] transition-colors">
              <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-700 flex items-center justify-center">
                <FileSpreadsheet className="w-6 h-6" />
              </div>
              <h3 className="text-xs font-bold text-slate-800">Bank Statement CSV</h3>
              <p className="text-[11px] text-[var(--muted)]">
                Local parsing only. Zero data sent to LLM.
              </p>
              <span className="text-[10px] font-mono font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                16 Transactions Pre-loaded
              </span>
            </div>
          </div>

          {/* Golden Corpus Summary Card */}
          <div className="bg-[var(--surface)] p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-[var(--ink)]">
                  Golden Benchmark Corpus Overview
                </h3>
                <p className="text-xs text-[var(--muted)] mt-0.5">
                  Synthesized Indian corporate expenditure and bank records covering 10 statutory scenarios.
                </p>
              </div>
              <span className="text-xs font-bold px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200">
                FY 2025-26
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <div className="text-slate-400 font-medium text-[11px]">Total Documents</div>
                <div className="text-lg font-bold font-mono text-slate-800 mt-1">16</div>
                <div className="text-[10px] text-slate-500 mt-0.5">GST, Fuel, Cab, Ins.</div>
              </div>

              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <div className="text-slate-400 font-medium text-[11px]">Bank Matches</div>
                <div className="text-lg font-bold font-mono text-slate-800 mt-1">13</div>
                <div className="text-[10px] text-slate-500 mt-0.5">1-to-1 debit matched</div>
              </div>

              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <div className="text-slate-400 font-medium text-[11px]">Audit Flags</div>
                <div className="text-lg font-bold font-mono text-amber-700 mt-1">7</div>
                <div className="text-[10px] text-red-600 font-semibold mt-0.5">4 Blocking HIGH</div>
              </div>

              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <div className="text-slate-400 font-medium text-[11px]">Committed Target</div>
                <div className="text-lg font-bold font-mono text-emerald-700 mt-1">14</div>
                <div className="text-[10px] text-slate-500 mt-0.5">G06 & G07 rejected</div>
              </div>
            </div>

            {/* Checklist of Core Audit Scenarios */}
            <div className="space-y-2 pt-2 border-t border-slate-100 text-xs text-slate-600">
              <div className="font-semibold text-slate-800">Verified Statutory Scenarios:</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                <div className="flex items-center space-x-1.5">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Exact Cab Fare Duplicate (G05 & G06)</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Out-of-Period April 2026 Cutoff (G07)</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Section 40A(3) Cash Limit &gt; ₹10k (G09)</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                  <span>GSTIN Mod-36 Checksum Failure (G10)</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Blocked ITC 17(5) Food & Car Service</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Unidentified Bank Debit ₹9,999.00</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
