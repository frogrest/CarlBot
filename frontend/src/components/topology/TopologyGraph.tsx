import React from 'react';
import { Router, Server, Camera, Cpu, Cloud, CheckCircle2, AlertCircle, ArrowDown } from 'lucide-react';
import type { Asset } from '../../api/types';

interface TopologyGraphProps {
  siteId: string;
  siteName?: string;
  assets: Asset[];
  activeFaults: Record<string, string[]>;
  onSelectAsset?: (assetId: string) => void;
}

export const TopologyGraph: React.FC<TopologyGraphProps> = ({
  siteId,
  assets,
  activeFaults,
  onSelectAsset,
}) => {
  const siteAssets = assets.filter((a) => a.site_id === siteId);
  const cameras = siteAssets.filter((a) => a.kind === 'camera');
  const nvrs = siteAssets.filter((a) => a.kind === 'nvr');

  const isFaulty = (id: string) => Boolean(activeFaults[id] && activeFaults[id].length > 0);

  const nvrDown = nvrs.some((n) => isFaulty(n.id));
  const multiCameraDown = cameras.filter((c) => isFaulty(c.id)).length > 1;

  return (
    <div className="p-6 bg-surface-subtle rounded-xl border border-surface-border space-y-6">
      {/* Dependency alert if shared node is down */}
      {(nvrDown || multiCameraDown) && (
        <div className="p-3.5 rounded-lg bg-amber-950/40 border border-amber-800/60 text-amber-300 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 shrink-0 text-amber-400" />
          <span>
            {nvrDown
              ? 'Shared Dependency Warning: Upstream NVR is degraded or unavailable. Downstream video feeds and storage are impacted.'
              : 'Shared Outage Correlation: Multiple endpoint cameras at this site are reporting concurrent failures. Inspect upstream PoE switch / gateway.'}
          </span>
        </div>
      )}

      <div className="flex flex-col items-center space-y-4">
        {/* Tier 1: Gateway / Internet Router */}
        <div className="flex flex-col items-center">
          <div className="px-4 py-2.5 rounded-lg bg-surface border border-surface-border shadow-xs flex items-center gap-2.5 min-w-[200px] justify-between">
            <div className="flex items-center gap-2">
              <Router className="w-4 h-4 text-sky-400" />
              <div>
                <div className="text-xs font-semibold text-slate-200">Site Gateway</div>
                <div className="text-[10px] font-mono text-slate-400">10.10.x.1</div>
              </div>
            </div>
            <span className="w-2 h-2 rounded-full bg-emerald-400" title="Gateway Online" />
          </div>
          <ArrowDown className="w-4 h-4 text-slate-600 mt-2" />
        </div>

        {/* Tier 2: NVR Recording Storage Core */}
        <div className="flex flex-col items-center">
          <div className="flex gap-4 justify-center flex-wrap">
            {nvrs.length > 0 ? (
              nvrs.map((nvr) => {
                const faulty = isFaulty(nvr.id);
                return (
                  <div
                    key={nvr.id}
                    onClick={() => onSelectAsset && onSelectAsset(nvr.id)}
                    className={`px-4 py-2.5 rounded-lg border transition-all cursor-pointer min-w-[210px] ${
                      faulty
                        ? 'bg-rose-950/40 border-rose-800 hover:border-rose-600'
                        : 'bg-surface border-surface-border hover:border-brand-500'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Server className={`w-4 h-4 ${faulty ? 'text-rose-400' : 'text-emerald-400'}`} />
                        <div>
                          <div className="text-xs font-semibold text-slate-200">{nvr.name}</div>
                          <div className="text-[10px] font-mono text-slate-400">{nvr.id} • {nvr.ip}</div>
                        </div>
                      </div>
                      <span className={`w-2 h-2 rounded-full ${faulty ? 'bg-rose-400 animate-ping' : 'bg-emerald-400'}`} />
                    </div>
                    {faulty && (
                      <div className="mt-2 text-[10px] font-mono text-rose-300">
                        Active Fault: {activeFaults[nvr.id].join(', ')}
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="px-4 py-2 rounded bg-surface border border-surface-border text-xs text-slate-400 font-mono">
                Central Site Switch (Layer 2)
              </div>
            )}
          </div>
          <ArrowDown className="w-4 h-4 text-slate-600 mt-2" />
        </div>

        {/* Tier 3: Edge Devices (Cameras & AI Boxes) */}
        <div className="w-full">
          <div className="text-[11px] font-mono uppercase text-slate-400 tracking-wider text-center mb-3">
            Connected Edge Endpoints ({siteAssets.length} total)
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {siteAssets.map((asset) => {
              const faulty = isFaulty(asset.id);
              const isCamera = asset.kind === 'camera';
              const isAiBox = asset.kind === 'ai_box';
              const isNvr = asset.kind === 'nvr';

              return (
                <div
                  key={asset.id}
                  onClick={() => onSelectAsset && onSelectAsset(asset.id)}
                  className={`p-3 rounded-lg border transition-all cursor-pointer ${
                    faulty
                      ? 'bg-rose-950/30 border-rose-800/80 hover:border-rose-600'
                      : 'bg-surface border-surface-border hover:border-slate-500'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2 min-w-0">
                      {isCamera && <Camera className={`w-3.5 h-3.5 shrink-0 ${faulty ? 'text-rose-400' : 'text-sky-400'}`} />}
                      {isAiBox && <Cpu className={`w-3.5 h-3.5 shrink-0 ${faulty ? 'text-rose-400' : 'text-purple-400'}`} />}
                      {isNvr && <Server className={`w-3.5 h-3.5 shrink-0 ${faulty ? 'text-rose-400' : 'text-emerald-400'}`} />}
                      <span className="text-xs font-semibold text-slate-200 truncate">{asset.id}</span>
                    </div>
                    <span className={`w-2 h-2 rounded-full shrink-0 ${faulty ? 'bg-rose-400 animate-pulse' : 'bg-emerald-400'}`} />
                  </div>

                  <div className="text-[11px] text-slate-300 truncate">{asset.name}</div>
                  <div className="text-[10px] font-mono text-slate-400 mt-1">{asset.ip}</div>

                  {faulty ? (
                    <div className="mt-2 text-[10px] font-mono text-rose-300 bg-rose-950/70 p-1 rounded border border-rose-900/60 truncate">
                      ! {activeFaults[asset.id].join(', ')}
                    </div>
                  ) : (
                    <div className="mt-2 text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>Operational</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Tier 4: Cloud Uplink */}
        <div className="flex flex-col items-center pt-2">
          <ArrowDown className="w-4 h-4 text-slate-600 mb-2" />
          <div className="px-4 py-2 rounded-lg bg-surface border border-surface-border flex items-center gap-2 text-xs text-slate-300">
            <Cloud className="w-4 h-4 text-brand-400" />
            <span>EG Cloud Synchronization & Surveillance Archive</span>
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
          </div>
        </div>
      </div>
    </div>
  );
};
