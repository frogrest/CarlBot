import React, { useState, useEffect } from 'react';
import { RefreshCw, Play, Sliders, CheckCircle, AlertCircle, Info, X, Menu, Activity } from 'lucide-react';
import { useLab } from '../../context/LabContext';

interface HeaderProps {
  title: string;
  subtitle?: string;
  onOpenLabControls: () => void;
  onToggleSidebar?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  subtitle,
  onOpenLabControls,
  onToggleSidebar,
}) => {
  const { refreshing, refresh, triggerAgentCycle, lastUpdated, notification, setNotification } = useLab();
  const [clockUtc, setClockUtc] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setClockUtc(now.toUTCString().slice(17, 25) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 px-4 md:px-6 bg-surface border-b border-surface-border flex items-center justify-between shrink-0 z-10">
      <div className="flex items-center gap-3">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            aria-label="Toggle navigation menu"
            className="md:hidden p-2 rounded-md bg-surface-subtle hover:bg-surface-elevated border border-surface-border text-slate-300 hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-brand-500/50"
          >
            <Menu className="w-4 h-4" />
          </button>
        )}
        <div>
          <h1 className="text-base md:text-lg font-bold text-slate-100 flex items-center gap-2 tracking-tight">
            {title}
          </h1>
          {subtitle && <p className="text-xs text-slate-400 hidden sm:block">{subtitle}</p>}
        </div>
      </div>

      <div className="flex items-center gap-2 md:gap-3">
        {/* Notification Toast */}
        {notification && (
          <div
            role="status"
            aria-live="polite"
            className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs border ${
              notification.type === 'success'
                ? 'bg-emerald-950/90 border-emerald-700/80 text-emerald-200'
                : notification.type === 'error'
                ? 'bg-rose-950/90 border-rose-700/80 text-rose-200'
                : 'bg-sky-950/90 border-sky-700/80 text-sky-200'
            }`}
          >
            {notification.type === 'success' && <CheckCircle className="w-3.5 h-3.5" />}
            {notification.type === 'error' && <AlertCircle className="w-3.5 h-3.5" />}
            {notification.type === 'info' && <Info className="w-3.5 h-3.5" />}
            <span>{notification.message}</span>
            <button
              onClick={() => setNotification(null)}
              aria-label="Dismiss notification"
              className="ml-1 text-slate-400 hover:text-white focus-visible:outline-none"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        )}

        {/* NOC UTC Live Clock */}
        <div className="hidden xl:flex items-center gap-2 px-2.5 py-1 rounded bg-surface-subtle border border-surface-border text-xs font-mono text-slate-300">
          <Activity className="w-3 h-3 text-brand-400" />
          <span>{clockUtc}</span>
        </div>

        {/* Last telemetry sync */}
        {lastUpdated && (
          <div className="hidden lg:flex items-center gap-1.5 text-xs font-mono text-slate-400">
            <span className="text-[10px] text-slate-400 uppercase tracking-wider">SYNC:</span>
            <span className="text-slate-200">{lastUpdated.toLocaleTimeString()}</span>
          </div>
        )}

        {/* Refresh telemetry */}
        <button
          onClick={refresh}
          disabled={refreshing}
          aria-label="Refresh telemetry data"
          className="p-2 rounded-md bg-surface-subtle hover:bg-surface-elevated border border-surface-border text-slate-300 hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-brand-500/50"
          title="Refresh Operations State"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-brand-400' : ''}`} />
        </button>

        {/* Run agent cycle */}
        <button
          onClick={triggerAgentCycle}
          aria-label="Execute one autonomous investigation cycle"
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-sm transition-colors focus-visible:ring-2 focus-visible:ring-brand-400"
          title="Execute one full autonomous agent investigation cycle"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span className="hidden sm:inline">Run Cycle</span>
        </button>

        {/* Fault Simulator Lab button */}
        <button
          onClick={onOpenLabControls}
          aria-label="Open Fault Simulator & Injection Controls"
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold bg-surface-elevated hover:bg-surface-hover border border-surface-borderLight text-amber-300 transition-colors focus-visible:ring-2 focus-visible:ring-amber-400"
          title="Open Fault Simulator & Injection Controls"
        >
          <Sliders className="w-3.5 h-3.5" />
          <span>Fault Lab</span>
        </button>
      </div>
    </header>
  );
};
