import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Network, MapPin, ArrowRight, ShieldCheck, AlertTriangle } from 'lucide-react';
import { portalApi } from '../api';
import type { Site, SiteHealth } from '../api/types';
import { Badge } from '../components/common/Badge';
import { Skeleton } from '../components/common/Skeleton';
import { useLab } from '../context/LabContext';

export const SitesPage: React.FC = () => {
  const navigate = useNavigate();
  const { assets } = useLab();

  const [sites, setSites] = useState<Site[]>([]);
  const [siteHealthMap, setSiteHealthMap] = useState<Record<string, SiteHealth>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSites = async () => {
      setLoading(true);
      try {
        const sList = await portalApi.getSites();
        setSites(sList);

        const healths = await Promise.all(
          sList.map((s) => portalApi.getSiteHealth(s.id).catch(() => null))
        );
        const map: Record<string, SiteHealth> = {};
        healths.forEach((h) => {
          if (h) map[h.site_id] = h;
        });
        setSiteHealthMap(map);
      } catch (err) {
        console.error('Failed to load sites:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchSites();
  }, []);

  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div>
        <h2 className="text-base font-bold text-slate-100">Operational Facilities & Sites</h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Monitoring {sites.length} operational surveillance zones across facilities
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {sites.map((site) => {
          const health = siteHealthMap[site.id];
          const siteAssets = assets.filter((a) => a.site_id === site.id);
          const hasIssues = health && health.issues.length > 0;

          return (
            <div
              key={site.id}
              onClick={() => navigate(`/sites/${site.id}`)}
              className={`panel p-5 cursor-pointer transition-all hover:border-brand-500/70 space-y-4 ${
                hasIssues ? 'border-amber-900/60 bg-amber-950/10' : ''
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-surface-elevated text-brand-400 border border-surface-border">
                    <Network className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="font-mono text-xs font-bold text-slate-100">{site.id}</span>
                    <h3 className="text-sm font-semibold text-slate-200 mt-0.5">{site.name}</h3>
                  </div>
                </div>

                <Badge status={hasIssues ? 'warning' : 'healthy'} />
              </div>

              <div className="text-xs text-slate-400 flex items-center gap-1.5 font-mono">
                <MapPin className="w-3.5 h-3.5 text-slate-500" />
                <span>{site.location}</span>
              </div>

              {/* Stats */}
              <div className="p-3 rounded-lg bg-surface-subtle border border-surface-border grid grid-cols-3 gap-2 text-center text-xs font-mono">
                <div>
                  <div className="text-[10px] uppercase text-slate-400">Total</div>
                  <div className="text-sm font-bold text-slate-200">{health?.total_assets || siteAssets.length}</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase text-slate-400">Reachable</div>
                  <div className="text-sm font-bold text-emerald-400">{health?.reachable_assets || 0}</div>
                </div>
                <div>
                  <div className="text-[10px] uppercase text-slate-400">Healthy</div>
                  <div className="text-sm font-bold text-sky-400">{health?.healthy_assets || 0}</div>
                </div>
              </div>

              {/* Active issues or clean indicator */}
              {hasIssues ? (
                <div className="text-[11px] font-mono text-amber-300 bg-amber-950/40 p-2 rounded border border-amber-900/60 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                  <span className="truncate">{health?.issues.length} active issue(s) detected</span>
                </div>
              ) : (
                <div className="text-[11px] font-mono text-emerald-400 flex items-center gap-1.5">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>All site endpoints operational</span>
                </div>
              )}

              <div className="pt-2 flex justify-end">
                <span className="text-xs text-brand-400 hover:text-brand-300 font-medium flex items-center gap-1">
                  <span>Inspect Site Topology</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
