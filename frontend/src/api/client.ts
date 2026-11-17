import type {
  Run,
  Receipt,
  Match,
  RiskFlag,
  JournalEntry,
  TrialBalance,
  PnL,
  DeductionSchedule,
  ITRDraft,
  AuditEvent,
  EgressResponse,
  FlagDecisionRequest,
  CommitResponse,
} from '../types/api';

import {
  initialRun,
  initialReceipts,
  initialBankLines,
  initialMatches,
  initialFlags,
  initialJournalEntries,
  committedGoldenEntries,
  initialTrialBalance,
  initialPnL,
  initialDeductions,
  initialITRDraft,
  initialAuditEvents,
  initialEgress,
} from './mockData';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const FORCE_MOCK = import.meta.env.VITE_MOCK_API === '1';

// Stateful in-memory mock store
class MockStore {
  run: Run = { ...initialRun };
  receipts: Receipt[] = [...initialReceipts];
  bankLines = [...initialBankLines];
  matches: Match[] = [...initialMatches];
  flags: RiskFlag[] = initialFlags.map((f) => ({ ...f }));
  journalEntries: JournalEntry[] = initialJournalEntries.map((j) => ({ ...j }));
  trialBalance: TrialBalance = { ...initialTrialBalance };
  pnl: PnL = { ...initialPnL };
  deductions: DeductionSchedule = {
    ...initialDeductions,
    items: initialDeductions.items.map((i) => ({ ...i })),
    notes: [...initialDeductions.notes],
  };
  itrDraft: ITRDraft = { ...initialITRDraft, payload: { ...initialITRDraft.payload } };
  auditEvents: AuditEvent[] = [...initialAuditEvents];
  egress: EgressResponse = { ...initialEgress, entries: [...initialEgress.entries] };

  reset() {
    this.run = { ...initialRun };
    this.receipts = [...initialReceipts];
    this.bankLines = [...initialBankLines];
    this.matches = [...initialMatches];
    this.flags = initialFlags.map((f) => ({ ...f }));
    this.journalEntries = initialJournalEntries.map((j) => ({ ...j }));
    this.trialBalance = { ...initialTrialBalance };
    this.pnl = { ...initialPnL };
    this.deductions = {
      ...initialDeductions,
      items: initialDeductions.items.map((i) => ({ ...i })),
      notes: [...initialDeductions.notes],
    };
    this.itrDraft = { ...initialITRDraft, payload: { ...initialITRDraft.payload } };
    this.auditEvents = [...initialAuditEvents];
    this.egress = { ...initialEgress, entries: [...initialEgress.entries] };
  }
}

export const mockStore = new MockStore();

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  if (FORCE_MOCK) {
    throw new Error('FORCE_MOCK');
  }

  const isFormData = typeof FormData !== 'undefined' && options?.body instanceof FormData;
  const headers: Record<string, string> = {};
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      ...headers,
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ message: res.statusText }));
    const err = new Error(errorBody.message || `HTTP ${res.status}`);
    (err as unknown as { status: number; details: unknown; code?: string }).status = res.status;
    (err as unknown as { status: number; details: unknown; code?: string }).details = errorBody.details || errorBody;
    (err as unknown as { status: number; details: unknown; code?: string }).code = errorBody.code;
    throw err;
  }

  return res.json();
}

export const api = {
  async healthCheck(): Promise<{ status: string; llm_mode: string; model_id: string }> {
    try {
      return await request<{ status: string; llm_mode: string; model_id: string }>('/health');
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in (err as object)) throw err;
      return { status: 'ok', llm_mode: 'replay', model_id: 'argon-vision-v1' };
    }
  },

  async createRun(payload: {
    period_start: string;
    period_end: string;
    tax_regime_choice: 'old' | 'new';
    id?: string;
    cash_limit?: string;
    date_window_days?: number;
    amount_tolerance?: string;
  }): Promise<Run> {
    try {
      return await request<Run>('/runs', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in (err as object)) throw err;
      return mockStore.run;
    }
  },

  async uploadDocuments(
    runId: string,
    files: File[]
  ): Promise<Array<{ id: string; filename: string; file_hash: string; mime: string; extraction_status: string }>> {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    return await request<Array<{ id: string; filename: string; file_hash: string; mime: string; extraction_status: string }>>(
      `/runs/${runId}/documents`,
      {
        method: 'POST',
        body: formData,
      }
    );
  },

  async uploadBankCsv(
    runId: string,
    file: File
  ): Promise<{ lines_parsed: number; errors: string[] }> {
    const formData = new FormData();
    formData.append('file', file);
    return await request<{ lines_parsed: number; errors: string[] }>(
      `/runs/${runId}/bank-csv`,
      {
        method: 'POST',
        body: formData,
      }
    );
  },

  async getRun(runId: string = 'run:2025-26-demo'): Promise<Run> {
    try {
      return await request<Run>(`/runs/${runId}`);
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in (err as object)) throw err;
      return mockStore.run;
    }
  },

  async listReceipts(runId: string = 'run:2025-26-demo'): Promise<Receipt[]> {
    try {
      return await request<Receipt[]>(`/runs/${runId}/receipts`);
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in (err as object)) throw err;
      return mockStore.receipts;
    }
  },

  async listMatches(runId: string = 'run:2025-26-demo'): Promise<Match[]> {
    try {
      return await request<Match[]>(`/runs/${runId}/matches`);
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in (err as object)) throw err;
      return mockStore.matches;
    }
  },

  async listBankLines(_runId: string = 'run:2025-26-demo') {
    return mockStore.bankLines;
  },

  async listFlags(runId: string = 'run:2025-26-demo'): Promise<RiskFlag[]> {
    try {
      return await request<RiskFlag[]>(`/runs/${runId}/flags`);
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in (err as object)) throw err;
      return mockStore.flags;
    }
  },

  async submitFlagDecision(
    _runId: string,
    flagId: string,
    payload: FlagDecisionRequest
  ): Promise<RiskFlag> {
    try {
      return await request<RiskFlag>(`/flags/${flagId}/decision`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in (err as object)) throw err;
      const flag = mockStore.flags.find((f) => f.id === flagId);
      if (!flag) {
        throw new Error(`Flag not found: ${flagId}`);
      }
      if (payload.reason.trim().length < 10) {
        throw new Error('Reason must be at least 10 characters');
      }

      flag.status = payload.decision === 'approve' ? 'APPROVED' : 'REJECTED';
      flag.decided_by = payload.auditor_id;
      flag.decision_reason = payload.reason;
      flag.decided_at = new Date().toISOString();

      // Append audit event
      const newEvent: AuditEvent = {
        id: `evt:${String(mockStore.auditEvents.length + 1).padStart(4, '0')}`,
        ts: new Date().toISOString(),
        run_id: _runId,
        actor: payload.auditor_id,
        action: payload.decision === 'approve' ? 'FLAG_APPROVED' : 'FLAG_REJECTED',
        entity_id: flagId,
        reason: payload.reason,
        payload_hash: Math.random().toString(16).slice(2) + Math.random().toString(16).slice(2),
      };
      mockStore.auditEvents.push(newEvent);

      // Check if all HIGH flags are resolved
      const openHigh = mockStore.flags.filter(
        (f) => f.severity === 'HIGH' && f.status === 'OPEN'
      );
      if (openHigh.length === 0 && mockStore.run.status === 'AWAITING_REVIEW') {
        mockStore.run.status = 'APPROVED';
        mockStore.auditEvents.push({
          id: `evt:${String(mockStore.auditEvents.length + 1).padStart(4, '0')}`,
          ts: new Date().toISOString(),
          run_id: _runId,
          actor: 'system',
          action: 'STATE_CHANGE',
          entity_id: _runId,
          reason: 'All HIGH severity risk flags resolved. Run transitioned to APPROVED.',
          payload_hash: Math.random().toString(16).slice(2) + Math.random().toString(16).slice(2),
        });
      }

      return flag;
    }
  },

  async commitRun(runId: string, auditorId: string = 'auditor-a'): Promise<CommitResponse> {
    try {
      return await request<CommitResponse>(`/runs/${runId}/commit`, {
        method: 'POST',
        body: JSON.stringify({ auditor_id: auditorId }),
      });
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in (err as object)) {
        throw err;
      }

      const openHigh = mockStore.flags.filter(
        (f) => f.severity === 'HIGH' && f.status === 'OPEN'
      );

      if (openHigh.length > 0) {
        const gateErr = new Error(
          `Gate Rule Blocked: ${openHigh.length} HIGH severity risk flags remain OPEN`
        );
        (gateErr as unknown as { status: number; open_high_flags: RiskFlag[]; details: unknown; code: string }).status = 409;
        (gateErr as unknown as { status: number; open_high_flags: RiskFlag[]; details: unknown; code: string }).open_high_flags = openHigh;
        (gateErr as unknown as { status: number; open_high_flags: RiskFlag[]; details: unknown; code: string }).code = 'GATE_BLOCKED_HIGH_RISK';
        (gateErr as unknown as { status: number; open_high_flags: RiskFlag[]; details: unknown; code: string }).details = {
          open_high_flags: openHigh,
        };
        throw gateErr;
      }

      // Commit books
      mockStore.run.status = 'COMMITTED';
      mockStore.journalEntries = committedGoldenEntries.map((j) => ({
        ...j,
        status: 'COMMITTED',
      }));

      // Append committed audit event
      mockStore.auditEvents.push({
        id: `evt:${String(mockStore.auditEvents.length + 1).padStart(4, '0')}`,
        ts: new Date().toISOString(),
        run_id: runId,
        actor: auditorId,
        action: 'RUN_COMMITTED',
        entity_id: runId,
        reason: 'All risk flags resolved and signed off. 14 double-entry journal entries committed to immutable ledger.',
        payload_hash: Math.random().toString(16).slice(2) + Math.random().toString(16).slice(2),
      });

      return {
        entries_committed: 14,
        message: 'Successfully committed 14 journal entries to immutable ledger.',
      };
    }
  },

  async listJournal(runId: string = 'run:2025-26-demo'): Promise<JournalEntry[]> {
    try {
      return await request<JournalEntry[]>(`/runs/${runId}/journal`);
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in (err as object)) throw err;
      return mockStore.journalEntries;
    }
  },

  async getTrialBalance(runId: string = 'run:2025-26-demo'): Promise<TrialBalance> {
    try {
      return await request<TrialBalance>(`/runs/${runId}/trial-balance`);
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in (err as object)) throw err;
      return mockStore.trialBalance;
    }
  },

  async getPnL(runId: string = 'run:2025-26-demo'): Promise<PnL> {
    try {
      return await request<PnL>(`/runs/${runId}/pnl`);
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in (err as object)) throw err;
      return mockStore.pnl;
    }
  },

  async getDeductions(runId: string = 'run:2025-26-demo'): Promise<DeductionSchedule> {
    try {
      return await request<DeductionSchedule>(`/runs/${runId}/tax/deductions`);
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in (err as object)) throw err;
      return mockStore.deductions;
    }
  },

  async getITRDraft(runId: string = 'run:2025-26-demo'): Promise<ITRDraft> {
    try {
      return await request<ITRDraft>(`/runs/${runId}/tax/itr?form=ITR-3`);
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in (err as object)) throw err;
      return mockStore.itrDraft;
    }
  },

  async getAuditLog(runId: string = 'run:2025-26-demo'): Promise<AuditEvent[]> {
    try {
      return await request<AuditEvent[]>(`/runs/${runId}/audit-log`);
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in (err as object)) throw err;
      return mockStore.auditEvents;
    }
  },

  async getEgress(runId: string = 'run:2025-26-demo'): Promise<EgressResponse> {
    try {
      return await request<EgressResponse>(`/runs/${runId}/egress`);
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in (err as object)) throw err;
      return mockStore.egress;
    }
  },

  async processRun(runId: string = 'run:2025-26-demo'): Promise<{ status: string }> {
    try {
      return await request<{ status: string }>(`/runs/${runId}/process`, { method: 'POST' });
    } catch (err: unknown) {
      if (err instanceof Error && 'status' in (err as object)) throw err;
      mockStore.run.status = 'AWAITING_REVIEW';
      return { status: mockStore.run.status };
    }
  },

  resetMock() {
    mockStore.reset();
  },
};
