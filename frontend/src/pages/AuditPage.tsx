import React, { useState, useEffect } from 'react';
import { ScrollText, RefreshCw } from 'lucide-react';
import { portalApi, agentApi } from '../api';
import type { ActionLogEntry, FaultHistoryEntry, AgentHistoryEntry } from '../api/types';
import { Card } from '../components/common/Card';
import { PolicyBadge } from '../components/common/PolicyBadge';
import { Skeleton } from '../components/common/Skeleton';
import { EmptyState } from '../components/common/EmptyState';

export const AuditPage: React.FC = () => {
  const [actionLog, setActionLog] = useState<ActionLogEntry[]>([]);
  const [faultHistory, setFaultHistory] = useState<FaultHistoryEntry[]>([]);
  const [agentHistory, setAgentHistory] = useState<AgentHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'actions' | 'faults' | 'agent'>('actions');

  const fetchAuditData = async () => {
    setLoading(true);
    try {
      const [actions, faults, state] = await Promise.all([
        portalApi.getActionLog().catch(() => []),
        portalApi.getFaultHistory().catch(() => []),
        agentApi.getState().catch(() => ({ history: [] })),
      ]);
      setActionLog(actions);
      setFaultHistory(faults);
      setAgentHistory(state?.history || []);
    } catch (err) {
      console.error('Failed to load audit data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditData();
  }, []);

  const getPolicyForAction = (action: string) => {
    const safeActions = ['reconnect_stream', 'restart_service', 'retry_upload', 'clear_transient'];
    const approvalActions = ['credential_change', 'network_change', 'nvr_reboot', 'configuration_change'];
    if (safeActions.includes(action)) return 'SAFE_REVERSIBLE';
    if (approvalActions.includes(action)) return 'APPROVAL_REQUIRED';
    return 'HUMAN_ONLY';
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header and Refresh */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <ScrollText className="w-5 h-5 text-brand-400" />
            Operations Audit Log & Policy Traceability
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Cryptographically immutable record of autonomous agent operations and hardware telemetry changes
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchAuditData}
            className="p-2 rounded-lg bg-surface border border-surface-border text-slate-300 hover:text-white"
            title="Refresh Audit Log"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-surface-border pb-2 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('actions')}
          className={`px-3 py-1.5 rounded-lg transition-colors ${
            activeTab === 'actions'
              ? 'bg-brand-600/30 text-brand-300 border border-brand-500/50'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Automated Actions ({actionLog.length})
        </button>
        <button
          onClick={() => setActiveTab('agent')}
          className={`px-3 py-1.5 rounded-lg transition-colors ${
            activeTab === 'agent'
              ? 'bg-brand-600/30 text-brand-300 border border-brand-500/50'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Agent Cycle Events ({agentHistory.length})
        </button>
        <button
          onClick={() => setActiveTab('faults')}
          className={`px-3 py-1.5 rounded-lg transition-colors ${
            activeTab === 'faults'
              ? 'bg-brand-600/30 text-brand-300 border border-brand-500/50'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Fault Injections ({faultHistory.length})
        </button>
      </div>

      {/* Table Content */}
      <Card
        title={
          activeTab === 'actions'
            ? 'Execution Audit Trail'
            : activeTab === 'agent'
            ? 'Agent Autonomous Cycle Log'
            : 'Simulated Fault Injection Log'
        }
        subtitle="Auditable timeline ensuring zero unauthorized changes to hardware"
      >
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-full" />
            <Skeleton className="h-6 w-full" />
          </div>
        ) : activeTab === 'actions' ? (
          actionLog.length === 0 ? (
            <EmptyState
              title="No automated actions recorded"
              description="Actions performed by the autonomous agent or portal will appear here."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-surface-border text-slate-400 font-mono uppercase text-[10px]">
                  <tr>
                    <th className="pb-3 font-semibold">Timestamp</th>
                    <th className="pb-3 font-semibold">Actor</th>
                    <th className="pb-3 font-semibold">Action</th>
                    <th className="pb-3 font-semibold">Target Resource</th>
                    <th className="pb-3 font-semibold">Result</th>
                    <th className="pb-3 font-semibold">Safety Policy</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border/60 font-mono">
                  {actionLog.slice().reverse().map((log, i) => (
                    <tr key={i} className="hover:bg-surface-elevated/40">
                      <td className="py-3 text-slate-400">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </td>
                      <td className="py-3 text-brand-400 font-semibold">AI Agent</td>
                      <td className="py-3 text-slate-200">{log.action}</td>
                      <td className="py-3 text-amber-300">{log.asset_id}</td>
                      <td className="py-3">
                        <span className="text-emerald-400 font-bold">{log.result.toUpperCase()}</span>
                      </td>
                      <td className="py-3">
                        <PolicyBadge policyClass={getPolicyForAction(log.action)} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : activeTab === 'agent' ? (
          agentHistory.length === 0 ? (
            <EmptyState
              title="No agent history events recorded"
              description="Agent state changes and diagnostic investigations will be listed here."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-surface-border text-slate-400 font-mono uppercase text-[10px]">
                  <tr>
                    <th className="pb-3 font-semibold">Timestamp</th>
                    <th className="pb-3 font-semibold">Resource</th>
                    <th className="pb-3 font-semibold">Event / Diagnosis</th>
                    <th className="pb-3 font-semibold">Ticket Reference</th>
                    <th className="pb-3 font-semibold">Verification Note</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border/60 font-mono">
                  {agentHistory.slice().reverse().map((item, i) => (
                    <tr key={i} className="hover:bg-surface-elevated/40">
                      <td className="py-3 text-slate-400">{new Date(item.at).toLocaleTimeString()}</td>
                      <td className="py-3 text-brand-300 font-bold">{item.asset_id}</td>
                      <td className="py-3 text-slate-200">{item.fault || item.event || 'diagnostic_cycle'}</td>
                      <td className="py-3 text-sky-400">{item.ticket_id || '—'}</td>
                      <td className="py-3 text-slate-400 text-[11px] truncate max-w-xs">{item.verification || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : faultHistory.length === 0 ? (
          <EmptyState
            title="No fault injections recorded"
            description="Hardware and network fault injections will appear here."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-surface-border text-slate-400 font-mono uppercase text-[10px]">
                <tr>
                  <th className="pb-3 font-semibold">Timestamp</th>
                  <th className="pb-3 font-semibold">Event</th>
                  <th className="pb-3 font-semibold">Target Asset</th>
                  <th className="pb-3 font-semibold">Fault Type</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border/60 font-mono">
                {faultHistory.slice().reverse().map((item, i) => (
                  <tr key={i} className="hover:bg-surface-elevated/40">
                    <td className="py-3 text-slate-400">{new Date(item.at).toLocaleTimeString()}</td>
                    <td className="py-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          item.event === 'injected'
                            ? 'bg-rose-950 text-rose-300 border border-rose-800'
                            : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        }`}
                      >
                        {item.event.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 text-brand-300 font-bold">{item.asset_id}</td>
                    <td className="py-3 text-amber-300">{item.fault}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};
