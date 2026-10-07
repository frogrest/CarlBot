# Frontend Component Inventory

This inventory translates all six pages in [`SCREENSHOT_INVENTORY.md`](./SCREENSHOT_INVENTORY.md) into a synthetic technician workflow. Page references point to `reference/screenshots/reference.pdf`.

| Component | Responsibility | Visual source |
|---|---|---|
| `AppShell` | Desktop application frame and responsive content layout | Pages 1–6 |
| `BrandHeader` | Synthetic CarlBot Support identity, environment label, technician menu | Pages 1–4 |
| `PrimaryNavigation` | Dashboard, Users, Tasks, Tickets, Knowledgebase; active Tickets state | Pages 1–4 |
| `TicketToolbar` | Open/My Tickets/Closed/Search/New Ticket links and actions | Pages 1–4 |
| `TicketListPage` | Search, filters, queue count, sort and ticket table | Page 1 |
| `SearchBar` | Search ticket IDs, subjects, assets and descriptions | Page 1 |
| `FilterBar` | Status, priority, site and assignment filters | Page 1 |
| `TicketTable` / `TicketRow` | Compact sortable ticket columns, synthetic rows, selected-row navigation | Page 1 |
| `StatusBadge` / `PriorityBadge` | Consistent ticket-state and priority cues | Pages 1–4 |
| `TicketDetailPage` | Ticket summary, metadata, conversation and copilot | Pages 2–3 |
| `TicketMetadata` | ID, status, priority, site, asset, owner and timestamps | Page 2 |
| `ActivityThread` / `ActivityItem` | Reporter, technician, monitor and AI notes with timestamps | Pages 2–3 |
| `TicketComposer` | Technician note entry and status/verification controls | Page 3 |
| `AssetTreePage` | Site → NVR → camera / AI Box hierarchy and health state | Adapted from Page 2's asset evidence; lab inventory contract |
| `AssetRow` | Asset type, IP, reachability, service/RTSP and fault | Adapted from Page 2 |
| `LabControlPanel` | Clearly labeled simulated fault injection and reset controls | New synthetic lab affordance |
| `LabStatusStrip` | Agent running/poll state and most recent run outcomes | New synthetic lab affordance |
| `AIInsightPanel` | Diagnosis, confidence, observed/retrieved evidence and next step | New additive copilot panel on Page 2 |
| `EvidenceCard` | Source-labeled health probes, history and document citations | New additive copilot panel on Page 2 |
| `SuggestedActionCard` | Request an agent run, clearly display policy/verification outcome | New additive copilot panel on Page 2 |
| `TechnicianHandoffCard` | Requested physical action, uncertainty and recheck steps | New additive copilot panel on Page 2 |
| `ChatPanel` / `ChatComposer` | Ticket-bound chat shell, suggested prompts, session-only `/clear` | Phase 6 contract, not present in reference |
| `LoadingState` / `EmptyState` / `ErrorState` | Explicit data-fetch, no-results and service error states | Shared |

## Implementation boundary

- React + Vite + TypeScript; desktop-first, usable at widths of 1024 px and above, responsive below.
- APIs are accessed only through same-origin `/helpdesk`, `/portal`, and `/agent` proxies.
- The interface can request work and render backend decisions; it cannot authorize or execute infrastructure actions.
- Chat endpoints may return 404 until the chat backend phase. `/clear` is local session state only and never calls a data-deletion endpoint.
- The current backend offers notes, verification requests, manual runs, events, diagnostics and safe simulated actions, but not ticket creation/editing of arbitrary fields, live progress streaming, or chat. Missing capabilities are represented as honest UI states, not fabricated behavior.
