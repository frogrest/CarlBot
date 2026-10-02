---
name: CarlBot High-Density NOC Console
description: Mission-critical CCTV & AI infrastructure monitoring, diagnostics, and human-in-the-loop autonomous operations.
colors:
  background: "#070b12"
  surface: "#0e1524"
  surface-subtle: "#0a0f1d"
  surface-elevated: "#152035"
  surface-border: "#1c2a44"
  surface-border-bright: "#2d4268"
  primary: "#0ea5e9"
  primary-glow: "rgba(14, 165, 233, 0.25)"
  status-healthy: "#10b981"
  status-warning: "#f59e0b"
  status-critical: "#f43f5e"
  status-investigating: "#38bdf8"
  status-technician: "#fb923c"
  policy-read: "#38bdf8"
  policy-safe: "#10b981"
  policy-approval: "#f59e0b"
  policy-human: "#f43f5e"
typography:
  display:
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    letterSpacing: "-0.02em"
  mono:
    fontFamily: "'JetBrains Mono', 'SFMono-Regular', Consolas, monospace"
    fontSize: "0.8125rem"
    fontWeight: 500
    letterSpacing: "0.02em"
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
    border: "1px solid {colors.surface-border}"
  policy-pill:
    rounded: "{rounded.sm}"
    typography: "{typography.mono}"
---

# Design System: High-Density NOC Console

## Overview
The CarlBot Operations Console is engineered for Network Operations Centers (NOC) and technical helpdesks monitoring multi-site CCTV, NVR, PoE, and Edge AI hardware. The interface prioritizes rapid scanning, strict policy differentiation, deterministic diagnostic transparency, and continuous telemetry monitoring under intense operational conditions.

## Colors
- **Core Dark Surfaces:** Deep obsidian blue foundations (`#070b12`, `#0e1524`, `#152035`) avoid washed-out grays and provide deep contrast for glowing status beacons.
- **Borders & Dividers:** Subtle nautical slate borders (`#1c2a44`) delineate panels without visual noise.
- **Diagnostic Signal Hierarchy:**
  - **Healthy / Resolved:** `#10b981` (Emerald) with soft emerald aura.
  - **Investigating / AI Active:** `#38bdf8` (Cyan) with pulsing beacon.
  - **Warning / Degraded:** `#f59e0b` (Amber) for stream packet loss and NTP drift.
  - **Technician Required / Human Action:** `#fb923c` (Orange/Coral) for hardware faults.
  - **Critical / Offline:** `#f43f5e` (Rose) with immediate high-contrast alert treatment.

## Typography
- **UI / Headings:** Crisp system interface stack (`-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif`).
- **Telemetry & Logs:** High-precision monospaced numerals (`'JetBrains Mono', Consolas, monospace`) for IP addresses, MACs, RTSP bitrates, PoE wattage, and timestamps.
- **Hierarchy:** Strict vertical scale with tabular numbers (`font-variant-numeric: tabular-nums`) so live telemetry values do not shift layout on update.

## Layout
- **Density:** High-density operational view with compact padding (`px-3 py-2`), collapsible side navigation, and responsive grid layouts.
- **Grid Systems:** Standardized 12-column responsive layout, 4-tier KPI metrics deck, and modular split views (telemetry left, diagnostic history right).

## Elevation & Depth
- **Layering:** Depth is conveyed through subtle tonal elevation (`#070b12` -> `#0e1524` -> `#152035`) and crisp hairline borders rather than muddy drop shadows.
- **Status Beacons:** Pinned LED indicator dots with subtle `box-shadow: 0 0 8px [color]` glow to communicate state at a glance across room monitors.

## Shapes
- Compact radiuses (`rounded-md`, 6px) to maximize viewable density.
- Monospaced metric pills with tight pill bounding (`px-2 py-0.5`).

## Components
- **Policy Tier Badges:** Prominent tags indicating `READ`, `SAFE_REVERSIBLE`, `APPROVAL_REQUIRED`, or `HUMAN_ONLY`.
- **Diagnostic Execution Pills:** Clear execution status pills (`Running`, `Success`, `Failed`, `Blocked`).
- **Camera Stream Preview Frames:** CCTV camera viewport cards with timestamp overlay, FPS, resolution, and stream health status.
- **Human-in-the-Loop Action Cards:** Highlighted intervention prompts requiring operator confirmation for physical hardware steps.

## Do's and Don'ts
- **DO** use tabular monospaced numbers for all latency, bitrate, and wattage metrics.
- **DO** maintain at least 4.5:1 text contrast for all labels and statuses.
- **DO** respect `prefers-reduced-motion` for all blinking, spinning, and pulsing indicators.
- **DON'T** use generic purple-to-blue gradient fills.
- **DON'T** use low-contrast washed out gray text on colored badge backgrounds.
- **DON'T** hide critical telemetry behind hover states; make it directly scannable.
