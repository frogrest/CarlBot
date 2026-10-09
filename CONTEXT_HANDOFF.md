# CONTEXT HANDOFF PROMPT (paste this to another AI agent)

You are a coding agent working on **CarlBot / AI Ops Assistant Lab** at `c:\Users\USER\Documents\HelpdeskBotPreview\CarlBot`.

## Mission (read first)
A **safe, fully-emulated technical-operations lab** (v0.2.0). It simulates a CCTV/helpdesk environment (cameras, NVRs, AI Boxes across multiple sites) and an autonomous agent that investigates faults — WITHOUT ever touching production hardware, networks, or credentials. Automate repetitive investigation/documentation; keep humans responsible for physical/consequential work and approvals. **The safety boundary is non-negotiable.**

## Hard rules (from AGENTS.md — obey these)
1. Never connect to a real customer system/camera/NVR/AI Box/helpdesk.
2. Never put credentials, tokens, keys, or customer data in the repo.
3. A fake tool must never silently call a real device.
4. Do NOT bypass the policy/action layer just because a model recommends an action.
5. Destructive/physical/irreversible actions stay human-controlled.
6. Prefer deterministic tests + simulated faults.
- Doc hierarchy: source code/tests > `AGENTS.md` > `AUTONOMOUS_AGENT_LAB.md` > `README.md`/`docs/`. Ignore the `legacy/` folder (outdated v0.3 docs).

## Tech stack
Python 3.13+ · FastAPI · Pydantic v2 · httpx · SQLite | React 19 + TypeScript + Vite (nginx) | pytest (in-process) | Docker Compose.

## Architecture (4 containers)
```
Browser ──> Frontend nginx :8003 (proxies /helpdesk /portal /agent)
              ├─ Helpdesk :8000  (tickets + chatbot + knowledge API, SQLite)
              ├─ Portal    :8001  (15 fake assets / 4 sites / 8 faults / 2 safe actions)
              └─ Agent     :8002  (autonomous worker + orchestrator + specialists + policy)
```
- **Portal** (`services/portal/app.py`): in-memory `ASSETS`; `current()` overlays fault effects; `/api/events` feed; safe actions `reconnect-rtsp`, `restart-ai-service`.
- **Helpdesk** (`services/helpdesk/app.py`): seeds 25 synthetic tickets. TWO status axes: user desk status (`ticket_status`: Open/Answered/Closed) vs agent workflow `status` (open/in_progress/pending_technician/ready_for_verification/resolved/closed). DB path from `HELPDESK_DB`.
- **Agent** (`services/agent/main.py`): worker thread polls every 5s (`AGENT_POLL_INTERVAL`); `monitor_once()` creates 1 ticket per active fault episode (dedup via `monitor_events`); `process_ticket()` runs the orchestrator.

## Agent internals (`services/agent/`)
- `core.py` — legacy `Agent`; now READ-ONLY (direct actions raise).
- `orchestrator/` — `state.py` (12-state machine + SQLite-persisted `IncidentContext` JSON), `router.py` (evidence-based routing, not keywords), `budgets.py` (caps tool/specialist/action/retry/wall-clock → forces handoff), `engine.py` (stage driver), `models.py` (Pydantic contracts).
- `policy/engine.py` — **safety gate**: allow-list of 2 safe actions + preconditions; everything else is C/D (approval/human-only). `policy/audit.py` — audit trail.
- `tools/bus.py` — the ONLY outside-world path; refuses unregistered actions (2nd barrier).
- `specialists/dispatcher.py` — 8 deterministic evidence-only specialists (helpdesk/network/rtsp/camera_nvr/aibox/knowledge/evidence/technician) via budgeted read-only tools.
- `reasoning/` — `deterministic.py` (decision table), `llm_adapter.py` (OpenAI-compatible, strict `Plan` schema, secret redaction, deterministic fallback via `FallbackReasoner`), `schemas.py` (strict contracts).
- `evaluation.py` — 7 declarative benchmark scenarios + metrics; CLI `scripts/run_evaluation.py`.

## Orchestrator state machine
```
NEW→CLASSIFYING→INVESTIGATING→EVIDENCE_REVIEW→DIAGNOSED→ACTION_PROPOSED
     →SAFE_EXECUTION→VERIFYING→RESOLVED
     ↘HUMAN_REQUIRED→PENDING_TECHNICIAN→READY_FOR_VERIFICATION→VERIFYING→RESOLVED
```
Rule: propose → policy decide → execute (only if allowed) → verify real telemetry → resolve OR escalate to `pending_technician`. `SUPPRESS_STATES={PENDING_TECHNICIAN,RESOLVED}` enable idempotency/duplicate suppression.

## CarlBot chatbot (helpdesk-side, NOT the agent)
- `ticket_chat.py` — token-overlap ticket search (live DB + optional CSV export), target-ticket-ID extraction, NL synthesis.
- `chat_knowledge.py` — `KnowledgeRetriever` searches ONLY approved doc subdirs (`SOP, RTSP, Networking, Cameras, NVR, AI-Box, Alarm-EG, AI-Cloud, Vendor, Escalation, Known-Issues`) with section parsing + line locators + citations.
- `chat_reasoner.py` — optional LLM with grounding/citation checks + deterministic fallback; can draft (not send) customer replies; redacts secrets. Endpoints: `POST /api/chat/query`, `POST /api/tickets/{id}/customer-replies` (idempotent).

## Local LLM runtime (`services/local_llm/`)
- CarlBot can start/own its own local **llama.cpp** `llama-server` (OpenAI-compatible `/v1`) — no Ollama, no API key.
- `config.py` — validated `LOCAL_LLM_*` env with safe defaults; `runtime.py` — `LocalLlmRuntime` (`status()`/`ensure_started()`/`health_check()`/`generate()`/`stop()`, single-instance guard, loopback bind, validated argv, bounded timeouts, child reaping); `client.py` — `resolve_endpoint()` (ready local runtime > external `LLM_BASE_URL`/`LLM_MODEL` > deterministic).
- Helpdesk and agent each manage their own runtime in their `lifespan`; both expose `GET /api/llm/status` and `POST /api/llm/start`.
- UI: `frontend/src/components/LlmStatusBadge.tsx` (truthful state + retry) in `CarlBotChatView.tsx` and the ticket-side chat.
- Docs: `LOCAL_LLM_SETUP.md`; tests: `tests/test_local_llm.py`.
- **Real inference smoke test NOT yet run** (no GGUF model installed); deterministic fallback is the default.

## Frontend (`frontend/src/`)
`App.tsx` (router/state) · `api.ts` (typed fetch, `/helpdesk|/portal|/agent` prefixes) · `types.ts` · `components/` (Dashboard, Tasks, Knowledge, CarlBotChatView) · `knowledgeData.ts`. `vite.config.ts` proxies to **127.0.0.1** (NOT localhost) with a 502 `backend_unreachable` handler.

## Testing (no network/Docker)
`tests/conftest.py` runs FastAPI apps via `TestClient` and re-points the agent's httpx client at a `MockTransport` routed to those apps. Fixtures: `helpdesk` (fresh DB), `portal` (pristine state), `agent_main`. Commands:
```
python -m pytest -q                 # ~81 passed, 1 skipped (LLM tests opt-in via RUN_LLM_TESTS=1)
python -m compileall services tests
```

## Conventions / gotchas
- All paths/URLs are env-injectable (`HELPDESK_DB`, `AGENT_DB`, `DOCS_ROOT`, `HELPDESK_URL`, `PORTAL_URL`).
- Uses `lifespan` handlers (not deprecated `@app.on_event`).
- On this Windows host use `npm.cmd` (npm.ps1 is blocked).
- Style: small typed modules, explicit Pydantic schemas, deterministic sim state, dependency injection, idempotent ops, tests near behavior. Avoid hidden globals, hard-coded prod endpoints, model→DB coupling, unbounded retries.
- Definition of done: behavior implemented + tests pass + no real systems contacted + safety/policy intact + docs updated + clean-checkout bootstrap still works.

## Quick API map
Agent: `GET /api/status`, `POST /api/monitor/run`, `POST /api/tickets/{id}/run`, `GET /api/incidents/{id}`.
Helpdesk: `GET/POST /api/tickets`, `GET/PATCH /api/tickets/{id}`, `/notes`, `/customer-replies`, `/request-verification`, `POST /api/chat/query`, `GET /api/knowledge`, `GET /api/search`.
Portal: `GET /api/assets`, `/health`, `/ping`, `/tcp-test`, `/rtsp-test`, `/events`, `POST /api/simulate/fault`, `/actions/reconnect-rtsp`, `/actions/restart-ai-service`, `/actions/reset-simulation`.

Now read `NEXT_AGENT_BRIEF.md`, then the specific files for your task, and confirm the plan before editing.

