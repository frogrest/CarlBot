import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft,
  Camera,
  Server,
  Cpu,
  Bot,
  AlertCircle,
} from 'lucide-react';
import { portalApi, agentApi, helpdeskApi } from '../api';
import type { Asset, CheckResult, Ticket, InvestigationReport } from '../api/types';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Skeleton } from '../components/common/Skeleton';
import { ErrorState } from '../components/common/ErrorState';
import { InvestigationTimeline } from '../components/timeline/InvestigationTimeline';
import { useLab } from '../context/LabContext';

export const DeviceDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { activeFaults, clearFault, refresh: refreshGlobal } = useLab();

  const [asset, setAsset] = useState<Asset | null>(null);
  const [check, setCheck] = useState<CheckResult | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Investigation report state
  const [investigating, setInvestigating] = useState(false);
  const [investigationReport, setInvestigationReport] = useState<InvestigationReport | null>(null);

  const fetchDeviceData = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [assetData, checkData, ticketsData] = await Promise.all([
        portalApi.getAsset(id),
        portalApi.checkAsset(id),
        helpdeskApi.getTickets({ asset_id: id }).catch(() => []),
      ]);
      setAsset(assetData);
      setCheck(checkData);
      setTickets(ticketsData);
    } catch (err: any) {
      setError(err.message || 'Failed to load device');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeviceData();
  }, [id]);

  const handleInvestigate = async () => {
    if (!id) return;
    setInvestigating(true);
    try {
      const report = await agentApi.investigateAsset(id);
      setInvestigationReport(report);
      await fetchDeviceData();
      refreshGlobal();
    } catch (err: any) {
      alert(`Investigation failed: ${err.message}`);
    } finally {
      setInvestigating(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 max-w-5xl mx-auto space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !asset || !check) {
    return (
      <div className="p-6 max-w-3xl mx-auto">
        <button
          onClick={() => navigate('/devices')}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white mb-4"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Devices
        </button>
        <ErrorState
          title="Device Unavailable"
          message={`Failed to retrieve telemetry for ${id}.`}
          error={error}
          onRetry={fetchDeviceData}
        />
      </div>
    );
  }

  const faults = activeFaults[asset.id] || [];
  const isFaulty = faults.length > 0;

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      {/* Back button & Title banner */}
      <div>
        <button
          onClick={() => navigate('/devices')}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Devices
        </button>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-surface border border-surface-border text-brand-400">
              {asset.kind === 'camera' && <Camera className="w-6 h-6" />}
              {asset.kind === 'nvr' && <Server className="w-6 h-6" />}
              {asset.kind === 'ai_box' && <Cpu className="w-6 h-6" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold font-mono text-slate-100">{asset.id}</h2>
                <span className="text-xs uppercase font-mono px-2 py-0.5 rounded bg-surface-elevated text-slate-300 border border-surface-border">
                  {asset.kind}
                </span>
                <Badge status={isFaulty ? 'critical' : 'healthy'} />
              </div>
              <div className="text-sm text-slate-300 font-medium mt-0.5">{asset.name}</div>
              <div className="text-xs text-slate-400 font-mono mt-1">
                Site: <Link to={`/sites/${asset.site_id}`} className="text-brand-400 hover:underline">{asset.site_id}</Link> • IP: {asset.ip}
              </div>
            </div>
          </div>

          {/* Action Button: AI Investigate */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleInvestigate}
              disabled={investigating}
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-brand-600 hover:bg-brand-500 text-white flex items-center gap-2 shadow-xs transition-colors"
            >
              <Bot className={`w-4 h-4 ${investigating ? 'animate-spin' : ''}`} />
              <span>{investigating ? 'Investigating...' : 'Investigate with AI'}</span>
            </button>

            {isFaulty && (
              <button
                onClick={async () => {
                  await clearFault(asset.id);
                  await fetchDeviceData();
                }}
                className="px-3 py-2 rounded-lg text-xs font-medium bg-surface-elevated hover:bg-surface-hover text-slate-200 border border-surface-border transition-colors"
              >
                Clear Fault
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Active Fault Alert if present */}
      {isFaulty && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-400" />
            <div>
              <span className="font-bold">Active Fault Injected:</span>{' '}
              <span className="font-mono text-white">{faults.join(', ')}</span>
            </div>
          </div>
          <button
            onClick={handleInvestigate}
            className="px-3 py-1.5 text-xs font-semibold rounded bg-rose-900/60 hover:bg-rose-800/70 text-white border border-rose-700/60"
          >
            Run Diagnostic
          </button>
        </div>
      )}

      {/* Subsystems Telemetry Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Network Subsystem */}
        <div className="panel p-4 space-y-3">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Network Telemetry
          </div>
          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between items-center p-2 rounded bg-surface-subtle">
              <span className="text-slate-400">Ping ICMP:</span>
              <span className={check.ping ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                {check.ping ? 'PASS' : 'FAIL'}
              </span>
            </div>
            {asset.kind === 'camera' && (
              <div className="flex justify-between items-center p-2 rounded bg-surface-subtle">
                <span className="text-slate-400">TCP Port 554:</span>
                <span className={check.tcp554 ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                  {check.tcp554 ? 'PASS' : 'FAIL'}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Video / Service Subsystem */}
        <div className="panel p-4 space-y-3">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Stream & Service
          </div>
          <div className="space-y-2 text-xs font-mono">
            {asset.kind === 'camera' ? (
              <>
                <div className="flex justify-between items-center p-2 rounded bg-surface-subtle">
                  <span className="text-slate-400">RTSP Stream:</span>
                  <span className={check.rtsp === true || check.rtsp === 'up' ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                    {check.rtsp === true || check.rtsp === 'up' ? 'UP' : 'DOWN'}
                  </span>
                </div>
                <div className="flex justify-between items-center p-2 rounded bg-surface-subtle">
                  <span className="text-slate-400">Credentials Auth:</span>
                  <span className={check.rtsp_auth !== false ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                    {check.rtsp_auth !== false ? 'PASS' : 'FAIL'}
                  </span>
                </div>
              </>
            ) : asset.kind === 'ai_box' ? (
              <>
                <div className="flex justify-between items-center p-2 rounded bg-surface-subtle">
                  <span className="text-slate-400">Detection Service:</span>
                  <span className={check.service === 'up' ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                    {check.service || 'up'}
                  </span>
                </div>
                <div className="flex justify-between items-center p-2 rounded bg-surface-subtle">
                  <span className="text-slate-400">Cloud Sync:</span>
                  <span className={check.cloud_sync === 'up' ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                    {check.cloud_sync || 'up'}
                  </span>
                </div>
              </>
            ) : (
              <div className="flex justify-between items-center p-2 rounded bg-surface-subtle">
                <span className="text-slate-400">NVR Daemon:</span>
                <span className="text-emerald-400 font-semibold">RUNNING</span>
              </div>
            )}
          </div>
        </div>

        {/* Power & Hardware Resource Subsystem */}
        <div className="panel p-4 space-y-3">
          <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
            Hardware & Power
          </div>
          <div className="space-y-2 text-xs font-mono">
            {asset.kind === 'camera' && (
              <div className="flex justify-between items-center p-2 rounded bg-surface-subtle">
                <span className="text-slate-400">PoE Power:</span>
                <span className={check.poe !== false ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                  {check.poe !== false ? 'POWERED ON' : 'POWER OFF'}
                </span>
              </div>
            )}
            {asset.kind === 'nvr' && (
              <div className="flex justify-between items-center p-2 rounded bg-surface-subtle">
                <span className="text-slate-400">Storage Used:</span>
                <span className={(check.storage_used || 0) >= 95 ? 'text-rose-400 font-semibold' : 'text-emerald-400 font-semibold'}>
                  {check.storage_used}%
                </span>
              </div>
            )}
            {asset.kind === 'ai_box' && (
              <div className="flex justify-between items-center p-2 rounded bg-surface-subtle">
                <span className="text-slate-400">CPU Load:</span>
                <span className={(check.cpu || 0) >= 90 ? 'text-rose-400 font-semibold' : 'text-emerald-400 font-semibold'}>
                  {check.cpu}%
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Investigation Report Card if triggered */}
      {investigationReport && (
        <Card
          title="On-Demand AI Investigation Report"
          subtitle={`Autonomous evaluation for ${asset.id} executed just now`}
        >
          <div className="space-y-4">
            <div className="p-3.5 rounded-lg bg-surface-subtle border border-surface-border flex items-center justify-between text-xs">
              <div>
                <span className="font-semibold text-slate-300">Diagnosis: </span>
                <span className="font-mono text-brand-300 font-bold">
                  {investigationReport.diagnosis.fault}
                </span>
                <div className="text-slate-400 mt-1">
                  Recommendation: {investigationReport.diagnosis.recommendation}
                </div>
              </div>
              <div className="text-right">
                <div className="font-mono text-xs text-slate-300">
                  Confidence: {(investigationReport.diagnosis.confidence * 100).toFixed(0)}%
                </div>
                <div className="mt-1">
                  <Badge
                    status={
                      investigationReport.diagnosis.safety_class === 'SAFE_REVERSIBLE'
                        ? 'healthy'
                        : 'technician'
                    }
                    label={investigationReport.diagnosis.safety_class}
                  />
                </div>
              </div>
            </div>

            <div>
              <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Investigation Step Timeline
              </div>
              <InvestigationTimeline timeline={investigationReport.timeline} />
            </div>
          </div>
        </Card>
      )}

      {/* Linked Incident History */}
      <Card
        title={`Incident History for ${asset.id} (${tickets.length})`}
        subtitle="Historical support tickets linked to this equipment"
      >
        {tickets.length === 0 ? (
          <div className="p-4 text-center text-xs text-slate-400 font-mono">
            No incident tickets recorded for this device.
          </div>
        ) : (
          <div className="divide-y divide-surface-border/60">
            {tickets.map((t) => (
              <div
                key={t.id}
                onClick={() => navigate(`/incidents/${t.id}`)}
                className="py-3 flex items-center justify-between hover:bg-surface-subtle/50 px-2 rounded cursor-pointer text-xs"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold text-slate-200">{t.id}</span>
                    <Badge status={t.status} />
                  </div>
                  <div className="text-slate-300 mt-0.5">{t.title}</div>
                </div>
                <div className="text-right font-mono text-[11px] text-slate-400">
                  <div>{t.root_cause || '—'}</div>
                  <div>{new Date(t.created_at).toLocaleDateString()}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
};
