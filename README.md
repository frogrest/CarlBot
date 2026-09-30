# Autonomous CCTV Technical-Support AI Lab

> **Automate the repetitive technical work around the technician, not the technician out of the work.**

This repository is a **safe, fully simulated** environment for developing an autonomous technical-support assistant for CCTV, IP cameras, NVRs, AI Boxes, and helpdesk operations. It never connects to real customer systems, real cameras, or production infrastructure.

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

This launches all four services:
This launches all five components:
- **Operations Web UI** → http://localhost:5173
- **Helpdesk API** → http://127.0.0.1:8001/docs
- **Portal API** → http://127.0.0.1:8002/docs
- **Agent API** → http://127.0.0.1:8003/docs
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

## Quick Start (Docker)

```bash
docker compose up --build
```

## Run Tests

```bash
# Backend pytest suite (60 tests) + linter
python -m pytest -q
python -m ruff check .

# Frontend Vitest suite (19 tests)
cd frontend
npm test
npm run build
```

## Operations UI Features

The Operations Web UI provides 10 purpose-built NOC views and real-time monitoring:
- **NOC Operations Dashboard** (`/`): Real-time KPI metric cards, site health breakdown, recent incident queue, active fault indicators, and a one-click Quick Fault Simulator modal.
- **Incident Queue & Detail** (`/incidents`, `/incidents/:id`): Filterable tickets with status tabs, severity indicators, expandable diagnostic timelines, historical matches, and technician note-taking.
- **Device Inventory & Detail** (`/devices`, `/devices/:id`): Camera/NVR/AI Box cards with RTSP ping/latency indicators, telemetry gauges (CPU, memory, storage, temp), and live fault injection shortcuts.
- **Site Overview & Detail** (`/sites`, `/sites/:id`): Multi-site health rollups with visual **Topology Graphs** visualizing network dependencies (Gateway → NVR → Cameras/AI Box → Cloud Sync) and identifying correlated outages.
- **AI Assistant** (`/assistant`): Interactive conversational console with rich markdown, tool execution step pills (`running`, `success`, `failure`, `blocked`), and command auto-completion.
- **Authoritative Knowledge Base** (`/knowledge`): Full-text searchable Markdown SOP and runbook browser rendered dynamically from `data/knowledge/`.
- **System Audit Log** (`/audit`): Filterable chronological log of all autonomous and human actions.

### AI Assistant Slash Commands

| Command | Usage | Description |
|---|---|---|
| `/investigate <ASSET_ID>` | `/investigate CAM-001` | Runs autonomous diagnostics, checks policy, retrieves SOPs, and reports evidence |
| `/status <ASSET_ID>` | `/status AI-BOX-001` | Instant telemetry snapshot (health, ping, RTSP, CPU, storage, memory) |
| `/site <SITE_ID>` | `/site SITE-001` | Full site diagnostics, device statuses, and multi-camera correlated outage analysis |
| `/history <QUERY>` | `/history rtsp error` | Searches historical tickets and past resolution notes |
| `/help` | `/help` | Displays available slash commands, usage examples, and safety constraints |
| `/clear` | `/clear` | Clears conversation state while safely preserving tickets, devices, and audit logs |

### Safety Policy Enforcement & Visualization

Every action displays its strict safety tier:
- 🟢 **SAFE_REVERSIBLE** (e.g. `reconnect_stream`, `restart_service`): Safe to automate autonomously.
- 🟡 **APPROVAL_REQUIRED** (e.g. `reboot_host`, `update_config`): Requires human confirmation.
- 🔴 **HUMAN_ONLY** (e.g. `hardware_repair`, `credential_rotation`): Blocked from autonomous execution; creates technician alert.
- 🔵 **READ** (e.g. `ping_check`, `rtsp_check`): Read-only diagnostic checks, always safe.

*The policy engine (`services/agent/policy.py`) is authoritative and runs strictly on the backend. Frontend controls reflect policy but can never bypass it.*

## Inject a Fault

```bash
# Via Web UI:
Click the "Lab Controls" / "Inject Fault" button in the top navigation bar.

# Via API (with services running)
curl -X POST http://localhost:8002/faults/CAM-001 -H "Content-Type: application/json" -d '{"fault":"rtsp_down"}'

# Via CLI helper (works offline against state file)
python scripts/inject_fault.py CAM-001 rtsp_down

# Clear a fault
python scripts/inject_fault.py --clear CAM-001

# List active faults
python scripts/inject_fault.py --list
```

## Read Tickets

```bash
curl http://localhost:8001/tickets
curl http://localhost:8001/search?q=rtsp
```

## Trigger One Agent Cycle

```bash
curl -X POST http://localhost:8003/run-once
curl -X POST http://localhost:8003/investigate/CAM-001
```

## View Agent Policy

```bash
curl http://localhost:8003/policy
```

## Reset All State

```bash
python scripts/reset_lab.py
```

## Supported Faults

| Fault | Auto-recoverable? | Agent action |
|---|---|---|
| `network_down` | No | Escalate to technician |
| `rtsp_down` | ✅ Yes | `reconnect_stream` |
| `rtsp_auth_failure` | No | Escalate to technician |
| `wrong_rtsp_path` | No | Escalate to technician |
| `poe_power_off` | No | Escalate (physical repair) |
| `high_cpu` | No | Escalate to technician |
| `storage_full` | No | Escalate to technician |
| `intermittent_connectivity` | ✅ Yes | `clear_transient` |
| `nvr_unavailable` | No | Escalate to technician |
| `ai_box_service_failure` | ✅ Yes | `restart_service` |
| `cloud_sync_failure` | ✅ Yes | `retry_upload` |
| `multi_camera_site_outage` | No | Escalate (site-level) |

## Documentation

- [SETUP_AND_DEVELOPMENT.md](SETUP_AND_DEVELOPMENT.md) — complete setup, development workflow, frontend architecture, and debugging
- [AUTONOMOUS_AGENT_LAB.md](AUTONOMOUS_AGENT_LAB.md) — architecture, evidence model, and specification
- [AGENTS.md](AGENTS.md) — instructions for AI coding agents and developer guidelines
- [docs/LLM_INTERFACE.md](docs/LLM_INTERFACE.md) — future LLM integration contract
