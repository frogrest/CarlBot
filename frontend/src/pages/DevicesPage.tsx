import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, Server, Cpu, Search, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useLab } from '../context/LabContext';
import { Badge } from '../components/common/Badge';

export const DevicesPage: React.FC = () => {
  const { assets, activeFaults } = useLab();
  const navigate = useNavigate();

  const [kindFilter, setKindFilter] = useState<string>('ALL');
  const [search, setSearch] = useState<string>('');

  const filteredAssets = assets.filter((a) => {
    if (kindFilter !== 'ALL' && a.kind !== kindFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchId = a.id.toLowerCase().includes(q);
      const matchName = a.name.toLowerCase().includes(q);
      const matchIp = a.ip.toLowerCase().includes(q);
      const matchSite = a.site_id.toLowerCase().includes(q);
      if (!matchId && !matchName && !matchIp && !matchSite) return false;
    }
    return true;
  });

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header filter controls */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by device ID, IP, or site..."
            className="w-full pl-9 pr-4 py-2 text-xs rounded-lg bg-surface border border-surface-border text-slate-200 placeholder-slate-500 focus:outline-hidden focus:border-brand-500"
          />
        </div>

        <div className="flex items-center gap-2">
          {['ALL', 'camera', 'nvr', 'ai_box'].map((k) => (
            <button
              key={k}
              onClick={() => setKindFilter(k)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                kindFilter === k
                  ? 'bg-brand-600/30 text-brand-300 border-brand-500/50'
                  : 'bg-surface border-surface-border text-slate-400 hover:text-slate-200'
              }`}
            >
              {k === 'ALL' ? 'All Kinds' : k === 'camera' ? 'Cameras' : k === 'nvr' ? 'NVRs' : 'AI Boxes'}
            </button>
          ))}
        </div>
      </div>

      {/* Grid of Devices */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredAssets.map((asset) => {
          const faults = activeFaults[asset.id] || [];
          const isFaulty = faults.length > 0;

          return (
            <div
              key={asset.id}
              onClick={() => navigate(`/devices/${asset.id}`)}
              className={`panel p-5 cursor-pointer transition-all hover:border-brand-500/70 ${
                isFaulty ? 'border-rose-900/60 bg-rose-950/10' : ''
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={`p-2.5 rounded-xl border ${
                      asset.kind === 'camera'
                        ? 'bg-sky-950/40 text-sky-400 border-sky-800'
                        : asset.kind === 'nvr'
                        ? 'bg-emerald-950/40 text-emerald-400 border-emerald-800'
                        : 'bg-purple-950/40 text-purple-400 border-purple-800'
                    }`}
                  >
                    {asset.kind === 'camera' && <Camera className="w-5 h-5" />}
                    {asset.kind === 'nvr' && <Server className="w-5 h-5" />}
                    {asset.kind === 'ai_box' && <Cpu className="w-5 h-5" />}
                  </div>

                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-slate-100">{asset.id}</span>
                      <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-surface-elevated text-slate-400 border border-surface-border">
                        {asset.kind}
                      </span>
                    </div>
                    <div className="text-xs text-slate-300 font-medium mt-0.5">{asset.name}</div>
                  </div>
                </div>

                <Badge status={isFaulty ? 'critical' : 'healthy'} />
              </div>

              {/* Specs & IP */}
              <div className="mt-4 pt-3 border-t border-surface-border/60 flex items-center justify-between text-xs font-mono text-slate-400">
                <span>Site: {asset.site_id}</span>
                <span>IP: {asset.ip}</span>
              </div>

              {/* Active Fault Alert */}
              {isFaulty ? (
                <div className="mt-3 p-2 rounded bg-rose-950/60 border border-rose-800 text-[11px] font-mono text-rose-300 flex items-center gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span className="truncate">Active Fault: {faults.join(', ')}</span>
                </div>
              ) : (
                <div className="mt-3 text-[11px] font-mono text-emerald-400 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Subsystem telemetry healthy</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
