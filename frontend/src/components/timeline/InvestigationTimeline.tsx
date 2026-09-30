import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  ShieldCheck,
  ShieldAlert,
  ChevronDown,
  ChevronRight,
  Wrench,
  Search,
  BookOpen,
  Activity,
} from 'lucide-react';
import type { TimelineStep } from '../../api/types';

interface InvestigationTimelineProps {
  timeline: TimelineStep[];
  className?: string;
}

export const InvestigationTimeline: React.FC<InvestigationTimelineProps> = ({
  timeline,
  className = '',
}) => {
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({
    0: true,
    1: true,
  });

  const toggleStep = (idx: number) => {
    setExpandedSteps((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const getStatusIcon = (status: string, step: string) => {
    switch (status) {
      case 'PASS':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case 'FAIL':
        return <XCircle className="w-4 h-4 text-rose-400" />;
      case 'ALLOWED':
        return <ShieldCheck className="w-4 h-4 text-emerald-400" />;
      case 'BLOCKED':
        return <ShieldAlert className="w-4 h-4 text-amber-400" />;
      case 'ESCALATED':
        return <Wrench className="w-4 h-4 text-orange-400" />;
      default:
        if (step === 'knowledge_retrieval') return <BookOpen className="w-4 h-4 text-sky-400" />;
        if (step === 'history_retrieval') return <Search className="w-4 h-4 text-sky-400" />;
        return <Activity className="w-4 h-4 text-sky-400" />;
    }
  };

  const getBadgeClass = (status: string) => {
    switch (status) {
      case 'PASS':
        return 'text-emerald-400 bg-emerald-950/70 border-emerald-800/60';
      case 'FAIL':
        return 'text-rose-400 bg-rose-950/70 border-rose-800/60';
      case 'ALLOWED':
        return 'text-emerald-300 bg-emerald-950/70 border-emerald-700/60';
      case 'BLOCKED':
        return 'text-amber-400 bg-amber-950/70 border-amber-800/60';
      case 'ESCALATED':
        return 'text-orange-400 bg-orange-950/70 border-orange-800/60';
      default:
        return 'text-sky-400 bg-sky-950/70 border-sky-800/60';
    }
  };

  if (!timeline || timeline.length === 0) {
    return (
      <div className="p-4 rounded-lg bg-surface-subtle text-center text-xs text-slate-400">
        No investigation timeline recorded yet.
      </div>
    );
  }

  return (
    <div className={`space-y-0 relative ${className}`}>
      {timeline.map((item, idx) => {
        const isLast = idx === timeline.length - 1;
        const isExpanded = Boolean(expandedSteps[idx]);

        return (
          <div key={idx} className="relative flex items-start gap-3 group">
            {/* Vertical connector line */}
            {!isLast && (
              <div className="absolute left-[13px] top-6 bottom-0 w-0.5 bg-surface-border group-hover:bg-slate-700 transition-colors" />
            )}

            {/* Step node icon */}
            <div className="relative z-10 w-7 h-7 rounded-full bg-surface-elevated border border-surface-borderLight flex items-center justify-center shrink-0 mt-0.5 shadow-xs">
              {getStatusIcon(item.status, item.step)}
            </div>

            {/* Step content card */}
            <div className="flex-1 pb-6 min-w-0">
              <div
                onClick={() => toggleStep(idx)}
                className="p-3 rounded-lg bg-surface-subtle hover:bg-surface-elevated border border-surface-border transition-colors cursor-pointer select-none"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-xs font-semibold text-slate-200 truncate">
                      {item.title}
                    </span>
                    <span
                      className={`text-[10px] font-mono px-1.5 py-0.2 rounded border ${getBadgeClass(
                        item.status
                      )}`}
                    >
                      {item.status}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-slate-400 text-xs shrink-0">
                    <span className="font-mono text-[11px] hidden sm:inline">
                      {item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : ''}
                    </span>
                    {isExpanded ? (
                      <ChevronDown className="w-3.5 h-3.5" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5" />
                    )}
                  </div>
                </div>

                {/* Structured Evidence Preview when expanded */}
                {isExpanded && item.details && (
                  <div className="mt-3 pt-3 border-t border-surface-border/60">
                    <div className="text-[11px] font-mono text-slate-400 mb-1 uppercase tracking-wider">
                      Structured Evidence:
                    </div>
                    <pre className="p-2.5 rounded bg-surface border border-surface-border text-[11px] font-mono text-slate-300 overflow-x-auto max-h-56 leading-relaxed">
                      {typeof item.details === 'string'
                        ? item.details
                        : JSON.stringify(item.details, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
