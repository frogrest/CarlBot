# Agent Orchestrator

## Purpose

The orchestrator is the supervisor for the multi-agent system.

It should answer:

> Who needs to investigate this, what evidence is missing, what is allowed to happen next, and when should the system stop and ask a human?

## Core loop

```text
RECEIVE INCIDENT
      ↓
NORMALIZE CONTEXT
      ↓
CHECK DUPLICATE / EXISTING EPISODE
      ↓
PLAN INVESTIGATION
      ↓
ROUTE TO SPECIALISTS
      ↓
COLLECT RESULTS
      ↓
EVIDENCE REVIEW
      ↓
FORM / REFINE DIAGNOSIS
      ↓
POLICY CHECK
   ┌──┴───────────────┐
   ↓                  ↓
SAFE ACTION       HUMAN ACTION
   ↓                  ↓
VERIFY            HANDOFF
   ↓                  ↓
RESOLVE       WAIT FOR TECHNICIAN
```

## Routing rules

Route based on evidence, not keywords alone.

Examples:

| Signal | Initial specialist(s) |
|---|---|
| Ping failure | Network + Camera/NVR |
| TCP/554 reachable but RTSP fails | RTSP |
| RTSP auth failure | RTSP + Helpdesk/Knowledge |
| Multiple cameras on same NVR fail | Network + Camera/NVR |
| AI Box offline | AI Box + Network |
| Cloud sync failure | AI Box + Knowledge |
| Physical/power clue | Network + Technician |
| Historical known issue | Helpdesk/Knowledge |

The orchestrator may run several specialists in parallel when their investigations are independent.

## Budgets

Every incident should have:

- maximum wall-clock investigation time
- maximum specialist calls
- maximum tool calls
- maximum retries
- maximum autonomous actions

When a budget is exhausted, stop and hand off instead of looping.

## Parallelism

Independent read-only investigations may run concurrently.

Example:

```text
           Orchestrator
          /      |      \
         /       |       \
   Network      RTSP     History
       \          |        /
        \         |       /
         Evidence Aggregator
```

Mutating actions remain sequential and policy-controlled.

## State machine

```text
NEW
 ↓
CLASSIFYING
 ↓
INVESTIGATING
 ↓
EVIDENCE_REVIEW
 ↓
DIAGNOSED
 ↓
ACTION_PROPOSED
 ├── SAFE_EXECUTION → VERIFYING → RESOLVED
 └── HUMAN_REQUIRED → PENDING_TECHNICIAN
                              ↓
                       READY_FOR_VERIFICATION
                              ↓
                          VERIFYING
                              ↓
                           RESOLVED
```

## Specialist contract

A specialist receives:

```json
{
  "incident_id": "INC-123",
  "ticket_id": "T-456",
  "asset_context": [],
  "symptom": "No video",
  "known_evidence": [],
  "requested_question": "Determine whether the stream failure is network, RTSP or recorder-side."
}
```

It returns evidence and conclusions only.

A specialist should not:

- close the ticket independently
- change policy
- execute privileged actions
- invent test results
- fabricate historical matches

## Current deterministic implementation

`services/agent/specialists/` provides evidence-only implementations for Helpdesk, Network, RTSP, Camera/NVR, AI Box, Knowledge, Evidence Review, and Technician Handoff. The orchestrator invokes the routed diagnostic specialists after its base probes. Historical-ticket, document, and site-inventory lookups use a budgeted read-only tool view; specialist code cannot access the action method.

The Evidence Review specialist checks an action proposal against the live observations and the routed specialist's recommendation. It can block execution, but it cannot grant permission. The independent policy engine must still allow the action, and the orchestrator must verify the postcondition. Technician Handoff produces a human-only recommendation and never changes ticket state itself.

These implementations are deterministic rules, not LLM agents. Specialists run sequentially in the current build. They report findings to the orchestrator; diagnosis, ticket transitions, policy decisions, and actions remain orchestrator-owned.

The legacy `Agent` adapter is read-only with respect to infrastructure: direct action calls fail explicitly. All autonomous execution must enter through the orchestrator's evidence review and policy gates.

## Human handoff

A handoff must contain:

1. Observed facts.
2. Evidence already collected.
3. Most likely diagnosis.
4. Confidence and uncertainty.
5. Exact technician action requested.
6. Why the AI stopped.
7. Verification steps after human work.

## Why this matters

The orchestrator is what prevents a collection of clever prompts from becoming an uncontrolled agent swarm. The routing, state machine, budgets, permissions, and audit trail remain deterministic software.
