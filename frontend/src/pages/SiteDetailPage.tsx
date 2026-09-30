import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Network, MapPin, Camera, Server, Cpu } from 'lucide-react';
import { portalApi, helpdeskApi } from '../api';
import type { Site, SiteHealth, Ticket } from '../api/types';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Skeleton } from '../components/common/Skeleton';
import { ErrorState } from '../components/common/ErrorState';
import { TopologyGraph } from '../components/topology/TopologyGraph';
import { useLab } from '../context/LabContext';

export const SiteDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { assets, activeFaults } = useLab();

  const [site, setSite] = useState<Site | null>(null);
  const [health, setHealth] = useState<SiteHealth | null>(null);
  const [siteTickets, setSiteTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSite = async () => {
      if (!id) return;
      setLoading(true);
      setError(null);
      try {
        const [sitesList, healthData, ticketsData] = await Promise.all([
          portalApi.getSites(),
          portalApi.getSiteHealth(id),
          helpdeskApi.getTickets({ site_id: id }).catch(() => []),
        ]);

        const currentSite = sitesList.find((s) => s.id === id);
        if (!currentSite) throw new Error(`Site ${id} not found`);

        setSite(currentSite);
        setHealth(healthData);
        setSiteTickets(ticketsData);
      } catch (err: any) {
        setError(err.message || 'Failed to load site details');
      } finally {
        setLoading(false);
      }
    };
    fetchSite();
  }, [id]);

  if (loading) {
    return (
      <div className="p-6 max-w-5xl mx-auto space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (error || !site || !health) {
    return (
      <div className="p-6 max-w-3xl mx-auto">
        <button
          onClick={() => navigate('/sites')}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white mb-4"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Sites
        </button>
        <ErrorState
          title="Site Not Found"
          message={`Could not load site information for ${id}.`}
          error={error}
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }

  const siteAssets = assets.filter((a) => a.site_id === site.id);
  const hasIssues = health.issues.length > 0;

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      {/* Back button & Header */}
      <div>
        <button
          onClick={() => navigate('/sites')}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white mb-3"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Sites
        </button>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-surface border border-surface-border text-brand-400">
              <Network className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xl font-bold text-slate-100">{site.id}</span>
                <Badge status={hasIssues ? 'warning' : 'healthy'} />
              </div>
              <h2 className="text-base font-semibold text-slate-200 mt-0.5">{site.name}</h2>
              <div className="text-xs text-slate-400 flex items-center gap-1.5 font-mono mt-1">
                <MapPin className="w-3.5 h-3.5 text-slate-500" />
                <span>{site.location}</span>
              </div>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-surface border border-surface-border flex items-center gap-4 text-xs font-mono">
            <div>
              <span className="text-slate-400 block text-[10px] uppercase">Reachable</span>
              <span className="font-bold text-emerald-400">{health.reachable_assets}/{health.total_assets}</span>
            </div>
            <div className="border-l border-surface-border pl-4">
              <span className="text-slate-400 block text-[10px] uppercase">Healthy</span>
              <span className="font-bold text-sky-400">{health.healthy_assets}/{health.total_assets}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Network & Infrastructure Topology View */}
      <Card
        title="Infrastructure Topology & Dependency Tree"
        subtitle="Visual map of upstream gateway, NVR nodes, and connected surveillance endpoints"
      >
        <TopologyGraph
          siteId={site.id}
          siteName={site.name}
          assets={assets}
          activeFaults={activeFaults}
          onSelectAsset={(assetId) => navigate(`/devices/${assetId}`)}
        />
      </Card>

      {/* Connected Assets List */}
      <Card
        title={`Connected Surveillance Endpoints (${siteAssets.length})`}
        subtitle="Inventory of cameras, storage nodes, and analytics boxes at this facility"
      >
        <div className="divide-y divide-surface-border/60">
          {siteAssets.map((asset) => {
            const faults = activeFaults[asset.id] || [];
            const isFaulty = faults.length > 0;

            return (
              <div
                key={asset.id}
                onClick={() => navigate(`/devices/${asset.id}`)}
                className="py-3 flex items-center justify-between hover:bg-surface-subtle/50 px-2 rounded cursor-pointer text-xs"
              >
                <div className="flex items-center gap-3">
                  {asset.kind === 'camera' && <Camera className="w-4 h-4 text-sky-400" />}
                  {asset.kind === 'nvr' && <Server className="w-4 h-4 text-emerald-400" />}
                  {asset.kind === 'ai_box' && <Cpu className="w-4 h-4 text-purple-400" />}
                  <div>
                    <span className="font-mono font-semibold text-slate-200">{asset.id}</span>
                    <span className="text-slate-400 ml-2 font-mono text-[11px]">{asset.ip}</span>
                    <div className="text-slate-300 text-[11px]">{asset.name}</div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Badge status={isFaulty ? 'critical' : 'healthy'} />
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Incidents at this site */}
      <Card
        title={`Facility Incidents & Tickets (${siteTickets.length})`}
        subtitle="All active and resolved incidents recorded for this location"
      >
        {siteTickets.length === 0 ? (
          <div className="p-4 text-center text-xs text-slate-400 font-mono">
            No incidents recorded for this facility site.
          </div>
        ) : (
          <div className="divide-y divide-surface-border/60">
            {siteTickets.map((t) => (
              <div
                key={t.id}
                onClick={() => navigate(`/incidents/${t.id}`)}
                className="py-3 flex items-center justify-between hover:bg-surface-subtle/50 px-2 rounded cursor-pointer text-xs"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold text-slate-200">{t.id}</span>
                    <Badge status={t.status} />
                    {t.asset_id && (
                      <span className="text-brand-300 font-mono text-[11px] font-semibold">
                        {t.asset_id}
                      </span>
                    )}
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
