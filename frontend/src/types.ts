export type TicketStatus =
  | 'open'
  | 'in_progress'
  | 'pending_technician'
  | 'ready_for_verification'
  | 'resolved'
  | 'closed'

export interface TicketNote {
  author: string
  body: string
  created_at: string
}

export interface Ticket {
  id: number
  title: string
  description: string
  status: TicketStatus
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
