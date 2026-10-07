# AI Ops Assistant Lab v0.2

> **AI development instructions:** See `AGENTS.md` before asking an AI coding agent to modify this repository. For clean-machine setup, see `SETUP_AND_DEVELOPMENT.md`.
> **Current status & next steps:** See `NEXT_AGENT_BRIEF.md`. Frontend work follows `frontend/FRONTEND_BUILD_PROMPT.md`; the visual reference is `reference/screenshots/reference.pdf`.

A safe, fully emulated environment for developing an autonomous technical-operations assistant without touching production cameras, NVRs, AI Boxes, customer networks, or live helpdesk data.

## What changed from v0.1

The original prototype ran one diagnosis and exited. v0.2 turns it into a **persistent local agent service**:

- Continuously polls the fake portal for unhealthy assets.
- Automatically creates helpdesk tickets for new simulated faults.
- Watches the helpdesk for actionable tickets.
- Runs a multi-step diagnostic workflow.
- Searches historical helpdesk incidents.
- Searches Markdown knowledge documents.
- Performs only explicitly allow-listed safe recovery actions.
- Verifies an automatic recovery before resolving the ticket.
- Stops at `pending_technician` when physical/configuration work needs a worker.
- Exposes agent status and manual-run APIs.
- Persists run history in `data/agent.db`.

## Services

| Service | URL | Purpose |
|---|---|---|
| Helpdesk | http://localhost:8000 | Tickets, notes, history, technician workflow |
| Portal | http://localhost:8001 | Fake cameras, NVR, AI Box, telemetry, fault injection |
| Agent | http://localhost:8002 | Continuous autonomous monitor + diagnostic worker |
| Frontend | http://localhost:8003 | Synthetic ticket queue, ticket detail, copilot and lab inventory |

FastAPI interactive docs are available at `/docs` on all three services.

## Prerequisites

Recommended: Docker Desktop with Docker Compose.

The repository does not require an LLM API key for v0.2. The deterministic control loop comes first so that the tool, policy, and verification layers can be tested independently from model quality.

## Start the full lab

From the project directory:

```bash
docker compose up --build
```

The three services run continuously. The agent checks the portal/helpdesk roughly every 5 seconds.

To stop:

```bash
docker compose down
```

To reset persisted helpdesk/agent state for a fresh lab, stop the stack and remove the contents of `./data/` (leave the directory itself in place).

## Observe the system

Open:

- Helpdesk workspace: http://localhost:8003
- Helpdesk: http://localhost:8000
- Portal: http://localhost:8001
- Agent: http://localhost:8002

Useful APIs:

```text
GET  /api/status                    (agent)
POST /api/monitor/run               (agent)
POST /api/tickets/{id}/run          (agent)
GET  /api/tickets                   (helpdesk)
GET  /api/tickets/{id}              (helpdesk)
POST /api/chat/query                (read-only ticket lookup)
POST /api/tickets/{id}/notes        (helpdesk)
POST /api/tickets/{id}/request-verification (helpdesk)
GET  /api/assets                    (portal)
GET  /api/events                    (portal)
POST /api/simulate/fault            (portal)
POST /api/assets/{id}/actions/reset-simulation (portal)
```

The ticket lookup chat searches live Helpdesk records and, when present, the
local `reference/ticketreference examples.csv` export. That export is
git-ignored, mounted read-only, and is not required to run the lab. It contains
metadata only; lookup replies do not expose sender email addresses. The chat
does not use an LLM API key and cannot change tickets or run investigations.

## End-to-end autonomous test

### 1. Inject a recoverable RTSP fault

```bash
curl -X POST http://localhost:8001/api/simulate/fault \
  -H 'Content-Type: application/json' \
  -d '{"asset_id":"CAM-027","fault":"rtsp_down"}'
```

Within the polling interval, the agent should:

1. Detect the fault.
2. Create a helpdesk ticket.
3. Read the ticket.
4. Run health, ping, TCP/554 and RTSP checks.
5. Search history and knowledge docs.
6. Execute `reconnect-rtsp` because it is allow-listed as safe.
7. Re-check RTSP.
8. Resolve the ticket and record the automatic action.

### 2. Inject a technician-required fault

```bash
curl -X POST http://localhost:8001/api/simulate/fault \
  -H 'Content-Type: application/json' \
  -d '{"asset_id":"CAM-027","fault":"poe_off"}'
```

The agent should create an incident and stop at `pending_technician`, with a note similar to:

> Inspect PoE port, Ethernet cable, and camera power.

No automatic physical action is attempted.

After the simulated technician work, reset the fault:

```bash
curl -X POST http://localhost:8001/api/assets/CAM-027/actions/reset-simulation
```

Then request verification on the ticket:

```bash
curl -X POST http://localhost:8000/api/tickets/<TICKET_ID>/request-verification
```

The agent will pick it up again and verify the live state.

## Fault library

The portal currently supports:

- `network_down`
- `rtsp_auth_failure`
- `rtsp_down`
- `high_cpu`
- `storage_full`
- `poe_off`
- `ai_service_down`
- `cloud_down`

The goal is not to make every fault automatically recoverable. Some failures intentionally stop at a worker action so the human remains part of the operational loop.

## Autonomous-action policy

The current agent can automatically perform only:

- `reconnect-rtsp`
- `restart-ai-service`

These actions are simulated. They do not contact real devices.

Examples that are **not** automatically allowed:

- changing IP addresses
- changing subnet/gateway
- changing credentials
- changing firewall rules
- firmware upgrades
- factory resets
- physical troubleshooting
- destructive storage operations

The policy layer is deliberately separated from the reasoning layer. Documentation or future LLM output does not grant permission to perform an action.

## Agent lifecycle

```text
Portal telemetry
      |
      v
Detect anomaly
      |
      v
Create / locate helpdesk ticket
      |
      v
Understand incident
      |
      v
Run diagnostics
      |
      +----> historical helpdesk search
      |
      +----> Markdown knowledge search
      |
      v
Form diagnosis
      |
      +----> safe action allowed? ---- yes ---> execute ---> verify
      |                                           |
      |                                           v
      |                                        resolve
      |
      no
      |
      v
pending_technician
      |
      v
worker performs suggested action
      |
      v
ready_for_verification
      |
      v
agent verifies
```

## Why the first agent is deterministic

The LLM is intentionally not the control system yet. Before adding an LLM, we want reliable answers to:

- What tools exist?
- What does each tool return?
- What state does the agent maintain?
- What actions are permitted?
- What must always require a worker?
- How is an automatic recovery verified?
- How do we prevent loops and repeated work?
- How do we evaluate a diagnosis against the actual simulated root cause?

Once these are stable, an LLM can be inserted as a reasoning/planning component behind the same tools and safety policy.

## Adding your documents

Place Markdown files below `docs/`. The agent will search them automatically during investigations. Start with SOPs, RTSP/networking references, camera/NVR procedures, AI Box procedures, escalation rules, and known issues.

See `docs/README.md` for a recommended structure and document format.

## Development workflow

1. Add or modify a simulated fault.
2. Define the expected evidence.
3. Define the expected diagnosis.
4. Define the expected technician action.
5. Define which recovery actions are safe.
6. Add a test.
7. Run the lab and inject the fault.
8. Inspect helpdesk and agent run history.
9. Only then add an LLM or make a new action autonomous.

## Local non-Docker development

The project can also be run with Python 3.13+:

```bash
python -m venv .venv
# activate the environment using your OS-specific command
pip install -r requirements.txt
uvicorn services.helpdesk.app:app --port 8000
uvicorn services.portal.app:app --port 8001
python -m services.agent.main
```

For local non-Docker execution, the agent uses the defaults `http://localhost:8000`, `http://localhost:8001` and stores its state under `./data` when `AGENT_DB` is set accordingly. The helpdesk resolves its database path from `HELPDESK_DB` (default `/app/data/helpdesk.db`) — set it to `./data/helpdesk.db` when running outside Docker.

## Roadmap

### v0.3 — Knowledge and state

- Better structured ticket history
- richer site/device topology
- document metadata and citations
- explicit incident state machine
- idempotent event handling

### v0.4 — LLM reasoning

- model adapter
- tool calling
- structured plans
- confidence/evidence requirements
- hallucination-resistant action selection

### v0.5 — Technician copilot

- ticket-side diagnostic panel
- guided troubleshooting
- approve/reject actions
- technician feedback capture

### v0.6 — Evaluation

- historical replay
- injected-fault benchmark
- diagnosis accuracy
- tool efficiency
- unnecessary escalation
- safe-action success rate

### v0.7 — Advanced emulation

- network topology
- VLAN/subnet scenarios
- realistic RTSP states
- NVR limits
- AI Box CPU/memory pressure
- intermittent packet loss and latency

## Safety boundary

This lab is intentionally fake. Keep it isolated from production credentials and production network access. Do not point the simulated tool endpoints at real systems until the action policy, approvals, audit logs, testing, and security architecture have been reviewed.
