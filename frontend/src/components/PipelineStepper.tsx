import React from 'react';
import type { RunStatus } from '../types/api';
import { CheckCircle2, Circle, AlertCircle } from 'lucide-react';

interface PipelineStepperProps {
  currentStatus: RunStatus;
}

const STAGES: { key: RunStatus; label: string }[] = [
  { key: 'CREATED', label: '1. Created' },
  { key: 'EXTRACTED', label: '2. Extracted' },
  { key: 'VALIDATED', label: '3. Validated' },
  { key: 'MATCHED', label: '4. Matched' },
  { key: 'RISK_DONE', label: '5. Risk Assessed' },
  { key: 'AWAITING_REVIEW', label: '6. Review Gate' },
  { key: 'APPROVED', label: '7. Gate Approved' },
  { key: 'COMMITTED', label: '8. Committed' },
];

export const PipelineStepper: React.FC<PipelineStepperProps> = ({ currentStatus }) => {
  if (currentStatus === 'FAILED') {
    return (
      <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2 text-xs text-red-700">
        <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
        <span className="font-semibold">Pipeline Execution Failed</span>
      </div>
    );
  }

  const currentIndex = STAGES.findIndex((s) => s.key === currentStatus);

  return (
    <div className="w-full bg-slate-50 border border-slate-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
          Statutory Pipeline Status
        </span>
        <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-white border border-slate-200 text-slate-800">
          State: {currentStatus}
        </span>
      </div>

      <div className="overflow-x-auto py-1">
        <div className="flex items-center min-w-[720px] justify-between">
          {STAGES.map((stage, idx) => {
            const isCompleted = idx < currentIndex;
            const isCurrent = idx === currentIndex;

            return (
              <React.Fragment key={stage.key}>
                <div className="flex flex-col items-center text-center">
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center transition-colors shadow-2xs ${
                      isCompleted
                        ? 'bg-emerald-600 text-white'
                        : isCurrent
                        ? 'bg-[var(--accent)] text-white ring-4 ring-cyan-100 animate-pulse'
                        : 'bg-white text-slate-400 border border-slate-300'
                    }`}
                  >
                    {isCompleted ? (
                      <CheckCircle2 className="w-4 h-4" />
                    ) : isCurrent ? (
                      <Circle className="w-4 h-4 fill-current" />
                    ) : (
                      <span className="text-[11px] font-mono">{idx + 1}</span>
                    )}
                  </div>
                  <span
                    className={`text-[11px] mt-1.5 font-medium whitespace-nowrap ${
                      isCurrent
                        ? 'text-[var(--accent)] font-bold'
                        : isCompleted
                        ? 'text-slate-800'
                        : 'text-slate-400'
                    }`}
                  >
                    {stage.label}
                  </span>
                </div>

                {idx < STAGES.length - 1 && (
                  <div
                    className={`flex-1 h-0.5 mx-2 rounded transition-colors ${
                      idx < currentIndex ? 'bg-emerald-500' : 'bg-slate-200'
                    }`}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
};
