# Instructions for Future AI Coding Agents

## Mission

Build and extend a **deterministic, safe** CCTV technical-support lab with a production-grade Operations console. Never connect to production or customer infrastructure.

---

## Core Rules Before Modifying Code

1. Read `README.md`, `AUTONOMOUS_AGENT_LAB.md`, `SETUP_AND_DEVELOPMENT.md`, and this file.
2. Inspect existing backend APIs (`services/*/app.py`) and frontend clients (`frontend/src/api/*.ts`) before modifying behavior.
3. Keep simulator state fake and local under `data/runtime/`.
4. Run full validation after every change:
   ```bash
   python -m pytest -q
   python -m ruff check .
   cd frontend && npm test && npm run build
   ```

---

## Backend Architecture Rules

- The **policy engine** (`services/agent/policy.py`) is authoritative. AI prompts, chat interfaces, and frontend controls never grant permissions.
- Keep **READ**, **SAFE/REVERSIBLE**, **APPROVAL_REQUIRED**, and **HUMAN_ONLY** actions strictly segregated.
- Every automatic action must be:
  - Allow-listed in the policy engine
  - Reversible in the simulator
  - Followed by post-action verification
  - Bounded by retry/stop conditions
- **Never invent** observations, historical evidence, tool output, or successful repairs.
- Preserve **deduplication/re-arm** semantics:
  - An active fault on an asset must not generate duplicate open tickets.
  - A later fault occurring after verified recovery must create a new incident.
- Keep LLM integration behind a replaceable `ReasoningProvider` interface. The deterministic simulator and tool layer must work without an LLM.

---

## Frontend Architecture Rules

- **Tech Stack:** React 19, TypeScript (strict), Vite, Tailwind CSS v3.4, Lucide icons, React Router v7.
- **Strict TypeScript:** `noUnusedLocals: true` and `noUnusedParameters: true` are enabled in `tsconfig.app.json`. Never leave unused imports, variables, or unhandled types.
- **Safety Policy Visualization:**
  - Render policy badges (`SAFE_REVERSIBLE`, `APPROVAL_REQUIRED`, `HUMAN_ONLY`, `READ`) accurately.
  - Never add frontend buttons that execute actions blocked by backend policy.
  - When an action is `HUMAN_ONLY` or `APPROVAL_REQUIRED`, render an explicit human-in-the-loop alert card with technician guidance.
- **Chat Assistant Slash Commands:**
  - Commands (`/investigate`, `/status`, `/site`, `/history`, `/help`, `/clear`) must parse arguments cleanly and provide helpful feedback for invalid IDs.
  - `/clear` must only clear UI conversational messages. It must **never** wipe backend tickets, portal assets, or audit logs.
- **Diagnostic Transparency:** Always render tool execution pills (`Running`, `Success`, `Failure`, `Blocked`) so the operator sees exactly what checks and tools ran.
- **No Mock Placeholders:** Components must bind to real backend data from `LabContext` or API clients. Empty states must clearly indicate "No incidents" or "All systems normal" rather than fabricating mock alerts.

---

## Adding a New Fault

1. Add the fault identifier to `SUPPORTED_FAULTS` in `services/portal/app.py`.
2. Add its state transformation in `_effective_state()` in `services/portal/app.py`.
3. Add diagnosis logic in `diagnose()` and `investigate_single_asset()` in `services/agent/agent.py`.
4. If auto-recoverable, add it to `FAULT_TO_ACTION` and `FAULT_VERIFICATION`.
5. If auto-recoverable, add the corresponding action to `ALLOWED_ACTIONS` in the portal.
6. Categorize the safety class using `services/agent/policy.py`.
7. Add runbook documentation in `data/knowledge/troubleshooting.md`.
8. Add frontend fault simulation shortcut in `frontend/src/components/layout/LabControlsModal.tsx`.
9. Add regression and recovery/escalation tests in `tests/test_lab.py` and frontend tests if applicable.

---

## Adding a New Frontend Page

1. Create page component in `frontend/src/pages/YourPage.tsx`.
2. Register route in `frontend/src/App.tsx`.
3. Add navigation link with Lucide icon in `frontend/src/components/layout/Sidebar.tsx`.
4. Write test in `frontend/src/test/` to verify rendering and data display.

---

## Key Files Reference

| File | Purpose |
|---|---|
| `services/common/config.py` | Central configuration and ports |
| `services/common/models.py` | Shared Pydantic models and enums |
| `services/helpdesk/app.py` | Helpdesk REST API (Port 8001) |
| `services/portal/app.py` | Operations Portal REST API (Port 8002) |
| `services/agent/agent.py` | Autonomous agent core loop & single asset investigation |
| `services/agent/policy.py` | Safety policy engine (Authoritative) |
| `services/agent/knowledge.py` | Knowledge retrieval layer & doc endpoints |
| `services/agent/reasoning.py` | LLM boundary contract |
| `services/agent/app.py` | Agent API endpoints (Port 8003) |
| `frontend/src/App.tsx` | Frontend routes and layout container |
| `frontend/src/context/LabContext.tsx` | Real-time telemetry, polling, and fault management |
| `frontend/src/components/timeline/InvestigationTimeline.tsx` | Diagnostic evidence and step breakdown |
| `frontend/src/components/topology/TopologyGraph.tsx` | Network hierarchy and correlated outage visualizer |
| `frontend/src/components/chat/ChatContainer.tsx` | AI Assistant conversational console & slash parser |
| `tests/test_lab.py` | Backend comprehensive test suite (60 tests) |
| `frontend/src/test/` | Frontend Vitest test suites (19 tests) |
| `data/knowledge/` | Authoritative troubleshooting documents (Markdown) |
| `data/runtime/` | Generated simulator state files (gitignored) |
