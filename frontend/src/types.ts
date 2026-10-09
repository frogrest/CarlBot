export type TicketStatus =
  | 'open'
  | 'in_progress'
  | 'pending_technician'
  | 'ready_for_verification'
  | 'resolved'
  | 'closed'

export type TicketDeskStatus = 'Open' | 'Answered' | 'Closed'

export interface TicketNote {
  author: string
  body: string
  created_at: string
}

export interface CustomerReply {
  id: number
  ticket_id: number
  author: string
  body: string
  created_at: string
  idempotency_key?: string | null
}

export interface Ticket {
  id: number
  title: string
  description: string
  status: TicketStatus
  ticket_status: TicketDeskStatus
  priority: 'low' | 'medium' | 'high' | 'urgent' | string
  site_id: string
  asset_id: string
  created_at: string
  updated_at: string
  resolution: string | null
  root_cause: string | null
  ai_summary: string | null
  ai_state: string | null
  notes?: TicketNote[]
  customer_replies?: CustomerReply[]
}

export interface Asset {
  asset_id: string
  type: 'camera' | 'nvr' | 'ai_box' | string
  site_id?: string
  ip?: string
  nvr_id?: string
  ai_box_id?: string
  reachable?: boolean
  rtsp?: string
  auth?: string
  service?: string
  cloud?: string
  cpu?: number
  storage?: number
  poe?: boolean
  fault?: string | null
}

export interface AgentRun {
  id: number
  ticket_id: number
  started_at: string
  finished_at: string | null
  status: string
  diagnosis: string | null
  confidence: string | null
  auto_action: string | null
  error: string | null
}

export interface AgentStatus {
  poll_interval: number
  running: boolean
  recent_runs: AgentRun[]
}

export type LocalLlmState =
  | 'disabled'
  | 'runtime_missing'
  | 'model_not_configured'
  | 'loading'
  | 'ready'
  | 'busy'
  | 'error'

export interface LocalLlmStatus {
  state: LocalLlmState
  ready: boolean
  detail: string
  model_path: string
  base_url: string
  pid: number | null
  instructions: string[]
}

export type LocalLlmDownloadState =
  | 'idle'
  | 'downloading'
  | 'verifying'
  | 'completed'
  | 'error'
  | 'cancelled'

/** One entry in the curated, allow-listed download catalog. */
export interface LocalLlmModel {
  id: string
  display_name: string
  family: string
  parameters: string
  quantization: string
  filename: string
  size_bytes: number
  license: string
  repo: string
  download_url: string
  context_window: number
  min_ram_gb: number
  summary: string
  recommended: boolean
  installed: boolean
  installed_size_bytes: number | null
  is_selected: boolean
}

export interface ModelDownloadProgress {
  model_id: string
  state: LocalLlmDownloadState
  bytes_downloaded: number
  total_bytes: number
  percent: number | null
  error: string
}

export interface LocalLlmModelCatalog {
  models: LocalLlmModel[]
  selected_id: string | null
  active_model_path: string
  models_dir: string
  download: Record<string, ModelDownloadProgress>
  runtime: LocalLlmStatus
}

export interface KnowledgeDocumentSection {
  title: string
  start_line?: number
  end_line?: number
  content: string
}

export interface KnowledgeDocument {
  id: string
  title: string
  category: string
  source_path: string
  sections: KnowledgeDocumentSection[]
  raw_text?: string
}

export interface PortalEvent {
  event_id?: string
  id?: string | number
  asset_id: string
  site_id?: string
  fault_type?: string
  fault?: string
  timestamp?: string
  created_at?: string
  cleared?: boolean
  resolved?: boolean
}

export interface IncidentRecord {
  incident_id?: string
  ticket_id: number
  asset_id: string
  status: string
  diagnosis?: string | null
  confidence?: string | null
  auto_action?: string | null
  root_cause?: string | null
  route?: Array<{ agent: string; reason?: string }>
  evidence?: Array<{ label: string; text: string; source: string }>
}
