# AI Coding Agent Instructions — AI Ops Assistant Lab

## Mission

You are the coding/development agent responsible for building, testing, debugging, and extending this repository.

Current build status, known defects, the phase-by-phase work plan, and the GitHub sync procedure are in `NEXT_AGENT_BRIEF.md` — read it first. Frontend work follows `frontend/FRONTEND_BUILD_PROMPT.md`.

The repository is a **safe, fully emulated technical-operations lab**. It must remain isolated from production cameras, NVRs, AI Boxes, customer networks, customer credentials, and live helpdesk systems.

Your objective is to build an autonomous technical-support assistant that removes repetitive investigation and documentation work while keeping technicians responsible for physical work, consequential configuration changes, approvals, and operational judgment.

## Non-negotiable boundaries

1. Never connect this project to a real customer system unless the human explicitly requests a separate integration project and supplies the required credentials/endpoint details.
2. Never put production credentials, API tokens, private keys, or customer data in the repository.
3. Never make a fake tool silently call a real device, cloud service, camera, NVR, AI Box, or external helpdesk.
4. Do not bypass the policy/action layer just because an LLM recommends an action.
5. Destructive, privileged, physical, or irreversible actions stay human-controlled unless a later design explicitly adds an approval gate and test coverage.
6. Prefer deterministic tests and simulated faults over real-world experiments.

## Source-of-truth order

When deciding how the project should behave, use this order:

1. Current source code and tests.
2. `AGENTS.md` (these development instructions).
3. `AUTONOMOUS_AGENT_LAB.md` (architecture/specification).
4. `README.md` and `docs/`.
5. User-provided project documents added under `docs/`.

When a user-provided document conflicts with the code, do not silently invent a resolution. Explain the conflict and preserve the safe emulator boundary.

## Environment bootstrap

### Step 1 — Inspect the host

Before changing code, determine the OS, shell, architecture, and installed tooling.

Required primary runtime:

- Docker Desktop (Windows/macOS) or Docker Engine + Compose plugin (Linux).
- Git.
- Python 3.13+ for local development/testing outside containers.

Useful checks:

```bash
uname -a
python --version
python3 --version
git --version
docker --version
docker compose version
```

On Windows PowerShell, use:

```powershell
$PSVersionTable
python --version
git --version
docker --version
docker compose version
```

### Step 2 — Install missing dependencies when permitted

Use the platform's normal package manager when the environment allows unattended installation.

- Windows: Docker Desktop + Git + Python. Docker Desktop may require interactive installation, administrator approval, WSL2, or a reboot; do not fake success. If automatic installation is not possible, report exactly what the human must install and continue with whatever parts can be tested locally.
- macOS: Docker Desktop, Git, Python via Homebrew or the team's approved package manager.
- Debian/Ubuntu Linux: Docker Engine/Compose plugin, Git, Python/venv using the system package manager.

Never overwrite an existing working installation without explicit permission.

### Step 3 — Prepare the project

From the repository root:

```bash
python -m venv .venv
```

Activate the environment using the current shell, then:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Docker is the primary supported runtime, so local Python dependencies are mainly for tests, debugging, linting, and utility scripts.

### Step 4 — Validate the repository

Run:

```bash
python -m compileall services tests
python -m pytest -q
```

Then build/start the complete lab:

```bash
docker compose up --build -d
```

Check:

```bash
docker compose ps
```

Open/inspect:

- Helpdesk: `http://localhost:8000/docs`
- Portal: `http://localhost:8001/docs`
- Agent: `http://localhost:8002/docs`

The agent is designed to keep running continuously.

### Step 5 — Smoke test

Inject a simulated RTSP outage and verify the complete loop:

```bash
curl -X POST http://localhost:8001/api/simulate/fault \
  -H 'Content-Type: application/json' \
  -d '{"asset_id":"CAM-027","fault":"rtsp_down"}'
```

Expected sequence:

```text
fault
→ monitor detects fault
→ helpdesk ticket created
→ agent investigates
→ history/docs retrieved
→ safe recovery selected
→ recovery executed in emulator
→ recovery verified
→ ticket resolved
```

Also test a worker-required fault such as `poe_off` and confirm the agent stops at `pending_technician` rather than pretending it can repair physical equipment.

## Development workflow

For every feature or bug:

1. Read the relevant code and tests before editing.
2. State the desired behavior in concrete terms.
3. Reproduce the problem or create a deterministic test case.
4. Make the smallest coherent change.
5. Run unit tests.
6. Run a service/integration smoke test if the change affects APIs or agent behavior.
7. Inspect logs and persisted state when behavior is unexpected.
8. Update documentation for behavior, setup, or architecture changes.
9. Re-run the full relevant test suite.
10. Summarize what changed, what was tested, and any remaining limitations.

Do not patch symptoms by weakening tests or hiding exceptions.

## Architecture rules

The system has four conceptual layers:

```text
LLM / deterministic reasoner
        ↓
Agent orchestrator / state machine
        ↓
Policy + action contracts
        ↓
Tools / emulated environment
```

Keep these responsibilities separated.

### Reasoner

The reasoner interprets evidence, retrieves knowledge, forms hypotheses, and proposes structured plans.

It must not receive unrestricted shell access or unrestricted production/network access.

### Orchestrator

The orchestrator manages incident state, retries, timeouts, idempotency, scheduling, and handoff between AI and technician.

### Policy layer

The policy layer determines whether a proposed action is allowed. A model recommendation never grants permission by itself.

### Tool layer

Tools expose narrow, auditable capabilities with explicit inputs, outputs, preconditions, postconditions, verification, retry limits, and audit requirements.

## Agent behavior requirements

The agent should follow this operational loop:

```text
Observe
→ Understand
→ Gather evidence
→ Retrieve relevant knowledge
→ Form hypothesis
→ Test hypothesis
→ Decide
→ Safe action OR technician handoff
→ Verify
→ Document
→ Learn/evaluate
```

Rules:

- Investigate before diagnosing.
- Use tools instead of guessing.
- Separate observed facts from hypotheses and recommendations.
- Cite or identify retrieved historical/document evidence where practical.
- Never claim a physical condition that the emulator cannot observe.
- Never report an action as successful without verification.
- Stop when evidence is insufficient or the next step requires a worker.
- Avoid duplicate tickets and repeated work during one fault episode.
- Respect retry/timeout/action budgets.

## Safe-action policy

Current simulated automatic actions are:

```text
reconnect-rtsp
restart-ai-service
```

These are allowed because they act only on fake state.

The following remain non-autonomous by default:

```text
change credentials
change IP/subnet/gateway
change firewall rules
firmware update
factory reset
storage deletion
physical repair
production network changes
```

If a new automatic action is added, it must include:

- tool contract
- risk classification
- preconditions
- postconditions
- verification method
- retry/timeout limit
- audit record
- unit/integration tests
- documentation

## Knowledge-base workflow

User-provided technical documentation belongs under `docs/`.

The agent should:

1. Preserve the original document meaning.
2. Add metadata where useful (source, topic, vendor, revision/date).
3. Avoid inventing unsupported procedures.
4. Prefer exact internal procedures over generic advice when both apply.
5. Make retrieval traceable enough to tell which document informed a recommendation.

When upgrading retrieval, move from the current lightweight Markdown/token search to a structured retrieval layer (metadata + chunks + embeddings/vector search) without removing the deterministic fallback used by tests.

## LLM integration rules

When an LLM is introduced:

- Put model-specific prompts/instructions in version-controlled files.
- Keep the policy engine outside the prompt.
- Require structured output for plans/actions.
- Validate every tool call against a schema before execution.
- Reject unknown tools/actions.
- Limit context to the incident, relevant assets, retrieved evidence, and approved documents.
- Do not send secrets or raw credentials into the model context unless the design explicitly requires it and a security review approves it.
- Keep deterministic replay tests so model changes can be evaluated against known scenarios.

## Testing requirements

Every simulated failure should eventually define:

```text
scenario
expected evidence
expected diagnosis
expected technician action
allowed automatic action
expected postcondition
```

At minimum, maintain tests for:

- RTSP outage with successful safe recovery.
- PoE/power fault requiring technician action.
- RTSP authentication failure with no autonomous credential change.
- AI service failure with safe restart and verification.
- Repeated fault episodes creating separate incidents.
- No duplicate tickets while one fault episode is active.
- Automatic recovery that fails verification and escalates safely.

For an LLM-enabled version, add replay/evaluation metrics such as diagnosis accuracy, unnecessary escalation, safe-action success, verification success, tool-call count, and time-to-useful-technician-action.

## Debugging playbook

When the system fails, debug in this order:

1. Is the container/service running?
2. Is the endpoint reachable?
3. Does the endpoint return the expected schema/status?
4. Is the simulated asset state correct?
5. Was the event detected?
6. Was a ticket created or matched?
7. Did the agent claim the correct ticket state?
8. Did diagnostics run and return evidence?
9. Did knowledge retrieval return relevant material?
10. Did the policy layer allow/block the action correctly?
11. Did the tool execute?
12. Did verification actually observe recovery?
13. Was the ticket updated correctly?
14. Was an audit/run record persisted?

Useful commands:

```bash
docker compose ps
docker compose logs --tail=200 agent
docker compose logs --tail=200 helpdesk
docker compose logs --tail=200 portal
docker compose restart agent
python -m pytest -q
```

If a database/state problem is suspected, stop the stack before deleting or recreating persistent state. Never delete data just to make a test pass without understanding the failure.

## Repository hygiene

Do not commit:

```text
.venv/
__pycache__/
*.pyc
*.db
.pytest_cache/
node_modules/
dist/
.vite/
.env
secrets/
private keys
production exports
customer data
```

Keep generated runtime data out of source-controlled files unless it is an intentional, tiny fixture.

## Definition of done

A change is complete when:

- The behavior is implemented.
- The relevant tests pass.
- Integration behavior is verified when applicable.
- No real systems are contacted.
- Safety/policy boundaries remain intact.
- Documentation is updated when user-visible behavior or setup changes.
- The repository can still be bootstrapped by another developer/AI agent from a clean checkout.

## Preferred implementation style

Favor:

- small Python modules
- typed function signatures where practical
- explicit Pydantic/API schemas
- structured JSON logs
- deterministic simulation state
- dependency injection for service URLs and storage paths
- idempotent operations
- clear error messages
- tests close to the behavior they protect

Avoid:

- hidden global state
- hard-coded production endpoints
- unrestricted shell commands from model output
- brittle string parsing for safety decisions
- coupling the LLM directly to database writes
- automatic retries without limits
- silently swallowing errors
