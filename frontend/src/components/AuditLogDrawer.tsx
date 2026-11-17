import React from 'react';
import type { AuditEvent } from '../types/api';
import { X, Database, ShieldAlert } from 'lucide-react';

interface AuditLogDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  events: AuditEvent[];
}

export const AuditLogDrawer: React.FC<AuditLogDrawerProps> = ({ isOpen, onClose, events }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Drawer Panel */}
      <div className="relative w-full max-w-xl bg-[var(--surface)] h-full shadow-2xl flex flex-col z-10 border-l border-slate-200">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div>
            <div className="flex items-center space-x-2">
              <Database className="w-5 h-5 text-[var(--accent)]" />
              <h2 className="text-base font-bold text-[var(--ink)]">Immutable Audit Trail</h2>
            </div>
            <div className="mt-1 flex items-center space-x-2">
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center space-x-1">
                <ShieldAlert className="w-3 h-3 text-emerald-600" />
                <span>Append-Only SQLite Trigger Enforced</span>
              </span>
              <span className="text-xs text-[var(--muted)]">({events.length} events)</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Audit Log Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          <p className="text-xs text-[var(--muted)]">
            Chronological, immutable ledger of all status transitions, auditor overrides, and perception calls. SQLite triggers prevent all UPDATE and DELETE mutations.
          </p>

          <div className="space-y-3">
            {events.map((evt) => (
              <div
                key={evt.id}
                className="p-3.5 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition-colors text-xs space-y-1.5 shadow-2xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono font-bold text-slate-800 text-[11px] bg-slate-100 px-1.5 py-0.5 rounded">
                    {evt.id}
                  </span>
                  <span className="font-mono text-slate-500 text-[11px]">
                    {new Date(evt.ts).toLocaleString('en-IN', {
                      timeZone: 'Asia/Kolkata',
                      hour12: false,
                    })}
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  <span
                    className={`font-semibold px-2 py-0.5 rounded text-[10px] uppercase tracking-wider ${
                      evt.action.includes('REJECT')
                        ? 'bg-red-50 text-red-700 border border-red-200'
                        : evt.action.includes('APPROVE') || evt.action.includes('COMMITTED')
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : 'bg-blue-50 text-blue-700 border border-blue-200'
                    }`}
                  >
                    {evt.action}
                  </span>
                  <span className="text-slate-600">
                    by <strong className="text-slate-800">{evt.actor}</strong>
                  </span>
                  {evt.entity_id && (
                    <span className="font-mono text-slate-500 text-[11px] truncate max-w-[160px]">
                      on {evt.entity_id}
                    </span>
                  )}
                </div>

                {evt.reason && (
                  <p className="text-slate-700 bg-slate-50 p-2 rounded border border-slate-100 italic">
                    "{evt.reason}"
                  </p>
                )}

                <div className="text-[10px] text-slate-400 font-mono pt-1 border-t border-slate-100 flex items-center justify-between">
                  <span>SHA-256 Hash:</span>
                  <span title={evt.payload_hash}>
                    {evt.payload_hash.slice(0, 16)}...{evt.payload_hash.slice(-8)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
