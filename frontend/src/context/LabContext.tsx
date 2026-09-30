import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { helpdeskApi, portalApi, agentApi } from '../api';
import type { Asset, Ticket, AgentState } from '../api/types';

interface LabContextValue {
  assets: Asset[];
  tickets: Ticket[];
  agentState: AgentState | null;
  activeFaults: Record<string, string[]>;
  supportedFaults: string[];
  agentOnline: boolean;
  loading: boolean;
  refreshing: boolean;
  lastUpdated: Date | null;
  refresh: () => Promise<void>;
  triggerAgentCycle: () => Promise<void>;
  injectFault: (assetId: string, fault: string) => Promise<void>;
  injectSiteFault: (siteId: string, fault: string) => Promise<void>;
  clearFault: (assetId: string) => Promise<void>;
  clearAllFaults: () => Promise<void>;
  notification: { message: string; type: 'success' | 'error' | 'info' } | null;
  setNotification: (notif: { message: string; type: 'success' | 'error' | 'info' } | null) => void;
}

const LabContext = createContext<LabContextValue | undefined>(undefined);

export const LabProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [agentState, setAgentState] = useState<AgentState | null>(null);
  const [activeFaults, setActiveFaults] = useState<Record<string, string[]>>({});
  const [supportedFaults, setSupportedFaults] = useState<string[]>([]);
  const [agentOnline, setAgentOnline] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const [assetsData, ticketsData, faultsData, supportedData, stateData, healthData] = await Promise.all([
        portalApi.getAssets().catch(() => []),
        helpdeskApi.getTickets().catch(() => []),
        portalApi.getActiveFaults().catch(() => ({})),
        portalApi.getSupportedFaults().catch(() => []),
        agentApi.getState().catch(() => null),
        agentApi.getHealth().catch(() => ({ ok: false })),
      ]);

      setAssets(assetsData);
      setTickets(ticketsData);
      setActiveFaults(faultsData);
      setSupportedFaults(supportedData);
      setAgentState(stateData);
      setAgentOnline(Boolean(healthData && healthData.ok));
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to refresh lab data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 6000); // 6s poll
    return () => clearInterval(interval);
  }, [refresh]);

  const triggerAgentCycle = async () => {
    try {
      await agentApi.triggerRun();
      setNotification({ message: 'Agent investigation cycle completed', type: 'success' });
      await refresh();
    } catch (err: any) {
      setNotification({ message: `Agent cycle error: ${err.message}`, type: 'error' });
    }
  };

  const injectFault = async (assetId: string, fault: string) => {
    try {
      await portalApi.injectFault(assetId, fault);
      setNotification({ message: `Fault '${fault}' injected on ${assetId}`, type: 'info' });
      await refresh();
    } catch (err: any) {
      setNotification({ message: `Failed to inject fault: ${err.message}`, type: 'error' });
    }
  };

  const injectSiteFault = async (siteId: string, fault: string) => {
    try {
      await portalApi.injectSiteFault(siteId, fault);
      setNotification({ message: `Site fault '${fault}' injected on ${siteId}`, type: 'info' });
      await refresh();
    } catch (err: any) {
      setNotification({ message: `Failed to inject site fault: ${err.message}`, type: 'error' });
    }
  };

  const clearFault = async (assetId: string) => {
    try {
      await portalApi.clearFault(assetId);
      setNotification({ message: `Fault cleared on ${assetId}`, type: 'success' });
      await refresh();
    } catch (err: any) {
      setNotification({ message: `Failed to clear fault: ${err.message}`, type: 'error' });
    }
  };

  const clearAllFaults = async () => {
    try {
      await portalApi.clearAllFaults();
      setNotification({ message: 'All faults cleared successfully', type: 'success' });
      await refresh();
    } catch (err: any) {
      setNotification({ message: `Failed to clear all faults: ${err.message}`, type: 'error' });
    }
  };

  return (
    <LabContext.Provider
      value={{
        assets,
        tickets,
        agentState,
        activeFaults,
        supportedFaults,
        agentOnline,
        loading,
        refreshing,
        lastUpdated,
        refresh,
        triggerAgentCycle,
        injectFault,
        injectSiteFault,
        clearFault,
        clearAllFaults,
        notification,
        setNotification,
      }}
    >
      {children}
    </LabContext.Provider>
  );
};

export const useLab = () => {
  const context = useContext(LabContext);
  if (!context) {
    throw new Error('useLab must be used within a LabProvider');
  }
  return context;
};
