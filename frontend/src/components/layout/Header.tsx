import React from 'react';
import { RefreshCw, Play, Sliders, CheckCircle, AlertCircle, Info, X } from 'lucide-react';
import { useLab } from '../../context/LabContext';

interface HeaderProps {
  title: string;
  subtitle?: string;
  onOpenLabControls: () => void;
}

export const Header: React.FC<HeaderProps> = ({ title, subtitle, onOpenLabControls }) => {
  const { refreshing, refresh, triggerAgentCycle, lastUpdated, notification, setNotification } = useLab();

  return (
    <header className="h-16 px-6 bg-surface border-b border-surface-border flex items-center justify-between shrink-0">
      <div>
        <h1 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          {title}
        </h1>
        {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        {/* Notification Toast */}
        {notification && (
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs border ${
              notification.type === 'success'
                ? 'bg-emerald-950/80 border-emerald-800 text-emerald-300'
                : notification.type === 'error'
                ? 'bg-rose-950/80 border-rose-800 text-rose-300'
                : 'bg-sky-950/80 border-sky-800 text-sky-300'
            }`}
          >
            {notification.type === 'success' && <CheckCircle className="w-3.5 h-3.5" />}
            {notification.type === 'error' && <AlertCircle className="w-3.5 h-3.5" />}
            {notification.type === 'info' && <Info className="w-3.5 h-3.5" />}
            <span>{notification.message}</span>
            <button
              onClick={() => setNotification(null)}
              className="ml-1 text-slate-400 hover:text-white"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        )}

        {/* Timestamp */}
        {lastUpdated && (
          <div className="hidden lg:flex items-center gap-1.5 text-xs font-mono text-slate-400">
            <span>SYNC:</span>
            <span>{lastUpdated.toLocaleTimeString()}</span>
          </div>
        )}

        {/* Refresh button */}
        <button
          onClick={refresh}
          disabled={refreshing}
          className="p-2 rounded-md bg-surface-subtle hover:bg-surface-elevated border border-surface-border text-slate-300 hover:text-white transition-colors"
          title="Refresh Operations State"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-brand-400' : ''}`} />
        </button>

        {/* Run agent cycle */}
        <button
          onClick={triggerAgentCycle}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow transition-colors"
          title="Execute one full autonomous agent investigation cycle"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>Run Agent Cycle</span>
        </button>

        {/* Simulator button */}
        <button
          onClick={onOpenLabControls}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold bg-surface-elevated hover:bg-surface-hover border border-surface-borderLight text-amber-300 transition-colors"
          title="Open Fault Simulator & Injection Controls"
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>Fault Lab</span>
        </button>
      </div>
    </header>
  );
};
