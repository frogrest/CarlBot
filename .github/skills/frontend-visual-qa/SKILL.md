---
name: frontend-visual-qa
description: "Use when validating a frontend against screenshots, visual references, or responsive requirements. Run the app, inspect pages in a browser, exercise real interactions, compare at matching viewports, and fix measurable layout or behavior gaps."
argument-hint: "Name the routes, viewports, and reference screenshots to validate"
user-invocable: true
---

# Screenshot-Grounded Frontend QA

Validate what users actually see and do. A passing build is necessary but does not establish visual or interaction quality.

## Workflow

1. Read the screen/component inventory and map each implemented route to its reference page.
2. Start the existing development/build task using the project's package manager and proxy configuration.
3. Confirm the page loads and record the viewport dimensions and available test data.
4. Inspect each route with browser accessibility/read-page tools first; use screenshots to assess layout, color, density, clipping, and alignment.
5. Compare the implementation and source reference at matching viewport sizes. List concrete discrepancies (for example, header height, column widths, row density, or panel order).
6. Exercise search, filters, navigation, actions, dialogs/forms, loading/empty/error states, keyboard focus, and responsive breakpoints.
7. Inspect browser console/network failures. Requests must stay within approved same-origin proxies; do not invent a successful response when an endpoint is unavailable.
8. Fix the highest-impact discrepancy and repeat the affected checks, then run the build and relevant tests.

## Evidence to report

- Routes/screens inspected and viewport sizes.
- Interactions and states exercised.
- Build/test results and browser errors, if any.
- Remaining visual mismatches or backend limitations.

Never claim pixel fidelity, action success, or backend integration without directly verifying it.
