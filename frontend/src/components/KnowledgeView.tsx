import { useMemo, useState } from 'react'
import type { KnowledgeDocument } from '../types'

interface KnowledgeViewProps {
  documents: KnowledgeDocument[]
  onAskCarlBot: (prompt: string) => void
}

export function KnowledgeView({ documents, onAskCarlBot }: KnowledgeViewProps) {
  const [selectedDocId, setSelectedDocId] = useState<string>(
    documents[0]?.id || 'network-protocols-and-commands'
  )
  const [activeCategory, setActiveCategory] = useState<string>('All')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null)

  // Categories list
  const categories = useMemo(() => {
    const set = new Set(documents.map((d) => d.category))
    return ['All', ...Array.from(set).sort()]
  }, [documents])

  // Filtered documents
  const filteredDocs = useMemo(() => {
    return documents.filter((doc) => {
      const matchesCategory = activeCategory === 'All' || doc.category.toLowerCase() === activeCategory.toLowerCase()
      if (!matchesCategory) return false

      if (!searchQuery.trim()) return true
      const q = searchQuery.toLowerCase()
      const inTitle = doc.title.toLowerCase().includes(q)
      const inCat = doc.category.toLowerCase().includes(q)
      const inSections = doc.sections.some(
        (s) => s.title.toLowerCase().includes(q) || s.content.toLowerCase().includes(q)
      )
      return inTitle || inCat || inSections
    })
  }, [documents, activeCategory, searchQuery])

  // Current document
  const currentDoc = useMemo(() => {
    return (
      documents.find((d) => d.id === selectedDocId) ||
      filteredDocs[0] ||
      documents[0]
    )
  }, [documents, selectedDocId, filteredDocs])

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedSnippet(text)
    setTimeout(() => setCopiedSnippet(null), 2500)
  }

  return (
    <section className="knowledge-page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">
            <span className="eyebrow-dot" /> TECHNICAL OPERATIONS / APPROVED KNOWLEDGE
          </div>
          <h1>Standard Operating Procedures & Knowledge Base</h1>
          <p>
            Approved operational documentation, network protocols, diagnostic CLI tools, and troubleshooting playbooks cited by CarlBot.
          </p>
        </div>
        <div className="dashboard-actions">
          {currentDoc && (
            <button
              type="button"
              className="button button-primary"
              onClick={() => onAskCarlBot(`tell me about ${currentDoc.title}`)}
            >
              ◈ Ask CarlBot About This SOP
            </button>
          )}
        </div>
      </div>

      {/* Search and Category Filters */}
      <div className="knowledge-toolbar content-card">
        <div className="knowledge-search-box">
          <span className="search-icon">🔍</span>
          <input
            type="search"
            placeholder="Search protocols, CLI commands, playbooks, or hardware terms…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search knowledge base"
          />
          {searchQuery && (
            <button
              type="button"
              className="clear-search"
              onClick={() => setSearchQuery('')}
            >
              ✕
            </button>
          )}
        </div>

        <div className="category-pills">
          {categories.map((cat) => {
            const count = cat === 'All' ? documents.length : documents.filter((d) => d.category === cat).length
            return (
              <button
                key={cat}
                type="button"
                className={`category-pill ${activeCategory === cat ? 'active' : ''}`}
                onClick={() => setActiveCategory(cat)}
              >
                {cat} <span className="cat-count">{count}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Two-Column Explorer Layout */}
      <div className="knowledge-layout">
        {/* Left Column: Document Directory */}
        <aside className="content-card knowledge-sidebar">
          <div className="section-heading">
            <div>
              <span className="section-icon">📚</span>
              <h2>Approved Documents</h2>
              <span className="section-count">{filteredDocs.length}</span>
            </div>
          </div>

          <div className="knowledge-doc-list">
            {filteredDocs.length === 0 ? (
              <div className="empty-docs-msg">No documents match your search query.</div>
            ) : (
              filteredDocs.map((doc) => {
                const isSelected = currentDoc?.id === doc.id
                return (
                  <div
                    key={doc.id}
                    className={`knowledge-doc-card ${isSelected ? 'selected' : ''}`}
                    onClick={() => setSelectedDocId(doc.id)}
                    role="button"
                    tabIndex={0}
                  >
                    <div className="doc-card-head">
                      <span className="doc-cat-tag">{doc.category}</span>
                      <span className="doc-sections-count">{doc.sections.length} sections</span>
                    </div>
                    <strong className="doc-card-title">{doc.title}</strong>
                    <span className="doc-card-path">{doc.source_path}</span>
                  </div>
                )
              })
            )}
          </div>
        </aside>

        {/* Right Column: Full Document Reader */}
        <main className="content-card knowledge-reader">
          {currentDoc ? (
            <article className="document-article">
              <header className="article-header">
                <div className="article-meta">
                  <span className="doc-cat-badge">{currentDoc.category}</span>
                  <span className="doc-path-tag">{currentDoc.source_path}</span>
                </div>
                <h1 className="article-title">{currentDoc.title}</h1>
                <div className="article-actions">
                  <button
                    type="button"
                    className="button button-outline button-small"
                    onClick={() => onAskCarlBot(`explain ${currentDoc.title}`)}
                  >
                    ◈ Ask CarlBot to Summarize
                  </button>
                </div>
              </header>

              <div className="article-body">
                {currentDoc.sections.map((section, idx) => (
                  <section key={idx} className="article-section">
                    <h2 className="section-title">{section.title}</h2>
                    <div className="section-content">
                      {section.content.split('\n\n').map((para, pIdx) => {
                        // Check if paragraph contains command blocks
                        const lines = para.split('\n')
                        return (
                          <div key={pIdx} className="content-block">
                            {lines.map((line, lIdx) => {
                              // If line starts with diagnostic command or bullet
                              if (line.trim().startsWith('•') || line.trim().startsWith('-')) {
                                return (
                                  <li key={lIdx} className="article-bullet">
                                    {line.replace(/^[•-]\s*/, '')}
                                  </li>
                                )
                              }
                              // Diagnostic command pattern
                              const isCommand =
                                /^(?:ping|arp|ipconfig|ifconfig|traceroute|tracert|Test-NetConnection|nc -zv|docker|curl|sudo systemctl)\b/.test(
                                  line.trim()
                                ) || /^\d+\.\s+(?:ping|arp|ipconfig|traceroute|Test-NetConnection)/.test(line.trim())

                              if (isCommand) {
                                const cleanCmd = line.replace(/^\d+\.\s+/, '').split(':')[0].trim()
                                return (
                                  <div key={lIdx} className="cli-command-box">
                                    <code>{line}</code>
                                    <button
                                      type="button"
                                      className="copy-cmd-btn"
                                      onClick={() => copyToClipboard(cleanCmd)}
                                      title="Copy command"
                                    >
                                      {copiedSnippet === cleanCmd ? '✔ Copied' : 'Copy'}
                                    </button>
                                  </div>
                                )
                              }

                              return <p key={lIdx} className="article-p">{line}</p>
                            })}
                          </div>
                        )
                      })}
                    </div>
                  </section>
                ))}
              </div>

              {/* Quick Knowledge Suggestions Footer */}
              <footer className="article-footer">
                <div className="article-footer-heading">Related Troubleshooting Resources</div>
                <div className="related-links">
                  <button
                    type="button"
                    className="related-chip"
                    onClick={() => onAskCarlBot('what to do when a camera is offline')}
                  >
                    Camera Offline Playbook
                  </button>
                  <button
                    type="button"
                    className="related-chip"
                    onClick={() => onAskCarlBot('what is the difference between reboot and power cycle')}
                  >
                    Reboot vs Power Cycle
                  </button>
                  <button
                    type="button"
                    className="related-chip"
                    onClick={() => onAskCarlBot('what ip commands should a technician use')}
                  >
                    IP Diagnostic Commands
                  </button>
                </div>
              </footer>
            </article>
          ) : (
            <div className="empty-reader">Select a document from the catalog to read its contents.</div>
          )}
        </main>
      </div>
    </section>
  )
}
