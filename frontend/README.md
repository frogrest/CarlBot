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

- Search/filter synthetic helpdesk tickets and open their detail records.
- Add technician notes to the simulated helpdesk.
- Run portal health, ping, TCP/554 and RTSP probes from a ticket.
- Request an investigation from the backend agent; the backend policy engine
  remains authoritative for every automatic action.
- Inspect site assets and inject/reset simulated faults.
- Use `/clear` in the chat shell to clear only local conversation state.

The chat responder is not implemented in the backend yet. The UI says so
explicitly rather than presenting a fabricated model response. Physical work,
credentials, network configuration and other consequential changes remain
technician-controlled. A technician verification-request button is also
withheld for now: the current helpdesk endpoint updates ticket status but does
not set the agent's `verify_requested` state expected by its worker. Resolve
that backend workflow before exposing the button. No production systems are
contacted.
