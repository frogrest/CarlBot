# Master One-Shot Build Prompt

> **Status note (2026-10-06):** The phase order below is still authoritative. Before starting, read `NEXT_AGENT_BRIEF.md` — it records what already exists (upgraded prompts, `frontend/FRONTEND_BUILD_PROMPT.md`, regenerated `FILE_MANIFEST.txt`), known defects to fix early, and the GitHub sync procedure. Screenshot references now mean `reference/screenshots/reference.pdf` (6 pages).

You are the lead AI software engineer for this repository. Build and improve the project until it is runnable, tested, documented, and visually coherent.

## Mission

Build a safe local emulation of a CCTV technical-support helpdesk with:

- a replicated helpdesk-style frontend based on supplied screenshots
- fake helpdesk backend
- fake operations/CCTV portal
- multi-agent orchestrator
- specialist diagnostic agents
- knowledge and historical-ticket retrieval
- deterministic safety/policy layer
- LLM-ready reasoning adapter
- technician-facing AI chatbot/copilot
- evaluation scenarios and tests

The purpose is to automate repetitive investigation and documentation while keeping humans responsible for physical repairs, consequential changes, approvals, and final judgement.

## Source of truth

Read these in order:

1. Existing source code and tests.
2. `AGENTS.md`.
3. `docs/architecture/*.md`.
4. `docs/subagents/*.md`.
5. `prompts/*.md`.
6. `docs/frontend/*.md`.
7. Existing README/setup documentation.
8. User-provided technical documents under `docs/`.
9. Screenshot references under `reference/screenshots/` for appearance only.

Do not silently weaken safety behavior to make a feature work.

## First action

Inspect:

- OS
- Python
- Git
- Docker
- Docker Compose
- Node/npm
- repository tree
- tests
- current services

Run the existing tests before changing code.

## Build order

### Phase 1 — Stabilize the deterministic lab

Make the existing Helpdesk, Portal, Agent, tests, and Docker stack reliable.

### Phase 2 — Orchestrator

Implement the supervisor state machine, specialist contracts, routing, budgets, retries, duplicate suppression, and technician handoff.

### Phase 3 — Specialist agents

Implement:

- Helpdesk Investigation
- Network
- RTSP/Video
- Camera/NVR
- AI Box
- Knowledge
- Evidence Review
- Technician Handoff

### Phase 4 — LLM reasoning

Add a model adapter and structured plan output behind the existing policy/tool boundary. Keep deterministic test scenarios working without the LLM.

### Phase 5 — Helpdesk replica frontend

Inspect the screenshots first. Build a faithful synthetic replica rather than a generic dashboard template.

### Phase 6 — Chatbot/copilot

Integrate the ticket-side AI assistant with:

- investigation progress
- findings
- evidence
- confidence
- suggested action
- safe action state
- technician handoff
- verification status
- `/clear`

### Phase 7 — Evaluation

Add deterministic scenario replay and regression coverage.

## Non-negotiable safety

The system remains fake/emulated during development.

Do not connect it to:

- real cameras
- real NVRs
- real AI Boxes
- customer networks
- production helpdesks
- production credentials
- real cloud infrastructure

The LLM must never bypass the policy layer or receive unrestricted shell access.

## Done means

A feature is not complete because files exist.

The coding agent must actually:

1. start the environment,
2. run tests,
3. run API smoke tests,
4. inject known faults,
5. demonstrate safe simulated recovery,
6. demonstrate technician handoff,
7. demonstrate verification,
8. validate the frontend,
9. demonstrate `/clear`,
10. document exact reproduction steps.

## Final report

Report:

- final architecture
- final directory tree
- commands used
- tests passed
- scenarios passed
- implemented specialists
- implemented chatbot behavior
- current autonomous actions
- limitations
- next recommended phase

Never claim success without actually verifying it.
