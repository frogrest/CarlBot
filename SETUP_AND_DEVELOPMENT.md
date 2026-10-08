# AI Ops Assistant Lab — Setup & Development Guide

This document is the practical bootstrap guide for a human developer **or an AI coding agent** working from a clean machine/checkout.

## 1. What this repository is

A local-only emulator consisting of:

- Fake Helpdesk
- Fake Video/AI Portal
- Persistent Agent
- Simulated faults and recovery actions
- Local knowledge documents
- Automated tests

No production system should be required to run the project.

## 2. Prerequisites

### Recommended

- Docker Desktop (Windows/macOS) or Docker Engine + Compose plugin (Linux)
- Git
- Python 3.13+

### Verify

```bash
docker --version
docker compose version
git --version
python --version
```

If Docker is missing, install Docker Desktop/Engine using the official installer for the host OS. Do not substitute a real camera/NVR environment for the emulator.

## 3. First-time bootstrap

Clone/extract the repository, then from the repository root:

```bash
python -m venv .venv
```

Activate it and install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run tests:

```bash
python -m pytest -q
```

Compile-check the source:

```bash
python -m compileall services tests
```

## 4. Start the complete lab

```bash
docker compose up --build -d
```

Confirm:

```bash
docker compose ps
```

Services:

| Service | Address |
|---|---|
| Helpdesk | http://localhost:8000 |
| Portal | http://localhost:8001 |
| Agent | http://localhost:8002 |

Interactive API documentation is available at `/docs` for each service.

## 5. Confirm the agent is alive

```bash
curl http://localhost:8002/api/status
```

The agent should report its monitoring state and recent activity.

## 6. Run an autonomous recovery scenario

Inject a transient RTSP outage:

```bash
curl -X POST http://localhost:8001/api/simulate/fault \
  -H 'Content-Type: application/json' \
  -d '{"asset_id":"CAM-027","fault":"rtsp_down"}'
```

The agent should autonomously:

1. Detect the event.
2. Create/find the corresponding ticket.
3. Diagnose the condition.
4. Use historical/document evidence.
5. Execute the simulated `reconnect-rtsp` action.
6. Verify RTSP recovery.
7. Update/resolve the ticket.

## 7. Run a technician-handoff scenario

```bash
curl -X POST http://localhost:8001/api/simulate/fault \
  -H 'Content-Type: application/json' \
  -d '{"asset_id":"CAM-027","fault":"poe_off"}'
```

Expected result: the agent stops at `pending_technician` and records the suggested physical checks.

After simulated worker intervention, reset the fake state:

```bash
curl -X POST http://localhost:8001/api/assets/CAM-027/actions/reset-simulation
```

Then request verification for the ticket through the helpdesk API.

## 8. Inspect logs

```bash
docker compose logs --tail=200 agent
docker compose logs --tail=200 helpdesk
docker compose logs --tail=200 portal
```

Follow the agent continuously:

```bash
docker compose logs -f agent
```

## 9. Stop/reset

Stop services:

```bash
docker compose down
```

For a fresh state, remove the local runtime database files under `data/` after stopping the stack. Keep source documents under `docs/`.

## 10. Development loop

Use this sequence for changes:

```text
Read → reproduce → test → edit → test → run stack → inject fault → inspect logs → document
```

Every new fault or autonomous action should have a deterministic test.

## 11. Adding project documentation

Put user-provided documents under `docs/`.

Recommended categories:

```text
docs/
  RTSP/
  Networking/
  Cameras/
  NVR/
  AI-Box/
  Alarm-EG/
  AI-Cloud/
  Vendor/
  SOP/
  Troubleshooting/
```

Do not rewrite source documents without preserving their meaning and origin.

## 12. Optional Phase 4 AI model configuration

The Phase 4 adapter is already available behind the existing tool/policy boundary.
It is disabled unless both `LLM_BASE_URL` and `LLM_MODEL` are configured. Set
`LLM_API_KEY` in the agent process environment only when the endpoint requires it;
never commit API keys. Docker Compose passes these variables through to the agent.
Malformed plans and request failures fall back to the deterministic reasoner.

The model produces a structured plan rather than executing arbitrary commands.

The safe path is:

```text
model reasoning
→ structured action proposal
→ schema validation
→ policy engine
→ tool execution
→ verification
→ ticket update
```

Do not replace the simulator with production systems while testing the model.
