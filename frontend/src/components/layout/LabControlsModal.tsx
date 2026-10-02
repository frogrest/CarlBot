import React, { useState } from 'react';
import { X, Sliders, AlertTriangle, ShieldCheck, Play, Trash2, Zap } from 'lucide-react';
import { useLab } from '../../context/LabContext';

interface LabControlsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LabControlsModal: React.FC<LabControlsModalProps> = ({ isOpen, onClose }) => {
  const {
    assets,
    activeFaults,
    supportedFaults,
    injectFault,
    injectSiteFault,
    clearFault,
    clearAllFaults,
    triggerAgentCycle,
  } = useLab();

  const [selectedAsset, setSelectedAsset] = useState<string>('CAM-001');
  const [selectedFault, setSelectedFault] = useState<string>('rtsp_down');
  const [selectedSite, setSelectedSite] = useState<string>('SITE-001');
  const [actionLoading, setActionLoading] = useState(false);
  const [lastInjectedInfo, setLastInjectedInfo] = useState<string | null>(null);

  if (!isOpen) return null;

  const currentAsset = assets.find((a) => a.id === selectedAsset);
  const assetKind = currentAsset?.kind || 'camera';

  // Compatible faults for the selected asset kind
  const compatibleFaults = supportedFaults.filter((f) => {
    if (assetKind === 'camera') {
      return ['rtsp_down', 'rtsp_auth_failure', 'wrong_rtsp_path', 'poe_power_off', 'network_down', 'intermittent_connectivity'].includes(f);
    }
    if (assetKind === 'nvr') {
      return ['storage_full', 'nvr_unavailable', 'network_down'].includes(f);
    }
    if (assetKind === 'ai_box') {
      return ['ai_box_service_failure', 'cloud_sync_failure', 'high_cpu', 'network_down'].includes(f);
    }
    return true;
  });

  const displayFaults = compatibleFaults.length > 0 ? compatibleFaults : supportedFaults;

  const handleAssetChange = (assetId: string) => {
    setSelectedAsset(assetId);
    const targetAsset = assets.find((a) => a.id === assetId);
    const kind = targetAsset?.kind || 'camera';
    if (kind === 'camera' && !['rtsp_down', 'rtsp_auth_failure', 'wrong_rtsp_path', 'poe_power_off', 'network_down', 'intermittent_connectivity'].includes(selectedFault)) {
      setSelectedFault('rtsp_down');
    } else if (kind === 'nvr' && !['storage_full', 'nvr_unavailable', 'network_down'].includes(selectedFault)) {
      setSelectedFault('storage_full');
    } else if (kind === 'ai_box' && !['ai_box_service_failure', 'cloud_sync_failure', 'high_cpu', 'network_down'].includes(selectedFault)) {
      setSelectedFault('ai_box_service_failure');
    }
  };

  const handleInject = async () => {
    if (!selectedAsset || !selectedFault) return;
    setActionLoading(true);
    setLastInjectedInfo(null);
    try {
      await injectFault(selectedAsset, selectedFault);
      if (['rtsp_down', 'ai_box_service_failure', 'cloud_sync_failure', 'intermittent_connectivity'].includes(selectedFault)) {
        setLastInjectedInfo(`Injected ${selectedFault} on ${selectedAsset}. Note: This fault is SAFE_REVERSIBLE — the autonomous agent will diagnose and auto-recover it within 5 seconds.`);
      } else {
        setLastInjectedInfo(`Injected ${selectedFault} on ${selectedAsset}. This fault is HUMAN_ONLY / APPROVAL_REQUIRED — the agent will escalate to a technician.`);
      }
    } finally {
      setActionLoading(false);
    }
  };

  const handleQuickInject = async (assetId: string, fault: string, note?: string) => {
    setActionLoading(true);
    setLastInjectedInfo(null);
    try {
      await injectFault(assetId, fault);
      if (note) {
        setLastInjectedInfo(note);
      }
    } finally {
      setActionLoading(false);
    }
  };

  const handleSiteInject = async () => {
    if (!selectedSite) return;
    setActionLoading(true);
    setLastInjectedInfo(null);
    try {
      await injectSiteFault(selectedSite, 'multi_camera_site_outage');
      setLastInjectedInfo(`Site-wide outage injected across all cameras at ${selectedSite}. The agent correlates this as a site-level gateway failure.`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleClearAll = async () => {
    setActionLoading(true);
    try {
      await clearAllFaults();
    } finally {
      setActionLoading(false);
    }
  };

  const handleRunAgent = async () => {
    setActionLoading(true);
    try {
      await triggerAgentCycle();
    } finally {
      setActionLoading(false);
    }
  };

  const totalActiveFaults = Object.values(activeFaults).reduce((sum, f) => sum + f.length, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs">
      <div className="bg-surface border border-surface-border rounded-xl shadow-modal w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between bg-surface-elevated">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">CCTV Operations Fault Simulator</h2>
              <p className="text-xs text-slate-400">Inject simulated hardware/network faults to observe autonomous AI investigation</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-surface-border transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1">
          {/* Active Faults Overview */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                Active Faults ({totalActiveFaults})
              </span>
              {totalActiveFaults > 0 && (
                <button
                  onClick={handleClearAll}
                  disabled={actionLoading}
                  className="text-xs text-rose-400 hover:text-rose-300 flex items-center gap-1"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Clear All Active Faults
                </button>
              )}
            </div>

            {totalActiveFaults === 0 ? (
              <div className="p-4 rounded-lg bg-emerald-950/20 border border-emerald-900/40 text-emerald-400 text-xs flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 shrink-0" />
                <span>No active faults injected. All 8 assets are running in normal telemetry state.</span>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(activeFaults).map(([assetId, faults]) =>
                  faults.map((fault) => (
                    <div
                      key={`${assetId}-${fault}`}
                      className="p-2.5 rounded bg-surface-subtle border border-surface-border flex items-center justify-between"
                    >
                      <div>
                        <span className="text-xs font-mono font-semibold text-slate-200">{assetId}</span>
                        <div className="text-[11px] font-mono text-amber-400">{fault}</div>
                      </div>
                      <button
                        onClick={() => clearFault(assetId)}
                        disabled={actionLoading}
                        className="px-2.5 py-1 text-[11px] font-medium rounded bg-surface-elevated hover:bg-rose-900/40 text-slate-300 hover:text-rose-200 border border-surface-border hover:border-rose-700/50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500/50"
                      >
                        Clear
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Status Feedback Notice */}
          {lastInjectedInfo && (
            <div className="p-3.5 rounded-lg bg-surface-elevated border border-brand-500/40 text-xs text-slate-200 flex items-start gap-2.5">
              <Zap className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium text-brand-300">Simulator Status</p>
                <p className="text-slate-300 mt-0.5 leading-relaxed">{lastInjectedInfo}</p>
              </div>
            </div>
          )}

          {/* Fault Injection Panel */}
          <div className="p-4 rounded-lg bg-surface-subtle border border-surface-border space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                Targeted Fault Injection
              </h4>
              <span className="text-[10px] font-mono text-slate-400 uppercase">
                {assetKind} mode ({displayFaults.length} compatible faults)
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Target Asset</label>
                <select
                  value={selectedAsset}
                  onChange={(e) => handleAssetChange(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-md bg-surface border border-surface-border text-slate-200 focus:outline-hidden focus:border-brand-500"
                >
                  {assets.map((asset) => (
                    <option key={asset.id} value={asset.id}>
                      {asset.id} — {asset.name} ({asset.kind})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Fault Type</label>
                <select
                  value={selectedFault}
                  onChange={(e) => setSelectedFault(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-md bg-surface border border-surface-border text-slate-200 focus:outline-hidden focus:border-brand-500 font-mono"
                >
                  {displayFaults.map((fault) => (
                    <option key={fault} value={fault}>
                      {fault}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={handleInject}
                disabled={actionLoading}
                className="px-4 py-2 text-xs font-semibold rounded-md bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white transition-colors flex items-center gap-1.5 shadow"
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                {actionLoading ? 'Injecting...' : `Inject Fault on ${selectedAsset}`}
              </button>
            </div>
          </div>

          {/* Quick Scenario Shortcuts */}
          <div className="p-4 rounded-lg bg-surface-subtle border border-surface-border space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Quick Test Scenarios
            </h4>
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() =>
                  handleQuickInject(
                    'CAM-001',
                    'rtsp_down',
                    'Injected rtsp_down on CAM-001. SAFE_REVERSIBLE: Autonomous loop will automatically detect and recover stream within 5 seconds.'
                  )
                }
                disabled={actionLoading}
                className="p-2.5 rounded bg-surface hover:bg-surface-elevated disabled:opacity-50 border border-surface-border text-left"
              >
                <div className="text-xs font-medium text-slate-200">1. Safe RTSP Down</div>
                <div className="text-[10px] text-emerald-400">CAM-001 • Auto-recovers</div>
              </button>

              <button
                onClick={() =>
                  handleQuickInject(
                    'CAM-002',
                    'rtsp_auth_failure',
                    'Injected rtsp_auth_failure on CAM-002. HUMAN_ONLY: Policy engine blocks autonomous action and escalates to technician.'
                  )
                }
                disabled={actionLoading}
                className="p-2.5 rounded bg-surface hover:bg-surface-elevated disabled:opacity-50 border border-surface-border text-left"
              >
                <div className="text-xs font-medium text-slate-200">2. RTSP Auth Failure</div>
                <div className="text-[10px] text-orange-400">CAM-002 • Tech required</div>
              </button>

              <button
                onClick={() =>
                  handleQuickInject(
                    'CAM-003',
                    'poe_power_off',
                    'Injected poe_power_off on CAM-003. HUMAN_ONLY: Physical PoE port check required.'
                  )
                }
                disabled={actionLoading}
                className="p-2.5 rounded bg-surface hover:bg-surface-elevated disabled:opacity-50 border border-surface-border text-left"
              >
                <div className="text-xs font-medium text-slate-200">3. PoE Power Tripped</div>
                <div className="text-[10px] text-rose-400">CAM-003 • Hardware fault</div>
              </button>

              <button
                onClick={() =>
                  handleQuickInject(
                    'AIBOX-001',
                    'ai_box_service_failure',
                    'Injected ai_box_service_failure on AIBOX-001. SAFE_REVERSIBLE: Agent will auto-restart detection service.'
                  )
                }
                disabled={actionLoading}
                className="p-2.5 rounded bg-surface hover:bg-surface-elevated disabled:opacity-50 border border-surface-border text-left"
              >
                <div className="text-xs font-medium text-slate-200">4. AI Box Crash</div>
                <div className="text-[10px] text-emerald-400">AIBOX-001 • Auto-restart</div>
              </button>

              <button
                onClick={() =>
                  handleQuickInject(
                    'NVR-001',
                    'storage_full',
                    'Injected storage_full on NVR-001. APPROVAL_REQUIRED: Technician must review disk retention.'
                  )
                }
                disabled={actionLoading}
                className="p-2.5 rounded bg-surface hover:bg-surface-elevated disabled:opacity-50 border border-surface-border text-left"
              >
                <div className="text-xs font-medium text-slate-200">5. NVR Storage 99%</div>
                <div className="text-[10px] text-orange-400">NVR-001 • Retention review</div>
              </button>

              <div className="p-2.5 rounded bg-surface border border-surface-border text-left flex flex-col justify-between">
                <div>
                  <div className="text-xs font-medium text-slate-200">6. Site-wide Outage</div>
                  <select
                    value={selectedSite}
                    onChange={(e) => setSelectedSite(e.target.value)}
                    className="w-full mt-1 text-[11px] font-mono rounded bg-surface-subtle border border-surface-border text-slate-300"
                  >
                    <option value="SITE-001">SITE-001</option>
                    <option value="SITE-002">SITE-002</option>
                    <option value="SITE-003">SITE-003</option>
                  </select>
                </div>
                <button
                  onClick={handleSiteInject}
                  disabled={actionLoading}
                  className="mt-1 text-[10px] text-rose-400 hover:text-rose-300 disabled:opacity-50 font-semibold text-left"
                >
                  Trigger Outage on {selectedSite} →
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-surface-border bg-surface-elevated flex items-center justify-between">
          <button
            onClick={handleClearAll}
            disabled={actionLoading}
            className="px-3 py-1.5 text-xs font-medium rounded bg-surface border border-surface-border text-slate-300 hover:text-white"
          >
            Clear All Faults
          </button>

          <div className="flex items-center gap-3">
            <button
              onClick={handleRunAgent}
              disabled={actionLoading}
              className="px-4 py-1.5 text-xs font-semibold rounded bg-brand-600 hover:bg-brand-500 text-white flex items-center gap-1.5"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              Trigger AI Investigation Cycle
            </button>
            <button
              onClick={onClose}
              className="px-4 py-1.5 text-xs font-medium rounded bg-surface-subtle hover:bg-surface border border-surface-border text-slate-300"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
