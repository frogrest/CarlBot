export type SafetyClass = 'READ' | 'SAFE_REVERSIBLE' | 'APPROVAL_REQUIRED' | 'HUMAN_ONLY';

export interface Comment {
  author: string;
  body: string;
  at: string;
}

export interface TechnicianNote {
  author: string;
  body: string;
  at: string;
}

export interface Ticket {
  id: string;
  title: string;
  description: string;
  status: 'open' | 'investigating' | 'pending_technician' | 'pending_approval' | 'resolved' | 'closed';
  site_id: string;
  asset_id?: string;
  root_cause?: string;
  resolution?: string;
  created_at: string;
  updated_at: string;
  comments: Comment[];
  technician_notes: TechnicianNote[];
  tags: string[];
}

export interface Asset {
  id: string;
  site_id: string;
  name: string;
  kind: 'camera' | 'nvr' | 'ai_box';
  ip: string;
  state: Record<string, any>;
  effective_state?: Record<string, any>;
}

export interface CheckResult {
  id: string;
  kind: 'camera' | 'nvr' | 'ai_box';
  ip: string;
  site_id: string;
  ping: boolean;
  tcp554?: boolean;
  rtsp?: boolean | 'up' | 'down';
  rtsp_auth?: boolean;
  rtsp_path?: boolean;
  poe?: boolean;
  storage_used?: number;
  service?: 'up' | 'down';
  cpu?: number;
  cloud_sync?: 'up' | 'down';
  [key: string]: any;
}

export interface Site {
  id: string;
  name: string;
  location: string;
  assets: Asset[];
}

export interface SiteHealth {
  site_id: string;
  name: string;
  total_assets: number;
  reachable_assets: number;
  healthy_assets: number;
  issues: Array<{
    asset_id: string;
    kind: string;
    issue: string;
  }>;
}

export interface ActionLogEntry {
  asset_id: string;
  action: string;
  timestamp: string;
  result: string;
}

export interface FaultHistoryEntry {
  asset_id: string;
  fault: string;
  at: string;
  event: 'injected' | 'cleared';
}

export interface AgentActiveIncident {
  ticket_id: string;
  fault: string;
  attempts: number;
  last_at: string;
  verification?: string;
}

export interface AgentHistoryEntry {
  asset_id: string;
  fault?: string;
  ticket_id?: string;
  event?: string;
  at: string;
  verification?: string;
}

export interface AgentState {
  active: Record<string, AgentActiveIncident>;
  history: AgentHistoryEntry[];
}

export interface TimelineStep {
  step: 'observation' | 'history_retrieval' | 'hypothesis' | 'knowledge_retrieval' | 'policy_evaluation' | 'recovery_and_verification' | 'escalation' | 'verification';
  title: string;
  status: 'PASS' | 'FAIL' | 'ALLOWED' | 'BLOCKED' | 'ESCALATED' | 'INFO';
  details: any;
  timestamp: string;
}

export interface InvestigationReport {
  found: boolean;
  asset: Asset;
  check: CheckResult;
  post_check: CheckResult;
  is_problem: boolean;
  diagnosis: {
    fault: string;
    confidence: number;
    recommendation: string;
    safety_class: SafetyClass;
  };
  policy: {
    action: string | null;
    safety_class: SafetyClass;
    allowed_automatically: boolean;
  };
  action_executed: string | null;
  ticket: Ticket | null;
  historical_matches: Array<{ id: string; title?: string; root_cause?: string; status?: string }>;
  knowledge_sources: Array<{ source: string; score: number; snippet: string }>;
  timeline: TimelineStep[];
  site_info: any;
}

export interface KnowledgeDocSummary {
  source: string;
  title: string;
  size: number;
  lines: number;
  snippet: string;
}

export interface KnowledgeDocDetail {
  source: string;
  title: string;
  size: number;
  lines: number;
  content: string;
}

export interface PolicyRule {
  class: SafetyClass;
  description: string;
  requires_human: boolean;
  actions: string[];
}
