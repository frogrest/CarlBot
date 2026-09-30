import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  Loader2,
  ShieldAlert,
  MinusCircle,
  ChevronDown,
  ChevronRight,
  Terminal,
} from 'lucide-react';
import type { ChatToolCall } from './types';

interface ChatToolStepProps {
  toolCalls: ChatToolCall[];
}

export const ChatToolStep: React.FC<ChatToolStepProps> = ({ toolCalls }) => {
  const [isOpen, setIsOpen] = useState(true);

  if (!toolCalls || toolCalls.length === 0) return null;

  const getStatusIcon = (status: ChatToolCall['status']) => {
    switch (status) {
      case 'running':
        return <Loader2 className="w-3.5 h-3.5 text-sky-400 animate-spin" />;
      case 'success':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
      case 'failure':
        return <XCircle className="w-3.5 h-3.5 text-rose-400" />;
      case 'blocked':
        return <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />;
      case 'skipped':
        return <MinusCircle className="w-3.5 h-3.5 text-slate-500" />;
    }
  };

  const completedCount = toolCalls.filter((t) => t.status !== 'running').length;

  return (
    <div className="my-3 rounded-lg border border-surface-border bg-surface-subtle/80 overflow-hidden text-xs">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3 py-2 flex items-center justify-between text-slate-300 hover:text-white bg-surface-elevated/50 font-mono transition-colors"
      >
        <div className="flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-brand-400" />
          <span className="font-semibold uppercase text-[11px] tracking-wider">
            Diagnostic Tool Activity ({completedCount}/{toolCalls.length})
          </span>
        </div>
        {isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
      </button>

      {isOpen && (
        <div className="p-3 space-y-2 border-t border-surface-border/50 font-mono text-[11px]">
          {toolCalls.map((tc, idx) => (
            <div key={idx} className="flex items-start justify-between gap-2 text-slate-300">
              <div className="flex items-center gap-2 min-w-0">
                {getStatusIcon(tc.status)}
                <span className="truncate">{tc.label}</span>
              </div>
              <span
                className={`uppercase text-[10px] shrink-0 ${
                  tc.status === 'success'
                    ? 'text-emerald-400'
                    : tc.status === 'failure'
                    ? 'text-rose-400'
                    : tc.status === 'blocked'
                    ? 'text-amber-400'
                    : tc.status === 'running'
                    ? 'text-sky-400'
                    : 'text-slate-500'
                }`}
              >
                {tc.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
