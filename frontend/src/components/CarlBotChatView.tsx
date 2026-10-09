import { useEffect, useRef, useState, type FormEvent } from 'react'
import type { KnowledgeSource, TicketChatMatch, TicketChatRecommendation } from '../api'
import type { LocalLlmStatus, Ticket } from '../types'
import { LlmStatusBadge } from './LlmStatusBadge'
import { ModelManager } from './ModelManager'

export type ChatMessage = {
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

interface CarlBotChatViewProps {
  chatMessages: ChatMessage[]
  chatDraft: string
  setChatDraft: (draft: string) => void
  onChat: (event: FormEvent<HTMLFormElement>) => void
  isLoading: boolean
  selectedTicketId: number | null
  setSelectedTicketId: (id: number | null) => void
  tickets: Ticket[]
  onOpenTicket: (ticketId: number) => void
  onPublishReply: (ticketId: number, body: string, messageIndex: number) => Promise<void>
  onCancelDraft: (messageIndex: number) => void
  onClearChat: () => void
  onOpenKnowledgeDoc: (sourcePath: string) => void
  llmStatus: LocalLlmStatus | null
  onRetryLlm: () => void
  isRetryingLlm: boolean
  onRefreshLlmStatus: () => void
}

const promptStarters = [
  {
    title: 'Camera Offline Playbook',
    desc: 'Step-by-step diagnostic workflow for dropped streams & PoE faults',
    prompt: 'what to do when a camera is offline',
  },
  {
    title: 'Reboot vs. Power Cycling',
    desc: 'Soft OS restart vs. cold 20s capacitor drain and PoE bouncing',
    prompt: 'what is the difference between reboot and power cycle',
  },
  {
    title: 'RTSP & Port 554 Protocol',
    desc: 'RFC 2326 streaming, DESCRIBE/SETUP/PLAY handshakes & URI format',
    prompt: 'explain rtsp and how streaming works in the lab',
  },
  {
    title: 'IP Diagnostic Commands',
    desc: 'ping, arp -a, ipconfig, traceroute, and Test-NetConnection port tests',
    prompt: 'what ip commands should a technician use to troubleshoot',
  },
]

export function CarlBotChatView({
  chatMessages,
  chatDraft,
  setChatDraft,
  onChat,
  isLoading,
  selectedTicketId,
  setSelectedTicketId,
  tickets,
  onOpenTicket,
  onPublishReply,
  onCancelDraft,
  onClearChat,
  onOpenKnowledgeDoc,
  llmStatus,
  onRetryLlm,
  isRetryingLlm,
  onRefreshLlmStatus,
}: CarlBotChatViewProps) {
  const [isPublishingIndex, setIsPublishingIndex] = useState<number | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages, isLoading])

  const handleStarterClick = (prompt: string) => {
    setChatDraft(prompt)
    // Dispatch submit
    setTimeout(() => {
      const form = document.querySelector<HTMLFormElement>('.carlbot-composer-form')
      if (form) form.requestSubmit()
    }, 50)
  }

  const selectedTicket = tickets.find((t) => t.id === selectedTicketId)

  return (
    <section className="carlbot-chat-page">
      {/* Top Header Bar */}
      <div className="carlbot-chat-header">
        <div className="carlbot-header-left">
          <div className="carlbot-avatar-large">C</div>
          <div>
            <div className="carlbot-title-row">
              <h2>CarlBot AI Copilot</h2>
              <span className="carlbot-status-tag">● Active Companion</span>
            </div>
            <p className="carlbot-subtitle">
              Specialized in CCTV video infrastructure, NVR multi-channel recording, Edge AI Boxes, and IT operations.
            </p>
            <LlmStatusBadge status={llmStatus} onRetry={onRetryLlm} isRetrying={isRetryingLlm} />
          </div>
        </div>

        <div className="carlbot-header-controls">
          <div className="ticket-context-selector">
            <label htmlFor="ticket-context-select">Ticket Context:</label>
            <select
              id="ticket-context-select"
              value={selectedTicketId || ''}
              onChange={(e) => setSelectedTicketId(e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">System-Wide (No specific ticket)</option>
              {tickets.map((ticket) => (
                <option key={ticket.id} value={ticket.id}>
                  #{ticket.id} · {ticket.title} ({ticket.site_id})
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="button button-outline button-small new-chat-btn"
            onClick={onClearChat}
            title="Clear conversation context"
          >
            + New Chat
          </button>
        </div>
      </div>

      {/* Local model chooser (collapsible) */}
      <ModelManager onRefreshStatus={onRefreshLlmStatus} />

      {/* Main Conversation Stream */}
      <div className="carlbot-chat-body">
        <div className="carlbot-messages-container">
          {/* Welcome Screen / Prompt Starters if only greeting exists */}
          {chatMessages.length <= 1 && (
            <div className="carlbot-welcome-hero">
              <div className="hero-avatar">C</div>
              <h1>Hello, I'm Carlbot, ask me anything about the Helpdesk</h1>
              <p>
                Grounded in our local surveillance lab and approved SOPs. Ask about camera streams, network protocols, diagnostic commands, or incident troubleshooting:
              </p>

              <div className="starters-grid">
                {promptStarters.map((item, idx) => (
                  <div
                    key={idx}
                    className="starter-card"
                    onClick={() => handleStarterClick(item.prompt)}
                    role="button"
                    tabIndex={0}
                  >
                    <strong>{item.title}</strong>
                    <span>{item.desc}</span>
                    <div className="starter-prompt">"{item.prompt}" →</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Render Messages */}
          {chatMessages.map((msg, idx) => {
            const isUser = msg.role === 'user'

            return (
              <div key={idx} className={`carlbot-message-row ${isUser ? 'row-user' : 'row-assistant'}`}>
                {!isUser && <div className="carlbot-msg-avatar">C</div>}

                <div className="carlbot-bubble-wrapper">
                  <div className="carlbot-bubble-meta">
                    <strong>{isUser ? 'Technician' : 'CarlBot Copilot'}</strong>
                    {!isUser && msg.reasoningMode && (
                      <span className="reasoning-mode-badge">{msg.reasoningMode.toUpperCase()}</span>
                    )}
                  </div>

                  <div className={`carlbot-bubble ${isUser ? 'bubble-user' : 'bubble-assistant'}`}>
                    <div className="carlbot-text-content">
                      {msg.text.split('\n\n').map((paragraph, pIdx) => (
                        <p key={pIdx}>{paragraph}</p>
                      ))}
                    </div>

                    {/* Recommendations */}
                    {msg.recommendations && msg.recommendations.length > 0 && (
                      <div className="carlbot-recommendations-box">
                        <span className="rec-title">Recommended Next Steps:</span>
                        {msg.recommendations.map((rec, rIdx) => (
                          <div key={rIdx} className="rec-item">
                            <span className={`rec-badge badge-${rec.category}`}>{rec.category}</span>
                            <span className="rec-instruction">{rec.instruction}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Cited Knowledge Sources */}
                    {msg.knowledgeSources && msg.knowledgeSources.length > 0 && (
                      <div className="carlbot-sources-box">
                        <span className="source-title">Approved SOP Documentation Referenced:</span>
                        <div className="sources-chips">
                          {msg.knowledgeSources.map((src, sIdx) => (
                            <button
                              key={sIdx}
                              type="button"
                              className="source-chip"
                              onClick={() => onOpenKnowledgeDoc(src.source_path)}
                              title={`Open ${src.source_path}`}
                            >
                              📖 {src.section_title} <small>({src.locator})</small>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Cited Ticket Records */}
                    {msg.matches && msg.matches.length > 0 && (
                      <div className="carlbot-tickets-cited">
                        <span className="tickets-title">Related Ticket Records:</span>
                        <div className="ticket-chips">
                          {msg.matches.slice(0, 3).map((match) => (
                            <button
                              key={match.ticket_id}
                              type="button"
                              className="ticket-chip"
                              onClick={() => onOpenTicket(Number(match.ticket_id))}
                            >
                              #{match.ticket_id} · {match.title} ({match.status})
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Customer Reply Draft Box */}
                    {msg.ticketReplyDraft && selectedTicketId && (
                      <div className="carlbot-reply-draft">
                        <div className="draft-header">
                          <span className="draft-tag">Simulated Customer Reply Draft</span>
                          <span className="draft-sub">Technician approval required before publishing</span>
                        </div>
                        <p className="draft-body">{msg.ticketReplyDraft}</p>
                        <div className="draft-actions">
                          <button
                            type="button"
                            className="button button-small button-outline"
                            onClick={() => onCancelDraft(idx)}
                          >
                            Dismiss
                          </button>
                          <button
                            type="button"
                            className="button button-small button-primary"
                            disabled={isPublishingIndex === idx}
                            onClick={async () => {
                              setIsPublishingIndex(idx)
                              try {
                                await onPublishReply(selectedTicketId, msg.ticketReplyDraft!, idx)
                              } finally {
                                setIsPublishingIndex(null)
                              }
                            }}
                          >
                            {isPublishingIndex === idx ? 'Publishing…' : 'Publish to Ticket Thread'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {isUser && <div className="carlbot-user-avatar">T</div>}
              </div>
            )
          })}

          {isLoading && (
            <div className="carlbot-message-row row-assistant">
              <div className="carlbot-msg-avatar">C</div>
              <div className="carlbot-bubble-wrapper">
                <div className="carlbot-bubble bubble-assistant carlbot-loading-bubble">
                  <span className="carlbot-typing-dots">
                    <span />
                    <span />
                    <span />
                  </span>
                  <span>CarlBot is reasoning over documentation and tickets…</span>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Bottom Floating Composer (ChatGPT style) */}
      <div className="carlbot-composer-area">
        <form className="carlbot-composer-form" onSubmit={onChat}>
          <div className="carlbot-composer-wrapper">
            <input
              type="text"
              value={chatDraft}
              onChange={(e) => setChatDraft(e.target.value)}
              placeholder={
                selectedTicket
                  ? `Ask CarlBot about Ticket #${selectedTicket.id} (${selectedTicket.title})…`
                  : 'Message CarlBot or ask anything about Helpdesk, RTSP, NVR, SOPs… (type /clear to reset)'
              }
              aria-label="Message CarlBot"
              disabled={isLoading}
            />
            <button
              type="submit"
              className="carlbot-send-btn"
              disabled={!chatDraft.trim() || isLoading}
              aria-label="Send message"
            >
              ↑
            </button>
          </div>
        </form>
        <div className="carlbot-disclaimer">
          CarlBot is a safe technical-support assistant for this emulated lab. Autonomous policy enforces that physical repairs and credential changes require technician verification.
        </div>
      </div>
    </section>
  )
}
