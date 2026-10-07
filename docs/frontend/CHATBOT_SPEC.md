# CarlBot Ticket Lookup Specification

## Purpose

CarlBot helps technicians find and understand existing helpdesk tickets. It is a
read-only lookup assistant, not an incident investigator or autonomous resolver.
Technicians can ask about a site, camera, issue, or ticket status from either the
ticket queue or ticket detail screen.

Examples:

- `Is there an open ticket about an offline camera at SITE-104?`
- `Show closed RTSP tickets for SITE-104.`
- `What was recorded in ticket 1002?`

## Retrieval and answers

- Search both live Helpdesk ticket records and the optional locally mounted
  `reference/ticketreference examples.csv` export.
- Filter by explicit open, closed, or resolved intent. A closed query returns
  `closed` records only; resolved records are not mislabeled as closed. Never
  present an open reference-export record as closed.
- Prefer exact site identifiers or names. Label weaker site overlap as a
  possible match and state that the site is unconfirmed. A requester/`From`
  value alone can never confirm site identity.
- Summarize only retrieved ticket fields and notes. Do not invent camera IDs,
  site identity, conversation details, or a resolution.
- Treat explicit requests for a ticket's subject/title as a lookup intent and
  return the stored subject exactly as recorded.
- For live Helpdesk matches, show direct links that open the corresponding
  ticket detail in the workspace. Do not show local-ticket links for
  reference-export-only matches.
- Use short, plain-language replies. For broad searches, show at most three
  ticket summaries and invite the technician to ask about a ticket number for
  more detail. For a single ticket, include its status and one useful recorded
  detail. Explain statuses in everyday words (for example,
  `pending_technician` means the ticket is waiting for a technician) and
  translate known technical causes without changing their meaning.
- Live records may include ticket descriptions, resolution/root-cause fields,
  summaries, and technician notes. The reference export contains metadata only;
  say that its conversation is unavailable.
- Never return sender email addresses. The optional export remains local and is
  mounted read-only into the Helpdesk service.
- If the export is not mounted, disclose that only live records were searched.

## Visual hierarchy and motion

- Keep CarlBot easy to find on both the ticket queue and ticket detail views.
- Give the chat panel more visual weight than secondary status indicators, with
  a clear title, readable message text, and a comfortable input target.
- On wide queue views, keep the assistant visible beside the ticket list; on
  narrow screens, place it after the queue without causing horizontal overflow.
- Keep replies concise and scannable; larger type should improve readability
  without turning the panel into the primary page.
- Use CSS for small message-arrival and input-focus transitions. Respect the
  operating system's reduced-motion preference and avoid decorative or
  continuous motion.

## Read-only boundary

Chat uses only `POST /api/chat/query` on the Helpdesk service. That endpoint
performs reads and does not create/update tickets, add notes, invoke the agent,
query the portal, or run diagnostic/recovery actions. Keep chat controls
separate from the investigation and simulated-lab controls.

## `/clear`

`/clear` resets the browser conversation only. It does not delete or change
tickets, notes, audit records, the CSV, or agent state.

After `/clear`, show a clear message such as:

> Conversation context cleared. Ticket and system data were not changed.

## Transparency and errors

Answers identify matching ticket IDs, statuses, and available details. Use
wording such as “possible match (site not confirmed)” when the site is not an
exact match. Distinguish an empty result from an unavailable Helpdesk service.
Never claim to have searched or read records after an API failure.

Do not expose hidden chain-of-thought. Provide concise summaries grounded in
the retrieved source records.
