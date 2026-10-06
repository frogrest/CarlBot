# AI Ops Assistant Lab — Knowledge Base

Drop internal documentation into this directory. The autonomous agent reads Markdown files from here using a lightweight local keyword retriever.

Recommended structure:

```text
 docs/
 ├── SOP/
 ├── RTSP/
 ├── Networking/
 ├── Cameras/
 ├── NVR/
 ├── AI-Box/
 ├── Alarm-EG/
 ├── AI-Cloud/
 ├── Vendor/
 ├── Escalation/
 └── Known-Issues/
```

## What the agent uses

The agent combines three evidence sources:

1. **Live telemetry** from the fake portal.
2. **Historical incidents** from the fake helpdesk.
3. **Internal documentation** from this folder.

The current retrieval layer is intentionally simple and deterministic. Later we can replace it with embeddings/vector search without changing the rest of the agent workflow.

## Writing good knowledge documents

Prefer concise documents with explicit sections:

- Symptoms
- Preconditions
- Diagnostics
- Evidence to collect
- Safe actions
- Technician actions
- Verification
- Escalation criteria
- Known failure modes

Example:

```markdown
# RTSP Authentication Failure

## Symptoms
- TCP/554 is reachable.
- RTSP handshake reaches the device.
- Authentication fails.

## Diagnostics
1. Confirm device IP.
2. Test TCP/554.
3. Verify RTSP username/password.
4. Verify stream path.

## Technician Action
Update credentials or stream configuration using the approved procedure.

## Verification
Confirm the NVR/AI Box receives video for at least 60 seconds.
```

## Trust boundary

Documents are advisory knowledge. The agent's action-policy layer still decides whether an action is allowed. A document can recommend a reboot; it cannot grant the agent permission to reboot a production system.
