# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
CCTV technical support technicians, field engineers, NOC operators, and technical leads responsible for monitoring, diagnosing, and remediating issues across IP cameras, NVRs, PoE switches, and AI video analytics boxes.

## Product Purpose
CarlBot is a safe, deterministic CCTV Technical Support Lab and Operations Console. It simulates realistic CCTV hardware environments, fault generation, and autonomous diagnostic workflows while keeping the technician in the loop ("Automate the repetitive technical work around the technician, not the technician out of the work"). It operates entirely in local simulation and never connects to customer production infrastructure.

## Positioning
A deterministic AI-assisted operations console that enforces hard security policy tiers (`READ`, `SAFE_REVERSIBLE`, `APPROVAL_REQUIRED`, `HUMAN_ONLY`) where AI reasoning is strictly bounded by deterministic tool verification and transparent telemetry rather than unverified actions.

## Operating Context
NOC control rooms and technical support desks. Operators monitor multi-site CCTV deployments, investigate camera stream dropouts, RTSP packet loss, PoE budget overruns, NTP drift, and firmware issues, reviewing AI hypotheses against empirical telemetry before approving corrective actions.

## Capabilities and Constraints
- Full simulation of multi-vendor cameras (Hikvision, Dahua, Axis, Hanwha), NVRs, PoE switches, and AI boxes.
- Fault generation and diagnosis engine with re-arm and deduplication semantics.
- Policy engine (`services/agent/policy.py`) is authoritative: UI and AI prompts cannot override backend permissions.
- Local runtime state stored under `data/runtime/`.
- Frontend Stack: React 19, TypeScript (strict mode: `noUnusedLocals`, `noUnusedParameters`), Vite, Tailwind CSS v3.4, Lucide icons, React Router v7.

## Brand Commitments
- Visual Identity: High-Density NOC Console. Industrial dark palette, crisp telemetry indicators, monospaced data grids, glowing status beacons, and distinct status badges.
- Avoid generic AI design tropes (no generic purple/blue gradients or washed-out gray text on dark backgrounds).
- Distinctive typography suitable for dense monitoring dashboards.

## Evidence on Hand
- Working FastAPI backend services (`services/helpdesk`, `services/portal`, `services/agent`).
- Working React 19 frontend with real API clients and `LabContext`.
- 86+ automated tests passing in backend and Vitest frontend tests.
- Documented faults in `services/portal/app.py` and `ui_redesign_prompt.md`.

## Product Principles
1. Automate repetitive diagnostics around the technician, not the technician out of the work.
2. The policy engine is authoritative; UI and AI cannot grant permissions.
3. Strict segregation of observed facts, historical evidence, AI hypotheses, and verified actions.
4. Deterministic telemetry and tool execution over assumptions.
5. High-density, scan-friendly visual ergonomics for mission-critical operations.

## Accessibility & Inclusion
WCAG AA standards, high-contrast indicators (>= 4.5:1 text contrast), visible focus rings, keyboard navigability for quick NOC triage, and `prefers-reduced-motion` compliance.
