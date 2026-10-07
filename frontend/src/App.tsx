import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  addTicketNote,
  getAgentStatus,
  getTicket,
  listAssets,
  listTickets,
  queryTickets,
  runAssetDiagnostics,
  resetSimulation,
  runInvestigation,
  simulateFault,
} from './api'
import type { DiagnosticProbe, TicketChatMatch } from './api'
import type { AgentStatus, Asset, Ticket, TicketStatus } from './types'
import './App.css'

type View = 'tickets' | 'assets'
type ServiceName = 'helpdesk' | 'portal' | 'agent'
type ServiceErrors = Partial<Record<ServiceName, string>>

const statusLabels: Record<TicketStatus, string> = {
  open: 'Open',
  in_progress: 'In progress',
  pending_technician: 'Pending technician',
  ready_for_verification: 'Ready to verify',
  resolved: 'Resolved',
  closed: 'Closed',
}

const faultOptions = [
  { value: 'rtsp_down', label: 'RTSP stream unavailable' },
  { value: 'poe_off', label: 'PoE power off' },
  { value: 'rtsp_auth_failure', label: 'RTSP authentication failure' },
  { value: 'ai_service_down', label: 'AI service down' },
  { value: 'network_down', label: 'Network unreachable' },
]

type ChatMessage = {
  role: 'user' | 'assistant'
  text: string
  matches?: TicketChatMatch[]
}

function ticketIdFromLocation(): number | null {
  const ticketId = new URLSearchParams(window.location.search).get('ticket_id')
  if (!ticketId || !/^\d+$/.test(ticketId)) return null
  const parsed = Number(ticketId)
  return Number.isSafeInteger(parsed) ? parsed : null
}

function faultOptionsFor(asset: Asset) {
  return faultOptions.filter(({ value }) => {
    if (value === 'poe_off') return asset.type === 'camera'
    if (value === 'ai_service_down') return asset.type === 'ai_box'
    if (value === 'rtsp_down' || value === 'rtsp_auth_failure') return asset.type === 'camera' || asset.type === 'nvr'
    return true
  })
}

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Unknown'
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

function StatusBadge({ status }: { status: string }) {
  const knownStatus = status in statusLabels ? statusLabels[status as TicketStatus] : status
  return <span className={`status-badge status-${status}`}>{knownStatus.replaceAll('_', ' ')}</span>
}

function PriorityBadge({ priority }: { priority: string }) {
  return (
    <span className={`priority-badge priority-${priority.toLowerCase()}`}>
      <span className="priority-dot" />
      {priority}
    </span>
  )
}

function Signal({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`signal ${ok ? 'signal-ok' : 'signal-error'}`}>
      <span className="signal-dot" />
      {label}
    </span>
  )
}

function App() {
  const [view, setView] = useState<View>('tickets')
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null)
  const [selectedTicketId, setSelectedTicketId] = useState<number | null>(ticketIdFromLocation)
  const [ticketDetail, setTicketDetail] = useState<Ticket | null>(null)
  const [serviceErrors, setServiceErrors] = useState<ServiceErrors>({})
  const [detailError, setDetailError] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [detailLoadedTicketId, setDetailLoadedTicketId] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [refreshKey, setRefreshKey] = useState(0)
  const [notice, setNotice] = useState('')
  const [noteDraft, setNoteDraft] = useState('')
  const [isSavingNote, setIsSavingNote] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [faultByAsset, setFaultByAsset] = useState<Record<string, string>>({})
  const [isChangingLabState, setIsChangingLabState] = useState<string | null>(null)
  const [chatDraft, setChatDraft] = useState('')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { role: 'assistant', text: 'Hi, I can look up tickets and summarize what’s recorded. Try asking about a site, camera, or ticket number.' },
  ])
  const [isChatLoading, setIsChatLoading] = useState(false)

  const refreshWorkspace = useCallback(async () => {
    const [ticketResult, assetResult, agentResult] = await Promise.allSettled([
      listTickets(),
      listAssets(),
      getAgentStatus(),
    ])

    setServiceErrors((current) => {
      const next = { ...current }
      if (ticketResult.status === 'fulfilled') delete next.helpdesk
      else next.helpdesk = ticketResult.reason instanceof Error ? ticketResult.reason.message : 'Ticket service unavailable'
      if (assetResult.status === 'fulfilled') delete next.portal
      else next.portal = assetResult.reason instanceof Error ? assetResult.reason.message : 'Portal service unavailable'
      if (agentResult.status === 'fulfilled') delete next.agent
      else next.agent = agentResult.reason instanceof Error ? agentResult.reason.message : 'Agent service unavailable'
      return next
    })

    if (ticketResult.status === 'fulfilled') {
      setTickets(ticketResult.value)
    }
    if (assetResult.status === 'fulfilled') setAssets(assetResult.value)
    if (agentResult.status === 'fulfilled') setAgentStatus(agentResult.value)
    setIsLoading(false)
  }, [])

  useEffect(() => {
    const initialRefresh = window.setTimeout(() => void refreshWorkspace(), 0)
    const timer = window.setInterval(() => void refreshWorkspace(), 4000)
    return () => {
      window.clearTimeout(initialRefresh)
      window.clearInterval(timer)
    }
  }, [refreshWorkspace])

  useEffect(() => {
    function syncTicketFromLocation() {
      const ticketId = ticketIdFromLocation()
      setSelectedTicketId(ticketId)
      setView('tickets')
      setTicketDetail(null)
      setDetailLoadedTicketId(null)
      setDetailError('')
    }
    window.addEventListener('popstate', syncTicketFromLocation)
    return () => window.removeEventListener('popstate', syncTicketFromLocation)
  }, [])

  useEffect(() => {
    if (selectedTicketId === null) {
      return
    }

    let active = true
    getTicket(selectedTicketId)
      .then((ticket) => {
        if (!active) return
        setTicketDetail(ticket)
        setDetailError('')
      })
      .catch((error: unknown) => {
        if (!active) return
        setTicketDetail(null)
        setDetailError(error instanceof Error ? error.message : 'Ticket details could not be loaded')
      })
      .finally(() => {
        if (active) setDetailLoadedTicketId(selectedTicketId)
      })

    return () => {
      active = false
    }
  }, [selectedTicketId, refreshKey])

  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(''), 4500)
    return () => window.clearTimeout(timer)
  }, [notice])

  const filteredTickets = useMemo(() => {
    const term = search.trim().toLowerCase()
    return tickets.filter((ticket) => {
      const matchesSearch =
        !term ||
        [ticket.id, ticket.title, ticket.description, ticket.site_id, ticket.asset_id]
          .some((value) => String(value).toLowerCase().includes(term))
      const matchesStatus = statusFilter === 'all' ||
        (statusFilter === 'active' ? !['resolved', 'closed'].includes(ticket.status) : ticket.status === statusFilter)
      const matchesPriority = priorityFilter === 'all' || ticket.priority === priorityFilter
      return matchesSearch && matchesStatus && matchesPriority
    })
  }, [tickets, search, statusFilter, priorityFilter])

  const selectedTicket =
    selectedTicketId === null
      ? null
      : ticketDetail?.id === selectedTicketId
        ? ticketDetail
        : tickets.find((ticket) => ticket.id === selectedTicketId) ?? null
  const isDetailLoading = selectedTicketId !== null && detailLoadedTicketId !== selectedTicketId
  const openCount = tickets.filter((ticket) => !['resolved', 'closed'].includes(ticket.status)).length
  const ticketRuns = agentStatus?.recent_runs.filter((run) => run.ticket_id === selectedTicketId) ?? []
  const latestRun = ticketRuns[0]
  const ticketError = serviceErrors.helpdesk
  const agentError = serviceErrors.agent

  async function handleInvestigation() {
    if (!selectedTicketId) return
    setIsRunning(true)
    setNotice('')
    try {
      const result = await runInvestigation(selectedTicketId)
      setNotice(`Investigation completed with state: ${result.state.replaceAll('_', ' ')}.`)
      setRefreshKey((key) => key + 1)
      await refreshWorkspace()
    } catch (error) {
      setNotice(`Investigation request failed: ${error instanceof Error ? error.message : 'Agent service error'}`)
    } finally {
      setIsRunning(false)
    }
  }

  async function handleAddNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedTicketId || !noteDraft.trim()) return
    setIsSavingNote(true)
    try {
      await addTicketNote(selectedTicketId, noteDraft.trim())
      setNoteDraft('')
      setNotice('Technician note added to the helpdesk record.')
      setRefreshKey((key) => key + 1)
      await refreshWorkspace()
    } catch (error) {
      setNotice(`Note was not saved: ${error instanceof Error ? error.message : 'Helpdesk service error'}`)
    } finally {
      setIsSavingNote(false)
    }
  }

  async function handleFaultChange(asset: Asset) {
    const fault = faultByAsset[asset.asset_id]
    if (!fault) return
    setIsChangingLabState(asset.asset_id)
    try {
      await simulateFault(asset.asset_id, fault)
      setNotice(`Simulated ${fault.replaceAll('_', ' ')} on ${asset.asset_id}. The lab monitor may create a ticket.`)
      setFaultByAsset((current) => ({ ...current, [asset.asset_id]: '' }))
      await refreshWorkspace()
    } catch (error) {
      setNotice(`Simulation request failed: ${error instanceof Error ? error.message : 'Portal service error'}`)
    } finally {
      setIsChangingLabState(null)
    }
  }

  async function handleResetAsset(asset: Asset) {
    setIsChangingLabState(asset.asset_id)
    try {
      await resetSimulation(asset.asset_id)
      setNotice(`Simulation state reset for ${asset.asset_id}.`)
      setFaultByAsset((current) => ({ ...current, [asset.asset_id]: '' }))
      await refreshWorkspace()
    } catch (error) {
      setNotice(`Reset request failed: ${error instanceof Error ? error.message : 'Portal service error'}`)
    } finally {
      setIsChangingLabState(null)
    }
  }

  async function handleChat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const message = chatDraft.trim()
    if (!message || isChatLoading) return
    if (message === '/clear') {
      setChatMessages([])
      setChatDraft('')
      setNotice('Conversation context cleared. Ticket and system data were not changed.')
      return
    }
    setChatDraft('')
    setChatMessages((messages) => [...messages, { role: 'user', text: message }])
    setIsChatLoading(true)
    try {
      const result = await queryTickets(message)
      setChatMessages((messages) => [...messages, {
        role: 'assistant',
        text: result.answer,
        matches: result.matches,
      }])
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Helpdesk service error'
      setChatMessages((messages) => [...messages, {
        role: 'assistant',
        text: `I could not search ticket records: ${detail}`,
      }])
    } finally {
      setIsChatLoading(false)
    }
  }

  function selectTicket(ticketId: number) {
    window.history.pushState({}, '', `/?ticket_id=${ticketId}`)
    setSelectedTicketId(ticketId)
    setDetailLoadedTicketId(null)
    setTicketDetail(null)
    setDetailError('')
    setView('tickets')
  }

  function returnToQueue() {
    window.history.pushState({}, '', window.location.pathname)
    setSelectedTicketId(null)
    setTicketDetail(null)
    setDetailLoadedTicketId(null)
    setView('tickets')
  }

  const activeError = view === 'tickets' ? ticketError : serviceErrors.portal

  return (
    <div className="app-shell">
      <header className="brand-header">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">C</div>
          <div>
            <div className="brand-name">CarlBot <span>Support</span></div>
            <div className="brand-caption">TECHNICAL OPERATIONS DESK</div>
          </div>
        </div>
        <div className="header-center"><span className="environment-tag"><span /> SIMULATED LAB</span></div>
        <div className="header-account">
          <span className="header-operator">Technician workspace</span>
          <span className="operator-avatar">T</span>
        </div>
      </header>

      <nav className="primary-nav" aria-label="Primary navigation">
        <button className="nav-item nav-disabled" type="button" disabled title="Not available in this preview"><span className="nav-glyph">⌂</span>Dashboard</button>
        <button className="nav-item nav-disabled" type="button" disabled title="Not available in this preview"><span className="nav-glyph">◷</span>Tasks</button>
        <button className={`nav-item ${view === 'tickets' ? 'nav-active' : ''}`} type="button" onClick={returnToQueue}><span className="nav-glyph">▤</span>Tickets <span className="nav-count">{openCount}</span></button>
        <button className={`nav-item ${view === 'assets' ? 'nav-active' : ''}`} type="button" onClick={() => setView('assets')}><span className="nav-glyph">⌘</span>Assets</button>
        <button className="nav-item nav-disabled" type="button" disabled title="Not available in this preview"><span className="nav-glyph">▧</span>Knowledge</button>
        <span className="nav-spacer" />
        <span className="nav-section-label">WORKSPACE</span>
        <span className="nav-user">SITE-104 · North campus</span>
      </nav>

      <div className="ticket-toolbar">
        <div className="toolbar-links">
          <button className={view === 'tickets' && statusFilter === 'active' ? 'toolbar-active' : ''} onClick={() => { returnToQueue(); setStatusFilter('active') }} type="button">Open Tickets <span>{openCount}</span></button>
          <button className={view === 'tickets' && statusFilter === 'all' ? 'toolbar-active' : ''} onClick={() => { returnToQueue(); setStatusFilter('all') }} type="button">All Tickets</button>
          <button className={view === 'tickets' && statusFilter === 'closed' ? 'toolbar-active' : ''} onClick={() => { returnToQueue(); setStatusFilter('closed') }} type="button">Closed</button>
          <button onClick={() => setView('assets')} type="button">Asset Inventory</button>
        </div>
        <div className="toolbar-status">
          <Signal ok={!ticketError} label={ticketError ? 'Helpdesk offline' : 'Helpdesk connected'} />
          <Signal ok={!serviceErrors.portal} label={serviceErrors.portal ? 'Portal offline' : 'Portal connected'} />
          <Signal ok={!agentError && Boolean(agentStatus?.running)} label={agentError ? 'Agent unavailable' : agentStatus?.running ? 'Agent monitoring' : 'Agent stopped'} />
        </div>
      </div>

      {notice && <div className="notice-banner" role="status">{notice}<button onClick={() => setNotice('')} aria-label="Dismiss message" type="button">×</button></div>}

      <main className="workspace">
        {view === 'tickets' ? (
          <section className={`ticket-page ${selectedTicketId === null ? 'ticket-page-with-chat' : ''}`}>
            {selectedTicketId === null ? (
              <TicketQueue
                tickets={filteredTickets}
                search={search}
                setSearch={setSearch}
                statusFilter={statusFilter}
                setStatusFilter={setStatusFilter}
                priorityFilter={priorityFilter}
                setPriorityFilter={setPriorityFilter}
                isLoading={isLoading}
                error={activeError}
                onSelect={selectTicket}
                onRefresh={() => void refreshWorkspace()}
              />
            ) : selectedTicket ? (
              <TicketDetail
                ticket={selectedTicket}
                asset={assets.find((asset) => asset.asset_id === selectedTicket.asset_id)}
                loading={isDetailLoading}
                error={detailError}
                latestRun={latestRun}
                agentError={agentError}
                noteDraft={noteDraft}
                setNoteDraft={setNoteDraft}
                onSubmitNote={handleAddNote}
                isSavingNote={isSavingNote}
                onRun={handleInvestigation}
                isRunning={isRunning}
                onBack={returnToQueue}
              />
            ) : (
              <div className="state-panel"><div className={detailError ? 'state-symbol' : 'loading-spinner'}>{detailError ? '!' : null}</div><h2>{detailError ? 'Ticket details unavailable' : 'Loading ticket details'}</h2><p>{detailError || 'Fetching the full helpdesk record…'}</p><button className="button button-outline" type="button" onClick={() => setRefreshKey((key) => key + 1)}>Try again</button></div>
            )}
            <TicketLookupChat
              chatMessages={chatMessages}
              chatDraft={chatDraft}
              isLoading={isChatLoading}
              setChatDraft={setChatDraft}
              onChat={handleChat}
              onOpenTicket={selectTicket}
            />
          </section>
        ) : (
          <AssetInventory
            assets={assets}
            error={serviceErrors.portal}
            isLoading={isLoading}
            faultByAsset={faultByAsset}
            setFaultByAsset={setFaultByAsset}
            onSimulate={handleFaultChange}
            onReset={handleResetAsset}
            isChanging={isChangingLabState}
          />
        )}
      </main>

      <footer className="app-footer">
        <span>CARLBOT SUPPORT · EMULATED ENVIRONMENT ONLY</span>
        <span>Local lab <i /> No production systems connected</span>
      </footer>
    </div>
  )
}

interface TicketQueueProps {
  tickets: Ticket[]
  search: string
  setSearch: (value: string) => void
  statusFilter: string
  setStatusFilter: (value: string) => void
  priorityFilter: string
  setPriorityFilter: (value: string) => void
  isLoading: boolean
  error?: string
  onSelect: (ticketId: number) => void
  onRefresh: () => void
}

function TicketQueue({
  tickets, search, setSearch, statusFilter, setStatusFilter, priorityFilter,
  setPriorityFilter, isLoading, error, onSelect, onRefresh,
}: TicketQueueProps) {
  return (
    <section className="queue-panel" aria-labelledby="queue-title">
      <div className="page-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-dot" /> SERVICE DESK / QUEUE</div>
          <h1 id="queue-title">Ticket queue</h1>
          <p>Review active incidents and technician handoffs across the emulated lab.</p>
        </div>
        <button className="button button-outline" type="button" onClick={onRefresh}><span className="button-icon">↻</span> Refresh queue</button>
      </div>

      <div className="queue-toolbar">
        <label className="search-field">
          <span aria-hidden="true" className="search-icon">⌕</span>
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search tickets, assets, sites..." aria-label="Search tickets" />
        </label>
        <label className="filter-control">
          <span>Status</span>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} aria-label="Filter by status">
            <option value="all">All statuses</option>
            <option value="active">Active tickets</option>
            {Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label className="filter-control">
          <span>Priority</span>
          <select value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)} aria-label="Filter by priority">
            <option value="all">All priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </label>
        <button className="icon-button" aria-label="More queue options" type="button">•••</button>
      </div>

      <div className="queue-meta">
        <span><strong>{tickets.length}</strong> {tickets.length === 1 ? 'ticket' : 'tickets'} <span className="meta-divider">/</span> Updated just now</span>
        <span className="queue-meta-right"><span className="tiny-green-dot" /> Live queue</span>
      </div>

      {error ? (
        <div className="state-panel state-error"><div className="state-symbol">!</div><h2>Ticket service unavailable</h2><p>{error}</p><button className="button button-outline" type="button" onClick={onRefresh}>Try again</button></div>
      ) : isLoading ? (
        <div className="state-panel"><div className="loading-spinner" /><h2>Loading ticket queue</h2><p>Connecting to the simulated helpdesk...</p></div>
      ) : tickets.length === 0 ? (
        <div className="state-panel"><div className="state-symbol">⌕</div><h2>No tickets match these filters</h2><p>Try a different status, priority, or search term.</p></div>
      ) : (
        <div className="table-scroll">
          <table className="ticket-table">
            <thead><tr><th className="check-column"><input type="checkbox" aria-label="Select all tickets" /></th><th>Ticket</th><th>Subject</th><th>Status</th><th>Priority</th><th>Site / Asset</th><th>AI status</th><th>Updated</th><th aria-label="Row actions" /></tr></thead>
            <tbody>
              {tickets.map((ticket) => (
                <tr key={ticket.id} onClick={() => onSelect(ticket.id)} tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter') onSelect(ticket.id) }}>
                  <td className="check-column"><input type="checkbox" aria-label={`Select ticket ${ticket.id}`} onClick={(event) => event.stopPropagation()} /></td>
                  <td className="ticket-number">#{ticket.id}</td>
                  <td className="subject-cell"><button type="button" onClick={(event) => { event.stopPropagation(); onSelect(ticket.id) }}>{ticket.title}</button><small>{ticket.description}</small></td>
                  <td><StatusBadge status={ticket.status} /></td>
                  <td><PriorityBadge priority={ticket.priority} /></td>
                  <td><span className="site-cell">{ticket.site_id}</span><small className="asset-subtext">{ticket.asset_id}</small></td>
                  <td><AiState state={ticket.ai_state} /></td>
                  <td className="updated-cell">{formatDate(ticket.updated_at)}</td>
                  <td className="row-more">···</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="queue-pagination"><span>Showing <strong>{tickets.length}</strong> of connected records</span><div><button type="button" disabled>← Previous</button><button type="button" disabled>Next →</button></div></div>
    </section>
  )
}

function AiState({ state }: { state: string | null }) {
  if (!state || state === 'new') return <span className="ai-state ai-state-new"><span /> Not started</span>
  if (state === 'investigating') return <span className="ai-state ai-state-live"><span /> Investigating</span>
  if (state === 'awaiting_technician') return <span className="ai-state ai-state-wait"><span /> Handoff</span>
  return <span className="ai-state ai-state-done"><span /> {state.replaceAll('_', ' ')}</span>
}

interface TicketDetailProps {
  ticket: Ticket
  asset?: Asset
  loading: boolean
  error: string
  latestRun?: AgentStatus['recent_runs'][number]
  agentError?: string
  noteDraft: string
  setNoteDraft: (value: string) => void
  onSubmitNote: (event: FormEvent<HTMLFormElement>) => void
  isSavingNote: boolean
  onRun: () => void
  isRunning: boolean
  onBack: () => void
}

function TicketDetail({
  ticket, asset, loading, error, latestRun, agentError, noteDraft, setNoteDraft,
  onSubmitNote, isSavingNote, onRun, isRunning, onBack,
}: TicketDetailProps) {
  const handoff = ticket.status === 'pending_technician' || ticket.ai_state === 'awaiting_technician'
  const handoffInstruction = [...(ticket.notes ?? [])]
    .reverse()
    .flatMap((note) => note.body.split('\n'))
    .find((line) => line.startsWith('Technician action:'))
    ?.replace('Technician action:', '')
    .trim()
  const recoveryVerified = ticket.status === 'resolved' && Boolean(ticket.resolution)
  const [probeResults, setProbeResults] = useState<DiagnosticProbe[] | null>(null)
  const [isProbing, setIsProbing] = useState(false)
  const [probedAt, setProbedAt] = useState('')

  async function handleRunDiagnostics() {
    if (!asset) return
    setIsProbing(true)
    try {
      setProbeResults(await runAssetDiagnostics(asset))
      setProbedAt(new Date().toISOString())
    } finally {
      setIsProbing(false)
    }
  }

  return (
    <section className="detail-page">
      <div className="detail-breadcrumb"><button onClick={onBack} type="button">← Ticket queue</button><span>/</span><span>Ticket #{ticket.id}</span></div>
      <div className="detail-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-dot" /> INCIDENT RECORD · {ticket.site_id}</div>
          <h1>{ticket.title}</h1>
          <div className="detail-title-meta"><span className="ticket-number">#{ticket.id}</span><StatusBadge status={ticket.status} /><PriorityBadge priority={ticket.priority} /></div>
        </div>
        <div className="detail-actions">
          <button className="button button-outline" type="button" onClick={onBack}>Back to queue</button>
          <button className="button button-primary" type="button" onClick={onRun} disabled={isRunning || Boolean(agentError) || handoff}>
            {isRunning ? <><span className="button-spinner" /> Running investigation</> : handoff ? 'Technician action required' : <><span className="button-icon">✦</span> Run investigation</>}
          </button>
        </div>
      </div>

      <div className="ticket-facts">
        <Fact label="Site" value={ticket.site_id} />
        <Fact label="Affected asset" value={ticket.asset_id} monospace />
        <Fact label="Created" value={formatDate(ticket.created_at)} />
        <Fact label="Last updated" value={formatDate(ticket.updated_at)} />
        <Fact label="AI state" value={ticket.ai_state?.replaceAll('_', ' ') || 'Not started'} />
      </div>

      {(error || agentError) && <div className="inline-error">{error ? `Ticket detail error: ${error}` : `Agent service error: ${agentError}`}</div>}
      {loading && <div className="detail-loading"><span className="loading-spinner" /> Refreshing ticket record…</div>}

      <div className="detail-layout">
        <div className="detail-main-column">
          <section className="content-card conversation-card">
            <div className="section-heading"><div><span className="section-icon">☷</span><h2>Conversation</h2><span className="section-count">{(ticket.notes?.length ?? 0) + 1}</span></div><button className="text-button" type="button">Activity history⌄</button></div>
            <article className="thread-item">
              <div className="thread-avatar reporter-avatar">R</div>
              <div className="thread-content">
                <div className="thread-author"><strong>Lab monitor</strong><span className="author-tag">AUTOMATED</span><time>{formatDate(ticket.created_at)}</time></div>
                <p>{ticket.description}</p>
                <div className="thread-source"><span className="source-dot" /> Initial incident report · simulated environment</div>
              </div>
            </article>
            {ticket.notes?.map((note, index) => (
              <article className="thread-item" key={`${note.created_at}-${index}`}>
                <div className={`thread-avatar ${note.author.toLowerCase().includes('agent') ? 'ai-avatar' : 'tech-avatar'}`}>{note.author.slice(0, 1).toUpperCase()}</div>
                <div className="thread-content">
                  <div className="thread-author"><strong>{note.author}</strong><span className="author-tag">{note.author.toLowerCase().includes('agent') ? 'COPILOT' : 'TECHNICIAN'}</span><time>{formatDate(note.created_at)}</time></div>
                  <p className="note-body">{note.body}</p>
                </div>
              </article>
            ))}
            {ticket.resolution && (
              <div className="resolution-row"><span className="resolution-check">✓</span><div><strong>Resolution recorded</strong><p>{ticket.resolution}</p></div></div>
            )}
            <form className="note-composer" onSubmit={onSubmitNote}>
              <div className="composer-heading"><span className="composer-avatar">T</span><strong>Internal note</strong><span>Visible to technicians only</span></div>
              <textarea value={noteDraft} onChange={(event) => setNoteDraft(event.target.value)} placeholder="Add an observation or technician note..." rows={3} aria-label="Internal technician note" />
              <div className="composer-footer"><span>Keep notes factual and evidence-based.</span><button className="button button-primary" type="submit" disabled={!noteDraft.trim() || isSavingNote}>{isSavingNote ? 'Saving…' : 'Add note'}</button></div>
            </form>
          </section>

          <section className="content-card evidence-section">
            <div className="section-heading">
              <div><span className="section-icon">⌁</span><h2>Incident evidence</h2></div>
              <button className="text-button" type="button" disabled={!asset || isProbing} onClick={() => void handleRunDiagnostics()}>{isProbing ? 'Checking…' : 'Run live checks'}</button>
            </div>
            <div className="evidence-grid">
              <div className="probe-heading"><span>LIVE DIAGNOSTICS · EMULATED PORTAL</span>{probedAt && <time>Observed {formatDate(probedAt)}</time>}</div>
              {probeResults ? probeResults.map((probe) => (
                <div className={`probe-row ${probe.ok ? 'probe-ok' : 'probe-fail'}`} key={probe.name}>
                  <span className="probe-state">{probe.ok ? '✓' : '!'}</span>
                  <strong>{probe.name}</strong>
                  <span>{probe.detail}</span>
                </div>
              )) : <div className="probe-empty">Run checks to view current emulator health, reachability and stream results.</div>}
              <Evidence label="Root cause" value={ticket.root_cause || 'Not established'} tone={ticket.root_cause ? 'blue' : 'muted'} />
              <Evidence label="Recorded diagnosis" value={ticket.ai_summary || 'Investigation has not produced a summary yet.'} tone={ticket.ai_summary ? 'blue' : 'muted'} />
              {latestRun && <Evidence label="Latest agent run" value={`${latestRun.status === 'success' ? 'Workflow completed' : latestRun.status}${latestRun.auto_action ? ` · ${latestRun.auto_action}` : ''}`} tone={latestRun.status === 'error' ? 'orange' : 'blue'} />}
            </div>
          </section>
        </div>

        <aside className="copilot-column">
          <section className="copilot-card">
            <div className="copilot-head"><div className="copilot-title"><span className="copilot-spark">✦</span><div><h2>AI copilot</h2><span>Investigation assistant</span></div></div><span className="copilot-mode">LAB</span></div>
            <div className="copilot-content">
              {agentError ? (
                <div className="copilot-message copilot-error"><strong>Agent service unavailable</strong><p>{agentError}</p></div>
              ) : handoff ? (
                <div className="handoff-card"><div className="handoff-top"><span className="handoff-icon">!</span><div><strong>Technician action required</strong><span>Automation has stopped safely</span></div></div><p>Recorded assessment: {ticket.root_cause || ticket.ai_summary || 'The current fault requires technician review. No physical repair was attempted.'}</p><div className="handoff-next"><span>NEXT STEP · FROM AGENT NOTE</span><strong>{handoffInstruction || 'Review the simulated work order and record physical observations before requesting further action.'}</strong></div></div>
              ) : (
                <div className="diagnosis-card">
                  <div className="diagnosis-overline"><span className="diagnosis-pulse" /> CURRENT ASSESSMENT</div>
                  <h3>{ticket.root_cause || (ticket.ai_state === 'investigating' ? 'Investigation in progress' : 'No diagnosis recorded')}</h3>
                  <p>{ticket.ai_summary || (ticket.ai_state === 'investigating' ? 'The agent is collecting evidence. Refresh this record for its latest findings.' : 'Run an investigation to let the policy-controlled agent examine this synthetic incident.')}</p>
                  {latestRun?.confidence && <div className="confidence-row"><span>Recorded confidence</span><strong>{latestRun.confidence}</strong></div>}
                </div>
              )}

              <div className="copilot-evidence">
                <div className="mini-section-title">EVIDENCE SOURCES</div>
                <div className="source-row"><span className="source-check">✓</span><div><strong>Ticket record</strong><small>Helpdesk · #{ticket.id}</small></div><span className="source-open">↗</span></div>
                {latestRun ? (
                  <div className="source-row"><span className="source-check">✓</span><div><strong>Agent run</strong><small>{formatDate(latestRun.started_at)} · {latestRun.status === 'success' ? 'workflow completed' : latestRun.status}</small></div><span className="source-open">↗</span></div>
                ) : (
                  <div className="source-row source-pending"><span className="source-wait">○</span><div><strong>Diagnostics and history</strong><small>Available after investigation</small></div></div>
                )}
              </div>

              <div className="safe-action-card">
                <div className="safe-action-head"><span>SAFE ACTION REQUEST</span><span className="policy-lock">POLICY-GATED</span></div>
                <p>Ask the backend agent to investigate. Any recovery action is independently checked by its policy engine.</p>
                <button className="button button-action" type="button" disabled={isRunning || Boolean(agentError) || handoff} onClick={onRun}>{isRunning ? 'Investigation running…' : handoff ? 'Awaiting technician' : 'Request investigation'}<span>→</span></button>
                <small>Only simulated RTSP reconnect or AI service restart can run automatically.</small>
              </div>

              {latestRun?.error && <div className="run-error"><strong>Latest run error</strong><p>{latestRun.error}</p></div>}
              {latestRun?.auto_action && <div className={`action-result ${recoveryVerified ? '' : 'action-unverified'}`}><span>{recoveryVerified ? '✓' : '!'}</span><div><strong>{recoveryVerified ? 'Recovery verified' : 'Automatic action recorded'}</strong><small>{recoveryVerified ? ticket.resolution : `${latestRun.auto_action} · no verified resolution recorded`}</small></div></div>}
            </div>
          </section>

        </aside>
      </div>
    </section>
  )
}

function TicketLookupChat({
  chatMessages, chatDraft, isLoading, setChatDraft, onChat, onOpenTicket,
}: {
  chatMessages: ChatMessage[]
  chatDraft: string
  isLoading: boolean
  setChatDraft: (value: string) => void
  onChat: (event: FormEvent<HTMLFormElement>) => void
  onOpenTicket: (ticketId: number) => void
}) {
  return (
    <section className="chat-card chat-lookup-global" aria-labelledby="ticket-chat-title">
      <div className="chat-heading">
        <div><span className="chat-icon">✦</span><div className="chat-title-copy"><h2 id="ticket-chat-title">CarlBot</h2><span>Ticket assistant</span></div></div>
        <span className="chat-readonly">READ ONLY</span>
      </div>
      <p className="chat-intro">Ask about a site, camera, or ticket number.</p>
      <div className="chat-messages" aria-live="polite" aria-busy={isLoading}>
        {chatMessages.map((message, index) => (
          <div
            key={`${index}-${message.role}`}
            className={`chat-message chat-${message.role}`}
          >
            {message.text}
            {message.matches?.some((match) => match.source === 'live_helpdesk' && /^\d+$/.test(match.ticket_id)) && (
              <div className="chat-ticket-links" aria-label="Open matching tickets">
                {message.matches
                  .filter((match) => match.source === 'live_helpdesk' && /^\d+$/.test(match.ticket_id))
                  .slice(0, 3)
                  .map((match) => {
                    const ticketId = Number(match.ticket_id)
                    return (
                      <a
                        key={match.ticket_id}
                        href={`/?ticket_id=${ticketId}`}
                        onClick={(event) => {
                          event.preventDefault()
                          onOpenTicket(ticketId)
                        }}
                      >
                        Open #{match.ticket_id} · {match.title}
                      </a>
                    )
                  })}
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="chat-message chat-searching">Checking ticket records…</div>
        )}
        {chatMessages.length === 0 && !isLoading && (
          <div className="chat-cleared">Conversation context cleared. Ticket and system data were not changed.</div>
        )}
      </div>
      <form className="chat-form" onSubmit={onChat}>
        <input
          value={chatDraft}
          onChange={(event) => setChatDraft(event.target.value)}
          placeholder="Ask about a ticket, site, or camera…"
          aria-label="Ask CarlBot about tickets"
        />
        <button type="submit" aria-label="Search tickets" disabled={!chatDraft.trim() || isLoading}>↑</button>
      </form>
      <div className="chat-disclaimer">Read-only ticket lookup. <span>/clear</span> clears this conversation.</div>
    </section>
  )
}

function Fact({ label, value, monospace = false }: { label: string; value: string; monospace?: boolean }) {
  return <div className="fact"><span>{label}</span><strong className={monospace ? 'mono' : ''}>{value}</strong></div>
}

function Evidence({ label, value, tone }: { label: string; value: string; tone: 'blue' | 'muted' | 'green' | 'orange' }) {
  return <div className={`evidence-card evidence-${tone}`}><span className="evidence-indicator" /><div><span>{label}</span><strong>{value}</strong></div></div>
}

interface AssetInventoryProps {
  assets: Asset[]
  error?: string
  isLoading: boolean
  faultByAsset: Record<string, string>
  setFaultByAsset: (value: Record<string, string>) => void
  onSimulate: (asset: Asset) => void
  onReset: (asset: Asset) => void
  isChanging: string | null
}

function AssetInventory({
  assets, error, isLoading, faultByAsset, setFaultByAsset,
  onSimulate, onReset, isChanging,
}: AssetInventoryProps) {
  const cameras = assets.filter((asset) => asset.type === 'camera')
  const recorders = assets.filter((asset) => asset.type === 'nvr')
  const otherInfrastructure = assets.filter((asset) => asset.type !== 'camera' && asset.type !== 'nvr')
  const unassignedCameras = cameras.filter((camera) => !recorders.some((recorder) => recorder.asset_id === camera.nvr_id))
  return (
    <section className="asset-page">
      <div className="page-heading">
        <div><div className="eyebrow"><span className="eyebrow-dot" /> LAB INVENTORY / SITE-104</div><h1>Asset inventory</h1><p>Emulated cameras, recorder and AI infrastructure. Controls affect simulated state only.</p></div>
        <span className="asset-total">{assets.length} synthetic assets</span>
      </div>
      <div className="asset-warning"><span>ⓘ</span><div><strong>Simulation controls</strong><p>Fault injection and reset operate only on this local lab emulator. The agent may automatically run only policy-approved safe actions.</p></div></div>
      {error ? <div className="state-panel state-error"><h2>Portal service unavailable</h2><p>{error}</p></div> : isLoading ? <div className="state-panel"><div className="loading-spinner" /><h2>Loading synthetic inventory</h2></div> : (
        <div className="asset-layout">
          <section className="content-card asset-tree-card">
            <div className="section-heading"><div><span className="section-icon">⌘</span><h2>Equipment tree</h2><span className="section-count">{assets.length}</span></div><span className="subtle-label">SITE-104</span></div>
            <div className="tree-root"><span className="tree-caret">⌄</span><span className="tree-site-icon">⌂</span><strong>North campus</strong><span className="tree-id">SITE-104</span><span className="tree-count">{assets.length}</span></div>
            {recorders.map((recorder) => (
              <div key={recorder.asset_id}>
                <AssetRow asset={recorder} depth={1} fault={faultByAsset[recorder.asset_id] || ''} setFault={(fault) => setFaultByAsset({ ...faultByAsset, [recorder.asset_id]: fault })} onSimulate={onSimulate} onReset={onReset} isChanging={isChanging === recorder.asset_id} />
                {cameras.filter((camera) => camera.nvr_id === recorder.asset_id).map((camera) => <AssetRow key={camera.asset_id} asset={camera} depth={2} fault={faultByAsset[camera.asset_id] || ''} setFault={(fault) => setFaultByAsset({ ...faultByAsset, [camera.asset_id]: fault })} onSimulate={onSimulate} onReset={onReset} isChanging={isChanging === camera.asset_id} />)}
              </div>
            ))}
            {unassignedCameras.map((asset) => <AssetRow key={asset.asset_id} asset={asset} depth={1} fault={faultByAsset[asset.asset_id] || ''} setFault={(fault) => setFaultByAsset({ ...faultByAsset, [asset.asset_id]: fault })} onSimulate={onSimulate} onReset={onReset} isChanging={isChanging === asset.asset_id} />)}
            {otherInfrastructure.map((asset) => <AssetRow key={asset.asset_id} asset={asset} depth={1} fault={faultByAsset[asset.asset_id] || ''} setFault={(fault) => setFaultByAsset({ ...faultByAsset, [asset.asset_id]: fault })} onSimulate={onSimulate} onReset={onReset} isChanging={isChanging === asset.asset_id} />)}
            {assets.length === 0 && <div className="asset-empty">No emulated assets were returned by the portal.</div>}
          </section>
          <section className="asset-summary content-card">
            <div className="section-heading"><div><span className="section-icon">⌁</span><h2>Lab status</h2></div></div>
            <div className="summary-stat"><span>Connected assets</span><strong>{assets.filter((asset) => asset.reachable !== false).length}<small> / {assets.length}</small></strong></div>
            <div className="summary-stat"><span>Active simulated faults</span><strong>{assets.filter((asset) => asset.fault).length}</strong></div>
            <div className="summary-stat"><span>Camera streams healthy</span><strong>{cameras.filter((asset) => asset.rtsp === 'healthy' && !asset.fault).length}<small> / {cameras.length}</small></strong></div>
            <div className="summary-divider" />
            <div className="lab-rule"><span className="rule-lock">⌑</span><div><strong>Human-controlled work</strong><p>Power, cabling, credentials and physical repairs stay with a technician.</p></div></div>
          </section>
        </div>
      )}
    </section>
  )
}

function AssetRow({
  asset, depth, fault, setFault, onSimulate, onReset, isChanging,
}: {
  asset: Asset
  depth: number
  fault: string
  setFault: (fault: string) => void
  onSimulate: (asset: Asset) => void
  onReset: (asset: Asset) => void
  isChanging: boolean
}) {
  const isHealthy = asset.reachable !== false && !asset.fault && asset.rtsp !== 'unavailable' && asset.service !== 'down'
  return (
    <div className={`asset-tree-row depth-${depth}`}>
      <div className="asset-row-main">
        <span className="tree-branch">{depth === 1 ? '├' : '└'}</span>
        <span className={`asset-type-icon asset-${asset.type}`}>{asset.type === 'camera' ? '◉' : asset.type === 'nvr' ? '▣' : '▤'}</span>
        <div className="asset-identity"><strong>{asset.asset_id}</strong><span>{asset.type.replace('_', ' ')}{asset.ip ? ` · ${asset.ip}` : ''}</span></div>
        <Signal ok={isHealthy} label={asset.fault ? asset.fault.replaceAll('_', ' ') : isHealthy ? 'Healthy' : 'Degraded'} />
        <div className="asset-metrics">{asset.rtsp && <span>RTSP <b>{asset.rtsp}</b></span>}{asset.service && <span>Service <b>{asset.service}</b></span>}{typeof asset.cpu === 'number' && <span>CPU <b>{asset.cpu}%</b></span>}</div>
      </div>
      <div className="asset-controls">
        {asset.fault ? (
          <button className="button button-outline button-small" type="button" disabled={isChanging} onClick={() => onReset(asset)}>{isChanging ? 'Resetting…' : 'Reset simulation'}</button>
        ) : (
          <>
            <label className="visually-hidden" htmlFor={`fault-${asset.asset_id}`}>Select simulated fault for {asset.asset_id}</label>
            <select id={`fault-${asset.asset_id}`} value={fault} onChange={(event) => setFault(event.target.value)} aria-label={`Select simulated fault for ${asset.asset_id}`}>
              <option value="">Inject a lab fault…</option>
              {faultOptionsFor(asset).map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
            <button className="button button-small button-outline" type="button" disabled={!fault || isChanging} onClick={() => onSimulate(asset)}>{isChanging ? 'Applying…' : 'Simulate'}</button>
          </>
        )}
      </div>
    </div>
  )
}

export default App
