import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Wrench } from 'lucide-react';
import { useLab } from '../context/LabContext';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { EmptyState } from '../components/common/EmptyState';

export const IncidentsPage: React.FC = () => {
  const { tickets } = useLab();
  const navigate = useNavigate();

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [siteFilter, setSiteFilter] = useState('ALL');
  const [techFilter, setTechFilter] = useState(false);

  // Extract unique sites
  const sites = useMemo(() => {
    const s = new Set<string>();
    tickets.forEach((t) => {
      if (t.site_id) s.add(t.site_id);
    });
    return Array.from(s);
  }, [tickets]);

  // Filtered tickets
  const filteredTickets = useMemo(() => {
    return tickets.filter((t) => {
      if (techFilter && t.status !== 'pending_technician' && t.status !== 'pending_approval') {
        return false;
      }
      if (statusFilter !== 'ALL' && t.status !== statusFilter) {
        return false;
      }
      if (siteFilter !== 'ALL' && t.site_id !== siteFilter) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTitle = t.title.toLowerCase().includes(q);
        const matchId = t.id.toLowerCase().includes(q);
        const matchAsset = (t.asset_id || '').toLowerCase().includes(q);
        const matchCause = (t.root_cause || '').toLowerCase().includes(q);
        if (!matchTitle && !matchId && !matchAsset && !matchCause) return false;
      }
      return true;
    });
  }, [tickets, searchQuery, statusFilter, siteFilter, techFilter]);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Controls and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search tickets by ID, device, symptom, or root cause..."
            className="w-full pl-9 pr-4 py-2 text-xs rounded-lg bg-surface border border-surface-border text-slate-200 placeholder-slate-500 focus:outline-hidden focus:border-brand-500"
          />
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 rounded-lg bg-surface border border-surface-border text-slate-200 focus:outline-hidden"
          >
            <option value="ALL">All Statuses</option>
            <option value="open">Open</option>
            <option value="investigating">Investigating</option>
            <option value="pending_technician">Pending Technician</option>
            <option value="pending_approval">Pending Approval</option>
            <option value="resolved">Resolved</option>
          </select>

          <select
            value={siteFilter}
            onChange={(e) => setSiteFilter(e.target.value)}
            className="px-3 py-2 rounded-lg bg-surface border border-surface-border text-slate-200 focus:outline-hidden"
          >
            <option value="ALL">All Sites</option>
            {sites.map((site) => (
              <option key={site} value={site}>
                {site}
              </option>
            ))}
          </select>

          <button
            onClick={() => setTechFilter(!techFilter)}
            className={`px-3 py-2 rounded-lg border font-medium flex items-center gap-1.5 transition-colors ${
              techFilter
                ? 'bg-orange-950/60 text-orange-300 border-orange-700'
                : 'bg-surface border-surface-border text-slate-300 hover:text-white'
            }`}
          >
            <Wrench className="w-3.5 h-3.5 text-orange-400" />
            <span>Tech Required Only</span>
          </button>
        </div>
      </div>

      {/* Incidents Table Card */}
      <Card
        title={`Incident Records (${filteredTickets.length} of ${tickets.length})`}
        subtitle="Complete audit history of automated triage and technician repairs"
      >
        {filteredTickets.length === 0 ? (
          <EmptyState
            title="No matching incidents"
            description="No tickets matched your current search filters."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-surface-border text-slate-400 font-mono uppercase text-[10px]">
                <tr>
                  <th className="pb-3 font-semibold">Incident ID</th>
                  <th className="pb-3 font-semibold">Title & Description</th>
                  <th className="pb-3 font-semibold">Site / Asset</th>
                  <th className="pb-3 font-semibold">Status</th>
                  <th className="pb-3 font-semibold">Root Cause</th>
                  <th className="pb-3 font-semibold">Created / Updated</th>
                  <th className="pb-3 font-semibold text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border/60">
                {filteredTickets.map((t) => (
                  <tr
                    key={t.id}
                    onClick={() => navigate(`/incidents/${t.id}`)}
                    className="hover:bg-surface-elevated/40 cursor-pointer transition-colors"
                  >
                    <td className="py-3 font-mono font-semibold text-slate-200">
                      {t.id}
                    </td>
                    <td className="py-3 max-w-sm">
                      <div className="font-semibold text-slate-100">{t.title}</div>
                      <div className="text-[11px] text-slate-400 truncate mt-0.5">{t.description}</div>
                    </td>
                    <td className="py-3">
                      <span className="font-mono text-slate-300">{t.site_id}</span>
                      {t.asset_id && (
                        <div className="text-[11px] font-mono text-brand-300 font-semibold mt-0.5">
                          {t.asset_id}
                        </div>
                      )}
                    </td>
                    <td className="py-3">
                      <Badge status={t.status} />
                    </td>
                    <td className="py-3">
                      {t.root_cause ? (
                        <span className="font-mono text-[11px] text-amber-300 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-900/60">
                          {t.root_cause}
                        </span>
                      ) : (
                        <span className="text-slate-500 font-mono text-[11px]">—</span>
                      )}
                    </td>
                    <td className="py-3 font-mono text-[11px] text-slate-400">
                      <div>{new Date(t.created_at).toLocaleDateString()}</div>
                      <div>{new Date(t.updated_at).toLocaleTimeString()}</div>
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/incidents/${t.id}`);
                        }}
                        className="px-2.5 py-1 text-[11px] font-medium rounded bg-surface-elevated hover:bg-surface-hover border border-surface-border text-slate-200"
                      >
                        View
                      </button>
                    </td>
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
