# Autonomous AI Ops Assistant Lab — Build Specification

## Purpose

This project is a safe emulator for developing an autonomous technical-operations assistant. It models the workflow of a helpdesk, a video/AI platform, and a technician while keeping all actions inside a local sandbox.

The design goal is:

> **Automate repetitive investigation, evidence gathering, documentation and safe recovery; keep physical work, consequential changes and operational judgment with the worker.**

## Current build: v0.2

The system is now a persistent service instead of a one-shot script.

```text
Fake Portal
    |
    | telemetry / simulated faults
    v
Agent Monitor -----> Fake Helpdesk
    |                     |
    | diagnostics         | tickets + history
    v                     v
Agent Orchestrator ---> Knowledge Retrieval
    |
    +--> safe autonomous action ----> verify ----> resolve
    |
    +--> technician action ----------> pending_technician
                                            |
                                            v
                                    worker repairs system
                                            |
                                            v
                                    ready_for_verification
                                            |
                                            v
                                         verify
```

## Components

### Fake Helpdesk

Provides:

- ticket creation
- ticket listing/filtering
- ticket retrieval
- historical search
- technician notes
- AI state and summary fields
- verification requests

Persistent data is stored in `data/helpdesk.db`.

### Fake Video/AI Portal

Simulates:

- cameras
- NVRs
- AI Boxes
- reachability
- TCP/554
- RTSP state
- authentication
- PoE state
- CPU/storage
- AI service state
- cloud state

Faults can be injected through an API. All actions are simulated and affect only in-memory fake devices.

### Autonomous Agent

The agent is an HTTP service with a background worker. It:

1. polls portal events
2. creates one ticket per active fault episode
3. detects actionable helpdesk tickets
4. runs diagnostics
5. searches historical tickets
6. searches Markdown documentation
7. forms a diagnosis
8. chooses an action based on the policy layer
9. executes only allow-listed safe actions
10. verifies an automatic repair
11. updates the ticket
12. stops for technician work when appropriate

Persistent agent run history is stored in `data/agent.db`.

## State model

### Ticket lifecycle

```text
open
  |
  v
in_progress
  |
  +----> resolved
  |
  v
pending_technician
  |
  | worker performs action
  v
ready_for_verification
  |
  v
in_progress
  |
  v
resolved
```

The agent does not repeatedly re-investigate tickets marked `pending_technician`. A technician explicitly requests verification after doing the suggested work.

### Fault episode lifecycle

The portal exposes active events. The monitor remembers whether an event is active. When a fault disappears, the event is re-armed so the same type of fault can create a new ticket the next time it happens.

This is important for testing repeated incidents.

## Action policy

The current allow-list is:

```text
reconnect-rtsp
restart-ai-service
```

These are safe only because they are **simulated actions** in this lab.

The agent will not autonomously perform:

```text
change credentials
change IP/subnet/gateway
change firewall rules
firmware update
factory reset
physical repair
storage deletion
production network changes
```

The policy layer is independent from the diagnosis layer. A future LLM can recommend something without automatically gaining permission to perform it.

## Knowledge model

The agent currently combines:

### Live evidence

From portal APIs:

- health
- ping
- TCP/554
- RTSP
- site context
- active faults

### Organizational memory

From helpdesk:

- previous ticket titles
- descriptions
- resolutions
- root causes
- technician notes

### Internal knowledge

From Markdown under `docs/`.

The current retrieval implementation is intentionally lightweight token matching. This is a placeholder for a future embedding/vector retrieval layer.

## Why this is not an LLM-first system

The first objective is to make the **environment and control plane correct** before model quality is introduced.

We need deterministic answers to:

- what a tool can do
- what its output means
- what the agent is allowed to change
- what evidence is required before a diagnosis
- what counts as verification
- how to prevent loops
- how a technician takes over
- how actual outcomes become training/evaluation data

Once those are stable, an LLM can replace the deterministic diagnosis/planning logic while continuing to call the same tools and policy layer.

## LLM integration target

The eventual architecture should look like:

```text
                    +-------------------+
                    |      LLM          |
                    | reasoning/planner |
                    +---------+---------+
                              |
                         structured plan
                              |
                    +---------v---------+
                    |  POLICY ENGINE    |
                    | permissions/risk  |
                    +---------+---------+
                              |
                    +---------v---------+
                    |     TOOL BUS      |
                    +---------+---------+
                              |
        +---------------------+---------------------+
        |           |             |                 |
      Helpdesk   Portal       Knowledge          Memory
```

The model should never directly receive raw credentials or an unrestricted shell. Tool execution should remain mediated by explicit contracts.

## Tool contract target

Future tools should define:

```yaml
name: restart_ai_service
risk: medium
reversible: true
requires_approval: false
preconditions:
  - asset_type == ai_box
  - incident_is_active == true
postconditions:
  - service == healthy
verification: health_check
max_attempts: 1
audit_required: true
```

This provides a stable interface between the model and the environment.

## Scenario examples

### RTSP transient failure

Expected behavior:

```text
fault injected
 -> monitor creates ticket
 -> agent diagnoses RTSP unavailable
 -> reconnect-rtsp
 -> RTSP becomes healthy
 -> ticket resolved
```

### PoE failure

Expected behavior:

```text
fault injected
 -> monitor creates ticket
 -> ping fails
 -> PoE reported false
 -> diagnosis: likely power/physical connectivity
 -> ticket pending_technician
 -> worker inspects physical system
 -> worker requests verification
 -> agent verifies
```

### RTSP authentication failure

Expected behavior:

```text
TCP/554 reachable
RTSP authentication fails
historical tickets mention credential mismatch
 -> agent recommends credential/path verification
 -> no autonomous credential change
```

## Evaluation strategy

Every simulated incident should eventually have an expected result:

```text
scenario
expected evidence
expected diagnosis
expected technician action
allowed automatic action
expected postcondition
```

Then the same scenarios can be replayed against different agent versions.

Useful metrics:

- diagnosis accuracy
- high-confidence false diagnosis rate
- unnecessary escalations
- successful safe-action rate
- verification success rate
- average number of diagnostic steps
- time to first useful technician action
- tickets closed without worker intervention
- tickets correctly handed to workers
- repeated-failure rate

## Development order

### Phase 1 — Environment

- finish fake portal topology
- add more vendor/device behaviors
- add network, NVR, RTSP and cloud failure modes

### Phase 2 — Agent control plane

- stronger state machine
- action contracts
- retries/timeouts
- event correlation
- audit trail

### Phase 3 — Knowledge

- richer ticket extraction
- document metadata
- citations to retrieved knowledge
- embedding/vector search

### Phase 4 — LLM

- model adapter
- tool calling
- structured plans
- evidence requirements
- confidence calibration

### Phase 5 — Technician copilot

- ticket-side AI panel
- guided steps
- approve/reject controls
- technician feedback capture

### Phase 6 — Evaluation

- scenario replay
- regression tests
- agent traces
- failure analysis

## Runbook

Start:

```bash
docker compose up --build
```

Services:

```text
Helpdesk  http://localhost:8000
Portal    http://localhost:8001
Agent     http://localhost:8002
```

Inject a fault:

```bash
curl -X POST http://localhost:8001/api/simulate/fault \
  -H 'Content-Type: application/json' \
  -d '{"asset_id":"CAM-027","fault":"rtsp_down"}'
```

Inspect the agent:

```bash
curl http://localhost:8002/api/status
```

Inspect tickets:

```bash
curl http://localhost:8000/api/tickets
```

Reset the simulated device:

```bash
curl -X POST http://localhost:8001/api/assets/CAM-027/actions/reset-simulation
```

Request worker-completed verification:

```bash
curl -X POST http://localhost:8000/api/tickets/<TICKET_ID>/request-verification
```

## Safety boundary

This environment is not connected to production. Keep it that way while developing the agent. When moving toward a real deployment, add authentication, network isolation, secrets management, approval workflows, signed/audited actions, rate limits, per-site permissions, and explicit change-control procedures before connecting any tool to real infrastructure.
