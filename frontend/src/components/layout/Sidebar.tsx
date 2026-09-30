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
} from 'lucide-react';
import { useLab } from '../../context/LabContext';

interface SidebarProps {
  onOpenLabControls: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onOpenLabControls }) => {
  const { tickets, assets, agentOnline, activeFaults, refreshing } = useLab();

  const activeIncidentsCount = tickets.filter(
    (t) => t.status === 'open' || t.status === 'investigating' || t.status === 'pending_technician' || t.status === 'pending_approval'
  ).length;

  const totalFaultsCount = Object.values(activeFaults).reduce((sum, f) => sum + f.length, 0);

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? 'bg-brand-600/20 text-brand-400 border border-brand-500/30 font-semibold'
        : 'text-slate-400 hover:text-slate-200 hover:bg-surface-elevated/70'
    }`;

  return (
    <aside className="w-64 bg-surface border-r border-surface-border flex flex-col h-screen shrink-0 select-none">
      {/* Brand header */}
      <div className="h-16 px-5 border-b border-surface-border flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand-600/20 border border-brand-500/40 flex items-center justify-center text-brand-400">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="text-sm font-bold tracking-wider text-slate-100 flex items-center gap-1.5">
              <span>EG SUPPORT</span>
              <span className="text-[10px] px-1.5 py-0.2 bg-brand-500/20 text-brand-400 rounded font-mono font-normal">NOC</span>
            </div>
            <div className="text-[11px] text-slate-400 font-mono">CCTV & AI Operations</div>
          </div>
        </div>
      </div>

      {/* Nav items */}
      <div className="flex-1 px-3 py-4 space-y-6 overflow-y-auto">
        <div>
          <div className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Overview
          </div>
          <NavLink to="/" end className={navClass}>
            <LayoutDashboard className="w-4 h-4" />
            <span>Dashboard</span>
          </NavLink>
        </div>

        <div>
          <div className="px-3 mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Operations
          </div>
          <div className="space-y-1">
            <NavLink to="/incidents" className={navClass}>
              <AlertOctagon className="w-4 h-4" />
              <span className="flex-1">Incidents</span>
              {activeIncidentsCount > 0 && (
                <span className="px-1.5 py-0.5 text-xs font-mono rounded bg-rose-950 text-rose-300 border border-rose-800">
                  {activeIncidentsCount}
                </span>
              )}
            </NavLink>
            <NavLink to="/sites" className={navClass}>
              <Network className="w-4 h-4" />
              <span>Sites</span>
            </NavLink>
            <NavLink to="/devices" className={navClass}>
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
            <NavLink to="/assistant" className={navClass}>
              <Bot className="w-4 h-4 text-brand-400" />
              <span className="flex-1">AI Assistant</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            </NavLink>
            <NavLink to="/knowledge" className={navClass}>
              <BookOpen className="w-4 h-4" />
              <span>Knowledge</span>
            </NavLink>
            <NavLink to="/audit" className={navClass}>
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
            onClick={onOpenLabControls}
            className="w-full flex items-center justify-between px-3 py-2 rounded-md text-sm font-medium text-slate-300 bg-surface-subtle hover:bg-surface-elevated border border-surface-border transition-colors text-left"
          >
            <div className="flex items-center gap-2.5">
              <Sliders className="w-4 h-4 text-amber-400" />
              <span>Fault Simulator</span>
            </div>
            {totalFaultsCount > 0 ? (
              <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-amber-950 text-amber-300 border border-amber-800">
                {totalFaultsCount} active
              </span>
            ) : (
              <span className="text-[10px] font-mono text-slate-400">0 faults</span>
            )}
          </button>
        </div>
      </div>

      {/* System status footer */}
      <div className="p-4 border-t border-surface-border bg-surface-subtle/70 text-xs">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                agentOnline && totalFaultsCount === 0
                  ? 'bg-emerald-400'
                  : totalFaultsCount > 0
                  ? 'bg-amber-400 animate-ping'
                  : 'bg-rose-400'
              }`}
            />
            <span className="font-medium text-slate-300">
              {totalFaultsCount === 0 && agentOnline
                ? 'All systems healthy'
                : `${totalFaultsCount} active fault${totalFaultsCount === 1 ? '' : 's'}`}
            </span>
          </div>
          {refreshing && <RefreshCw className="w-3 h-3 text-slate-400 animate-spin" />}
        </div>
        <div className="text-[11px] text-slate-400 flex items-center justify-between">
          <span>Agent daemon:</span>
          <span className={`font-mono ${agentOnline ? 'text-emerald-400' : 'text-rose-400'}`}>
            {agentOnline ? 'ONLINE' : 'OFFLINE'}
          </span>
        </div>
      </div>
    </aside>
  );
};
