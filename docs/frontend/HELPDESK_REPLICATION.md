# Helpdesk Frontend Replication Specification

## Objective

Recreate the visual language and workflow of the supplied helpdesk screenshots in a safe synthetic replica.

The screenshots in `reference/screenshots/` are visual references only. The replica must use synthetic data and must not connect to a production helpdesk.

## Critical instruction

Do not invent an unrelated generic admin dashboard.

The frontend coding agent must inspect the supplied screenshots before coding and reproduce their visual language and information hierarchy.

## Replication process

### 1. Inventory screenshots

Identify:

- navigation structure
- sidebar hierarchy
- typography and font weights
- spacing rhythm
- colors/surfaces
- row heights
- status indicators
- iconography
- search/filter controls
- table/list patterns
- detail panels
- device/camera tree structure

### 2. Build design tokens

Create reusable variables/components for:

- typography
- spacing
- radius
- borders
- surfaces
- status colors
- icon sizing

### 3. Build reusable components

At minimum:

- AppShell
- Sidebar
- Header
- SearchBar
- FilterBar
- TicketList
- TicketRow
- TicketDetail
- StatusBadge
- AssetTree
- CameraRow
- AIInsightPanel
- EvidenceCard
- SuggestedActionCard
- TechnicianHandoffCard
- ChatPanel
- ChatComposer

### 4. Synthetic data

Use fake:

- ticket IDs
- site names
- camera names
- IP addresses
- timestamps
- technician names

Never embed credentials or production tokens.

## Ticket page target

```text
Ticket Header
├── ID
├── status
├── priority
├── site/property
└── affected asset

Problem / conversation

Diagnostics
├── timeline
├── tests
├── results
└── evidence

AI Copilot
├── current summary
├── diagnosis
├── confidence
├── evidence sources
├── suggested next action
└── technician handoff
```

## Responsive behavior

Desktop is the primary target because the workflow is desktop-oriented. Support smaller widths without destroying ticket readability.

## Visual validation

After each major section, compare the implementation to the reference screenshots and correct the layout/visual discrepancies before proceeding.

The goal is structural and visual fidelity for a synthetic replica, not a connection to the real application.
