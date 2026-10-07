import type { AgentStatus, Asset, Ticket } from './types'

export interface DiagnosticProbe {
  name: string
  ok: boolean
  detail: string
}

export interface TicketChatMatch {
  ticket_id: string
  title: string
  status: string
  priority: string
  site_id: string
  asset_id: string
  site_match: 'exact' | 'partial' | 'unspecified'
  source: 'live_helpdesk' | 'reference_export'
  has_conversation: boolean
  details: string[]
}

export interface TicketChatResponse {
  answer: string
  matches: TicketChatMatch[]
  reference_export_available: boolean
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`${response.status} ${response.statusText}${detail ? `: ${detail}` : ''}`)
  }

  return response.json() as Promise<T>
}

export async function listTickets(): Promise<Ticket[]> {
  const result = await requestJson<{ tickets: Ticket[] }>('/helpdesk/api/tickets?limit=100')
  return result.tickets
}

export function getTicket(ticketId: number): Promise<Ticket> {
  return requestJson<Ticket>(`/helpdesk/api/tickets/${ticketId}`)
}

export function queryTickets(message: string): Promise<TicketChatResponse> {
  return requestJson<TicketChatResponse>('/helpdesk/api/chat/query', {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}

export async function listAssets(): Promise<Asset[]> {
  const result = await requestJson<{ assets: Asset[] }>('/portal/api/assets')
  return result.assets
}

export function getAgentStatus(): Promise<AgentStatus> {
  return requestJson<AgentStatus>('/agent/api/status')
}

export async function runAssetDiagnostics(asset: Asset): Promise<DiagnosticProbe[]> {
  const base = `/portal/api/assets/${encodeURIComponent(asset.asset_id)}`
  const checks: Array<{ name: string; path: string; fields: string[] }> = [
    { name: 'Health', path: `${base}/health`, fields: ['reachable', 'fault', 'rtsp', 'service', 'cpu'] },
    { name: 'Ping', path: `${base}/ping`, fields: ['ok', 'latency_ms'] },
  ]
  if (asset.type === 'camera' || asset.type === 'nvr') {
    checks.push(
      { name: 'TCP / 554', path: `${base}/tcp-test?port=554`, fields: ['open', 'port'] },
      { name: 'RTSP stream', path: `${base}/rtsp-test`, fields: ['stream', 'auth', 'reachable'] },
    )
  }

  return Promise.all(checks.map(async ({ name, path, fields }) => {
    try {
      const result = await requestJson<Record<string, unknown>>(path)
      const details = fields
        .filter((field) => field in result)
        .map((field) => `${field.replaceAll('_', ' ')}: ${String(result[field])}`)
      const failed = result.ok === false || result.open === false || result.reachable === false ||
        result.stream === 'unavailable' || result.stream === 'auth_failed' || result.service === 'down'
      return { name, ok: !failed, detail: details.join(' · ') || 'Probe completed' }
    } catch (error) {
      return {
        name,
        ok: false,
        detail: error instanceof Error ? error.message : 'Probe request failed',
      }
    }
  }))
}

export function runInvestigation(ticketId: number): Promise<{
  ticket_id: number
  diagnosis: string
  confidence: string
  state: string
  route: Array<{ agent: string; reason?: string }>
  auto_action: string | null
}> {
  return requestJson(`/agent/api/tickets/${ticketId}/run`, { method: 'POST' })
}

export function addTicketNote(ticketId: number, body: string): Promise<{ ok: boolean }> {
  return requestJson(`/helpdesk/api/tickets/${ticketId}/notes`, {
    method: 'POST',
    body: JSON.stringify({ author: 'technician', body }),
  })
}

export function simulateFault(assetId: string, fault: string): Promise<{ ok: boolean }> {
  return requestJson('/portal/api/simulate/fault', {
    method: 'POST',
    body: JSON.stringify({ asset_id: assetId, fault }),
  })
}

export function resetSimulation(assetId: string): Promise<{ ok: boolean }> {
  return requestJson(`/portal/api/assets/${assetId}/actions/reset-simulation`, {
    method: 'POST',
  })
}
