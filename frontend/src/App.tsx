import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from './api/client';
import { Header } from './components/Header';
import { ScreenUpload } from './components/ScreenUpload';
import { ScreenReviewQueue } from './components/ScreenReviewQueue';
import { ScreenReconciliation } from './components/ScreenReconciliation';
import { ScreenBooks } from './components/ScreenBooks';
import { AuditLogDrawer } from './components/AuditLogDrawer';
import { EgressDrawer } from './components/EgressDrawer';

export const App: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeScreen, setActiveScreen] = useState<'upload' | 'queue' | 'recon' | 'books'>('queue');
  const [auditDrawerOpen, setAuditDrawerOpen] = useState(false);
  const [egressDrawerOpen, setEgressDrawerOpen] = useState(false);

  // Queries
  const { data: run } = useQuery({
    queryKey: ['run'],
    queryFn: () => api.getRun(),
  });

  const { data: receipts = [] } = useQuery({
    queryKey: ['receipts'],
    queryFn: () => api.listReceipts(),
  });

  const { data: bankLines = [] } = useQuery({
    queryKey: ['bankLines'],
    queryFn: () => api.listBankLines(),
  });

  const { data: matches = [] } = useQuery({
    queryKey: ['matches'],
    queryFn: () => api.listMatches(),
  });

  const { data: flags = [] } = useQuery({
    queryKey: ['flags'],
    queryFn: () => api.listFlags(),
  });

  const { data: journalEntries = [] } = useQuery({
    queryKey: ['journal'],
    queryFn: () => api.listJournal(),
  });

  const { data: trialBalance } = useQuery({
    queryKey: ['trialBalance'],
    queryFn: () => api.getTrialBalance(),
  });

  const { data: pnl } = useQuery({
    queryKey: ['pnl'],
    queryFn: () => api.getPnL(),
  });

  const { data: deductions } = useQuery({
    queryKey: ['deductions'],
    queryFn: () => api.getDeductions(),
  });

  const { data: itrDraft } = useQuery({
    queryKey: ['itrDraft'],
    queryFn: () => api.getITRDraft(),
  });

  const { data: auditEvents = [] } = useQuery({
    queryKey: ['auditEvents'],
    queryFn: () => api.getAuditLog(),
  });

  const { data: egress } = useQuery({
    queryKey: ['egress'],
    queryFn: () => api.getEgress(),
  });

  // Mutations
  const decideMutation = useMutation({
    mutationFn: ({
      flagId,
      auditorId,
      decision,
      reason,
    }: {
      flagId: string;
      auditorId: string;
      decision: 'approve' | 'reject';
      reason: string;
    }) => api.submitFlagDecision(run?.id || 'run:2025-26-demo', flagId, { auditor_id: auditorId, decision, reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['flags'] });
      queryClient.invalidateQueries({ queryKey: ['run'] });
      queryClient.invalidateQueries({ queryKey: ['auditEvents'] });
    },
  });

  const commitMutation = useMutation({
    mutationFn: () => api.commitRun(run?.id || 'run:2025-26-demo', 'auditor-a'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['run'] });
      queryClient.invalidateQueries({ queryKey: ['journal'] });
      queryClient.invalidateQueries({ queryKey: ['auditEvents'] });
      queryClient.invalidateQueries({ queryKey: ['trialBalance'] });
      queryClient.invalidateQueries({ queryKey: ['pnl'] });
      queryClient.invalidateQueries({ queryKey: ['deductions'] });
      queryClient.invalidateQueries({ queryKey: ['itrDraft'] });
    },
  });

  const processMutation = useMutation({
    mutationFn: () => api.processRun(run?.id || 'run:2025-26-demo'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['run'] });
      queryClient.invalidateQueries({ queryKey: ['flags'] });
      queryClient.invalidateQueries({ queryKey: ['matches'] });
      queryClient.invalidateQueries({ queryKey: ['journal'] });
      queryClient.invalidateQueries({ queryKey: ['auditEvents'] });
    },
  });

  const openHighCount = flags.filter((f) => f.severity === 'HIGH' && f.status === 'OPEN').length;

  const handleUpdateConfig = (start: string, end: string, choice: 'old' | 'new') => {
    if (run) {
      run.period_start = start;
      run.period_end = end;
      run.regime = end <= '2026-03-31' ? 'ITA_1961' : 'ITA_2025';
      run.config.tax_regime_choice = choice;
      queryClient.invalidateQueries({ queryKey: ['run'] });
    }
  };

  const handleResetMock = () => {
    api.resetMock();
    queryClient.invalidateQueries();
  };

  if (!run || !trialBalance || !pnl || !deductions || !itrDraft || !egress) {
    return (
      <div className="min-h-screen bg-[var(--bg)] flex items-center justify-center">
        <div className="flex flex-col items-center space-y-2 text-slate-500 text-xs font-mono">
          <div className="w-8 h-8 rounded-full border-2 border-[var(--accent)] border-t-transparent animate-spin" />
          <span>Bootstrapping LedgerSense Baseline...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--ink)] flex flex-col font-sans">
      {/* Top Header Bar */}
      <Header
        run={run}
        activeScreen={activeScreen}
        setActiveScreen={setActiveScreen}
        openHighCount={openHighCount}
        auditCount={auditEvents.length}
        onOpenAuditDrawer={() => setAuditDrawerOpen(true)}
        onOpenEgressDrawer={() => setEgressDrawerOpen(true)}
        onResetMock={handleResetMock}
      />

      {/* Main Content Pane */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        {activeScreen === 'upload' && (
          <ScreenUpload
            run={run}
            onUpdateConfig={handleUpdateConfig}
            onProcessRun={() => processMutation.mutate()}
            isProcessing={processMutation.isPending}
            onNavigateToQueue={() => setActiveScreen('queue')}
          />
        )}

        {activeScreen === 'queue' && (
          <ScreenReviewQueue
            flags={flags}
            receipts={receipts}
            bankLines={bankLines}
            run={run}
            onDecideFlag={async (flagId, auditorId, decision, reason) => {
              await decideMutation.mutateAsync({ flagId, auditorId, decision, reason });
            }}
            onCommitBooks={async () => {
              await commitMutation.mutateAsync();
            }}
            isCommitting={commitMutation.isPending}
          />
        )}

        {activeScreen === 'recon' && (
          <ScreenReconciliation
            matches={matches}
            receipts={receipts}
            bankLines={bankLines}
          />
        )}

        {activeScreen === 'books' && (
          <ScreenBooks
            journalEntries={journalEntries}
            trialBalance={trialBalance}
            pnl={pnl}
            deductions={deductions}
            itrDraft={itrDraft}
          />
        )}
      </main>

      {/* Global Panels */}
      <AuditLogDrawer
        isOpen={auditDrawerOpen}
        onClose={() => setAuditDrawerOpen(false)}
        events={auditEvents}
      />

      <EgressDrawer
        isOpen={egressDrawerOpen}
        onClose={() => setEgressDrawerOpen(false)}
        egress={egress}
      />

      {/* Global Footer */}
      <footer className="border-t border-slate-200 py-3.5 px-6 text-center text-xs text-[var(--muted)] bg-[var(--surface)]">
        <p>
          LedgerSense Autonomous Indian Tax Copilot • Bank CSV records are parsed locally and never transmitted to LLM • PII masked before perception
        </p>
      </footer>
    </div>
  );
};

export default App;
