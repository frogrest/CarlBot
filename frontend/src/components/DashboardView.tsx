import { useState } from 'react'
import type { AgentStatus, Asset, PortalEvent, Ticket, TicketDeskStatus } from '../types'

interface DashboardViewProps {
  tickets: Ticket[]
  assets: Asset[]
  events: PortalEvent[]
  agentStatus: AgentStatus | null
  onNavigate: (view: 'dashboard' | 'tickets' | 'tasks' | 'knowledge' | 'assets', filter?: { site?: string; status?: TicketDeskStatus | 'all' }) => void
  onTriggerMonitor: () => Promise<void>
  isMonitoring: boolean
  onOpenTicket: (ticketId: number) => void
  onAskCarlBot: (prompt: string) => void
}

function formatDate(value: string | undefined): string {
  if (!value) return 'Just now'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Recently'
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

export function DashboardView({
  tickets,
  assets,
  events,
  agentStatus,
  onNavigate,
  onTriggerMonitor,
  isMonitoring,
  onOpenTicket,
  onAskCarlBot,
}: DashboardViewProps) {
  const [monitorNotice, setMonitorNotice] = useState<string>('')

  const openTickets = tickets.filter((t) => (t.ticket_status ? t.ticket_status === 'Open' : t.status !== 'closed' && t.status !== 'resolved'))
  const answeredTickets = tickets.filter((t) => t.ticket_status === 'Answered' || t.status === 'ready_for_verification')
  const closedTickets = tickets.filter((t) => t.ticket_status === 'Closed' || t.status === 'closed')

  const totalAssets = assets.length
  const faultedAssets = assets.filter((a) => a.fault)
  const onlineAssets = assets.filter((a) => a.reachable !== false && !a.fault)
  const cameras = assets.filter((a) => a.type === 'camera')
  const recorders = assets.filter((a) => a.type === 'nvr')
  const aiBoxes = assets.filter((a) => a.type === 'ai_box')

  const sites = [...new Set(assets.map((a) => a.site_id || 'Unassigned'))].sort()

  const handleRunMonitor = async () => {
    setMonitorNotice('Triggering autonomous monitor cycle…')
    try {
      await onTriggerMonitor()
      setMonitorNotice('Monitor cycle completed successfully.')
      setTimeout(() => setMonitorNotice(''), 4000)
    } catch {
      setMonitorNotice('Monitor trigger failed.')
    }
  }

  return (
    <section className="dashboard-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-dot" /> MULTI-SITE LAB / OPERATIONS OVERVIEW
          </div>
          <h1>Operations Command Center</h1>
          <p>Real-time telemetry, automated triage status, and incident response across all surveillance sites.</p>
        </div>
        <div className="dashboard-actions">
          <button
            type="button"
            className="button button-primary"
            onClick={handleRunMonitor}
            disabled={isMonitoring}
          >
            {isMonitoring ? 'Monitoring Active…' : '▶ Run Monitor Cycle'}
          </button>
        </div>
      </div>

      {monitorNotice && (
        <div className="dashboard-notice" role="status">
          <span>ⓘ</span> {monitorNotice}
        </div>
      )}

      {/* KPI Metrics Grid */}
      <div className="kpi-grid">
        <div
          className="kpi-card kpi-interactive"
          onClick={() => onNavigate('tickets', { status: 'Open' })}
          role="button"
          tabIndex={0}
        >
          <div className="kpi-head">
            <span className="kpi-label">Open Incidents</span>
            <span className="kpi-badge kpi-badge-open">{openTickets.length} ACTIVE</span>
          </div>
          <div className="kpi-value">{openTickets.length}</div>
          <div className="kpi-footer">Requires technician or agent review →</div>
        </div>

        <div
          className="kpi-card kpi-interactive"
          onClick={() => onNavigate('tickets', { status: 'Answered' })}
          role="button"
          tabIndex={0}
        >
          <div className="kpi-head">
            <span className="kpi-label">Answered / Verifying</span>
            <span className="kpi-badge kpi-badge-answered">{answeredTickets.length} IN FLIGHT</span>
          </div>
          <div className="kpi-value">{answeredTickets.length}</div>
          <div className="kpi-footer">Ready for verification or notes →</div>
        </div>

        <div
          className="kpi-card kpi-interactive"
          onClick={() => onNavigate('tickets', { status: 'Closed' })}
          role="button"
          tabIndex={0}
        >
          <div className="kpi-head">
            <span className="kpi-label">Resolved / Closed</span>
            <span className="kpi-badge kpi-badge-closed">{closedTickets.length} RESOLVED</span>
          </div>
          <div className="kpi-value">{closedTickets.length}</div>
          <div className="kpi-footer">Historical resolutions →</div>
        </div>

        <div
          className="kpi-card kpi-interactive"
          onClick={() => onNavigate('assets')}
          role="button"
          tabIndex={0}
        >
          <div className="kpi-head">
            <span className="kpi-label">Surveillance Assets</span>
            <span className={`kpi-badge ${faultedAssets.length > 0 ? 'kpi-badge-warning' : 'kpi-badge-healthy'}`}>
              {faultedAssets.length > 0 ? `${faultedAssets.length} FAULTED` : 'ALL HEALTHY'}
            </span>
          </div>
          <div className="kpi-value">{onlineAssets.length} <small>/ {totalAssets}</small></div>
          <div className="kpi-footer">
            {cameras.length} Cams · {recorders.length} NVRs · {aiBoxes.length} AI Boxes →
          </div>
        </div>

        <div
          className="kpi-card kpi-interactive"
          onClick={() => onNavigate('tasks')}
          role="button"
          tabIndex={0}
        >
          <div className="kpi-head">
            <span className="kpi-label">Agent Automation</span>
            <span className={`kpi-badge ${agentStatus?.running ? 'kpi-badge-healthy' : 'kpi-badge-warning'}`}>
              {agentStatus?.running ? 'ACTIVE' : 'STANDBY'}
            </span>
          </div>
          <div className="kpi-value">{agentStatus?.recent_runs.length || 0} <small>runs</small></div>
          <div className="kpi-footer">
            Poll interval {agentStatus?.poll_interval || 5}s · Policy gated →
          </div>
        </div>

        <div
          className="kpi-card kpi-interactive"
          onClick={() => onNavigate('knowledge')}
          role="button"
          tabIndex={0}
        >
          <div className="kpi-head">
            <span className="kpi-label">Approved SOPs</span>
            <span className="kpi-badge kpi-badge-info">9 GUIDES</span>
          </div>
          <div className="kpi-value">Library</div>
          <div className="kpi-footer">Playbooks, IP & Network SOPs →</div>
        </div>
      </div>

      {/* Main Two-Column Dashboard Layout */}
      <div className="dashboard-grid">
        {/* Left Column: Site Health & Telemetry Feed */}
        <div className="dashboard-column-main">
          {/* Site Matrix */}
          <section className="content-card dashboard-card">
            <div className="section-heading">
              <div>
                <span className="section-icon">⌘</span>
                <h2>Site Operations Matrix</h2>
                <span className="section-count">{sites.length} sites</span>
              </div>
            </div>
            <div className="site-cards-grid">
              {sites.map((site) => {
                const siteAssets = assets.filter((a) => (a.site_id || 'Unassigned') === site)
                const siteFaults = siteAssets.filter((a) => a.fault)
                const siteTickets = tickets.filter((t) => t.site_id === site && t.ticket_status !== 'Closed' && t.status !== 'closed')
                const isHealthy = siteFaults.length === 0

                return (
                  <div key={site} className={`site-card ${!isHealthy ? 'site-card-alert' : ''}`}>
                    <div className="site-card-header">
                      <div>
                        <strong>{site}</strong>
                        <span className="site-card-badge">{siteAssets.length} Devices</span>
                      </div>
                      <span className={`status-pill ${isHealthy ? 'pill-healthy' : 'pill-alert'}`}>
                        {isHealthy ? '● Normal' : `▲ ${siteFaults.length} Fault`}
                      </span>
                    </div>
                    <div className="site-card-stats">
                      <div>
                        <span>Open Tickets</span>
                        <strong>{siteTickets.length}</strong>
                      </div>
                      <div>
                        <span>Cameras</span>
                        <strong>{siteAssets.filter((a) => a.type === 'camera').length}</strong>
                      </div>
                      <div>
                        <span>Active Faults</span>
                        <strong className={siteFaults.length > 0 ? 'text-alert' : ''}>{siteFaults.length}</strong>
                      </div>
                    </div>
                    <div className="site-card-actions">
                      <button
                        type="button"
                        className="button button-small button-outline"
                        onClick={() => onNavigate('tickets', { site, status: 'all' })}
                      >
                        View Tickets
                      </button>
                      <button
                        type="button"
                        className="button button-small button-secondary"
                        onClick={() => onNavigate('assets')}
                      >
                        Inspect Devices
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </section>

          {/* Real-Time Events & Fault Telemetry Feed */}
          <section className="content-card dashboard-card">
            <div className="section-heading">
              <div>
                <span className="section-icon">⌁</span>
                <h2>Live Hardware Telemetry & Fault Events</h2>
                <span className="section-count">{events.length}</span>
              </div>
              <span className="subtle-label">EMULATED PORTAL FEED</span>
            </div>
            <div className="event-stream">
              {events.length === 0 ? (
                <div className="empty-stream-state">
                  <span>✔</span> All camera feeds and hardware links are reporting healthy status.
                </div>
              ) : (
                events.slice(0, 6).map((evt, idx) => {
                  const faultName = evt.fault_type || evt.fault || 'Outage'
                  const isCleared = evt.cleared || evt.resolved
                  return (
                    <div key={evt.event_id || evt.id || idx} className={`event-stream-row ${isCleared ? 'event-cleared' : 'event-active'}`}>
                      <span className={`event-icon ${isCleared ? 'icon-green' : 'icon-amber'}`}>
                        {isCleared ? '✔' : '▲'}
                      </span>
                      <div className="event-info">
                        <div>
                          <strong>{evt.asset_id}</strong>
                          <span className="event-fault-tag">{faultName.replaceAll('_', ' ')}</span>
                          {evt.site_id && <span className="event-site-tag">{evt.site_id}</span>}
                        </div>
                        <span className="event-timestamp">{formatDate(evt.timestamp || evt.created_at)}</span>
                      </div>
                      <span className={`event-status-badge ${isCleared ? 'badge-cleared' : 'badge-active'}`}>
                        {isCleared ? 'Resolved' : 'Active Alarm'}
                      </span>
                    </div>
                  )
                })
              )}
            </div>
          </section>

          {/* Active Incidents Awaiting Attention */}
          <section className="content-card dashboard-card">
            <div className="section-heading">
              <div>
                <span className="section-icon">▤</span>
                <h2>Active Incidents Awaiting Review</h2>
                <span className="section-count">{openTickets.length} open</span>
              </div>
              <button
                type="button"
                className="button button-small button-outline"
                onClick={() => onNavigate('tickets', { status: 'Open' })}
              >
                View Full Queue →
              </button>
            </div>
            <div className="dashboard-ticket-list">
              {openTickets.length === 0 ? (
                <div className="empty-stream-state">
                  <span>✔</span> No active unaddressed tickets in queue.
                </div>
              ) : (
                openTickets.slice(0, 5).map((ticket) => (
                  <div key={ticket.id} className="dashboard-ticket-row">
                    <div className="ticket-info">
                      <span className="ticket-id-tag mono">#{ticket.id}</span>
                      <strong className="ticket-title-text">{ticket.title}</strong>
                      <span className="ticket-site-tag">{ticket.site_id}</span>
                    </div>
                    <div className="ticket-row-actions">
                      <span className={`priority-pill priority-${ticket.priority.toLowerCase()}`}>
                        {ticket.priority}
                      </span>
                      <button
                        type="button"
                        className="button button-small button-outline"
                        onClick={() => onOpenTicket(ticket.id)}
                      >
                        Open Ticket
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>

        {/* Right Column: Quick Launchpad & Policy Guardrails */}
        <div className="dashboard-column-sidebar">
          {/* Quick Operations Launchpad */}
          <section className="content-card">
            <div className="section-heading">
              <div>
                <span className="section-icon">⚡</span>
                <h2>Quick Operations</h2>
              </div>
            </div>
            <div className="launchpad-list">
              <button
                type="button"
                className="launchpad-item"
                onClick={() => onNavigate('tickets', { status: 'Open' })}
              >
                <span className="launchpad-glyph">▤</span>
                <div>
                  <strong>Triage Open Tickets</strong>
                  <span>Investigate active incidents and review AI evidence</span>
                </div>
                <span className="launchpad-arrow">→</span>
              </button>

              <button
                type="button"
                className="launchpad-item"
                onClick={() => onNavigate('knowledge')}
              >
                <span className="launchpad-glyph">▧</span>
                <div>
                  <strong>SOP & Playbook Library</strong>
                  <span>Offline camera, network protocols & CLI diagnostic guides</span>
                </div>
                <span className="launchpad-arrow">→</span>
              </button>

              <button
                type="button"
                className="launchpad-item"
                onClick={() => onNavigate('tasks')}
              >
                <span className="launchpad-glyph">◷</span>
                <div>
                  <strong>Investigation Tasks</strong>
                  <span>Inspect agent runs, confidence ratings & policy gates</span>
                </div>
                <span className="launchpad-arrow">→</span>
              </button>

              <button
                type="button"
                className="launchpad-item"
                onClick={() => onNavigate('assets')}
              >
                <span className="launchpad-glyph">⌘</span>
                <div>
                  <strong>Hardware Asset Probes</strong>
                  <span>Simulate faults and test ping / RTSP connectivity</span>
                </div>
                <span className="launchpad-arrow">→</span>
              </button>
            </div>
          </section>

          {/* CarlBot Copilot Quick Assist */}
          <section className="content-card carlbot-widget-card">
            <div className="section-heading">
              <div>
                <span className="section-icon">◈</span>
                <h2>CarlBot AI Copilot</h2>
              </div>
              <span className="status-pill pill-healthy">Ready</span>
            </div>
            <p className="carlbot-widget-desc">
              Your AI companion is grounded in this surveillance lab. Ask questions about equipment or troubleshooting procedures:
            </p>
            <div className="carlbot-prompts">
              <button
                type="button"
                className="carlbot-quick-chip"
                onClick={() => onAskCarlBot('what to do when a camera is offline')}
              >
                "What to do when camera is offline?"
              </button>
              <button
                type="button"
                className="carlbot-quick-chip"
                onClick={() => onAskCarlBot('what is the difference between reboot and power cycle')}
              >
                "Reboot vs. Power Cycling?"
              </button>
              <button
                type="button"
                className="carlbot-quick-chip"
                onClick={() => onAskCarlBot('what ip commands should a technician use')}
              >
                "Essential IP commands?"
              </button>
            </div>
          </section>

          {/* Safety & Policy Boundaries */}
          <section className="content-card lab-policy-card">
            <div className="section-heading">
              <div>
                <span className="section-icon">⌑</span>
                <h2>Safety & Policy Gate</h2>
              </div>
            </div>
            <div className="policy-rule-box">
              <div className="policy-category allowed">
                <strong>✔ Autonomous Safe Actions</strong>
                <p>• <code>reconnect-rtsp</code> (restore dropped streams)<br />• <code>restart-ai-service</code> (restore edge containers)</p>
              </div>
              <div className="policy-category blocked">
                <strong>▲ Human-Controlled Actions</strong>
                <p>• Power/PoE cable repairs<br />• Credential changes & vault access<br />• Switch port & firewall configuration<br />• Factory reset & physical storage work</p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </section>
  )
}
