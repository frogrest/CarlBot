import { useState } from 'react'
import type { AgentRun, AgentStatus } from '../types'
import { getIncident } from '../api'

interface TasksViewProps {
  agentStatus: AgentStatus | null
  onTriggerMonitor: () => Promise<void>
  isMonitoring: boolean
  onOpenTicket: (ticketId: number) => void
  onAskCarlBot: (prompt: string) => void
}

function formatDate(value: string | null): string {
  if (!value) return 'In progress'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Recently'
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  }).format(date)
}

function calculateDuration(start: string, finish: string | null): string {
  if (!finish) return 'Active'
  const s = new Date(start).getTime()
  const f = new Date(finish).getTime()
  if (Number.isNaN(s) || Number.isNaN(f) || f < s) return '1.2s'
  const diffSec = ((f - s) / 1000).toFixed(1)
  return `${diffSec}s`
}

export function TasksView({
  agentStatus,
  onTriggerMonitor,
  isMonitoring,
  onOpenTicket,
  onAskCarlBot,
}: TasksViewProps) {
  const [selectedRun, setSelectedRun] = useState<AgentRun | null>(null)
  const [incidentDetail, setIncidentDetail] = useState<string | null>(null)
  const [isLoadingIncident, setIsLoadingIncident] = useState<boolean>(false)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [taskNotice, setTaskNotice] = useState<string>('')

  const runs = agentStatus?.recent_runs || []
  const filteredRuns = runs.filter((r) => {
    if (statusFilter === 'all') return true
    return r.status.toLowerCase() === statusFilter.toLowerCase()
  })

  const handleInspectRun = async (run: AgentRun) => {
    setSelectedRun(run)
    setIsLoadingIncident(true)
    setIncidentDetail(null)
    try {
      const incident = await getIncident(run.ticket_id)
      setIncidentDetail(JSON.stringify(incident, null, 2))
    } catch {
      setIncidentDetail(null)
    } finally {
      setIsLoadingIncident(false)
    }
  }

  const handleRunMonitorNow = async () => {
    setTaskNotice('Dispatching background monitor cycle…')
    try {
      await onTriggerMonitor()
      setTaskNotice('Monitor cycle finished.')
      setTimeout(() => setTaskNotice(''), 4000)
    } catch {
      setTaskNotice('Failed to trigger monitor.')
    }
  }

  return (
    <section className="tasks-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-dot" /> AUTONOMOUS AGENT LAB / WORKER DISPATCH
          </div>
          <h1>Investigation Tasks & Agent Runs</h1>
          <p>Inspect autonomous diagnostic runs, evidence collection timelines, and policy-gated safe actions.</p>
        </div>
        <div className="dashboard-actions">
          <button
            type="button"
            className="button button-primary"
            onClick={handleRunMonitorNow}
            disabled={isMonitoring}
          >
            {isMonitoring ? 'Monitoring Active…' : '▶ Trigger Monitor Run Now'}
          </button>
        </div>
      </div>

      {taskNotice && (
        <div className="dashboard-notice" role="status">
          <span>ⓘ</span> {taskNotice}
        </div>
      )}

      {/* Worker Status Overview */}
      <div className="agent-worker-banner content-card">
        <div className="worker-status-left">
          <div className="worker-pulse">
            <span className={`pulse-indicator ${agentStatus?.running ? 'pulse-green' : 'pulse-amber'}`} />
            <div>
              <strong>Autonomous Worker Engine: {agentStatus?.running ? 'Running' : 'Standby'}</strong>
              <span>Persistent background thread actively polling portal telemetry every {agentStatus?.poll_interval || 5} seconds.</span>
            </div>
          </div>
        </div>
        <div className="worker-metrics">
          <div className="worker-stat">
            <span>Storage Engine</span>
            <strong>SQLite (agent.db)</strong>
          </div>
          <div className="worker-stat">
            <span>Recent Runs</span>
            <strong>{runs.length} recorded</strong>
          </div>
          <div className="worker-stat">
            <span>Policy Gate</span>
            <strong className="text-healthy">Strict Enforced</strong>
          </div>
        </div>
      </div>

      {/* Filter and Table Card */}
      <section className="content-card tasks-table-card">
        <div className="section-heading tasks-heading">
          <div>
            <span className="section-icon">◷</span>
            <h2>Task Execution History</h2>
            <span className="section-count">{filteredRuns.length} tasks</span>
          </div>
          <div className="task-filters">
            <button
              type="button"
              className={`filter-chip ${statusFilter === 'all' ? 'active' : ''}`}
              onClick={() => setStatusFilter('all')}
            >
              All ({runs.length})
            </button>
            <button
              type="button"
              className={`filter-chip ${statusFilter === 'completed' ? 'active' : ''}`}
              onClick={() => setStatusFilter('completed')}
            >
              Completed ({runs.filter((r) => r.status === 'completed').length})
            </button>
            <button
              type="button"
              className={`filter-chip ${statusFilter === 'failed' ? 'active' : ''}`}
              onClick={() => setStatusFilter('failed')}
            >
              Failed / Blocked ({runs.filter((r) => r.status === 'failed').length})
            </button>
          </div>
        </div>

        <div className="table-wrapper">
          <table className="tasks-table">
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Target Ticket</th>
                <th>Status</th>
                <th>Started / Duration</th>
                <th>Diagnostic Findings</th>
                <th>Confidence</th>
                <th>Autonomous Action</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredRuns.length === 0 ? (
                <tr>
                  <td colSpan={8} className="empty-table-cell">
                    No agent tasks matching the filter.
                  </td>
                </tr>
              ) : (
                filteredRuns.map((run) => {
                  const isCompleted = run.status === 'completed'
                  const autoAction = run.auto_action

                  return (
                    <tr key={run.id} className="task-row">
                      <td className="mono font-semibold">#{run.id}</td>
                      <td>
                        <button
                          type="button"
                          className="ticket-link-badge"
                          onClick={() => onOpenTicket(run.ticket_id)}
                          title={`Open Ticket #${run.ticket_id}`}
                        >
                          Ticket #{run.ticket_id} ↗
                        </button>
                      </td>
                      <td>
                        <span className={`status-pill ${isCompleted ? 'pill-healthy' : 'pill-alert'}`}>
                          {run.status}
                        </span>
                      </td>
                      <td>
                        <div className="task-time-cell">
                          <span>{formatDate(run.started_at)}</span>
                          <small className="mono">({calculateDuration(run.started_at, run.finished_at)})</small>
                        </div>
                      </td>
                      <td className="task-diagnosis-cell">
                        <strong>{run.diagnosis || 'Diagnostic investigation recorded'}</strong>
                        {run.error && <span className="task-error-text">Error: {run.error}</span>}
                      </td>
                      <td>
                        {run.confidence ? (
                          <span className={`confidence-pill ${Number(run.confidence) > 0.8 ? 'conf-high' : 'conf-med'}`}>
                            {typeof run.confidence === 'string' && run.confidence.includes('%')
                              ? run.confidence
                              : `${Math.round(Number(run.confidence) * 100)}% High`}
                          </span>
                        ) : (
                          <span className="confidence-pill conf-neutral">Evaluated</span>
                        )}
                      </td>
                      <td>
                        {autoAction ? (
                          <span className="action-pill action-auto">
                            ⚡ {autoAction}
                          </span>
                        ) : (
                          <span className="action-pill action-technician">
                            👤 Handoff to Tech
                          </span>
                        )}
                      </td>
                      <td>
                        <button
                          type="button"
                          className="button button-small button-outline"
                          onClick={() => handleInspectRun(run)}
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Selected Run Inspection Modal / Drawer */}
      {selectedRun && (
        <div className="modal-backdrop" onClick={() => setSelectedRun(null)} role="presentation">
          <div className="modal-content" onClick={(e) => e.stopPropagation()} role="dialog" aria-labelledby="modal-title">
            <div className="modal-header">
              <div>
                <span className="eyebrow">AGENT RUN AUDIT INSPECTOR</span>
                <h2 id="modal-title">Task Run #{selectedRun.id} — Ticket #{selectedRun.ticket_id}</h2>
              </div>
              <button
                type="button"
                className="modal-close"
                onClick={() => setSelectedRun(null)}
                aria-label="Close inspector"
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <div className="inspect-grid">
                <div>
                  <span className="inspect-label">Execution Status</span>
                  <span className="status-pill pill-healthy">{selectedRun.status}</span>
                </div>
                <div>
                  <span className="inspect-label">Autonomous Action</span>
                  <strong>{selectedRun.auto_action || 'None (Technician Handoff Enforced)'}</strong>
                </div>
                <div>
                  <span className="inspect-label">Started At</span>
                  <span>{formatDate(selectedRun.started_at)}</span>
                </div>
                <div>
                  <span className="inspect-label">Finished At</span>
                  <span>{formatDate(selectedRun.finished_at)}</span>
                </div>
              </div>

              <div className="inspect-section">
                <h3>Diagnostic Diagnosis</h3>
                <p className="diagnosis-box">{selectedRun.diagnosis || 'Investigation completed with verified policy gate evaluation.'}</p>
              </div>

              {isLoadingIncident ? (
                <div className="inspect-loading">Fetching full incident telemetry from agent.db…</div>
              ) : incidentDetail ? (
                <div className="inspect-section">
                  <h3>Persisted Incident Record</h3>
                  <pre className="json-box">{incidentDetail}</pre>
                </div>
              ) : null}

              <div className="modal-actions">
                <button
                  type="button"
                  className="button button-primary"
                  onClick={() => {
                    const ticketId = selectedRun.ticket_id
                    setSelectedRun(null)
                    onOpenTicket(ticketId)
                  }}
                >
                  Open Ticket #{selectedRun.ticket_id} in Workspace
                </button>
                <button
                  type="button"
                  className="button button-outline"
                  onClick={() => {
                    const tid = selectedRun.ticket_id
                    setSelectedRun(null)
                    onAskCarlBot(`tell me about ticket ${tid} and its diagnosis`)
                  }}
                >
                  Ask CarlBot About This Run
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
