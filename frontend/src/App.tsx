import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode, type RefObject } from 'react'
import {
  addCustomerReply,
  addTicketNote,
  getAgentStatus,
  getLocalLlmStatus,
  getTicket,
  listAssets,
  listKnowledgeDocuments,
  listPortalEvents,
  listTickets,
  queryTickets,
  runAssetDiagnostics,
  runMonitorNow,
  resetSimulation,
  runInvestigation,
  simulateFault,
  startLocalLlm,
  updateTicketDeskStatus,
} from './api'
import type { ChatTurn, DiagnosticProbe, KnowledgeSource, TicketChatMatch, TicketChatRecommendation } from './api'
import type { AgentStatus, Asset, KnowledgeDocument, LocalLlmStatus, PortalEvent, Ticket, TicketDeskStatus, TicketStatus } from './types'
import { fallbackKnowledgeDocuments } from './knowledgeData'
import { DashboardView } from './components/DashboardView'
import { TasksView } from './components/TasksView'
import { KnowledgeView } from './components/KnowledgeView'
import { CarlBotChatView } from './components/CarlBotChatView'
import { LlmStatusBadge } from './components/LlmStatusBadge'
import './App.css'

type View = 'dashboard' | 'tickets' | 'tasks' | 'knowledge' | 'assets' | 'carlbot'
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
const ticketDeskStatuses: TicketDeskStatus[] = ['Open', 'Answered', 'Closed']

function deskStatus(ticket: Ticket): TicketDeskStatus {
  if (ticket.ticket_status) return ticket.ticket_status
  if (ticket.status === 'closed') return 'Closed'
  if (ticket.status === 'resolved' || ticket.status === 'ready_for_verification') return 'Answered'
  return 'Open'
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
  recommendations?: TicketChatRecommendation[]
  citedTicketIds?: string[]
  citedKnowledgeSources?: string[]
  knowledgeSources?: KnowledgeSource[]
  ticketReplyDraft?: string | null
  reasoningMode?: 'llm' | 'deterministic'
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
  const normalized = status.toLowerCase()
  const knownStatus = statusLabels[status as TicketStatus] ?? ticketDeskStatuses.find((label) => label.toLowerCase() === normalized) ?? status
  return <span className={`status-badge status-${normalized.replaceAll(' ', '_')}`}>{knownStatus.replaceAll('_', ' ')}</span>
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
  const [events, setEvents] = useState<PortalEvent[]>([])
  const [knowledgeDocs, setKnowledgeDocs] = useState<KnowledgeDocument[]>(fallbackKnowledgeDocuments)
  const [isMonitoring, setIsMonitoring] = useState(false)
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [assets, setAssets] = useState<Asset[]>([])
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null)
  const [llmStatus, setLlmStatus] = useState<LocalLlmStatus | null>(null)
  const [isRetryingLlm, setIsRetryingLlm] = useState(false)
  const [selectedTicketId, setSelectedTicketId] = useState<number | null>(ticketIdFromLocation)
  const [ticketDetail, setTicketDetail] = useState<Ticket | null>(null)
  const [serviceErrors, setServiceErrors] = useState<ServiceErrors>({})
  const [detailError, setDetailError] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [detailLoadedTicketId, setDetailLoadedTicketId] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [siteFilter, setSiteFilter] = useState('all')
  const [priorityFilter, setPriorityFilter] = useState('all')
  const [refreshKey, setRefreshKey] = useState(0)
  const [notice, setNotice] = useState('')
  const [noteDraft, setNoteDraft] = useState('')
  const [isSavingNote, setIsSavingNote] = useState(false)
  const [isSavingTicketStatus, setIsSavingTicketStatus] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [faultByAsset, setFaultByAsset] = useState<Record<string, string>>({})
  const [isChangingLabState, setIsChangingLabState] = useState<string | null>(null)
  const [chatDraft, setChatDraft] = useState('')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { role: 'assistant', text: "Hello, I'm Carlbot, ask me anything about the Helpdesk" },
  ])
  const [isChatLoading, setIsChatLoading] = useState(false)
  const chatMessagesRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = chatMessagesRef.current
    if (container) container.scrollTop = container.scrollHeight
  }, [chatMessages, isChatLoading])

  const refreshWorkspace = useCallback(async () => {
    const [ticketResult, assetResult, agentResult, eventResult, knowledgeResult, llmResult] = await Promise.allSettled([
      listTickets(),
      listAssets(),
      getAgentStatus(),
      listPortalEvents(),
      listKnowledgeDocuments(),
      getLocalLlmStatus(),
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
    if (eventResult.status === 'fulfilled') setEvents(eventResult.value)
    if (knowledgeResult.status === 'fulfilled' && knowledgeResult.value.length > 0) {
      setKnowledgeDocs(knowledgeResult.value)
    }
    // A status failure must not surface as a helpdesk outage; the ticket probe owns that signal.
    if (llmResult.status === 'fulfilled') setLlmStatus(llmResult.value)
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
      const matchesStatus = statusFilter === 'all' || deskStatus(ticket) === statusFilter
      const matchesSite = siteFilter === 'all' || ticket.site_id === siteFilter
      const matchesPriority = priorityFilter === 'all' || ticket.priority === priorityFilter
      return matchesSearch && matchesStatus && matchesSite && matchesPriority
    })
  }, [tickets, search, statusFilter, siteFilter, priorityFilter])

  const selectedTicket =
    selectedTicketId === null
      ? null
      : ticketDetail?.id === selectedTicketId
        ? ticketDetail
        : tickets.find((ticket) => ticket.id === selectedTicketId) ?? null
  const isDetailLoading = selectedTicketId !== null && detailLoadedTicketId !== selectedTicketId
  const openCount = tickets.filter((ticket) => deskStatus(ticket) === 'Open').length
  const answeredCount = tickets.filter((ticket) => deskStatus(ticket) === 'Answered').length
  const closedCount = tickets.filter((ticket) => deskStatus(ticket) === 'Closed').length
  const siteOptions = [...new Set(tickets.map((ticket) => ticket.site_id))].sort()
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

  async function handleTicketStatusChange(ticketStatus: TicketDeskStatus) {
    if (!selectedTicketId) return
    setIsSavingTicketStatus(true)
    try {
      await updateTicketDeskStatus(selectedTicketId, ticketStatus)
      setNotice(`Ticket status changed to ${ticketStatus}.`)
      setRefreshKey((key) => key + 1)
      await refreshWorkspace()
    } catch (error) {
      setNotice(`Ticket status was not changed: ${error instanceof Error ? error.message : 'Helpdesk service error'}`)
    } finally {
      setIsSavingTicketStatus(false)
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
    const nextUserMessage: ChatMessage = { role: 'user', text: message }
    const updatedMessages = [...chatMessages, nextUserMessage]
    setChatMessages(updatedMessages)
    setIsChatLoading(true)

    // Build bounded recent conversational history (up to 6 turns)
    const historyPayload: ChatTurn[] = updatedMessages
      .slice(-7, -1)
      .map((msg) => ({
        role: msg.role,
        content: msg.text,
      }))

    try {
      const result = await queryTickets(message, selectedTicketId, historyPayload)
      setChatMessages((messages) => [...messages, {
        role: 'assistant',
        text: result.answer,
        matches: result.matches,
        recommendations: result.recommendations,
        citedTicketIds: result.cited_ticket_ids,
        citedKnowledgeSources: result.cited_knowledge_sources,
        knowledgeSources: result.knowledge_sources,
        ticketReplyDraft: result.ticket_reply_draft,
        reasoningMode: result.reasoning_mode,
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

  async function handlePublishReply(ticketId: number, body: string, messageIndex: number) {
    if (!ticketId || !body.trim()) return
    const idempotencyKey = `reply-${ticketId}-${Date.now()}`
    try {
      const res = await addCustomerReply(ticketId, body.trim(), idempotencyKey)
      setNotice(res.duplicate ? 'Simulated reply was already published.' : 'Published to simulated ticket thread.')
      // Clear the draft preview from this message once published
      setChatMessages((prev) => prev.map((msg, idx) => (
        idx === messageIndex ? { ...msg, ticketReplyDraft: null } : msg
      )))
      setRefreshKey((k) => k + 1)
      await refreshWorkspace()
    } catch (error) {
      setNotice(`Failed to publish reply: ${error instanceof Error ? error.message : 'Helpdesk service error'}`)
    }
  }

  function handleCancelDraft(messageIndex: number) {
    setChatMessages((prev) => prev.map((msg, idx) => (
      idx === messageIndex ? { ...msg, ticketReplyDraft: null } : msg
    )))
  }

  async function handleRetryLlm() {
    setIsRetryingLlm(true)
    try {
      const status = await startLocalLlm()
      setLlmStatus(status)
      setNotice(
        status.ready
          ? 'Local model is ready. Chat can use local inference.'
          : `Local model not ready: ${status.detail}`,
      )
    } catch (error) {
      setNotice(`Local model retry failed: ${error instanceof Error ? error.message : 'Helpdesk service error'}`)
    } finally {
      setIsRetryingLlm(false)
    }
  }

  async function refreshLlmStatus() {
    try {
      setLlmStatus(await getLocalLlmStatus())
    } catch {
      // Non-fatal: keep the last truthful status rather than showing a false outage.
    }
  }

  const handleTriggerMonitor = async () => {
    setIsMonitoring(true)
    try {
      await runMonitorNow()
      setNotice('Agent monitor cycle completed successfully.')
      await refreshWorkspace()
    } catch (error) {
      setNotice(`Monitor request failed: ${error instanceof Error ? error.message : 'Agent service error'}`)
    } finally {
      setIsMonitoring(false)
    }
  }

  const handleNavigate = (
    targetView: View,
    filter?: { site?: string; status?: TicketDeskStatus | 'all' }
  ) => {
    if (filter?.site) setSiteFilter(filter.site)
    if (filter?.status) setStatusFilter(filter.status)
    if (targetView === 'tickets') {
      setSelectedTicketId(null)
      setTicketDetail(null)
    }
    setView(targetView)
  }

  const handleAskCarlBot = (prompt: string) => {
    setChatDraft(prompt)
    setSelectedTicketId(null)
    setView('tickets')
    setTimeout(() => {
      const inputEl = document.querySelector<HTMLInputElement>('.chat-form input')
      if (inputEl) inputEl.focus()
    }, 100)
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

  const ticketChat = (
    <TicketLookupChat
      chatMessages={chatMessages}
      chatDraft={chatDraft}
      isLoading={isChatLoading}
      messagesRef={chatMessagesRef}
      selectedTicketId={selectedTicketId}
      setChatDraft={setChatDraft}
      onChat={handleChat}
      onOpenTicket={selectTicket}
      onPublishReply={handlePublishReply}
      onCancelDraft={handleCancelDraft}
      llmStatus={llmStatus}
      onRetryLlm={() => void handleRetryLlm()}
      isRetryingLlm={isRetryingLlm}
    />
  )

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
        <div className="header-center"><span className="environment-tag"><span /> MULTI-SITE SIMULATED LAB</span></div>
        <div className="header-account">
          <span className="header-operator">Technician workspace</span>
          <span className="operator-avatar">T</span>
        </div>
      </header>

      <nav className="primary-nav" aria-label="Primary navigation">
        <button className={`nav-item ${view === 'dashboard' ? 'nav-active' : ''}`} type="button" onClick={() => setView('dashboard')}>
          <span className="nav-glyph">⌂</span>Dashboard
        </button>
        <button className={`nav-item ${view === 'tasks' ? 'nav-active' : ''}`} type="button" onClick={() => setView('tasks')}>
          <span className="nav-glyph">◷</span>Tasks {agentStatus?.recent_runs.length ? <span className="nav-count">{agentStatus.recent_runs.length}</span> : null}
        </button>
        <button className={`nav-item ${view === 'tickets' ? 'nav-active' : ''}`} type="button" onClick={returnToQueue}>
          <span className="nav-glyph">▤</span>Tickets <span className="nav-count">{openCount}</span>
        </button>
        <button className={`nav-item ${view === 'assets' ? 'nav-active' : ''}`} type="button" onClick={() => setView('assets')}>
          <span className="nav-glyph">⌘</span>Assets
        </button>
        <button className={`nav-item ${view === 'knowledge' ? 'nav-active' : ''}`} type="button" onClick={() => setView('knowledge')}>
          <span className="nav-glyph">▧</span>Knowledge <span className="nav-count">{knowledgeDocs.length}</span>
        </button>
        <button className={`nav-item ${view === 'carlbot' ? 'nav-active' : ''}`} type="button" onClick={() => setView('carlbot')}>
          <span className="nav-glyph">◈</span>CarlBot AI
        </button>
        <span className="nav-spacer" />
        <span className="nav-section-label">WORKSPACE</span>
        <span className="nav-user">{siteOptions.length} emulated sites</span>
      </nav>

      <div className="ticket-toolbar">
        <div className="toolbar-links">
          <button className={view === 'dashboard' ? 'toolbar-active' : ''} onClick={() => setView('dashboard')} type="button">Dashboard</button>
          <button className={view === 'tickets' && statusFilter === 'Open' ? 'toolbar-active' : ''} onClick={() => { returnToQueue(); setStatusFilter('Open') }} type="button">Open <span>{openCount}</span></button>
          <button className={view === 'tickets' && statusFilter === 'Answered' ? 'toolbar-active' : ''} onClick={() => { returnToQueue(); setStatusFilter('Answered') }} type="button">Answered <span>{answeredCount}</span></button>
          <button className={view === 'tickets' && statusFilter === 'Closed' ? 'toolbar-active' : ''} onClick={() => { returnToQueue(); setStatusFilter('Closed') }} type="button">Closed <span>{closedCount}</span></button>
          <button className={view === 'tickets' && statusFilter === 'all' ? 'toolbar-active' : ''} onClick={() => { returnToQueue(); setStatusFilter('all') }} type="button">All Tickets</button>
          <button className={view === 'tasks' ? 'toolbar-active' : ''} onClick={() => setView('tasks')} type="button">Tasks</button>
          <button className={view === 'knowledge' ? 'toolbar-active' : ''} onClick={() => setView('knowledge')} type="button">Knowledge</button>
          <button className={view === 'carlbot' ? 'toolbar-active' : ''} onClick={() => setView('carlbot')} type="button">CarlBot AI</button>
          <button className={view === 'assets' ? 'toolbar-active' : ''} onClick={() => setView('assets')} type="button">Asset Inventory</button>
        </div>
        <div className="toolbar-status">
          <Signal ok={!ticketError} label={ticketError ? 'Helpdesk offline' : 'Helpdesk connected'} />
          <Signal ok={!serviceErrors.portal} label={serviceErrors.portal ? 'Portal offline' : 'Portal connected'} />
          <Signal ok={!agentError && Boolean(agentStatus?.running)} label={agentError ? 'Agent unavailable' : agentStatus?.running ? 'Agent monitoring' : 'Agent stopped'} />
        </div>
      </div>

      {notice && <div className="notice-banner" role="status">{notice}<button onClick={() => setNotice('')} aria-label="Dismiss message" type="button">×</button></div>}

      <main className="workspace">
        {view === 'carlbot' ? (
          <CarlBotChatView
            chatMessages={chatMessages}
            chatDraft={chatDraft}
            setChatDraft={setChatDraft}
            onChat={handleChat}
            isLoading={isChatLoading}
            selectedTicketId={selectedTicketId}
            setSelectedTicketId={setSelectedTicketId}
            tickets={tickets}
            onOpenTicket={selectTicket}
            onPublishReply={handlePublishReply}
            onCancelDraft={handleCancelDraft}
            onClearChat={() => {
              setChatMessages([])
              setChatDraft('')
              setNotice('Conversation context cleared. Ticket and system data were not changed.')
            }}
            onOpenKnowledgeDoc={(_sourcePath) => {
              setView('knowledge')
            }}
            llmStatus={llmStatus}
            onRetryLlm={() => void handleRetryLlm()}
            isRetryingLlm={isRetryingLlm}
            onRefreshLlmStatus={() => void refreshLlmStatus()}
          />
        ) : view === 'dashboard' ? (
          <DashboardView
            tickets={tickets}
            assets={assets}
            events={events}
            agentStatus={agentStatus}
            onNavigate={handleNavigate}
            onTriggerMonitor={handleTriggerMonitor}
            isMonitoring={isMonitoring}
            onOpenTicket={selectTicket}
            onAskCarlBot={handleAskCarlBot}
          />
        ) : view === 'tasks' ? (
          <TasksView
            agentStatus={agentStatus}
            onTriggerMonitor={handleTriggerMonitor}
            isMonitoring={isMonitoring}
            onOpenTicket={selectTicket}
            onAskCarlBot={handleAskCarlBot}
          />
        ) : view === 'knowledge' ? (
          <KnowledgeView
            documents={knowledgeDocs}
            onAskCarlBot={handleAskCarlBot}
          />
        ) : view === 'assets' ? (
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
        ) : (
          <section className={`ticket-page ${selectedTicketId === null ? 'ticket-page-with-chat' : ''}`}>
            {selectedTicketId === null ? (
              <TicketQueue
                tickets={filteredTickets}
                search={search}
                setSearch={setSearch}
                statusFilter={statusFilter}
                setStatusFilter={setStatusFilter}
                siteFilter={siteFilter}
                setSiteFilter={setSiteFilter}
                siteOptions={siteOptions}
                priorityFilter={priorityFilter}
                setPriorityFilter={setPriorityFilter}
                isLoading={isLoading}
                error={activeError}
                onSelect={selectTicket}
                onRefresh={() => void refreshWorkspace()}
              />
            ) : selectedTicket ? (
              <TicketDetail
                key={selectedTicket.id}
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
                onStatusChange={(status) => void handleTicketStatusChange(status)}
                isSavingStatus={isSavingTicketStatus}
                chatPanel={ticketChat}
                onRun={handleInvestigation}
                isRunning={isRunning}
                onBack={returnToQueue}
              />
            ) : (
              <div className="state-panel"><div className={detailError ? 'state-symbol' : 'loading-spinner'}>{detailError ? '!' : null}</div><h2>{detailError ? 'Ticket details unavailable' : 'Loading ticket details'}</h2><p>{detailError || 'Fetching the full helpdesk record…'}</p><button className="button button-outline" type="button" onClick={() => setRefreshKey((key) => key + 1)}>Try again</button></div>
            )}
            {selectedTicketId === null && ticketChat}
          </section>
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
  siteFilter: string
  setSiteFilter: (value: string) => void
  siteOptions: string[]
  priorityFilter: string
  setPriorityFilter: (value: string) => void
  isLoading: boolean
  error?: string
  onSelect: (ticketId: number) => void
  onRefresh: () => void
}

function TicketQueue({
  tickets, search, setSearch, statusFilter, setStatusFilter, siteFilter, setSiteFilter,
  siteOptions, priorityFilter,
  setPriorityFilter, isLoading, error, onSelect, onRefresh,
}: TicketQueueProps) {
  return (
    <section className="queue-panel" aria-labelledby="queue-title">
      <div className="page-heading">
        <div>
          <div className="eyebrow"><span className="eyebrow-dot" /> SERVICE DESK / QUEUE</div>
          <h1 id="queue-title">Ticket queue</h1>
          <p>Review synthetic incidents across multiple emulated sites.</p>
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
            {ticketDeskStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
          </select>
        </label>
        <label className="filter-control">
          <span>Site</span>
          <select value={siteFilter} onChange={(event) => setSiteFilter(event.target.value)} aria-label="Filter by site">
            <option value="all">All sites</option>
            {siteOptions.map((site) => <option key={site} value={site}>{site}</option>)}
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
                  <td><StatusBadge status={deskStatus(ticket)} /></td>
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
  onStatusChange: (status: TicketDeskStatus) => void
  isSavingStatus: boolean
  chatPanel: ReactNode
  onRun: () => void
  isRunning: boolean
  onBack: () => void
}

function TicketDetail({
  ticket, asset, loading, error, latestRun, agentError, noteDraft, setNoteDraft,
  onSubmitNote, isSavingNote, onStatusChange, isSavingStatus, chatPanel, onRun, isRunning, onBack,
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
  const [ticketStatusDraft, setTicketStatusDraft] = useState<TicketDeskStatus>(() => deskStatus(ticket))

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
          <div className="detail-title-meta">
            <span className="ticket-number">#{ticket.id}</span>
            <StatusBadge status={deskStatus(ticket)} />
            <PriorityBadge priority={ticket.priority} />
            <label className="ticket-status-control">
              <span>Ticket status</span>
              <select
                value={ticketStatusDraft}
                onChange={(event) => setTicketStatusDraft(event.target.value as TicketDeskStatus)}
                disabled={isSavingStatus}
                aria-label="Change ticket status"
              >
                {ticketDeskStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
              </select>
            </label>
            {ticketStatusDraft !== deskStatus(ticket) && (
              <button
                className="button button-outline button-small"
                type="button"
                disabled={isSavingStatus}
                onClick={() => onStatusChange(ticketStatusDraft)}
              >
                {isSavingStatus ? 'Saving…' : 'Save status'}
              </button>
            )}
          </div>
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
            <div className="section-heading"><div><span className="section-icon">☷</span><h2>Conversation</h2><span className="section-count">{(ticket.notes?.length ?? 0) + (ticket.customer_replies?.length ?? 0) + 1}</span></div><button className="text-button" type="button">Activity history⌄</button></div>
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
            {ticket.customer_replies?.map((reply, index) => (
              <article className="thread-item thread-customer-reply" key={`reply-${reply.id || index}`}>
                <div className="thread-avatar customer-reply-avatar">✉</div>
                <div className="thread-content">
                  <div className="thread-author">
                    <strong>{reply.author || 'Technician'}</strong>
                    <span className="reply-badge">CUSTOMER-VISIBLE REPLY</span>
                    <time>{formatDate(reply.created_at)}</time>
                  </div>
                  <p className="note-body">{reply.body}</p>
                  <div className="thread-source"><span className="source-dot" /> Published to simulated ticket thread</div>
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
          {chatPanel}
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
  chatMessages, chatDraft, isLoading, messagesRef, selectedTicketId, setChatDraft,  onChat, onOpenTicket,
  onPublishReply, onCancelDraft,
  llmStatus, onRetryLlm, isRetryingLlm,
}: {
  chatMessages: ChatMessage[]
  chatDraft: string
  isLoading: boolean
  messagesRef: RefObject<HTMLDivElement | null>
  selectedTicketId: number | null
  setChatDraft: (value: string) => void
  onChat: (event: FormEvent<HTMLFormElement>) => void
  onOpenTicket: (ticketId: number) => void
  onPublishReply: (ticketId: number, body: string, messageIndex: number) => void
  onCancelDraft: (messageIndex: number) => void
  llmStatus: LocalLlmStatus | null
  onRetryLlm: () => void
  isRetryingLlm: boolean
}) {
  const [draftEdits, setDraftEdits] = useState<Record<number, string>>({})
  const [isPublishingIndex, setIsPublishingIndex] = useState<number | null>(null)

  return (
    <section
      className={`chat-card chat-lookup-global ${selectedTicketId !== null ? 'chat-in-detail' : ''}`}
      aria-labelledby="ticket-chat-title"
    >
      <div className="chat-heading">
        <div><span className="chat-icon">✦</span><div className="chat-title-copy"><h2 id="ticket-chat-title">CarlBot</h2><span>AI operations companion</span></div></div>
        <span className="chat-readonly">ADVICE ONLY</span>
      </div>
      <LlmStatusBadge status={llmStatus} onRetry={onRetryLlm} isRetrying={isRetryingLlm} compact />
      <p className="chat-intro">
        {selectedTicketId
          ? `Using ticket #${selectedTicketId} and its recorded conversation as context.`
          : 'Ask about tickets, RTSP, NVR, AI Box, PoE, or say hello.'}
        {' '}Suggestions do not run actions.
      </p>
      <div className="chat-messages" ref={messagesRef} role="log" aria-live="polite" aria-busy={isLoading}>
        {chatMessages.map((message, index) => (
          <div
            key={`${index}-${message.role}`}
            className={`chat-message chat-${message.role}`}
          >
            {message.text}
            {message.role === 'assistant' && message.reasoningMode && (
              <span className="chat-reasoning-mode">
                {message.reasoningMode === 'llm' ? 'LLM-assisted' : 'Record-based'}
              </span>
            )}
            {message.recommendations && message.recommendations.length > 0 && (
              <div className="chat-recommendations">
                <strong>Suggested next steps</strong>
                <ol>
                  {message.recommendations.map((recommendation, recommendationIndex) => (
                    <li key={`${recommendation.category}-${recommendationIndex}`}>
                      <span className={`chat-recommendation-category category-${recommendation.category}`}>
                        {recommendation.category}
                      </span>
                      {recommendation.instruction}
                    </li>
                  ))}
                </ol>
              </div>
            )}
            {message.knowledgeSources && message.knowledgeSources.length > 0 && (
              <div className="chat-knowledge-links" aria-label="Referenced approved documentation">
                <strong>Approved documentation cited</strong>
                {message.knowledgeSources.map((doc, docIdx) => (
                  <div className="chat-knowledge-item" key={`doc-${docIdx}`}>
                    <span className="chat-knowledge-title">{doc.section_title}</span>
                    <span className="chat-knowledge-loc">{doc.source_path} ({doc.locator})</span>
                  </div>
                ))}
              </div>
            )}
            {message.ticketReplyDraft && selectedTicketId !== null && (
              <div className="chat-reply-preview-card" aria-label="Customer reply draft preview">
                <div className="chat-reply-preview-header">
                  <strong>Proposed reply to customer (Ticket #{selectedTicketId})</strong>
                  <span className="preview-badge">PREVIEW · UNPUBLISHED</span>
                </div>
                <textarea
                  className="chat-reply-textarea"
                  rows={4}
                  value={draftEdits[index] !== undefined ? draftEdits[index] : message.ticketReplyDraft}
                  onChange={(e) => setDraftEdits((prev) => ({ ...prev, [index]: e.target.value }))}
                  aria-label="Editable customer reply draft"
                />
                <div className="chat-reply-preview-footer">
                  <button
                    className="button button-outline button-small"
                    type="button"
                    disabled={isPublishingIndex === index}
                    onClick={() => onCancelDraft(index)}
                  >
                    Cancel
                  </button>
                  <button
                    className="button button-primary button-small"
                    type="button"
                    disabled={
                      isPublishingIndex === index ||
                      !(draftEdits[index] ?? message.ticketReplyDraft ?? '').trim()
                    }
                    onClick={async () => {
                      const text = (draftEdits[index] ?? message.ticketReplyDraft ?? '').trim()
                      if (!text || selectedTicketId === null) return
                      setIsPublishingIndex(index)
                      try {
                        await onPublishReply(selectedTicketId, text, index)
                      } finally {
                        setIsPublishingIndex(null)
                      }
                    }}
                  >
                    {isPublishingIndex === index ? 'Publishing…' : 'Publish to simulated ticket'}
                  </button>
                </div>
              </div>
            )}
            {message.matches?.some((match) => match.source === 'live_helpdesk' && /^\d+$/.test(match.ticket_id)) && (
              <div className="chat-ticket-links" aria-label="Open cited ticket records">
                <strong>Ticket records used</strong>
                {message.matches
                  .filter((match) =>
                    match.source === 'live_helpdesk' &&
                    /^\d+$/.test(match.ticket_id) &&
                    (!message.citedTicketIds?.length || message.citedTicketIds.includes(match.ticket_id)))
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
          <div className="chat-message chat-searching">Reviewing ticket details and conversation…</div>
        )}
        {chatMessages.length === 0 && !isLoading && (
          <div className="chat-cleared">Conversation context cleared. Ticket and system data were not changed.</div>
        )}
      </div>
      <form className="chat-form" onSubmit={onChat}>
        <input
          value={chatDraft}
          onChange={(event) => setChatDraft(event.target.value)}
          placeholder={selectedTicketId ? `Ask about ticket #${selectedTicketId} or ask to draft a reply…` : 'Ask about tickets, RTSP, NVR, AI Box, or say hello…'}
          aria-label="Ask CarlBot about tickets"
        />
        <button type="submit" aria-label="Ask CarlBot" disabled={!chatDraft.trim() || isLoading}>↑</button>
      </form>
      <div className="chat-disclaimer">Suggestions only; CarlBot cannot change tickets or run actions. <span>/clear</span> clears this conversation.</div>
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
  const sites = [...new Set(assets.map((asset) => asset.site_id || 'Unassigned site'))].sort()
  const cameras = assets.filter((asset) => asset.type === 'camera')
  return (
    <section className="asset-page">
      <div className="page-heading">
        <div><div className="eyebrow"><span className="eyebrow-dot" /> MULTI-SITE LAB / INVENTORY</div><h1>Asset inventory</h1><p>Emulated cameras, recorders and AI infrastructure across the synthetic sites.</p></div>
        <span className="asset-total">{assets.length} synthetic assets</span>
      </div>
      <div className="asset-warning"><span>ⓘ</span><div><strong>Simulation controls</strong><p>Fault injection and reset operate only on this local lab emulator. The agent may automatically run only policy-approved safe actions.</p></div></div>
      {error ? <div className="state-panel state-error"><h2>Portal service unavailable</h2><p>{error}</p></div> : isLoading ? <div className="state-panel"><div className="loading-spinner" /><h2>Loading synthetic inventory</h2></div> : (
        <div className="asset-layout">
          <section className="content-card asset-tree-card">
            <div className="section-heading"><div><span className="section-icon">⌘</span><h2>Equipment by site</h2><span className="section-count">{assets.length}</span></div><span className="subtle-label">{sites.length} SITES</span></div>
            {sites.map((site) => {
              const siteAssets = assets.filter((asset) => (asset.site_id || 'Unassigned site') === site)
              const recorders = siteAssets.filter((asset) => asset.type === 'nvr')
              const siteCameras = siteAssets.filter((asset) => asset.type === 'camera')
              const otherInfrastructure = siteAssets.filter((asset) => asset.type !== 'camera' && asset.type !== 'nvr')
              const unassignedCameras = siteCameras.filter((camera) => !recorders.some((recorder) => recorder.asset_id === camera.nvr_id))
              return (
                <div className="site-asset-group" key={site}>
                  <div className="tree-root"><span className="tree-caret">⌄</span><span className="tree-site-icon">⌂</span><strong>{site}</strong><span className="tree-count">{siteAssets.length}</span></div>
                  {recorders.map((recorder) => (
                    <div key={recorder.asset_id}>
                      <AssetRow asset={recorder} depth={1} fault={faultByAsset[recorder.asset_id] || ''} setFault={(fault) => setFaultByAsset({ ...faultByAsset, [recorder.asset_id]: fault })} onSimulate={onSimulate} onReset={onReset} isChanging={isChanging === recorder.asset_id} />
                      {siteCameras.filter((camera) => camera.nvr_id === recorder.asset_id).map((camera) => <AssetRow key={camera.asset_id} asset={camera} depth={2} fault={faultByAsset[camera.asset_id] || ''} setFault={(fault) => setFaultByAsset({ ...faultByAsset, [camera.asset_id]: fault })} onSimulate={onSimulate} onReset={onReset} isChanging={isChanging === camera.asset_id} />)}
                    </div>
                  ))}
                  {unassignedCameras.map((asset) => <AssetRow key={asset.asset_id} asset={asset} depth={1} fault={faultByAsset[asset.asset_id] || ''} setFault={(fault) => setFaultByAsset({ ...faultByAsset, [asset.asset_id]: fault })} onSimulate={onSimulate} onReset={onReset} isChanging={isChanging === asset.asset_id} />)}
                  {otherInfrastructure.map((asset) => <AssetRow key={asset.asset_id} asset={asset} depth={1} fault={faultByAsset[asset.asset_id] || ''} setFault={(fault) => setFaultByAsset({ ...faultByAsset, [asset.asset_id]: fault })} onSimulate={onSimulate} onReset={onReset} isChanging={isChanging === asset.asset_id} />)}
                </div>
              )
            })}
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
