# NEXT AGENT BRIEF — start here

> Updated 2026-10-07. This file is the handoff: what exists, what is broken, what to do next, and how to sync GitHub. Read it before `ONE_SHOT_BUILD_PROMPT.md`.

## 1. Read order (new AI agent)

1. This file — status, defects, plan, sync.
2. `AGENTS.md` — hard rules (safety boundary, source-of-truth order, testing, definition of done).
3. `ONE_SHOT_BUILD_PROMPT.md` — master mission and phase order.
4. `PROJECT_WORKFLOW.md` + `PROJECT_INDEX.md` — system overview and file map.
5. Code: `services/helpdesk/app.py`, `services/portal/app.py`, `services/agent/{main,core,knowledge}.py`, `services/agent/{orchestrator,policy,tools}/*.py`, `tests/test_sanity.py`, `tests/test_orchestrator.py`.
6. Specs: `docs/architecture/*.md`, `docs/subagents/*.md`, `prompts/*.md`, `docs/frontend/*.md`.
7. Frontend phase: `frontend/FRONTEND_BUILD_PROMPT.md` (operative) + `reference/screenshots/reference.pdf`.

Bootstrap commands that must work from a clean checkout:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt      # now includes pytest
python -m compileall services tests
python -m pytest -q                            # 36 passed after read-only ticket chat
docker compose up --build -d
```

**Shortcut:** `powershell -ExecutionPolicy Bypass -File scripts\phase0_bootstrap.ps1` performs the whole sequence above (installs Python via winget if missing, re-run once after PATH refresh) and runs the optional Docker smoke.

## 2. Current state (verified 2026-10-06 against code)

| Component | State | Notes |
|---|---|---|
| Helpdesk API (`services/helpdesk`) | implemented, v0.2.0 | FastAPI + SQLite, 5 seed tickets, statuses incl. `pending_technician`/`ready_for_verification`, search/notes/PATCH; DB path env-configurable via `HELPDESK_DB` (defect #1 fixed) |
| Portal (`services/portal`) | implemented, v0.2.0 | in-memory assets `CAM-027/018/019`, `NVR-02`, `AI-BOX-07` @ `SITE-104`; 8 fault types; safe actions `reconnect-rtsp`, `restart-ai-service`; events feed |
| Agent (`services/agent`) | implemented, v0.2.0 | persistent worker thread, episode dedup (`monitor_events`), heuristic `investigate()`, token knowledge search, run history in `agent.db`, manual run/monitor APIs |
| Docker Compose | implemented and frontend smoke-tested | helpdesk :8000, portal :8001, agent :8002, nginx frontend :8003; front door and all three API proxies respond |
| Tests | ✅ 36 passed (2026-10-07) | Prior 32 tests plus four `test_ticket_chat` cases for live/export lookup, site confidence, status filtering, privacy, and read-only behavior; failed-verification escalation and formal replay metrics remain for Phase 7 |
| Docker Compose | ✅ installed and smoke-tested (2026-10-07) | Docker Desktop 4.94.0; Engine 29.8.2; Compose v5.5.1; helpdesk :8000, portal :8001, agent :8002 all healthy; RTSP recovery and PoE technician handoff verified in containers |
| Prompts (`prompts/`) | upgraded 2026-10-06 | all 10 rewritten: input contract, evidence labels (`observed/retrieved/inferred`), structured `SpecialistResult` JSON, confidence scale, per-role failure-signature tables, orchestrator routing table |
| Frontend | 🚧 working preview; Phase 5 still in progress | queue/detail, notes, portal probes, asset tree, simulation controls, backend investigation request, and read-only ticket lookup chat with simpler new-hire-friendly explanations and local `/clear`; verification-request wiring awaits a backend state-transition fix |
| Visual reference | `reference/screenshots/reference.pdf` | 6 pages, Word 2021 export 2026-10-06. Legacy JPG names (`helpdesk_camera_tree_01/02.jpg`) do NOT exist on disk |
| Ticket lookup chat | ✅ Implemented and locally smoke-tested | `POST /api/chat/query` reads Helpdesk tickets/notes and an optional read-only local CSV export; no LLM key, writes, portal calls, or agent actions. CSV metadata-only matches are identified; emails are never returned. |
| LLM adapter | NOT IMPLEMENTED | deterministic-first; adapter must sit behind policy (AGENTS.md LLM rules) |
| Orchestrator / policy / tool modules | ✅ Phase 2 validated (2026-10-07) | State machine, routing, budgets, evidence review, deterministic policy gate, safe-only ToolBus, audit persistence, and `main.py` monitor-to-ticket orchestration path are tested |
| Specialist modules | ✅ Phase 3 validated (2026-10-07) | Eight deterministic specialists dispatch behind the router; findings are persisted, retrieval is budgeted/read-only, and Evidence Review requires evidence + specialist support before the policy gate can execute a safe action |
| Git | ✅ synced 2026-10-06 | `origin` → `https://github.com/frogrest/CarlBot.git`, branch `main`, initial push force-approved + run + verified by the owner — see §5 |
| Knowledge docs | thin | `docs/` holds specs, no SOPs yet; retriever scans `docs/**/*.md` recursively (spec docs are currently searchable too — consider scoping later) |

## 3. Known defects & gotchas (fix early)

1. ~~Hard-coded DB path~~ ✅ **FIXED & validated 2026-10-06** — `db_path()` resolves `HELPDESK_DB` per call (Docker default `/app/data/helpdesk.db` unchanged); test fixtures rely on it. (Historical: the module constant broke local non-Docker tests.)
2. **Test coverage** — 36 tests pass. Coverage includes RTSP recovery, PoE technician handoff, auth-failure denial, AI-service recovery, monitor-created ticket processing, helpdesk status/note updates, incident/audit persistence, specialist dispatch, read-only tool boundaries, ticket lookup, and action/evidence mismatch denial for invalid or unknown auth. Failed-verification escalation and the formal replay/evaluation matrix remain for Phase 7.
3. **No CORS** — backends emit no CORS headers. The frontend must use the dev/nginx proxy (frontend prompt §3.1), or CORS must be added with an `ALLOWED_ORIGINS` env var.
4. **Agent re-run behavior** — the background worker periodically re-processes open/`ready_for_verification` tickets. Docker smoke verified monitor-created ticket processing through the worker for RTSP recovery and PoE handoff; broader long-duration worker behavior remains untested.
5. **Manifest** — regenerate from `git ls-files --cached --others --exclude-standard` whenever the tracked tree changes.
6. **Version wording** — code is `0.2.0`; README/PROJECT_INDEX now match. `legacy/` holds v0.3-era docs — not current, do not follow them over root docs.
7. **`pytest` was missing from `requirements.txt`** — fixed 2026-10-06 (`pytest>=8,<10`). If bootstrap fails, check `pip install` output first.
8. **Screenshots** — never cite `helpdesk_camera_tree_01.jpg` / `_02.jpg`; they do not exist. Use `reference/screenshots/reference.pdf`.
9. **Host tooling status (verified 2026-10-07)** — **Git: ✅ installed.** **Python: `.venv` runs 3.14.8** (meets the 3.13+ requirement; differs from the previous handoff's reported 3.13). **Node: v24.21.0; `npm.cmd`: 11.19.0.** `npm.ps1` is blocked by the current PowerShell execution policy; use `npm.cmd`. **Docker Desktop: ✅ installed and running** (4.94.0; Engine 29.8.2; Compose v5.5.1); all four containers run, the frontend responds on :8003, and its helpdesk/portal/agent proxies respond. Resolve `docker.exe` through Docker Desktop's installed path or refresh the shell if `docker` is not yet on PATH.
10. **`data/` state** — the directory exists via `.gitkeep`; runtime `*.db` files are gitignored. To reset the lab: stop the stack first, then delete `data/*.db` (never delete while running, per AGENTS.md debugging playbook).
11. **Deprecation warnings — FIXED 2026-10-08 for app code.** `services/helpdesk/app.py` and `services/agent/main.py` migrated from `@app.on_event('startup'/'shutdown')` to `lifespan` handlers (same behavior: helpdesk seeds DB on startup; agent starts/joins its worker thread). The remaining `httpx`-in-TestClient notice is a Starlette library warning, not project code.

## 4. Build phases (ONE_SHOT order; keep every phase green before starting the next)

| Phase | Work | Exit criteria |
|---|---|---|
| ✅ 0 Pre-flight | DONE 2026-10-06 via `scripts/phase0_bootstrap.ps1` (Python + `.venv` + deps); Docker installed 2026-10-07 | `pytest -q` → 32 passed ✔ · Compose build and service health checks ✔ |
| ✅ 1 Stabilize (code+tests) | DONE 2026-10-06: `HELPDESK_DB` fixed, 18 new tests, `data/.gitkeep`, README updated | suite green ✔ · Docker `rtsp_down` recovery and `poe_off` → `pending_technician` smoke verified 2026-10-07 |
| ✅ 2 Orchestrator | validated 2026-10-07: state machine + routing + budgets + duplicate suppression + policy gate + safe ToolBus + audit trail + helpdesk synchronization | compileall green; 29 passed at Phase 2 commit; monitor-to-orchestrator and persistence covered |
| ✅ 3 Specialists | validated 2026-10-07: 8 deterministic evidence-only specialists behind routing; knowledge/history/site lookups are read-only and budgeted | compileall green; full suite 32 passed; auth mismatch blocks RTSP recovery and only policy-approved safe actions execute |
| 4 LLM adapter | reasoner interface; deterministic reasoner as default; env-gated LLM adapter with strict schema validation and deterministic fallback | full replay suite passes with LLM off; malformed model output rejected |
| 🚧 5 Frontend | in progress; follow `frontend/FRONTEND_BUILD_PROMPT.md` F0–F7 (PDF inventory gate completed) | `npm run build` green; per-page visual pass; smoke flows in §12 of that file |
| 6 Chat | session store, responder, `/clear`, chat endpoints, ChatPanel | `/clear` test proves ticket/history/audit data untouched |
| 7 Evaluation | 7 required scenarios as declarative tests + metrics runner (diagnosis accuracy, safe-action success, verification success, unnecessary escalation, tool-call count) | all 7 scenarios pass locally and in Docker |

Never weaken a test to make a feature pass; never skip the evidence-review gate; any new autonomous action needs contract + risk class + preconditions/postconditions + verification + retry limit + audit + tests + docs (AGENTS.md).

## 5. GitHub sync — `https://github.com/frogrest/CarlBot.git`

**Status: ✅ initial sync done (2026-10-06); current frontend changes are local and uncommitted.** The owner installed Git and ran the initial sync manually from their own PowerShell after the executing agent's tool terminal proved wedged. The push to `https://github.com/frogrest/CarlBot.git` (branch `main`) was verified by the owner. `FILE_MANIFEST.txt` was regenerated from tracked and non-ignored untracked paths on 2026-10-07; regenerate again after future file additions. Routine flow, when explicitly ready to publish: `git add -A && git commit && git push`. The script below is kept only as a recovery path if the remote ever needs re-initializing.

Easiest — run the prepared script (init → stage → commit → attach remote → inspect → force-push):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\connect_github.ps1
```

Manual equivalent:

```powershell
cd <repo-root>
git init -b main
git config user.name  "<your name>"      # only if not globally configured
git config user.email "<your email>"
git add -A
git commit -m "AI helpdesk lab: services, upgraded prompts, frontend build prompt, docs"
git remote add origin https://github.com/frogrest/CarlBot.git
git ls-remote --heads origin             # inspect whatever the remote holds now
git push --force -u origin main          # force approved by the owner
git ls-remote --heads origin             # verify the push
```

Notes:

- **Auth**: Git Credential Manager (Windows default) or a PAT. An agent cannot bypass authentication — ask the human if credentials are unavailable.
- If `git init -b main` is unsupported (git < 2.28): `git init` then `git checkout -b main`.
- `.gitignore` already excludes `.venv/`, `__pycache__/`, `*.pyc`, `*.db`, `.env`, `.pytest_cache/`, `node_modules/`, `dist/`, `.vite/`, `reference/screenshots/pages/`.
- Never commit: secrets, keys, customer data, production exports (AGENTS.md repository hygiene).
- After the first successful push, routine flow is `git add -A && git commit && git push`.
- Reconcile `FILE_MANIFEST.txt` against `git ls-files` after the first commit.

## 6. Definition of done & final report

A phase is done only when all of these hold (AGENTS.md + ONE_SHOT):

1. behavior implemented; 2. relevant tests pass — actually run, not assumed; 3. integration/smoke verified where applicable; 4. no real systems contacted; 5. safety/policy boundaries intact; 6. docs updated; 7. a clean checkout still bootstraps.

Your final report must state: final architecture · directory tree · commands used · tests passed · scenarios passed · implemented specialists · chatbot behavior · current autonomous actions · limitations · next recommended phase. Never claim success you did not verify.

**Non-negotiables (repeat):** only `reconnect-rtsp` and `restart-ai-service` may run autonomously; the deterministic policy layer is the security boundary — never the prompt or the LLM; destructive, privileged, physical, or credential/network-config actions stay human-controlled; the lab stays disconnected from production cameras, NVRs, AI Boxes, customer networks, and live helpdesks.

---

## Progress log

- **2026-10-06 — Phase 1 ✅ VALIDATED (20 passed, 4.29s).** Owner ran `scripts/phase0_bootstrap.ps1`: Python 3.13 installed via winget, `.venv` created, `compileall` + `pytest -q` green = 2 original + 18 new tests. One bug found & fixed during validation (conftest MockTransport handler wasn't forwarding POST bodies → 422s; fixed by passing content+headers). Docker not installed → container smoke deferred (needed before Phase 5 / integration checks). Remaining warnings are cosmetic deprecation notices (defect #11). **Next: Phase 2 (orchestrator).**
- **2026-10-07 — Phase 2 ✅ VALIDATED (29 passed).** Pulled latest (`git pull --ff-only origin main`; already up to date), confirmed `main` matches `origin/main`, ran `python -m compileall services tests` and `.\\.venv\\Scripts\\python.exe -m pytest -q` (29 passed; 7 existing FastAPI/Starlette deprecation warnings). Targeted monitor/orchestrator tests pass (12). Verified simulated `rtsp_down` monitor event creates exactly one helpdesk ticket, `process_ticket()` runs the orchestrator, policy allows only `reconnect-rtsp`, verification resolves the helpdesk record, and incident/audit rows survive reopening their SQLite stores. Verified `poe_off` lands as `pending_technician` without an action and auth failure does not change credentials. Fixed test harness URL wiring and made verification outcome explicit in the helpdesk note. Regenerated `FILE_MANIFEST.txt`. No real services/devices were contacted. Docker is unavailable, so container/background-worker smoke remains deferred. **Next: Phase 3 — bounded specialist modules behind the router.**
- **2026-10-07 — Phase 3 ✅ VALIDATED (32 passed).** Added the eight deterministic specialists under `services/agent/specialists/`: Helpdesk, Network, RTSP, Camera/NVR, AI Box, Knowledge, Evidence Review, and Technician Handoff. Routed findings are stored in incident context; historical/document/site-inventory calls are budgeted and exposed through read-only tools. Evidence Review requires observed action preconditions and support from the routed RTSP/AI Box specialist; the policy engine still independently decides permission, and the ToolBus remains restricted to `reconnect-rtsp` and `restart-ai-service`. Disabled direct action execution in the legacy `Agent` adapter, so autonomous changes must enter through the policy-gated orchestrator. `compileall` and the full `pytest -q` suite pass (32 passed, 7 existing deprecation warnings); tests cover all specialist names, lack of mutation methods, and invalid/unknown-auth rejection. No real systems were contacted. Docker smoke remains deferred. **Next: Phase 4 — structured LLM adapter behind the same policy/tool boundary.**
- **2026-10-07 — Docker Desktop installed and Compose smoke verified.** After Docker Desktop installation/restart, started the engine (Docker Desktop 4.94.0; Engine 29.8.2; Compose v5.5.1), ran `docker compose up --build -d`, and confirmed all three services were Up with `/api/health` returning `ok: true`. Injected simulated `CAM-027:rtsp_down`; monitor created ticket 1006 and the container worker safely reconnected, verified, and resolved it. Injected `CAM-019:poe_off`; monitor created ticket 1007 and the worker stopped at `pending_technician` / `awaiting_technician` without autonomous action. Reset both simulated assets afterward. All checks remained within the fake lab; no production systems were contacted.
- **2026-10-07 — Frontend preview delivered; Phase 5 remains in progress.** Added the PDF screenshot/component inventories and original `impeccable`, `taste`, and `frontend-visual-qa` skills. Implemented the React/Vite/TypeScript ticket queue/detail, helpdesk notes, emulator health/ping/TCP/RTSP probes, policy-gated investigation request, hierarchical synthetic asset inventory, fault simulation/reset controls and an explicitly offline chat shell with local-only `/clear`. Added local Vite and Docker nginx proxies; Compose exposes the UI at :8003. `npm.cmd run lint` and `npm.cmd run build` pass. `compileall` and all 32 Python tests pass (7 pre-existing deprecation warnings). Browser QA at 1280px and 390px exercised ticket search/filter/detail, four diagnostics, nested camera tree, handoff-action disablement, and `/clear`; no page errors were observed and ticket count remained 7 before/after clearing. Docker frontend is Up and UI plus all three API proxies return healthy responses. `FILE_MANIFEST.txt` regenerated. The UI withholds technician verification request because the current helpdesk endpoint does not set the worker's expected `verify_requested` state; fix that transition before wiring a button. Remaining: page-by-page QA against all six PDF pages, a fresh UI-driven full fault/recovery run, and implementation of the missing chat backend. No production systems were contacted.
- **2026-10-07 — Read-only ticket lookup chat implemented.** Added `POST /api/chat/query`, deterministic matching over live Helpdesk records/notes and the optional local CSV export, open/closed filtering, unconfirmed partial-site wording, and metadata-only export disclosure. CSV sender emails are excluded from results; the local reference file is explicitly git-ignored and mounted read-only. Wired the chat into both ticket queue and detail views; it calls only the read-only Helpdesk lookup and `/clear` remains browser-local. No LLM/API key is needed. Focused ticket-chat tests pass (4), full `compileall` + pytest pass (36), and frontend lint/build pass. Rebuilt all Compose services; all four containers are Up and a closed RTSP lookup returned live ticket records. No real systems were contacted. Remaining frontend work: page-by-page visual QA, verification-request state wiring, and a UI-driven fault/recovery run.
- **2026-10-07 — Synthetic ticket demo and simpler chat replies.** Added 12 fake tickets (IDs 1008–1019) to the running local Helpdesk DB using only broad issue-category patterns from the user's CSV; no names, emails, ticket IDs, or locations were copied. The running agent completed 12/12 runs successfully. All 12 reports were not reproduced by the current healthy emulator, so the agent recorded low-confidence findings and handed them to a technician; no automatic actions ran. Chat now explains common diagnosis terms and ticket statuses in plain language, welcomes new hires with example questions, and offers a next-search suggestion when it finds no match. Changes are local; runtime demo records live only in ignored SQLite state and are not part of the source tree.
- **2026-10-07 — CarlBot visual emphasis and concise chat UI.** Updated the 12 local synthetic records (IDs 1008–1019) to remove the visible `DEMO:` prefix and use natural but qualified reported-issue wording; statuses and timestamps were preserved. CarlBot gained a wider, higher-contrast panel, 14px messages, and a 15px composer. A visual audit found the chat panel below the full ticket list, so the queue view now keeps it in a sticky side rail on desktop and stacks it below the list on narrow screens. Message arrival and focus transitions use CSS, with reduced-motion support; no animation dependency is needed. Updated `docs/frontend/CHATBOT_SPEC.md` and frontend build guidance with hierarchy, typography, and accessibility rules. Frontend lint/build pass; browser verified at 1280px and 390px with no horizontal overflow, and reduced-motion behavior was confirmed. Full Python suite was green at 38 tests before this frontend-only change. No production systems were contacted.
- **2026-10-07 — Ticket subject lookup and direct chat links.** Chat now treats `subject`/`title` as query-intent words so they do not weaken matching, and a regression test verifies that asking for a ticket's subject returns its stored title. Assistant messages render links for numeric live Helpdesk matches; selecting a link opens the ticket detail, updates the shareable `?ticket_id=` URL, supports direct reload, and handles browser back/forward. Reference-export-only rows remain unlinked. Updated chatbot and frontend guidance. Python compileall and all 39 tests pass; frontend lint/build pass. Browser confirmed subject reply, direct ticket link, ticket detail load after reload, and back navigation to the queue. No production systems were contacted.
