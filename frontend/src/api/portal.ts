import { http, PORTAL_BASE } from './client';
import type { Asset, CheckResult, Site, SiteHealth, ActionLogEntry, FaultHistoryEntry } from './types';

export const portalApi = {
  async getAssets(): Promise<Asset[]> {
    return http.get<Asset[]>(`${PORTAL_BASE}/assets`);
  },

  async getAsset(id: string): Promise<Asset> {
    return http.get<Asset>(`${PORTAL_BASE}/assets/${id}`);
  },

  async checkAsset(id: string): Promise<CheckResult> {
    return http.get<CheckResult>(`${PORTAL_BASE}/check/${id}`);
  },

  async pingAsset(id: string): Promise<{ id: string; ping: boolean; latency_ms?: number }> {
    return http.get(`${PORTAL_BASE}/ping/${id}`);
  },

  async getSites(): Promise<Site[]> {
    const raw = await http.get<any>(`${PORTAL_BASE}/sites`);
    const siteMetadata: Record<string, { name: string; location: string }> = {
      'SITE-001': { name: 'Corporate Lobby & Entrance', location: 'Building A, Floor 1' },
      'SITE-002': { name: 'Logistics & Parking Yard', location: 'Building B, External Perimeter' },
      'SITE-003': { name: 'Data Center & Server Room', location: 'Building A, Basement' },
    };

    if (Array.isArray(raw)) {
      return raw.map((item) => {
        if (typeof item === 'string') {
          const meta = siteMetadata[item] || { name: `Site ${item}`, location: 'Facility Zone' };
          return {
            id: item,
            name: meta.name,
            location: meta.location,
            assets: [],
          };
        }
        return item;
      });
    }
    return [];
  },

  async getSiteHealth(siteId: string): Promise<SiteHealth> {
    const data = await http.get<any>(`${PORTAL_BASE}/sites/${siteId}/health`);
    const siteMetadata: Record<string, { name: string; location: string }> = {
      'SITE-001': { name: 'Corporate Lobby & Entrance', location: 'Building A, Floor 1' },
      'SITE-002': { name: 'Logistics & Parking Yard', location: 'Building B, External Perimeter' },
      'SITE-003': { name: 'Data Center & Server Room', location: 'Building A, Basement' },
    };
    const meta = siteMetadata[siteId] || { name: `Site ${siteId}`, location: 'Facility Zone' };

    const assets = Array.isArray(data.assets) ? data.assets : [];
    let healthyCount = 0;
    let reachableCount = 0;
    const issues: Array<{ asset_id: string; kind: string; issue: string }> = [];

    assets.forEach((a: any) => {
      const st = a.effective_state || a.state || {};
      const fList = a.active_faults || [];
      if (st.reachable) reachableCount++;
      if (fList.length === 0 && st.reachable) {
        healthyCount++;
      } else {
        fList.forEach((f: string) => issues.push({ asset_id: a.id, kind: a.kind, issue: f }));
        if (!st.reachable && fList.length === 0) {
          issues.push({ asset_id: a.id, kind: a.kind, issue: 'unreachable' });
        }
      }
    });

    return {
      site_id: data.site_id || siteId,
      name: data.name || meta.name,
      total_assets: data.total_assets ?? assets.length,
      reachable_assets: data.reachable_assets ?? reachableCount,
      healthy_assets: data.healthy_assets ?? healthyCount,
      issues: Array.isArray(data.issues) ? data.issues : issues,
    };
  },

  async getActiveFaults(): Promise<Record<string, string[]>> {
    return http.get<Record<string, string[]>>(`${PORTAL_BASE}/faults`);
  },

  async getSupportedFaults(): Promise<string[]> {
    const data = await http.get<any>(`${PORTAL_BASE}/faults/supported`);
    if (Array.isArray(data)) {
      return data;
    }
    if (data && Array.isArray(data.supported_faults)) {
      return data.supported_faults;
    }
    return [];
  },

  async injectFault(assetId: string, fault: string): Promise<{ asset_id: string; active_faults: string[] }> {
    return http.post(`${PORTAL_BASE}/faults/${assetId}`, { fault });
  },

  async injectSiteFault(siteId: string, fault: string): Promise<{ site_id: string; affected_assets: string[]; fault: string }> {
    return http.post(`${PORTAL_BASE}/faults/site/${siteId}`, { fault });
  },

  async clearFault(assetId: string): Promise<{ asset_id: string; active_faults: string[] }> {
    return http.post(`${PORTAL_BASE}/faults/${assetId}/clear`);
  },

  async clearAllFaults(): Promise<{ cleared: number; message: string }> {
    return http.post(`${PORTAL_BASE}/faults/clear-all`);
  },

  async executeAction(assetId: string, action: string): Promise<{ asset_id: string; action: string; result: string; timestamp: string }> {
    return http.post(`${PORTAL_BASE}/assets/${assetId}/actions`, { action });
  },

  async getActionLog(): Promise<ActionLogEntry[]> {
    return http.get<ActionLogEntry[]>(`${PORTAL_BASE}/action-log`);
  },

  async getFaultHistory(): Promise<FaultHistoryEntry[]> {
    return http.get<FaultHistoryEntry[]>(`${PORTAL_BASE}/fault-history`);
  },
};
