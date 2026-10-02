import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  AlertOctagon,
  Network,
  Cpu,
  BookOpen,
  Bot,
  ScrollText,
  Sliders,
  ShieldCheck,
  RefreshCw,
  X,
} from 'lucide-react';
import { useLab } from '../../context/LabContext';

interface SidebarProps {
  onOpenLabControls: () => void;
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  onOpenLabControls,
  mobileOpen = false,
  onCloseMobile,
}) => {
  const { tickets, assets, agentOnline, activeFaults, refreshing } = useLab();

  const activeIncidentsCount = tickets.filter(
    (t) => t.status === 'open' || t.status === 'investigating' || t.status === 'pending_technician' || t.status === 'pending_approval'
  ).length;

  const totalFaultsCount = Object.values(activeFaults).reduce((sum, f) => sum + f.length, 0);

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-brand-500/50 ${
      isActive
        ? 'bg-brand-600/20 text-brand-300 border border-brand-500/30 font-semibold'
        : 'text-slate-300 hover:text-white hover:bg-surface-elevated/70 border border-transparent'
    }`;

  const sidebarContent = (
    <aside className="w-64 bg-surface border-r border-surface-border flex flex-col h-full shrink-0 select-none">
      {/* Brand header */}
      <div className="h-16 px-5 border-b border-surface-border flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand-600/20 border border-brand-500/40 flex items-center justify-center text-brand-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold tracking-wider text-slate-100 flex items-center gap-1.5">
              <span>EG SUPPORT</span>
              <span className="text-[10px] px-1.5 py-0.5 bg-brand-500/20 text-brand-400 rounded font-mono font-normal">NOC</span>
            </div>
            <div className="text-[11px] text-slate-400 font-mono">CCTV & AI Operations</div>
          </div>
        </div>
        {onCloseMobile && (
          <button
            onClick={onCloseMobile}
            aria-label="Close mobile menu"
            className="md:hidden p-1.5 rounded text-slate-400 hover:text-white hover:bg-surface-elevated"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Nav items */}
      <div className="flex-1 px-3 py-4 space-y-6 overflow-y-auto">
        <div>
          <div className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Overview
          </div>
          <NavLink to="/" end className={navClass} onClick={onCloseMobile}>
            <LayoutDashboard className="w-4 h-4" />
            <span>Dashboard</span>
          </NavLink>
        </div>

        <div>
          <div className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Operations
          </div>
          <div className="space-y-1">
            <NavLink to="/incidents" className={navClass} onClick={onCloseMobile}>
              <AlertOctagon className="w-4 h-4" />
              <span className="flex-1">Incidents</span>
              {activeIncidentsCount > 0 && (
                <span className="px-1.5 py-0.5 text-xs font-mono rounded bg-rose-950/90 text-rose-200 border border-rose-700/60 font-semibold">
                  {activeIncidentsCount}
                </span>
              )}
            </NavLink>
            <NavLink to="/sites" className={navClass} onClick={onCloseMobile}>
              <Network className="w-4 h-4" />
              <span>Sites</span>
            </NavLink>
            <NavLink to="/devices" className={navClass} onClick={onCloseMobile}>
              <Cpu className="w-4 h-4" />
              <span className="flex-1">Devices</span>
              <span className="text-xs font-mono text-slate-400">{assets.length}</span>
            </NavLink>
          </div>
        </div>

        <div>
          <div className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Intelligence
          </div>
          <div className="space-y-1">
            <NavLink to="/assistant" className={navClass} onClick={onCloseMobile}>
              <Bot className="w-4 h-4 text-brand-400" />
              <span className="flex-1">AI Assistant</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 ring-2 ring-emerald-400/30" />
            </NavLink>
            <NavLink to="/knowledge" className={navClass} onClick={onCloseMobile}>
              <BookOpen className="w-4 h-4" />
              <span>Knowledge</span>
            </NavLink>
            <NavLink to="/audit" className={navClass} onClick={onCloseMobile}>
              <ScrollText className="w-4 h-4" />
              <span>Audit Log</span>
            </NavLink>
          </div>
        </div>

        <div>
          <div className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Lab Tools
          </div>
          <button
            onClick={() => {
              onOpenLabControls();
              if (onCloseMobile) onCloseMobile();
            }}
            aria-label="Open Fault Simulator"
            className="w-full flex items-center justify-between px-3 py-2 rounded-md text-sm font-medium text-slate-200 bg-surface-subtle hover:bg-surface-elevated border border-surface-border transition-colors text-left focus-visible:ring-2 focus-visible:ring-amber-500/50"
          >
            <div className="flex items-center gap-2.5">
              <Sliders className="w-4 h-4 text-amber-400" />
              <span>Fault Simulator</span>
            </div>
            {totalFaultsCount > 0 ? (
              <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-amber-950/90 text-amber-200 border border-amber-700/60 font-semibold">
                {totalFaultsCount} active
              </span>
            ) : (
              <span className="text-[10px] font-mono text-slate-400">0 faults</span>
            )}
          </button>
        </div>
      </div>

      {/* System status footer */}
      <div className="p-4 border-t border-surface-border bg-surface-subtle text-xs">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                agentOnline && totalFaultsCount === 0
                  ? 'bg-emerald-400 ring-2 ring-emerald-400/30'
                  : totalFaultsCount > 0
                  ? 'bg-amber-400 ring-2 ring-amber-400/40'
                  : 'bg-rose-400 ring-2 ring-rose-400/30'
              }`}
            />
            <span className="font-medium text-slate-200">
              {totalFaultsCount === 0 && agentOnline
                ? 'All systems healthy'
                : `${totalFaultsCount} active fault${totalFaultsCount === 1 ? '' : 's'}`}
            </span>
          </div>
          {refreshing && <RefreshCw className="w-3 h-3 text-slate-400 animate-spin" />}
        </div>
        <div className="text-[11px] text-slate-400 flex items-center justify-between">
          <span>Agent daemon:</span>
          <span className={`font-mono font-semibold ${agentOnline ? 'text-emerald-400' : 'text-rose-400'}`}>
            {agentOnline ? 'ONLINE' : 'OFFLINE'}
          </span>
        </div>
      </div>
    </aside>
  );

  return (
    <>
      {/* Desktop view */}
      <div className="hidden md:flex h-screen">
        {sidebarContent}
      </div>

      {/* Mobile drawer view */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
            onClick={onCloseMobile}
          />
          <div className="relative z-10 h-full">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};
