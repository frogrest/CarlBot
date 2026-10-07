# NEXT AGENT BRIEF — start here

> Written 2026-10-06 by the previous coding agent. This file is the handoff: what exists, what is broken, what to do next, and how to sync GitHub. Read it before `ONE_SHOT_BUILD_PROMPT.md`.

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
python -m pytest -q                            # 29 passed after Phase 2 integration coverage
docker compose up --build -d
```

**Shortcut:** `powershell -ExecutionPolicy Bypass -File scripts\phase0_bootstrap.ps1` performs the whole sequence above (installs Python via winget if missing, re-run once after PATH refresh) and runs the optional Docker smoke.

## 2. Current state (verified 2026-10-06 against code)

| Component | State | Notes |
|---|---|---|
| Helpdesk API (`services/helpdesk`) | implemented, v0.2.0 | FastAPI + SQLite, 5 seed tickets, statuses incl. `pending_technician`/`ready_for_verification`, search/notes/PATCH; DB path env-configurable via `HELPDESK_DB` (defect #1 fixed) |
| Portal (`services/portal`) | implemented, v0.2.0 | in-memory assets `CAM-027/018/019`, `NVR-02`, `AI-BOX-07` @ `SITE-104`; 8 fault types; safe actions `reconnect-rtsp`, `restart-ai-service`; events feed |
| Agent (`services/agent`) | implemented, v0.2.0 | persistent worker thread, episode dedup (`monitor_events`), heuristic `investigate()`, token knowledge search, run history in `agent.db`, manual run/monitor APIs |
| Docker Compose | implemented | helpdesk :8000, portal :8001, agent :8002; bind mount `./data` |
| Tests | ✅ 29 passed (2026-10-07) | `test_sanity` (2) + `test_helpdesk_api` (7) + `test_portal_api` (8) + `test_monitor_dedup` (4) + `test_orchestrator` (8); failed-verification escalation and formal replay metrics remain for Phase 7 |
| Prompts (`prompts/`) | upgraded 2026-10-06 | all 10 rewritten: input contract, evidence labels (`observed/retrieved/inferred`), structured `SpecialistResult` JSON, confidence scale, per-role failure-signature tables, orchestrator routing table |
| Frontend | app code NOT STARTED | only `frontend/FRONTEND_BUILD_PROMPT.md`; build order F0–F7 inside it; gate F0 = inventory the PDF |
| Visual reference | `reference/screenshots/reference.pdf` | 6 pages, Word 2021 export 2026-10-06. Legacy JPG names (`helpdesk_camera_tree_01/02.jpg`) do NOT exist on disk |
| Chat/copilot backend | NOT IMPLEMENTED | endpoint contract defined in frontend prompt §7 |
| LLM adapter | NOT IMPLEMENTED | deterministic-first; adapter must sit behind policy (AGENTS.md LLM rules) |
| Orchestrator / policy / tool modules | ✅ Phase 2 validated (2026-10-07) | State machine, routing, budgets, evidence review, deterministic policy gate, safe-only ToolBus, audit persistence, and `main.py` monitor-to-ticket orchestration path are tested; specialist implementations remain Phase 3 |
| Git | ✅ synced 2026-10-06 | `origin` → `https://github.com/frogrest/CarlBot.git`, branch `main`, initial push force-approved + run + verified by the owner — see §5 |
| Knowledge docs | thin | `docs/` holds specs, no SOPs yet; retriever scans `docs/**/*.md` recursively (spec docs are currently searchable too — consider scoping later) |

## 3. Known defects & gotchas (fix early)

1. ~~Hard-coded DB path~~ ✅ **FIXED & validated 2026-10-06** — `db_path()` resolves `HELPDESK_DB` per call (Docker default `/app/data/helpdesk.db` unchanged); test fixtures rely on it. (Historical: the module constant broke local non-Docker tests.)
2. **Test coverage** — 29 tests pass. Phase 2 now covers RTSP recovery, PoE technician handoff, auth-failure denial, AI-service recovery, monitor-created ticket processing, helpdesk status/note updates, incident persistence, and audit persistence. Failed-verification escalation and the formal replay/evaluation matrix remain for Phase 7.
3. **No CORS** — backends emit no CORS headers. The frontend must use the dev/nginx proxy (frontend prompt §3.1), or CORS must be added with an `ALLOWED_ORIGINS` env var.
4. **Agent re-run behavior** — the background worker periodically re-processes open/`ready_for_verification` tickets. Monitor creation followed by `process_ticket()` is verified in-process, but the long-running background thread itself has not had a Docker smoke test.
5. **Manifest** — regenerate from `git ls-files --cached --others --exclude-standard` whenever the tracked tree changes.
6. **Version wording** — code is `0.2.0`; README/PROJECT_INDEX now match. `legacy/` holds v0.3-era docs — not current, do not follow them over root docs.
7. **`pytest` was missing from `requirements.txt`** — fixed 2026-10-06 (`pytest>=8,<10`). If bootstrap fails, check `pip install` output first.
8. **Screenshots** — never cite `helpdesk_camera_tree_01.jpg` / `_02.jpg`; they do not exist. Use `reference/screenshots/reference.pdf`.
9. **Host tooling status (verified 2026-10-07)** — **Git: ✅ installed; remote is synced.** **Python: `.venv` runs 3.14.8** (meets the 3.13+ requirement; differs from the previous handoff's reported 3.13). **Node: v24.21.0.** `npm.ps1` is blocked by the current PowerShell execution policy; use `npm.cmd` or adjust policy for the current user when Phase 5 begins. **Docker: NOT installed** — container smoke deferred; install before Phase 5/integration checks (`docker compose up --build -d` remains the container exit criterion).
10. **`data/` state** — the directory exists via `.gitkeep`; runtime `*.db` files are gitignored. To reset the lab: stop the stack first, then delete `data/*.db` (never delete while running, per AGENTS.md debugging playbook).
11. **Deprecation warnings (cosmetic, seen in the 20-passed run)** — FastAPI `@app.on_event('startup'/'shutdown')` in `services/helpdesk/app.py` and `services/agent/main.py` is deprecated (lifespan handlers are the replacement); starlette TestClient warns about `httpx`. Non-blocking; migrate opportunistically during the Phase 2 refactor.

## 4. Build phases (ONE_SHOT order; keep every phase green before starting the next)

| Phase | Work | Exit criteria |
|---|---|---|
| ✅ 0 Pre-flight (pytest part) | DONE 2026-10-06 via `scripts/phase0_bootstrap.ps1` (Python 3.13 + `.venv` + deps) | `pytest -q` → 20 passed ✔ · container smoke ⏳ (Docker not installed) |
| ✅ 1 Stabilize (code+tests) | DONE 2026-10-06: `HELPDESK_DB` fixed, 18 new tests, `data/.gitkeep`, README updated | suite green ✔ · end-to-end `rtsp_down`/`poe_off` Docker smoke ⏳ deferred until Docker install |
| ✅ 2 Orchestrator | validated 2026-10-07: state machine + routing + budgets + duplicate suppression + policy gate + safe ToolBus + audit trail + helpdesk synchronization | compileall green; full suite 29 passed; monitor-to-orchestrator and persistence covered |
| 3 Specialists | implement and wire 8 bounded specialists (from `docs/subagents/` + `prompts/`) behind deterministic routing; retain evidence review, policy, and tool-bus gates | specialist dispatch/output tests; `rtsp_auth_failure` never auto-changes credentials |
| 4 LLM adapter | reasoner interface; deterministic reasoner as default; env-gated LLM adapter with strict schema validation and deterministic fallback | full replay suite passes with LLM off; malformed model output rejected |
| 5 Frontend | follow `frontend/FRONTEND_BUILD_PROMPT.md` F0–F7 (PDF inventory gate first) | `npm run build` green; per-page visual pass; smoke flows in §12 of that file |
| 6 Chat | session store, responder, `/clear`, chat endpoints, ChatPanel | `/clear` test proves ticket/history/audit data untouched |
| 7 Evaluation | 7 required scenarios as declarative tests + metrics runner (diagnosis accuracy, safe-action success, verification success, unnecessary escalation, tool-call count) | all 7 scenarios pass locally and in Docker |

Never weaken a test to make a feature pass; never skip the evidence-review gate; any new autonomous action needs contract + risk class + preconditions/postconditions + verification + retry limit + audit + tests + docs (AGENTS.md).

## 5. GitHub sync — `https://github.com/frogrest/CarlBot.git`

**Status: ✅ DONE (2026-10-06).** The owner installed Git and ran the initial sync manually from their own PowerShell after the executing agent's tool terminal proved wedged (every command, even `Write-Output`, exited 1). The force-approved push to `https://github.com/frogrest/CarlBot.git` (branch `main`) completed and was verified by the owner. **When you arrive: confirm with `git log --oneline -3` and `git remote -v`, and reconcile `FILE_MANIFEST.txt` against `git ls-files` (§3.5 — manifest is currently STALE re Phase 2, see the 2026-10-07 Progress entry for the new files).** Routine flow from there: `git add -A && git commit && git push`. The script below is kept only as a recovery path if the remote ever needs re-initializing.

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
