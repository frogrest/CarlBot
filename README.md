# CarlBot — Autonomous CCTV Technical-Support AI Lab

> **Automate the repetitive technical work around the technician, not the technician out of the work.**

[![GitHub Repo](https://img.shields.io/badge/GitHub-frogrest%2FCarlBot-blue?logo=github)](https://github.com/frogrest/CarlBot)
[![Tests](https://img.shields.io/badge/Tests-86%20Passed-brightgreen)](#run-tests-86-automated-tests)
[![Python](https://img.shields.io/badge/Python-3.11+-informational?logo=python)](https://python.org)
[![React](https://img.shields.io/badge/Frontend-React%2019%20%7C%20Vite%206-61dafb?logo=react)](https://vitejs.dev)

This repository is a **safe, fully simulated** environment for developing an autonomous technical-support assistant for CCTV, IP cameras, NVRs, AI Boxes, and helpdesk operations. It never connects to real customer systems, real cameras, or production infrastructure.

- **GitHub Repository:** [https://github.com/frogrest/CarlBot](https://github.com/frogrest/CarlBot)

---

## Quick Start (Local)

```powershell
# Windows PowerShell (Python 3.11 recommended)
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Start everything with one command:
python scripts/run_local.py
```

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/run_local.py
```

This launches all five components concurrently:
- **Operations Web UI** → [http://localhost:5173](http://localhost:5173)
- **Helpdesk API** → [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)
- **Operations Portal API** → [http://127.0.0.1:8002/docs](http://127.0.0.1:8002/docs)
- **Agent API** → [http://127.0.0.1:8003/docs](http://127.0.0.1:8003/docs)
- **Agent loop** → runs in background, polling every 5 seconds

Press `Ctrl+C` to cleanly stop all services.

### Frontend Development

The frontend is a modern NOC/Operations console built with React 19, TypeScript, Tailwind CSS, Lucide icons, and Vite.

```powershell
cd frontend
npm install
npm run dev      # Start dev server on http://localhost:5173
npm test         # Run frontend test suite (Vitest + React Testing Library)
npm run build    # Build production bundle with strict TypeScript validation
```

---

## Quick Start (Docker)

```bash
docker compose up --build
```

---

## Run Tests (86 Automated Tests)

```bash
# Backend pytest suite (60 tests) + linter
python -m pytest -q
python -m ruff check .

# Frontend Vitest suite (26 tests across 7 suites)
cd frontend
npm test
npm run build
```

---

## Operations UI & AI Assistant Features

The Operations Web UI provides 10 purpose-built NOC views and real-time monitoring:
- **NOC Operations Dashboard** (`/`): Real-time KPI metric cards, site health breakdown, recent incident queue, active fault indicators, and a one-click Quick Fault Simulator modal.
- **Incident Queue & Detail** (`/incidents`, `/incidents/:id`): Filterable tickets with status tabs, severity indicators, expandable diagnostic timelines, historical matches, and technician note-taking.
- **Device Inventory & Detail** (`/devices`, `/devices/:id`): Camera/NVR/AI Box cards with RTSP ping/latency indicators, telemetry gauges (CPU, memory, storage, temp), and live fault injection shortcuts.
- **Site Overview & Detail** (`/sites`, `/sites/:id`): Multi-site health rollups with visual **Topology Graphs** visualizing network dependencies (`Gateway` → `NVR` → `Cameras/AI Box` → `Cloud Sync`) and identifying correlated multi-camera outages.
- **AI Assistant** (`/assistant`): Interactive conversational console supporting both slash commands and full natural language questions.
- **Authoritative Knowledge Base** (`/knowledge`): Full-text searchable Markdown SOP and runbook browser rendered dynamically from `data/knowledge/`.
- **System Audit Log** (`/audit`): Filterable chronological log of all autonomous and human actions.

### AI Assistant: Natural Language & Slash Commands

You can converse with CarlBot **naturally** without knowing specific command syntax:

| Interaction Style | Example Input | Behavior |
|---|---|---|
| **Natural Device Inquiry** | *"Check the lobby camera"* / *"What's wrong with cam 2?"* | Automatically resolves aliases (`lobby camera` → `CAM-001`), executes checks, retrieves SOPs, and reports status. |
| **Healthy Device Verification** | *"Is CAM-001 ok?"* | Accurately verifies operational health (`Asset verified healthy`) without false technician escalations. |
| **Fleet Health & Outages** | *"What faults are active?"* / *"System health"* | Summarizes all active faults, offline devices, and current open tickets. |
| **Safety Policy Inquiries** | *"Explain safety policy"* / *"Why can't you fix PoE?"* | Outlines policy tiers and explains why physical hardware & credentials require human technician dispatch. |
| **Direct Slash Command** | `/investigate CAM-002` | Structured on-demand investigation with live diagnostic tool transparency pills. |
| **Status Snapshot** | `/status AIBOX-001` | Instant telemetry snapshot (health, ping, RTSP, CPU, storage, memory). |
| **Multi-Camera Site Outage** | `/site SITE-001` | Analyzes site gateway dependencies and detects correlated switch outages. |
| **Knowledge Retrieval** | `/history rtsp error` | Searches past tickets and technician resolution notes. |
| **UI Reset** | `/clear` | Clears conversational message history while safely preserving all backend tickets and device telemetry. |

---

## Safety Policy Enforcement

Every action displays its strict safety tier:
- 🟢 **SAFE_REVERSIBLE** (e.g. `reconnect_stream`, `restart_service`, `retry_upload`, `clear_transient`): Automated autonomously with immediate post-action verification.
- 🟡 **APPROVAL_REQUIRED** (e.g. `reboot_host`, `update_config`): Requires human confirmation.
- 🔴 **HUMAN_ONLY** (e.g. `hardware_repair`, `credential_rotation`, `poe_power_off`): Blocked from autonomous execution; creates technician alert.
- 🔵 **READ** (e.g. `ping_check`, `rtsp_check`): Read-only diagnostic checks, always safe.

*The policy engine (`services/agent/policy.py`) is authoritative and runs strictly on the backend. Frontend controls reflect policy but can never bypass it.*

---

## Fault Simulator & Presets

```bash
# Via Web UI:
Click the "Lab Controls" button in the top navigation bar to inject or clear faults with one click.

# Via API (with services running)
curl -X POST http://localhost:8002/faults/CAM-001 -H "Content-Type: application/json" -d '{"fault":"rtsp_down"}'

# Via CLI helper (works offline against state file)
python scripts/inject_fault.py CAM-001 rtsp_down

# Clear a fault
python scripts/inject_fault.py --clear CAM-001

# List active faults
python scripts/inject_fault.py --list
```

### Supported Faults

| Fault | Target | Auto-recoverable? | Agent action |
|---|---|---|---|
| `network_down` | Camera | No | Escalate to technician (`HUMAN_ONLY`) |
| `rtsp_down` | Camera | ✅ Yes | `reconnect_stream` (`SAFE_REVERSIBLE`) |
| `rtsp_auth_failure` | Camera | No | Escalate to technician (`HUMAN_ONLY`) |
| `wrong_rtsp_path` | Camera | No | Escalate to technician (`HUMAN_ONLY`) |
| `poe_power_off` | Camera | No | Escalate (physical repair) (`HUMAN_ONLY`) |
| `high_cpu` | AI Box | No | Escalate to technician (`HUMAN_ONLY`) |
| `storage_full` | NVR | No | Escalate to technician (`HUMAN_ONLY`) |
| `intermittent_connectivity` | Camera | ✅ Yes | `clear_transient` (`SAFE_REVERSIBLE`) |
| `nvr_unavailable` | NVR | No | Escalate to technician (`HUMAN_ONLY`) |
| `ai_box_service_failure` | AI Box | ✅ Yes | `restart_service` (`SAFE_REVERSIBLE`) |
| `cloud_sync_failure` | AI Box | ✅ Yes | `retry_upload` (`SAFE_REVERSIBLE`) |
| `multi_camera_site_outage` | Site | No | Escalate (site-level correlated failure) |

---

## Deployment & Hosting Roadmap

CarlBot is engineered for dual deployment:
1. **Local Mode:** Python 3.11 microservices (`run_local.py`) + Vite dev server.
2. **Cloud Mode:**
   - **Frontend:** Static React bundle hosted on **GitHub Pages** ([https://frogrest.github.io/CarlBot](https://frogrest.github.io/CarlBot)).
   - **Backend:** Unified FastAPI gateway hosted on **Render** (free web service) running all 3 services + 24/7 background agent loop on a single port.
   - **Offline / Cold-Start Resilience:** Client-side in-memory mock fallback ensures the simulator works instantly on the web even while cloud instances wake up.

---

## Documentation Directory

- [SETUP_AND_DEVELOPMENT.md](SETUP_AND_DEVELOPMENT.md) — complete setup, development workflow, frontend architecture, and debugging
- [AUTONOMOUS_AGENT_LAB.md](AUTONOMOUS_AGENT_LAB.md) — architecture, evidence model, and specification
- [AGENTS.md](AGENTS.md) — instructions for AI coding agents and developer guidelines
- [docs/LLM_INTERFACE.md](docs/LLM_INTERFACE.md) — future LLM integration contract
