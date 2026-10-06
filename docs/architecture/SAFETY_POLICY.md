# Safety and Action Policy

## Principle

The model can recommend an action, but the model does not grant itself permission to execute it.

## Classes

### A — READ

Automatically allowed in the local lab:

- ticket search
- documentation retrieval
- health check
- ping
- port check
- RTSP check
- status/log retrieval
- asset discovery

### B — SAFE SIMULATED

Allowed only when the action has a registered contract and only against fake state:

- reconnect simulated RTSP
- restart simulated AI service
- clear simulated transient failure
- retry simulated upload when defined

### C — APPROVAL REQUIRED

Never run automatically without an explicit approval workflow:

- credential changes
- IP/subnet/gateway changes
- firewall/network-security changes
- configuration changes with service impact
- NVR/AI Box reboot if treated as consequential
- firmware actions

### D — HUMAN ONLY

Examples:

- cable/PoE physical repair
- camera replacement or movement
- factory reset
- production network changes
- physical inspection
- destructive storage work

## Action contract

Every executable action should declare:

```yaml
name: reconnect_rtsp
risk: low
reversible: true
requires_approval: false
allowed_environments:
  - simulator
preconditions:
  - incident_is_active == true
  - asset_type == camera
postconditions:
  - rtsp == healthy
verification:
  - test_rtsp
max_attempts: 1
timeout_seconds: 15
audit_required: true
```

## Policy decision

```text
model proposes action
       ↓
validate action schema
       ↓
check environment
       ↓
check asset permissions
       ↓
check preconditions
       ↓
check risk/approval
       ↓
execute OR deny/handoff
       ↓
verify postcondition
```

## Audit record

For every action record:

- incident ID
- ticket ID
- action name
- requester
- reason
- evidence IDs
- policy decision
- execution result
- verification result
- timestamp

## Never do this

Do not build a prompt that says "you are fully autonomous" and then let the model call arbitrary shell commands. The deterministic policy layer is the real safety boundary.
