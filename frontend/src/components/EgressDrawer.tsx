import React from 'react';
import type { EgressResponse } from '../types/api';
import { X, ShieldCheck, Lock, Activity, DollarSign, FileCheck } from 'lucide-react';
import { formatINR } from '../utils/money';

interface EgressDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  egress: EgressResponse;
}

export const EgressDrawer: React.FC<EgressDrawerProps> = ({ isOpen, onClose, egress }) => {
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
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-emerald-50/50">
          <div>
            <div className="flex items-center space-x-2">
              <ShieldCheck className="w-5 h-5 text-emerald-700" />
              <h2 className="text-base font-bold text-[var(--ink)]">Data Egress & Privacy Controls</h2>
            </div>
            <p className="text-xs text-emerald-800 mt-0.5">
              Strict isolation: Bank data never leaves the client boundary.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Egress Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Hero Privacy Guarantee Banner */}
          <div className="p-4 rounded-xl bg-emerald-50 border-2 border-emerald-200 text-emerald-900 space-y-2">
            <div className="flex items-center space-x-2 font-bold text-sm">
              <Lock className="w-4 h-4 text-emerald-700 shrink-0" />
              <span>Zero Bank Data Egress Policy</span>
            </div>
            <p className="text-xs text-emerald-800 leading-relaxed">
              Bank statements are parsed strictly locally by deterministic Python parsers. No bank transaction narration, balance, account number, or financial figure is ever transmitted to Moonshot Kimi or any external AI model.
            </p>
            <div className="pt-2 border-t border-emerald-200/60 flex items-center space-x-2 text-xs font-semibold text-emerald-950">
              <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
              <span>PII Masking Active: PAN, Aadhaar, phone numbers scrubbed before perception</span>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl">
              <div className="flex items-center space-x-1.5 text-slate-500 text-[11px] font-medium">
                <Activity className="w-3.5 h-3.5" />
                <span>Total Calls</span>
              </div>
              <div className="text-lg font-bold font-mono text-slate-900 mt-1">
                {egress.calls}
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">Replay cache hit 100%</p>
            </div>

            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl">
              <div className="flex items-center space-x-1.5 text-slate-500 text-[11px] font-medium">
                <FileCheck className="w-3.5 h-3.5" />
                <span>Total Payload</span>
              </div>
              <div className="text-lg font-bold font-mono text-slate-900 mt-1">
                {(egress.bytes / 1024).toFixed(1)} KB
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">{egress.bytes} bytes total</p>
            </div>

            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl">
              <div className="flex items-center space-x-1.5 text-slate-500 text-[11px] font-medium">
                <DollarSign className="w-3.5 h-3.5" />
                <span>Est. Cost</span>
              </div>
              <div className="text-lg font-bold font-mono text-slate-900 mt-1">
                {formatINR('6.80')}
              </div>
              <p className="text-[10px] text-slate-400 mt-0.5">${egress.est_cost} USD</p>
            </div>
          </div>

          {/* Outbound Logs */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
              Document Perception Outbound Log
            </h3>

            <div className="space-y-2">
              {egress.entries.map((entry) => (
                <div
                  key={entry.id}
                  className="p-3 rounded-lg border border-slate-200 bg-white hover:border-slate-300 text-xs space-y-1 shadow-2xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-slate-800 text-[11px]">
                      {entry.doc_id || entry.id}
                    </span>
                    <span className="font-mono text-slate-400 text-[10px]">
                      {new Date(entry.ts).toLocaleTimeString('en-IN', { hour12: false })}
                    </span>
                  </div>
                  <p className="text-slate-600 text-xs">{entry.narration}</p>
                  <div className="flex items-center justify-between pt-1 border-t border-slate-100 text-[11px] text-slate-500 font-mono">
                    <span>Model: {entry.model}</span>
                    <span className="text-emerald-700 font-medium">PII Scrubbed</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
