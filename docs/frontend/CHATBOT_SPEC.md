# AI Helpdesk Chatbot Specification

## Purpose

The chatbot is the technician-facing conversational layer for the AI investigation system.

It should feel like an integrated assistant inside the replicated helpdesk rather than a separate generic chatbot page.

## Example questions

- `Investigate this ticket.`
- `What have you found?`
- `What evidence supports this diagnosis?`
- `Which historical tickets are similar?`
- `What should I check physically?`
- `Run the approved diagnostic checks.`

## Context

A conversation may use:

- selected ticket
- selected asset
- selected site
- recent diagnostic results
- retrieved evidence
- active investigation state

## `/clear`

Implement `/clear` as a client/session conversation reset.

It clears:

- current chat messages
- temporary conversation context

It must NOT delete:

- ticket data
- historical incidents
- knowledge documents
- audit logs
- agent state

After `/clear`, show a clear message such as:

> Conversation context cleared. Ticket and system data were not changed.

## Transparency

Useful assistant messages should distinguish evidence from conclusions, for example:

```text
Diagnosis
Likely RTSP authentication failure

Confidence
High

Evidence
• TCP/554 reachable
• RTSP handshake reached camera
• Authentication rejected
• Similar historical ticket: T-123

Next step
Verify the approved camera credentials/stream configuration.
```

Do not expose hidden chain-of-thought. Expose concise evidence and work status.

## Action handling

A UI button such as `Run safe reconnect` is only a request to the backend. The backend must independently validate the action against policy.

## Streaming status

User-useful progress may be streamed:

- Investigating ticket
- Checking reachability
- Searching history
- Reviewing RTSP evidence
- Verification complete

## Error states

Distinguish:

- model unavailable
- tool unavailable
- ticket unavailable
- policy denied
- technician required
- verification failed

Never show success merely because an action started.
