import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Cpu,
  AlertTriangle,
  Play,
  ArrowRight,
  Camera,
  Server,
  Cloud,
  Wrench,
  Bot,
  ShieldCheck,
  Video,
  Terminal,
} from 'lucide-react';
import { useLab } from '../context/LabContext';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { EmptyState } from '../components/common/EmptyState';

export const DashboardPage: React.FC = () => {
  const { assets, tickets, agentState, activeFaults, triggerAgentCycle } = useLab();
  const navigate = useNavigate();

  // Metrics calculation
  const totalDevices = assets.length;
  const faultyDeviceIds = Object.keys(activeFaults).filter((k) => activeFaults[k].length > 0);
  const healthyCount = totalDevices - faultyDeviceIds.length;
  const healthyPct = totalDevices > 0 ? Math.round((healthyCount / totalDevices) * 100) : 100;

  const activeIncidents = tickets.filter(
    (t) => t.status === 'open' || t.status === 'investigating' || t.status === 'pending_technician' || t.status === 'pending_approval'
  );

  const technicianRequiredTickets = tickets.filter(
    (t) => t.status === 'pending_technician' || t.status === 'pending_approval'
  );

  const cameras = assets.filter((a) => a.kind === 'camera');
  const nvrs = assets.filter((a) => a.kind === 'nvr');
  const aiBoxes = assets.filter((a) => a.kind === 'ai_box');

  const camerasHealthy = cameras.filter((c) => !activeFaults[c.id]?.length).length;
  const nvrsHealthy = nvrs.filter((n) => !activeFaults[n.id]?.length).length;
  const aiBoxesHealthy = aiBoxes.filter((a) => !activeFaults[a.id]?.length).length;

  return (
    <div className="p-4 md:p-6 space-y-6 max-w-7xl mx-auto">
      {/* 4 Metric Cards (NOC KPI Deck) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="panel p-4 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Total Monitored</div>
            <div className="text-2xl font-bold font-mono text-slate-100 mt-1">{totalDevices}</div>
            <div className="text-[11px] text-slate-400 mt-1 font-mono">
              {cameras.length} CAM • {nvrs.length} NVR • {aiBoxes.length} AI
            </div>
          </div>
          <div className="p-3 rounded-lg bg-surface-elevated text-sky-400 border border-surface-border">
            <Cpu className="w-5 h-5" />
          </div>
        </div>

        <div className="panel p-4 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Active Incidents</div>
            <div className={`text-2xl font-bold font-mono mt-1 ${activeIncidents.length > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
              {activeIncidents.length}
            </div>
            <div className="text-[11px] text-slate-400 mt-1 font-mono">
              {activeIncidents.length === 0 ? 'Normal operations' : `${activeIncidents.length} active tickets`}
            </div>
          </div>
          <div className={`p-3 rounded-lg border ${activeIncidents.length > 0 ? 'bg-amber-950/80 text-amber-300 border-amber-700/60' : 'bg-emerald-950/80 text-emerald-300 border-emerald-700/60'}`}>
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>

        <div className="panel p-4 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Technician Required</div>
            <div className={`text-2xl font-bold font-mono mt-1 ${technicianRequiredTickets.length > 0 ? 'text-orange-400' : 'text-slate-200'}`}>
              {technicianRequiredTickets.length}
            </div>
            <div className="text-[11px] text-slate-400 mt-1 font-mono">Hardware / Approval action</div>
          </div>
          <div className={`p-3 rounded-lg border ${technicianRequiredTickets.length > 0 ? 'bg-orange-950/80 text-orange-300 border-orange-700/60' : 'bg-surface-elevated text-slate-400 border-surface-border'}`}>
            <Wrench className="w-5 h-5" />
          </div>
        </div>

        <div className="panel p-4 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Fleet Health</div>
            <div className={`text-2xl font-bold font-mono mt-1 ${healthyPct < 100 ? 'text-amber-400' : 'text-emerald-400'}`}>
              {healthyPct}%
            </div>
            <div className="text-[11px] text-slate-400 mt-1 font-mono">{healthyCount} of {totalDevices} operational</div>
          </div>
          <div className={`p-3 rounded-lg border ${healthyPct < 100 ? 'bg-amber-950/80 text-amber-300 border-amber-700/60' : 'bg-emerald-950/80 text-emerald-300 border-emerald-700/60'}`}>
            <ShieldCheck className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* CCTV Live Matrix Preview Wall */}
      <Card
        title="Live CCTV Telemetry & Stream Matrix"
        subtitle="Simulated real-time camera viewports with live RTSP telemetry and bitrate monitoring"
        action={
          <Link
            to="/devices"
            className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 font-medium focus-visible:outline-none"
          >
            <span>View all cameras</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        }
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {cameras.slice(0, 4).map((cam) => {
            const faults = activeFaults[cam.id] || [];
            const hasFault = faults.length > 0;
            return (
              <div
                key={cam.id}
                onClick={() => navigate(`/devices/${cam.id}`)}
                className={`group rounded-lg border p-3 bg-surface-subtle hover:bg-surface-elevated cursor-pointer transition-all ${
                  hasFault ? 'border-rose-700/70' : 'border-surface-border hover:border-brand-500/50'
                }`}
              >
                {/* Simulated Camera Viewport Frame */}
                <div className="relative aspect-video rounded bg-black/80 border border-surface-border overflow-hidden flex flex-col justify-between p-2">
                  {/* Top Bar: Rec beacon and ID */}
                  <div className="flex items-center justify-between text-[10px] font-mono text-slate-300 z-10">
                    <div className="flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${hasFault ? 'bg-rose-500' : 'bg-emerald-400'}`} />
                      <span className="font-bold text-slate-100">{cam.id}</span>
                    </div>
                    <span className="text-[9px] px-1 py-0.5 rounded bg-surface-elevated/80 text-slate-300 border border-slate-700/50">
                      {hasFault ? 'FAULT' : 'LIVE'}
                    </span>
                  </div>

                  {/* Center: Stream graphics simulation */}
                  <div className="flex-1 flex flex-col items-center justify-center text-slate-500 group-hover:text-slate-400 transition-colors">
                    <Video className="w-6 h-6 mb-1 opacity-70" />
                    <span className="text-[10px] font-mono text-slate-400 truncate max-w-[140px]">{cam.name}</span>
                  </div>

                  {/* Bottom Bar: Telemetry Overlay */}
                  <div className="flex items-center justify-between text-[9px] font-mono text-slate-400 border-t border-slate-800/80 pt-1 z-10">
                    <span>1080p @ 25fps</span>
                    <span className={hasFault ? 'text-rose-300' : 'text-slate-300'}>
                      {hasFault ? faults[0] : 'RTSP: OK'}
                    </span>
                  </div>
                </div>

                {/* Camera metadata footer */}
                <div className="mt-2.5 flex items-center justify-between text-xs">
                  <div>
                    <div className="text-[11px] font-mono text-slate-300">{cam.ip}</div>
                    <div className="text-[10px] text-slate-400">{cam.site_id}</div>
                  </div>
                  <Badge status={hasFault ? 'critical' : 'healthy'} />
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Main Grid: Active Incidents Table & System Subsystems */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Active Incidents */}
        <div className="lg:col-span-2 space-y-6">
          <Card
            title="Active Operational Incidents"
            subtitle="Real-time incidents being monitored or investigated by the AI agent"
            action={
              <Link
                to="/incidents"
                className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1 font-medium focus-visible:outline-none"
              >
                <span>View all tickets</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            }
          >
            {activeIncidents.length === 0 ? (
              <EmptyState
                title="No active incidents"
                description="All monitored cameras, NVRs, and AI boxes are currently operating within parameters."
                action={
                  <button
                    onClick={() => triggerAgentCycle()}
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium bg-surface-elevated hover:bg-surface-hover text-slate-200 border border-surface-borderLight transition-colors focus-visible:ring-2 focus-visible:ring-brand-500/50"
                  >
                    <Play className="w-3.5 h-3.5 fill-current text-brand-400" />
                    <span>Run Health Verification</span>
                  </button>
                }
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-surface-border text-slate-400 font-mono uppercase text-[10px]">
                    <tr>
                      <th className="pb-3 font-semibold">Incident</th>
                      <th className="pb-3 font-semibold">Site</th>
                      <th className="pb-3 font-semibold">Device</th>
                      <th className="pb-3 font-semibold">Status</th>
                      <th className="pb-3 font-semibold">AI Diagnosis</th>
                      <th className="pb-3 font-semibold text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border/60">
                    {activeIncidents.map((t) => (
                      <tr
                        key={t.id}
                        className="hover:bg-surface-elevated/40 cursor-pointer transition-colors"
                        onClick={() => navigate(`/incidents/${t.id}`)}
                      >
                        <td className="py-3">
                          <span className="font-mono font-semibold text-slate-200">{t.id}</span>
                          <div className="text-[11px] text-slate-400 truncate max-w-[200px]">{t.title}</div>
                        </td>
                        <td className="py-3 font-mono text-slate-300">{t.site_id}</td>
                        <td className="py-3 font-mono text-brand-300 font-semibold">{t.asset_id || '—'}</td>
                        <td className="py-3">
                          <Badge status={t.status} />
                        </td>
                        <td className="py-3">
                          <span className="font-mono text-[11px] text-amber-300">
                            {t.root_cause || 'Investigating...'}
                          </span>
                        </td>
                        <td className="py-3 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/incidents/${t.id}`);
                            }}
                            className="px-2.5 py-1 text-[11px] font-medium rounded bg-surface-elevated hover:bg-surface-hover border border-surface-border text-slate-200 transition-colors focus-visible:ring-2 focus-visible:ring-brand-500/50"
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          {/* Recent AI Agent Activity */}
          <Card
            title="Recent AI Support Activity"
            subtitle="Autonomous actions executed or escalated by the agent daemon"
            action={
              <Link to="/audit" className="text-xs text-brand-400 hover:text-brand-300 font-medium flex items-center gap-1 focus-visible:outline-none">
                <span>View audit trail</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            }
          >
            {(!agentState || agentState.history.length === 0) ? (
              <div className="p-4 text-center text-xs text-slate-400 font-mono">
                No recent agent events recorded in this session.
              </div>
            ) : (
              <div className="space-y-3 font-mono text-xs">
                {agentState.history.slice(-5).reverse().map((hist, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-surface-subtle border border-surface-border flex items-center justify-between gap-3"
                  >
                    <div className="flex items-center gap-2.5">
                      <Bot className="w-4 h-4 text-brand-400 shrink-0" />
                      <div>
                        <div className="text-slate-200">
                          <span className="font-bold text-brand-300">{hist.asset_id}</span> • {hist.fault || hist.event || 'diagnostic_cycle'}
                        </div>
                        {hist.verification && (
                          <div className="text-[11px] text-slate-400">{hist.verification}</div>
                        )}
                      </div>
                    </div>
                    <div className="text-[10px] text-slate-400 shrink-0">
                      {new Date(hist.at).toLocaleTimeString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Right 1 Col: Subsystem Health & Quick Actions */}
        <div className="space-y-6">
          {/* Subsystem Overview */}
          <Card title="Infrastructure Subsystems" subtitle="Telemetry status by hardware kind">
            <div className="space-y-3">
              <div className="p-3 rounded-lg bg-surface-subtle border border-surface-border flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded bg-sky-950/80 text-sky-300 border border-sky-700/60">
                    <Camera className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-slate-200">IP Cameras</div>
                    <div className="text-[11px] text-slate-400 font-mono">{camerasHealthy} / {cameras.length} operational</div>
                  </div>
                </div>
                <Badge status={camerasHealthy === cameras.length ? 'healthy' : 'warning'} />
              </div>

              <div className="p-3 rounded-lg bg-surface-subtle border border-surface-border flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-700/60">
                    <Server className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-slate-200">NVR Storage</div>
                    <div className="text-[11px] text-slate-400 font-mono">{nvrsHealthy} / {nvrs.length} operational</div>
                  </div>
                </div>
                <Badge status={nvrsHealthy === nvrs.length ? 'healthy' : 'warning'} />
              </div>

              <div className="p-3 rounded-lg bg-surface-subtle border border-surface-border flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded bg-purple-950/80 text-purple-300 border border-purple-700/60">
                    <Cpu className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-slate-200">AI Detection Boxes</div>
                    <div className="text-[11px] text-slate-400 font-mono">{aiBoxesHealthy} / {aiBoxes.length} operational</div>
                  </div>
                </div>
                <Badge status={aiBoxesHealthy === aiBoxes.length ? 'healthy' : 'warning'} />
              </div>

              <div className="p-3 rounded-lg bg-surface-subtle border border-surface-border flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded bg-blue-950/80 text-blue-300 border border-blue-700/60">
                    <Cloud className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-slate-200">Cloud Sync & Archive</div>
                    <div className="text-[11px] text-slate-400 font-mono">Surveillance Uplink</div>
                  </div>
                </div>
                <Badge status="healthy" label="Online" />
              </div>
            </div>
          </Card>

          {/* AI Support Assistant Quick Dispatch */}
          <div className="panel p-5 bg-surface-elevated border border-surface-borderLight space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-brand-300 font-semibold text-xs uppercase tracking-wider">
                <Bot className="w-4 h-4 text-brand-400" />
                <span>AI Support Assistant</span>
              </div>
              <span className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-300 bg-emerald-950/80 px-2 py-0.5 rounded border border-emerald-700/60">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                Ready
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Investigate any camera feed or outage conversationally. Review live hypotheses and non-destructive automated actions.
            </p>
            <div className="space-y-1.5 pt-1">
              <div className="text-[10px] font-mono uppercase text-slate-400 flex items-center gap-1">
                <Terminal className="w-3 h-3 text-slate-400" />
                <span>Quick Dispatch Commands:</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {['/investigate CAM-001', '/status', '/site HQ-MAIN'].map((cmd) => (
                  <Link
                    key={cmd}
                    to="/assistant"
                    className="px-2 py-1 rounded bg-surface-subtle border border-surface-border text-[11px] font-mono text-brand-300 hover:bg-surface hover:text-white transition-colors"
                  >
                    {cmd}
                  </Link>
                ))}
              </div>
            </div>
            <div className="pt-2">
              <Link
                to="/assistant"
                className="w-full inline-flex items-center justify-center gap-2 py-2 px-3 rounded-md text-xs font-semibold bg-brand-600 hover:bg-brand-500 text-white transition-colors focus-visible:ring-2 focus-visible:ring-brand-400"
              >
                <span>Open Assistant Console</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
