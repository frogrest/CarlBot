# CarlBot Ticket Chat Specification

## Purpose

CarlBot helps technicians find and understand existing helpdesk tickets. It can
reason over retrieved ticket details and the selected ticket's recorded notes,
give evidence-grounded recommendations, and link the ticket records it used. It
is read-only, not an autonomous resolver. Technicians can ask about a site,
camera, issue, or ticket status from either the ticket queue or ticket detail
screen.

## Implemented now

- The Helpdesk `POST /api/chat/query` endpoint reads live tickets, selected
  ticket details and up to 20 notes, recorded customer replies, plus an optional
  local metadata-only CSV export.
- Bounded multi-turn context: the chat client sends recent conversational turns
  (up to 6 turns) so follow-up questions are resolved in context.
- Approved local knowledge retrieval: `KnowledgeRetriever` searches approved
  markdown technical documentation and SOPs (e.g. `docs/SOP/`, `docs/RTSP/`, etc.),
  returning section titles, repository-relative paths, and locators (line ranges).
  Arbitrary filesystem paths, internal notes, and unapproved directories are excluded.
- Grounded customer reply drafting: when an operator explicitly requests a reply
  draft and a ticket is selected, CarlBot generates an editable preview draft.
  Drafts are never published automatically. Publishing requires explicit operator
  review and confirmation via the "Publish to simulated ticket" button, which posts
  to `/api/tickets/{id}/customer-replies`.
- Published replies are stored in a dedicated `customer_replies` SQLite table and
  displayed with a distinct visual badge in the ticket conversation, kept separate
  from internal technician notes. Idempotency keys prevent duplicate submission.
- Deterministic record-based answers work without an LLM. When explicitly
  configured, the optional structured LLM responder uses bounded retrieved
  ticket context, redacts credential-like values and emails, validates ticket
  and document citations and restricted recommendations, and falls back to
  deterministic answers when it cannot return an acceptable result.
- Answers cite linked live tickets, cited approved documentation, and suggest next steps.
  Those recommendations are advice only; chat cannot invoke tools, the Portal, or
  the agent.
- `/clear` clears the browser conversation only. Chat is read-only: it cannot
  automatically add a ticket note or customer-facing reply, change status, or
  otherwise write to ticket records.
- CarlBot appears in two modes:
  1. Embedded in the ticket workspace (beside the ticket queue and ticket detail views).
  2. A dedicated, full-screen ChatGPT-style copilot view accessible via the `◈ CarlBot AI`
     primary navigation tab (`CarlBotChatView.tsx`), equipped with modern prompt starters,
     a ticket context selector dropdown, full conversational history, and 1-click
     navigation to referenced SOP documents.

Examples:

- `Is there an open ticket about an offline camera at Freddy Fazbear's?`
- `Show answered tickets at Centerpark Tower 1.`
- `Find closed tickets for Pacman.`
- `Show closed RTSP tickets for SITE-104.`
- `What was recorded in ticket 1002?`

## Retrieval and answers

- Search both live Helpdesk ticket records and the optional locally mounted
  `reference/ticketreference examples.csv` export.
- Filter by explicit Open, Answered, or Closed helpdesk status, and retain
  support for legacy internal `resolved` queries. Do not present an open
  reference-export record as closed.
- Live tickets also have a distinct helpdesk status (`Open`, `Answered`, or
  `Closed`) for queue filters and technician updates. Preserve the separate
  internal workflow status used by the orchestrator and policy gate.
- Prefer exact site identifiers or names. Label weaker site overlap as a
  possible match and state that the site is unconfirmed. A requester/`From`
  value alone can never confirm site identity.
- Summarize only retrieved ticket fields and notes. Do not invent camera IDs,
  site identity, conversation details, or a resolution.
- When a ticket is selected, send its ticket ID with the query so the backend
  includes that ticket's details and up to 20 recorded notes, even if the
  question does not repeat the ticket number. Without a selected ticket, use
  deterministic ticket search to retrieve relevant records.
- When `LLM_BASE_URL` and `LLM_MODEL` are configured for the Helpdesk service,
  use the structured LLM responder over only the retrieved live records. Read
  `LLM_API_KEY` from the process environment when needed. With no configuration,
  use the deterministic grounded reply.
- Show whether a reply was `LLM-assisted` or `Record-based`. LLM output must
  cite only supplied live ticket IDs; render citations as links to those ticket
  details. Never make links from model-generated URLs.
- Render next-step recommendations separately from the answer. Suggestions are
  advice only: the chatbot does not call the Agent, Portal, or any action API.
  Any simulated action still goes through current evidence review and the
  deterministic policy engine.
- Treat explicit requests for a ticket's subject/title as a lookup intent and
  return the stored subject exactly as recorded.
- For live Helpdesk matches, show direct links that open the corresponding
  ticket detail in the workspace. Do not show local-ticket links for
  reference-export-only matches.
- Use short, plain-language replies. For broad searches, show at most three
  ticket summaries and invite the technician to ask about a ticket number for
  more detail. For a single ticket, include its status and one useful recorded
  detail. Explain statuses in everyday words (for example,
  `pending_technician` means the ticket is waiting for a technician) and
  translate known technical causes without changing their meaning.
- Live records may include ticket descriptions, resolution/root-cause fields,
  summaries, and technician notes. The reference export contains metadata only;
  say that its conversation is unavailable.
- Never return sender email addresses. The optional export remains local and is
  mounted read-only into the Helpdesk service.
- If the export is not mounted, disclose that only live records were searched.

## Visual hierarchy and motion

- Keep CarlBot easy to find on both the ticket queue and ticket detail views.
- Give the chat panel more visual weight than secondary status indicators, with
  a clear title, readable message text, and a comfortable input target.
- On wide queue views, keep the assistant visible beside the ticket list; on
  narrow screens, place it after the queue without causing horizontal overflow.
- Keep replies concise and scannable; larger type should improve readability
  without turning the panel into the primary page.
- Scroll the chat viewport to each newly added message while preserving normal
  upward scrolling through older messages.
- Use CSS for small message-arrival and input-focus transitions. Respect the
  operating system's reduced-motion preference and avoid decorative or
  continuous motion.

## Dedicated ChatGPT-Style View (`◈ CarlBot AI`)

In addition to the sidebar in the ticket queue and ticket detail views, the application features a dedicated, full-page ChatGPT-style conversational workspace accessible from the top navigation bar (`CarlBotChatView.tsx`):

- **Header Bar**: Displays CarlBot branding, active emulator status tag, an active ticket context selector dropdown, and a `+ New Chat` action.
- **Context Binding**: Technicians can converse in system-wide mode or bind reasoning directly to any active ticket from the dropdown without leaving the chat page.
- **Prompt Starter Grid**: When starting a fresh session, four prompt cards guide quick exploration:
  1. *Camera Offline Playbook* — Stepwise diagnostic and handoff triage for unreachable IP cameras.
  2. *Reboot vs. Power Cycling* — When to warm reboot via software vs cold power-cycle PoE switch ports.
  3. *RTSP & Port 554 Protocol* — Streaming specifications, transport modes (TCP/UDP), and authentication.
  4. *IP Diagnostic Commands* — Essential CLI networking tools (ping, curl, ffprobe, ip, arp, tcpdump).
- **Rich Message Stream**: Displays conversational bubbles with CarlBot avatar, expandable recommendation callouts, cited SOP/document chips linking to source lines, ticket reference tags, and human-confirmed customer reply draft cards.
- **Bottom Composer**: Fixed floating chat input with auto-focus, send trigger, `/clear` command support, and explicit operational safety disclaimer reminding technicians that actions are local and read-only.

## Read-only boundary

Chat uses only `POST /api/chat/query` on the Helpdesk service. That endpoint
performs reads and does not create/update tickets, add notes, invoke the agent,
query the portal, or run diagnostic/recovery actions. The selected ticket's
notes and question are sent to the configured LLM endpoint only when the
operator explicitly configures `LLM_BASE_URL` and `LLM_MODEL`; credential-like
values are redacted first. Keep chat controls separate from investigation and
simulated-lab controls.

## `/clear`

`/clear` resets the browser conversation only. It does not delete or change
tickets, notes, audit records, the CSV, or agent state.

After `/clear`, show a clear message such as:

> Conversation context cleared. Ticket and system data were not changed.

## Transparency and errors

Answers identify cited ticket IDs, statuses, and available details. Use
wording such as “possible match (site not confirmed)” when the site is not an
exact match. Distinguish an empty result from an unavailable Helpdesk service.
Never claim to have searched or read records after an API failure.

Do not expose hidden chain-of-thought. Provide concise summaries grounded in
the retrieved source records.
