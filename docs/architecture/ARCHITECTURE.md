# Architecture

## System objective

Create a safe, local technical-support AI lab that mirrors a CCTV/helpdesk workflow while keeping human technicians responsible for physical work, consequential changes, approvals, and final judgement.

## High-level architecture

```text
┌────────────────────────────────────────────────────────────┐
│                    Technician Frontend                     │
│  Helpdesk replica + ticket UI + AI chatbot/copilot         │
└──────────────────────────┬─────────────────────────────────┘
                           │ HTTP/WebSocket/SSE
                           v
┌────────────────────────────────────────────────────────────┐
│                    Agent API / Gateway                      │
└──────────────────────────┬─────────────────────────────────┘
                           v
┌────────────────────────────────────────────────────────────┐
│                    Agent Orchestrator                       │
│ incident state • routing • budgets • retries • handoff      │
└───────────────┬───────────────────────────┬────────────────┘
                │                           │
                v                           v
      ┌──────────────────┐        ┌────────────────────┐
      │ Specialist Agents│        │ Evidence/Knowledge│
      ├──────────────────┤        ├────────────────────┤
      │ Network          │        │ Historical tickets │
      │ RTSP             │        │ Internal docs      │
      │ Camera/NVR       │        │ Site context       │
      │ AI Box           │        │ Evidence review    │
      │ Helpdesk         │        └────────────────────┘
      └────────┬─────────┘
               v
      ┌────────────────────────────┐
      │ Model / Reasoning Adapter  │
      │ deterministic or LLM-based │
      └─────────────┬──────────────┘
                    v
      ┌────────────────────────────┐
      │ Policy + Action Contracts  │
      └─────────────┬──────────────┘
                    v
      ┌────────────────────────────┐
      │ Tool Bus / Simulated APIs  │
      └─────────────┬──────────────┘
                    │
         ┌──────────┴───────────┐
         v                      v
  Fake Helpdesk            Fake Operations Portal
```

## Responsibilities

### Frontend

Owns presentation and user interaction. It does not decide whether actions are safe.

### API gateway

Provides authenticated, structured application endpoints. It should never turn the model into an unrestricted shell user.

### Orchestrator

Owns incident state, specialist routing, retry budgets, timeout budgets, duplicate suppression, escalation, and task completion.

### Specialist agents

Perform constrained reasoning for a domain. They return structured findings instead of directly mutating the environment.

### Model adapter

Allows deterministic reasoning now and LLM reasoning later without rewriting the tool layer.

### Policy engine

Independently decides what can actually execute.

### Tool bus

Exposes small auditable actions with explicit contracts.

## Structured agent result

Every specialist should return something equivalent to:

```json
{
  "agent": "rtsp",
  "status": "complete",
  "facts": [],
  "hypotheses": [],
  "tests_performed": [],
  "evidence": [],
  "confidence": 0.0,
  "recommendations": [],
  "requires_human": false,
  "handoff_reason": null
}
```

The implementation may use Python models/classes rather than raw JSON, but the schema should remain stable.

## Incident context

The orchestrator should carry a bounded incident context:

- ticket ID
- site
- affected asset(s)
- reported symptom
- current state
- live evidence
- historical evidence
- document evidence
- completed tests
- specialist findings
- selected diagnosis
- allowed actions
- verification result
- technician handoff status

## No unrestricted model access

The model must never receive unrestricted shell access, unrestricted database access, or raw production credentials.

## Deterministic-first principle

Keep the environment deterministic enough that known scenarios can be replayed without an LLM. This makes regression testing possible.
