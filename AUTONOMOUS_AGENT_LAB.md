# Autonomous Agent Lab — Architecture & Specification

> **Automate the repetitive technical work around the technician, not the technician out of the work.**

---

## Agent Behaviour Cycle

```text
Observe → Understand → Gather Evidence → Retrieve Knowledge →
Form Hypothesis → Test Hypothesis → Decide →
Execute Safe Action or Request Technician Action →
Verify → Document → Learn from Actual Resolution
```

---

## Services Architecture

```text
                     HUMAN TECHNICIAN
                            │
              ┌─────────────┴─────────────┐
              │                           │
        OPERATIONS UI               AI ASSISTANT
     (NOC Console & Timeline)   (Chat & Slash Commands)
              │                           │
        System state                 Reasoning
        Evidence                     Investigation
        Incidents                    Recommendations
        Devices                      Tool use
        Sites                        Explanation
              │                           │
              └─────────────┬─────────────┘
                            │
                      POLICY ENGINE
             (services/agent/policy.py)
                            │
              ┌─────────────┴─────────────┐
              │                           │
        Safe automation              Human action
       (SAFE_REVERSIBLE)        (APPROVAL / HUMAN_ONLY)
```

### 1. Fake Helpdesk (`services/helpdesk/`, Port 8001)
- Ticket CRUD, status transitions, comments, and technician note-taking.
- Pre-seeded with 7 realistic historical incidents with diagnostic notes and root causes.
- Statuses: `open`, `investigating`, `pending_technician`, `pending_approval`, `resolved`, `closed`.
- Full-text keyword search across titles, descriptions, and resolution notes.

### 2. Fake Operations Portal (`services/portal/`, Port 8002)
- 8 simulated assets (4 IP cameras, 2 NVRs, 2 AI Boxes) distributed across 3 sites.
- Active telemetry simulation: health status, ping check, TCP port check, RTSP stream verification, and system resource metrics (CPU, RAM, disk, temperature).
- 12 injectable fault types with site-wide fault injection support.
- 4 allow-listed safe actions (`reconnect_stream`, `restart_service`, `retry_upload`, `clear_transient`).
- Full fault history and action audit log.

### 3. Autonomous Agent (`services/agent/`, Port 8003)
- Background autonomous loop polling portal state every 5 seconds.
- On-demand targeted single-asset investigation via `POST /investigate/{asset_id}`.
- Deterministic diagnosis engine — functions reliably without external LLM dependencies.
- Bounded retry logic (default max 3 attempts) to prevent infinite loops.
- Deduplication: Maintains at most one active open incident per asset.
- Re-arming: Cleared faults verified as recovered re-arm the asset for future incident creation.
- Authoritative knowledge retrieval from Markdown SOPs in `data/knowledge/`.
- Strict evidence structuring in every diagnostic ticket update.

### 4. Operations Web Console (`frontend/`, Port 5173)
- Production-grade NOC console built with React 19, TypeScript, and Tailwind CSS v3.4.
- 10 dedicated views:
  - **Dashboard (`/`)**: Metric cards, site health breakdown, active faults, and quick fault simulator modal.
  - **Incidents Queue (`/incidents`)**: Filterable ticket table with severity and status badges.
  - **Incident Detail (`/incidents/:id`)**: Full ticket metadata, expandable diagnostic timeline, historical matches, and technician note submission.
  - **Device Inventory (`/devices`)**: Device status grid, ping/RTSP latency, and fault injection shortcuts.
  - **Device Detail (`/devices/:id`)**: Comprehensive device specifications, real-time gauges, and live telemetry.
  - **Site Overview (`/sites`)**: Multi-site status rollups and summary statistics.
  - **Site Detail (`/sites/:id`)**: Interactive **Topology Graph** mapping network dependencies and correlating multi-camera outages.
  - **AI Assistant (`/assistant`)**: Conversational NOC chat with slash commands, tool execution step pills, and human-in-the-loop alerts.
  - **Knowledge Base (`/knowledge`)**: Authoritative Markdown runbook browser.
  - **Audit Log (`/audit`)**: Complete chronological log of autonomous and human actions.

---

## Safety Policy Tiers

| Class | Examples | Automatic Action? | Policy Treatment |
|---|---|---|---|
| **READ** | `ping_check`, `tcp_check`, `rtsp_check`, `get_logs`, `search_tickets` | ✅ Always | Executed immediately for diagnostic evidence |
| **SAFE_REVERSIBLE** | `reconnect_stream`, `restart_service`, `retry_upload`, `clear_transient` | ✅ If Allow-Listed | Executed autonomously, followed by verification |
| **APPROVAL_REQUIRED** | `reboot_host`, `update_config`, `firmware_upgrade`, `factory_reset` | ❌ Never autonomous | Flagged with yellow badge, requires human approval |
| **HUMAN_ONLY** | `hardware_repair`, `cable_replacement`, `lens_cleaning`, `credential_rotation` | ❌ Never autonomous | Red badge alert, ticket escalated to technician |

> **Security Rule:** Policy enforcement is strictly isolated in `services/agent/policy.py`. Frontend buttons and chat prompts cannot bypass or override policy decisions.

---

## Structured Evidence Model

Every investigation records and separates diagnostic facts:

| Field | Meaning | Rule |
|---|---|---|
| `observed_facts` | Raw check results (ping, RTSP, TCP, metrics) | Never invented; reflects real simulated telemetry |
| `historical_evidence` | Matching tickets from the helpdesk search | Extracted from actual past incidents |
| `documentation` | Runbook excerpts retrieved from SOPs | Sourced directly from `data/knowledge/` |
| `hypothesis` | Diagnosed root cause identifier | Determined by deterministic diagnosis rules |
| `confidence` | Confidence level (0.0 to 1.0) | Based on conclusive vs. partial check results |
| `recommended_action`| Proposed remediation action | Derived from SOP and fault mapping |
| `safety_class` | READ / SAFE_REVERSIBLE / APPROVAL_REQUIRED / HUMAN_ONLY | Authoritatively assigned by `policy.py` |
| `actions_performed` | Actions actually triggered | Never represent an unperformed action as performed |
| `verification` | Post-action verification result | Confirmed by fresh telemetry check |

---

## AI Assistant & Slash Commands

The conversational assistant supports quick-action slash commands:

- `/investigate <ASSET_ID>`: Runs full diagnostic suite on asset, consults policy, and applies recovery or escalates.
- `/status <ASSET_ID>`: Returns instant non-mutating telemetry snapshot.
- `/site <SITE_ID>`: Evaluates site health, active devices, and checks for correlated multi-camera outages.
- `/history <QUERY>`: Searches historical incidents for past resolutions.
- `/help`: Lists supported commands, usage syntax, and safety guidelines.
- `/clear`: Resets active chat conversation history without affecting backend tickets or device states.

### Tool Execution Transparency
When executing commands, the UI renders real-time tool execution pills:
- `Running` (Blue spinning indicator)
- `Success` (Green checkmark indicator)
- `Failure` (Red alert indicator)
- `Blocked by Policy` (Purple shield indicator)

---

## Supported Faults & Diagnosis Matrix

| Fault | Target | Auto-recoverable? | Safe Action | Policy Tier |
|---|---|---|---|---|
| `network_down` | Camera/NVR | No | — | `HUMAN_ONLY` |
| `rtsp_down` | Camera | Yes | `reconnect_stream` | `SAFE_REVERSIBLE` |
| `rtsp_auth_failure` | Camera | No | — | `HUMAN_ONLY` |
| `wrong_rtsp_path` | Camera | No | — | `HUMAN_ONLY` |
| `poe_power_off` | Camera | No | — | `HUMAN_ONLY` |
| `high_cpu` | AI Box | No | — | `APPROVAL_REQUIRED` |
| `storage_full` | NVR | No | — | `APPROVAL_REQUIRED` |
| `intermittent_connectivity` | Camera | Yes | `clear_transient` | `SAFE_REVERSIBLE` |
| `nvr_unavailable` | NVR | No | — | `HUMAN_ONLY` |
| `ai_box_service_failure` | AI Box | Yes | `restart_service` | `SAFE_REVERSIBLE` |
| `cloud_sync_failure` | AI Box | Yes | `retry_upload` | `SAFE_REVERSIBLE` |
| `multi_camera_site_outage` | Site | No | — | `HUMAN_ONLY` |

---

## Test Coverage & Evaluation

The full stack is covered by comprehensive automated tests:

### Backend Test Suite (`pytest`, 60 tests)
- **Policy Engine Unit Tests:** Enforcement of allow-lists, action constraints, and safety classes.
- **API Smoke Tests:** Endpoint contracts for Helpdesk (8001), Portal (8002), and Agent (8003).
- **Auto-Recovery Scenarios:** Verified execution and state recovery for RTSP, AI Box service, cloud sync, and intermittent faults.
- **Technician Escalation Scenarios:** Verified ticket escalation to `pending_technician` when faults are non-reversible.
- **Deduplication & Re-Arming:** Verified that active faults update existing tickets, and new incidents are only created after verified recovery.
- **Multi-Camera Site Outages:** Verified correlation of shared network/gateway failures across cameras at a site.
- **Knowledge Retrieval:** Verified keyword matching against runbooks.
- **Agent Retry Limits:** Verified agent halts after max retries without infinite looping.

### Frontend Test Suite (`Vitest`, 19 tests)
- **Badge & Policy Rendering:** Accurate color codes and labels for all safety classes.
- **Chat & Slash Commands:** Parser validation, `/investigate`, `/status`, `/site`, `/history`, and `/clear` state isolation.
- **Investigation Timeline:** Step-by-step diagnostic breakdown and JSON drawer toggling.
- **Topology Graph:** Dynamic node hierarchy rendering and correlated multi-camera failure detection.
- **Safety Enforcement:** Human-in-the-loop alert cards displayed when actions require approval or human intervention.
- **App Views:** Core route rendering and empty/error state handling.
