# CarlBot Support frontend

This is a synthetic technician workspace for the local helpdesk lab. It uses
React, TypeScript and Vite, and sends requests only through same-origin API
proxies to the emulated Helpdesk, Portal and Agent services.

## Run locally

Start the backend lab services from the repository root:

```powershell
docker compose up -d helpdesk portal agent
```

Then start the frontend:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open <http://localhost:5173>. The Vite server proxies `/helpdesk`, `/portal`
and `/agent` to local ports 8000, 8001 and 8002.

To run the whole lab including the static frontend container:

```powershell
docker compose up --build -d
```

Open <http://localhost:8003>.

## Implemented interactions

- Browse 25 varied synthetic tickets across SITE-104, Freddy Fazbear's,
  Centerpark Tower 1 and Pacman.
- Filter by Open, Answered or Closed status, site and priority; change a
  ticket's helpdesk status from its detail view.
- Add technician notes to the simulated helpdesk.
- Run portal health, ping, TCP/554 and RTSP probes from a ticket.
- Request an investigation from the backend agent; the backend policy engine
  remains authoritative for every automatic action.
- Inspect site assets and inject/reset simulated faults.
- Ask CarlBot about ticket fields and recorded conversation notes, follow
  cited ticket links, and review advice-only next steps. New messages scroll
  into view while the message history remains scrollable. The chat stays in
  the right sidebar on both the queue and ticket-detail views.
- Use `/clear` in the chat shell to clear only local conversation state.

The three user-facing ticket statuses are stored separately from the agent's
operational workflow state so helpdesk status changes cannot skip policy-gated
investigation or verification. Physical work, credentials, network
configuration and other consequential changes remain technician-controlled.
No production systems are contacted.
