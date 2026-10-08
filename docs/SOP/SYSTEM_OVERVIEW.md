# AI Ops Assistant Lab Architecture & System Overview

## System Purpose
The AI Ops Assistant Lab is a safe, fully emulated technical-support operations lab designed to automate routine diagnostic investigation and documentation for camera surveillance systems while enforcing strict deterministic safety boundaries. Physical repairs, credential changes, and network alterations are kept in the hands of technicians.

## Core Microservices Architecture
1. **Helpdesk Service (`:8000`)**:
   - Manages technical incident tickets, technician notes, customer-facing conversation logs, and status transitions (`Open`, `Answered`, `Closed`).
   - Backed by SQLite (`helpdesk.db`).
2. **Portal Service (`:8001`)**:
   - Emulates simulated physical assets (cameras, NVRs, AI Boxes, PoE switch ports) across multiple sites.
   - Provides diagnostic probes (ping, TCP port check, RTSP stream probe) and fault simulation injection (`rtsp_down`, `poe_off`, `rtsp_auth_failure`, `ai_service_down`).
3. **Agent Orchestrator & Policy Engine (`:8002`)**:
   - Continuously monitors telemetry events, dedupes recurring fault episodes, coordinates specialized investigation subagents, and enforces the deterministic Policy Engine.
   - *Allowed Safe Actions*: Only `reconnect-rtsp` and `restart-ai-service` may execute autonomously.
   - *Strict Human Handoff*: Physical repairs, cable replacements, and credential updates escalate to `pending_technician`.
4. **Operations Frontend (`:8003`)**:
   - Modern React/Vite/TypeScript operations dashboard with multi-site queue, asset inventory, emulator controls, and CarlBot AI copilot.
