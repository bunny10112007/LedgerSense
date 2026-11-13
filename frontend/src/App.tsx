import React from 'react';
import './styles/tokens.css';

export const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--ink)] flex flex-col font-sans">
      {/* Header Bar */}
      <header className="bg-[var(--surface)] border-b border-slate-200 px-6 py-4 shadow-sm flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-lg bg-[var(--accent)] flex items-center justify-center text-white font-bold text-lg shadow-sm">
            LS
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold tracking-tight text-[var(--ink)]">LedgerSense</h1>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-cyan-50 text-cyan-800 border border-cyan-200">
                CP0 Baseline
              </span>
            </div>
            <p className="text-xs text-[var(--muted)]">
              Autonomous audit & Indian tax-compliance copilot
            </p>
          </div>
        </div>

        {/* Status Badges */}
        <div className="flex items-center space-x-3 text-xs">
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>LLM: Replay Mode</span>
          </div>
          <div className="px-2.5 py-1 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono">
            Active Regime: ITA_1961
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        <div className="bg-[var(--surface)] rounded-xl border border-slate-200 p-8 shadow-sm">
          <div className="border-b border-slate-100 pb-5 mb-6">
            <h2 className="text-lg font-semibold text-[var(--ink)]">Checkpoint 0 Shell</h2>
            <p className="text-sm text-[var(--muted)] mt-1">
              Frozen data contracts verified across backend models, YAML statutory rules, and frontend types.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
              <div className="text-xs font-medium text-[var(--muted)] uppercase tracking-wider">Perception Mode</div>
              <div className="text-base font-semibold text-[var(--ink)] mt-1">Moonshot Kimi VLM</div>
              <p className="text-xs text-slate-500 mt-2">Zero bank data outbound. Images only.</p>
            </div>

            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
              <div className="text-xs font-medium text-[var(--muted)] uppercase tracking-wider">Deterministic Core</div>
              <div className="text-base font-semibold text-[var(--ink)] mt-1">Python Statutory Engine</div>
              <p className="text-xs text-slate-500 mt-2">Mod-36 GSTIN checksum, ITC 17(5), 40A(3), 80C/80D.</p>
            </div>

            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
              <div className="text-xs font-medium text-[var(--muted)] uppercase tracking-wider">Auditor Gate</div>
              <div className="text-base font-semibold text-[var(--ink)] mt-1">HTTP 409 Enforced</div>
              <p className="text-xs text-slate-500 mt-2">HIGH risk flags block journal commit.</p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 py-3 px-6 text-center text-xs text-[var(--muted)] bg-[var(--surface)]">
        PII masked before external transmission. Bank statements are parsed locally and never sent to any LLM.
      </footer>
    </div>
  );
};

export default App;
