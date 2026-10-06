# Frontend Development — Master Build Prompt

You are the frontend coding agent for this repository. Build a **faithful synthetic replica of a CCTV technical-support helpdesk** and embed the AI copilot into that workflow. This file is the operative prompt for all work inside `frontend/`.

## Mission

Deliver a runnable, tested, visually coherent helpdesk replica where a technician can:

```text
browse tickets → open a ticket → watch AI investigation progress
→ inspect evidence → trigger an approved safe action (request)
→ hand off to a technician → verify resolution → chat with the copilot
```

The AI is part of the technician's workflow, not a separate chatbot page.

## 1. Source of truth (read in this order before writing code)

1. Existing source code and tests (`services/`, `tests/`).
2. `AGENTS.md` — safety boundaries (non-negotiable).
3. `docs/frontend/HELPDESK_REPLICATION.md` — replication process and component list.
4. `docs/frontend/CHATBOT_SPEC.md` — chatbot UX and `/clear` semantics.
5. `FRONTEND_AGENT_PROMPT.md` (repo root) — stacking and integration rules.
6. `docs/architecture/*.md` — system layers; the backend is the policy boundary.
7. `ONE_SHOT_BUILD_PROMPT.md` — overall build order (this is Phase 5–6).
8. `reference/screenshots/reference.pdf` — **visual source of truth** (see §2).
9. `README.md` / `SETUP_AND_DEVELOPMENT.md` — how to run the lab.

If a document conflicts with the code, follow the code and report the conflict.

## 2. FIRST ACTION — inspect the reference PDF (mandatory, before any UI code)

Open and study **every page** of:

```text
reference/screenshots/reference.pdf
```

Facts about this file: 6 pages, exported from Microsoft Word 2021 (2026-10-06); each page contains one helpdesk UI screenshot. These screenshots — not your imagination — define the visual language.

### 2.1 How to view it

- Easiest: open the PDF directly in VS Code / a browser (Edge/Chrome) and page through all 6 pages side-by-side with your editor.
- If you need the pages extracted as images on disk (optional; requires a working shell + Python):

```powershell
python -m pip install pymupdf
python -c "import fitz, pathlib; d=fitz.open(r'reference/screenshots/reference.pdf'); out=pathlib.Path('reference/screenshots/pages'); out.mkdir(exist_ok=True, parents=True); [out.joinpath(f'page_{i+1}.png').write_bytes(p.get_pixmap().tobytes('png')) for i,p in enumerate(d)]"
```

Do **not** modify, move, or commit over `reference/`.

### 2.2 What to inventory per page (do all 6 pages)

For each page record:

- overall layout (regions, proportions, header/sidebar/content split)
- navigation structure and item labels (verbatim text you can read)
- sidebar hierarchy and expand/collapse patterns (esp. site → NVR → camera tree)
- typography (font feel, weights, sizes for headers vs rows)
- spacing rhythm, row heights, borders, corner radii
- colors/surfaces (backgrounds, accent color, status colors) — approximate hex ok
- iconography and where icons appear
- search/filter controls and their placement
- table/list patterns (columns, badges, pagination/scroll)
- detail panels (fields, tabs, sections)
- anything AI-related already visible in the screenshots

### 2.3 Deliverable of Step 2 (write before coding)

Create `frontend/docs/SCREENSHOT_INVENTORY.md` with one section per page following the checklist above, then `frontend/docs/COMPONENT_INVENTORY.md` listing the concrete components you will build and which PDF page each one comes from.

**Do not start component code until both files exist.** Do not invent a generic admin dashboard: every layout decision must trace to a PDF page or a doc in `docs/frontend/`.

## 3. Tech stack and project setup

- **React + Vite + TypeScript** (per `FRONTEND_AGENT_PROMPT.md`), unless the repo already contains a better-supported stack — check first.
- Location: `frontend/` (this directory), package name `helpdesk-frontend`.
- Desktop-first (the workflow is desktop-oriented); must remain usable at ≥1024 px without breaking ticket readability.

### 3.1 Ports and routing

| Mode | Frontend | Backend targets |
|---|---|---|
| Local dev (`npm run dev`) | http://localhost:5173 | Vite proxy: `/helpdesk` → `http://localhost:8000`, `/portal` → `http://localhost:8001`, `/agent` → `http://localhost:8002` |
| Docker (`docker compose up`) | **http://localhost:8003** | nginx proxies to service names `helpdesk:8000`, `portal:8001`, `agent:8002` |

Use the proxy so CORS never becomes a blocker (the backends do not yet emit CORS headers). All API calls in code go through `/helpdesk/...`, `/portal/...`, `/agent/...`.

### 3.2 Repo integration

- Add a `frontend` service to `docker-compose.yml`: build `frontend/Dockerfile` (multi-stage: `node` build → `nginx` serve with SPA fallback to `index.html`), external port **8003**.
- `.gitignore`: `node_modules/`, `dist/`, `.vite/`.
- Keep `npm run build` passing at every phase boundary.

## 4. Design tokens first

Before components, encode the PDF's visual language as tokens (CSS variables or a theme module):

```text
typography scale · spacing scale · radius · border styles
surfaces (app bg, panel bg, row hover, selected row)
status colors (open / in_progress / pending_technician /
               ready_for_verification / resolved / closed,
               priority low|medium|high, fault/healthy indicators)
icon sizing · shadow (if present in screenshots)
```

Components consume tokens only — no hard-coded one-off colors/sizes.

## 5. Component inventory (minimum)

From `docs/frontend/HELPDESK_REPLICATION.md`, extended with AI/chat:

```text
AppShell  Sidebar  Header  SearchBar  FilterBar
TicketList  TicketRow  TicketDetail  StatusBadge
AssetTree  CameraRow            (site → NVR → camera hierarchy)
AIInsightPanel  EvidenceCard  SuggestedActionCard  TechnicianHandoffCard
ChatPanel  ChatComposer
LoadingState  EmptyState  ErrorState
```

Each component must be small, typed (TypeScript props), and testable in isolation.

## 6. Screens and layout targets

### 6.1 Ticket list view (home)

- Header + search + status/priority/site filters matching the PDF's control placement.
- Table of tickets: ID, title, status badge, priority, site, asset, updated-at, `ai_state` indicator.
- Row click → ticket detail.

### 6.2 Ticket detail (the core screen)

Follow the target structure from `HELPDESK_REPLICATION.md`:

```text
Ticket Header:  ID · status · priority · site/property · affected asset
Problem / conversation:  description + notes (author, timestamp, body)
Diagnostics:    timeline of agent runs (status, diagnosis, confidence, error)
AI Copilot:     current summary · diagnosis · confidence · evidence sources
                · suggested next action · safe-action state · verification state
                · technician handoff card
Actions:        request verification · add note · (lab) run agent now
```

### 6.3 Asset / camera tree view

- Replicates the camera-tree screenshot page(s): site → NVR → cameras with health indicators.
- Each row: asset ID, type, IP, reachability, RTSP/service state, current fault (if any).
- Lab-only controls (clearly labeled "SIMULATED"): inject fault (enum in §7), reset simulation.

### 6.4 Lab status strip (small)

Agent status (from `/agent/api/status`): running flag, poll interval, last 5 runs. Lets a technician trust what the AI is doing.

## 7. Backend integration map (exact, verified against source)

### Helpdesk — `/helpdesk`

| Endpoint | Use in UI |
|---|---|
| `GET /api/tickets?status=&limit=` | list (`tickets[]`), status filter |
| `POST /api/tickets` | (agent creates tickets; UI only for lab demo) |
| `GET /api/tickets/{id}` | detail + `notes[]` |
| `PATCH /api/tickets/{id}` | status transitions, `ai_summary`, `ai_state`, `root_cause`, `resolution` |
| `GET /api/search?q=&asset_id=&limit=` | search box (`results[]`) |
| `POST /api/tickets/{id}/notes` | add note (author = synthetic technician name) |
| `POST /api/tickets/{id}/request-verification` | "Ready for verification" button |

Statuses: `open, in_progress, pending_technician, ready_for_verification, resolved, closed`.
AI states seen in code: `new, investigating, awaiting_technician, resolved`.

### Portal — `/portal`

| Endpoint | Use in UI |
|---|---|
| `GET /api/assets` | asset tree / health dashboard |
| `GET /api/assets/{id}` | asset detail |
| `GET /api/assets/{id}/health`, `/ping`, `/tcp-test?port=`, `/rtsp-test` | diagnostics on ticket detail |
| `GET /api/site/{site_id}/assets` | tree per site |
| `GET /api/events` | active-faults banner |
| `POST /api/simulate/fault` | lab fault injection `{asset_id, fault}` |
| `POST /api/assets/{id}/actions/reset-simulation` | lab reset |

Fault enum (valid values): `network_down, rtsp_auth_failure, rtsp_down, high_cpu, storage_full, poe_off, ai_service_down, cloud_down`.
Seed assets: `CAM-027, CAM-018, CAM-019, NVR-02, AI-BOX-07` at `SITE-104`.

### Agent — `/agent`

| Endpoint | Use in UI |
|---|---|
| `GET /api/status` | status strip, investigation feed (`recent_runs[]`) |
| `POST /api/monitor/run` | "Run monitor now" (lab) |
| `POST /api/tickets/{id}/run` | "Investigate now" → `diagnosis, confidence, recommended_action, auto_action, next_status, evidence` |

### Chat (Phase 6 — backend lands with the chat phase)

Design ChatPanel against this contract; treat 404 gracefully until deployed:

```text
POST /api/chat/sessions                → {session_id}
POST /api/chat/sessions/{id}/messages  → {reply, investigation?}
POST /api/chat/sessions/{id}/clear     → resets chat context only
GET  /api/incidents/{ticket_id}        → incident state/evidence/plan
```

## 8. AI copilot behavior (the differentiating screen)

`AIInsightPanel` must show, distinguishing evidence from conclusions:

```text
Diagnosis      — likely cause in plain language
Confidence     — high / medium / low (map from numeric when present)
Evidence       — bullet list: probe results, historical ticket IDs, doc paths
                 (each bullet labeled: observed / retrieved)
Next step      — suggested action or "technician required"
Action state   — idle | requested | policy-denied | executing | verifying
                 | verified | verification-failed
Handoff card   — the 7-element technician handoff when status is
                 pending_technician
Verification   — never show "success" until a post-action re-check passed
```

Rules:

- A button like **Run safe reconnect** sends a request to the backend. **The backend policy engine decides** — surface `policy-denied` honestly. The UI is never the permission boundary.
- Show agent progress lines (investigating / checking reachability / searching history / reviewing RTSP evidence / verification complete) via `/agent/api/status` polling (≈2–5 s; no websocket required).
- Never display an action as successful because it *started*. Success requires the verification state.

## 9. Chatbot / copilot panel

Per `docs/frontend/CHATBOT_SPEC.md`:

- Inline with the ticket view (right dock or bottom panel), bound to the selected ticket/asset context.
- Suggested prompts: `Investigate this ticket.` · `What have you found?` · `What evidence supports this diagnosis?` · `Which historical tickets are similar?` · `Run the approved diagnostic checks.`
- Answers show diagnosis, confidence, evidence bullets (with ticket/doc citations), and next step — concise, no hidden chain-of-thought.
- **`/clear`** typed in the composer clears only that session's conversation, then displays verbatim:

  > Conversation context cleared. Ticket and system data were not changed.

  It must never trigger deletes against helpdesk/portal/agent data.
- Distinguish error states in the UI: `model unavailable`, `tool unavailable`, `ticket unavailable`, `policy denied`, `technician required`, `verification failed`.

## 10. Safety rules (non-negotiable, from AGENTS.md)

- Synthetic data only. No production URLs, credentials, tokens, or customer data — anywhere, including `.env`.
- Fault injection / reset controls are clearly marked as **simulated lab controls**.
- No action may execute client-side; every action is a request the backend validates.
- Never render an AI claim as fact without its evidence source; label observed vs retrieved.
- The repo remains a local simulation — do not add integrations to real cameras, NVRs, AI Boxes, cloud, or live helpdesks.

## 11. Build order (each phase ends with a green build)

```text
F0  Read all sources (§1). Inspect all 6 PDF pages. Write
    SCREENSHOT_INVENTORY.md + COMPONENT_INVENTORY.md.          [gate]

F1  Scaffold Vite + React + TS in frontend/; tokens; AppShell,
    Sidebar, Header; proxy config; npm run build green.

F2  Static replica with synthetic fixtures: TicketList, TicketRow,
    StatusBadge, FilterBar, SearchBar, AssetTree/CameraRow, TicketDetail
    layout — visually matched against the relevant PDF pages.

F3  Live wiring: helpdesk list/detail/search/notes/verification,
    portal asset tree + events. Loading/Empty/Error states everywhere.

F4  Diagnostics + lab: portal probes on ticket detail, fault injection
    and reset controls, agent status strip, run-now buttons.

F5  AI copilot: AIInsightPanel, EvidenceCard, SuggestedActionCard,
    TechnicianHandoffCard, action-state machine, verification display.

F6  Chat: ChatPanel + ChatComposer + /clear + error taxonomy
    (graceful when chat endpoints are not yet deployed).

F7  Docker: Dockerfile + compose service on :8003; final visual pass
    page-by-page against reference.pdf; usage notes in README.
```

## 12. Validation (required — "files exist" is not done)

1. `npm run build` passes (and `npx tsc --noEmit` if configured).
2. Visual pass: side-by-side compare each implemented screen against its PDF page; fix layout/visual discrepancies before moving on (per `HELPDESK_REPLICATION.md`).
3. Smoke flow against the running stack (`docker compose up --build -d`):
   - open ticket list → open ticket 1001 → see notes and AI panel;
   - search "RTSP" → results render;
   - inject `rtsp_down` on CAM-027 → event/ticket appears → agent run updates the panel → safe-action state cycles to `verified` → ticket resolved;
   - inject `poe_off` → ticket reaches `pending_technician` → 7-element handoff card renders;
   - type `/clear` in chat → confirmation message shows, ticket data untouched (verify via API that counts are unchanged).
4. No console errors; no network calls outside the three proxies.

## 13. Final report

Report: pages of `reference.pdf` used per screen · component inventory · commands run · build/test results · smoke-flow results · remaining screenshot-vs-replica discrepancies · limitations · next step.

Never claim visual or functional success you did not verify.
