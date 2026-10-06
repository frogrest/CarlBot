# Frontend AI Coding Agent Prompt

Build the frontend as a faithful synthetic replica of the supplied helpdesk screenshots and integrate the AI copilot into that workflow.

Before writing UI code:

1. Inspect every page of `reference/screenshots/reference.pdf` (6 pages of helpdesk UI screenshots).
2. Identify layout, navigation, typography, spacing, colors, icons, tables/lists, and asset hierarchy.
3. Create a written component inventory.
4. Build the static replica using synthetic data.
5. Add live integration to the fake APIs.
6. Add AI diagnostic panels.
7. Add chatbot and `/clear`.

Use React + Vite + TypeScript unless the existing project already has a better-supported frontend stack.

Do not build a generic dashboard and call it a replica.

The UI should make the AI part of the technician workflow:

- investigation status
- findings
- evidence
- confidence
- recommended next action
- safe-action state
- technician handoff
- verification state

The backend—not the UI—is the policy boundary.
