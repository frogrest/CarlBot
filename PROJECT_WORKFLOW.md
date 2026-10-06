# Project Workflow — Plain-English Explanation

This document explains the whole project as if you are new to software development.

## 1. The problem

A helpdesk technician receives a ticket such as:

> Camera 7 has no video.

Today, a worker may need to manually:

- open the site record
- identify the camera
- inspect the NVR/AI Box
- check IP connectivity
- test the RTSP path
- compare the issue with historical tickets
- read internal procedures
- write the troubleshooting notes
- decide whether the issue needs a physical visit

The project automates the repetitive investigation work, not the technician's physical job.

## 2. The fake environment

Everything starts in a safe simulated environment.

### Fake Helpdesk

Stores:

- tickets
- comments
- technician notes
- status
- root cause
- resolution
- historical incidents

### Fake Operations Portal

Simulates:

- cameras
- NVRs
- AI Boxes
- network reachability
- TCP/554
- RTSP state
- authentication
- PoE
- CPU/storage
- cloud state

Faults can be intentionally injected for testing.

## 3. The event flow

```text
Fault appears
     ↓
Portal exposes telemetry
     ↓
Agent monitor notices it
     ↓
Helpdesk ticket is created/found
     ↓
Orchestrator starts investigation
```

## 4. The orchestrator

The orchestrator is the manager.

It does not need to know every CCTV detail itself.

It decides which specialist should investigate.

Example:

```text
                 ORCHESTRATOR
                      │
       ┌──────────────┼──────────────┐
       ↓              ↓              ↓
   Network         RTSP        Helpdesk/History
    Agent           Agent            Agent
       │              │              │
       └──────────────┼──────────────┘
                      ↓
               Evidence Agent
                      ↓
                  Conclusion
```

## 5. Specialist agents

### Network Agent

Looks for:

- IP addressing problems
- subnet mismatch
- reachability
- port checks
- gateway/network clues
- intermittent connectivity

### RTSP Agent

Looks for:

- TCP/554
- authentication failures
- wrong stream path
- RTSP service failures
- reconnect possibilities

### Camera/NVR Agent

Looks for:

- recorder-side issues
- channel configuration
- recording/stream conditions
- NVR availability
- camera/NVR relationships

### AI Box Agent

Looks for:

- AI Box health
- detection services
- CPU/storage pressure
- cloud synchronization
- service health

### Knowledge Agent

Looks through:

- historical tickets
- SOPs
- troubleshooting documentation
- vendor notes
- known issues

### Evidence Agent

Acts like a reviewer.

It asks:

> Do we actually have enough evidence to say this?

This reduces confident but unsupported diagnoses.

### Technician Agent

Converts the technical finding into a worker-friendly handoff:

- what was observed
- what is likely wrong
- what the technician should check
- what the AI could not verify
- what should be re-tested afterward

## 6. Why there are multiple agents

A single huge prompt tends to become difficult to control.

Specialists give you:

- smaller responsibilities
- easier testing
- clearer prompts
- easier debugging
- better evidence separation
- easier future replacement

The orchestrator remains the supervisor.

## 7. The knowledge system

The AI should not answer only from generic model memory.

It should use project knowledge:

```text
Live telemetry
     +
Historical tickets
     +
Internal documentation
     +
Current ticket
     ↓
Evidence package
```

The future RAG/vector database can improve retrieval, but the system must remain testable without an LLM.

## 8. The policy engine

This is one of the most important pieces.

Suppose the AI says:

> Restart the AI Box.

The model does not automatically get permission.

Instead:

```text
AI recommendation
      ↓
Policy engine
      ↓
Is the action allowed?
      ↓
Yes → simulated tool
No  → technician/approval
```

## 9. Three classes of actions

### Read-only

The AI can do these automatically in the lab:

- health checks
- ping
- TCP checks
- RTSP checks
- ticket search
- document retrieval
- log reading

### Safe simulated actions

Allowed only when specifically defined and tested:

- reconnect RTSP
- restart simulated AI service

### Human-controlled

The AI must not silently perform these:

- change credentials
- change IP/subnet/gateway
- change firewall rules
- firmware upgrades
- factory reset
- physical repair
- destructive storage changes
- production network changes

## 10. Why verification is separate

An action is not success merely because a button/API call returned OK.

Example:

```text
reconnect RTSP
      ↓
command succeeded
      ↓
verify RTSP stream
      ↓
healthy?
  │       │
 yes      no
  ↓        ↓
resolve   escalate
```

## 11. Ticket lifecycle

```text
open
  ↓
in_progress
  ↓
resolved

or

open
  ↓
in_progress
  ↓
pending_technician
  ↓
worker performs physical/configuration work
  ↓
ready_for_verification
  ↓
in_progress
  ↓
resolved
```

## 12. Chatbot role

The chatbot is the human-facing interface to the AI system.

A technician can ask:

> What have you found so far?

or:

> Investigate ticket 123.

or:

> What evidence supports the RTSP diagnosis?

The assistant should show its useful work context, not just output a mysterious answer.

A `/clear` command resets the conversation context in the UI without deleting ticket/history data.

## 13. Frontend role

The frontend is the screen a technician actually uses.

The target is not just a chatbot page.

It is:

```text
HELPDESK REPLICA
   ├── tickets
   ├── sites/assets
   ├── search/filter
   ├── ticket details
   └── technician workflow
             +
       AI COPILOT
   ├── investigation summary
   ├── evidence
   ├── diagnosis
   ├── suggested next step
   ├── action status
   └── technician handoff
```

The supplied screenshots (`reference/screenshots/reference.pdf`, 6 pages) become a visual reference for the replica.

## 14. What Python does

Python powers much of the backend.

It handles:

- HTTP endpoints
- agent logic
- tool calls
- state
- tests
- database access

## 15. What JavaScript/TypeScript does

The frontend is best handled by a browser-oriented stack such as React + Vite.

It handles:

- buttons
- forms
- ticket views
- chatbot UI
- streaming/status display
- visual layout

## 16. What Docker does

Docker runs the pieces as isolated services.

```text
Browser
  ↓
Frontend container
  ↓
Helpdesk API
Portal API
Agent API
```

This makes the lab much easier to start consistently.

## 17. Where the LLM goes

The LLM should sit behind the orchestrator/decision boundary.

```text
Frontend
   ↓
API
   ↓
Orchestrator
   ↓
Specialists / knowledge / tools
   ↓
Evidence bundle
   ↓
LLM reasoning
   ↓
Structured plan
   ↓
Policy
   ↓
Tool or technician handoff
```

The model should not have raw shell access.

## 18. Development order

The safest order is:

1. Run the existing deterministic lab.
2. Stabilize tests.
3. Add orchestrator state machine.
4. Add specialist agents.
5. Improve knowledge retrieval.
6. Add LLM reasoning.
7. Build screenshot-driven frontend replica.
8. Add chatbot/copilot.
9. Add evaluation scenarios.
10. Only then consider more advanced autonomy.
