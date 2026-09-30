import { http, AGENT_BASE } from './client';
import type {
  AgentState,
  InvestigationReport,
  KnowledgeDocSummary,
  KnowledgeDocDetail,
  PolicyRule,
} from './types';

export const agentApi = {
  async getHealth(): Promise<{ ok: boolean; service: string }> {
    return http.get(`${AGENT_BASE}/health`);
  },

  async getState(): Promise<AgentState> {
    return http.get<AgentState>(`${AGENT_BASE}/state`);
  },

  async getPolicy(): Promise<Record<string, PolicyRule>> {
    return http.get<Record<string, PolicyRule>>(`${AGENT_BASE}/policy`);
  },

  async triggerRun(): Promise<AgentState> {
    return http.post<AgentState>(`${AGENT_BASE}/run-once`);
  },

  async investigateAsset(assetId: string): Promise<InvestigationReport> {
    return http.post<InvestigationReport>(`${AGENT_BASE}/investigate/${assetId}`);
  },

  async getKnowledgeDocs(): Promise<KnowledgeDocSummary[]> {
    return http.get<KnowledgeDocSummary[]>(`${AGENT_BASE}/knowledge`);
  },

  async getKnowledgeDoc(docPath: string): Promise<KnowledgeDocDetail> {
    return http.get<KnowledgeDocDetail>(`${AGENT_BASE}/knowledge/doc/${docPath}`);
  },

  async searchKnowledge(query: string): Promise<Array<{ source: string; score: number; snippet: string }>> {
    return http.get(`${AGENT_BASE}/knowledge-search?q=${encodeURIComponent(query)}`);
  },
};
