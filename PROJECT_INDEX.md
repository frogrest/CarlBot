# AI Helpdesk Agent Project — Master Index

This repository combines the earlier AI Ops Lab with the new multi-agent helpdesk/chatbot/frontend design.

## Read these first

**AI coding agents: start with `NEXT_AGENT_BRIEF.md`** — current state of the repo, known defects, phase-by-phase work plan, and the GitHub sync procedure.

1. `INSTALL_AND_PYTHON_CRASH_COURSE.md` — start here on a fresh Windows 11 PC.
2. `PROJECT_WORKFLOW.md` — understand the system without needing Python knowledge.
3. `AGENTS.md` — rules for the coding agent (Antigravity/other agentic CLI).
4. `docs/architecture/ARCHITECTURE.md` — the full system architecture.
5. `docs/architecture/ORCHESTRATOR.md` — how the supervisor routes work to specialist agents.
6. `docs/architecture/SAFETY_POLICY.md` — hard boundary between recommendation and execution.
7. `docs/architecture/KNOWLEDGE_SYSTEM.md` — tickets + documents + evidence retrieval.
8. `docs/frontend/HELPDESK_REPLICATION.md` — screenshot-driven frontend replication.
9. `docs/frontend/CHATBOT_SPEC.md` — chatbot UX and `/clear` behavior.
10. `ONE_SHOT_BUILD_PROMPT.md` — one master build prompt for an AI coding agent.

## Specialist agents

See `docs/subagents/` for the role definition of each specialist.

## Model prompts

See `prompts/` for version-controlled system prompts. Prompts never replace the policy engine.

All 10 prompts were rewritten (2026-10-06) with per-role depth: investigation methods, failure-signature tables, the structured `SpecialistResult` output contract (from `docs/architecture/ARCHITECTURE.md`), a shared confidence scale, evidence-labeling rules, and hard safety boundaries. The orchestrator prompt contains the evidence-based routing table.

## Current implementation vs planned architecture

The included lab (services at version 0.2.0) already contains:

- Fake Helpdesk service
- Fake Operations Portal
- Persistent autonomous agent
- Simulated faults
- Knowledge retrieval
- Safe simulated recovery actions
- Tests
- Docker Compose runtime

The Phase 2 orchestrator is validated: `services/agent/orchestrator/` (state machine, evidence router, budgets, engine), `services/agent/policy/` (permission engine + audit log), and `services/agent/tools/` (safe ToolBus), wired into `services/agent/main.py` and helpdesk status updates. Phase 3 adds deterministic, evidence-only specialists under `services/agent/specialists/` for Helpdesk, Network, RTSP, Camera/NVR, AI Box, Knowledge, Evidence Review, and Technician Handoff. Specialist lookup tools are read-only and budgeted; policy remains the only permission authority. Validation details and limitations are in `NEXT_AGENT_BRIEF.md`. Still ahead: the LLM adapter, screenshot-driven frontend replica (operative prompt: `frontend/FRONTEND_BUILD_PROMPT.md`), and full chatbot UI.

## Safety rule

This package is a local simulation. Do not connect it to production cameras, NVRs, AI Boxes, customer networks, credentials, or a live helpdesk while developing the project.
