---
name: impeccable
description: "Use when designing, implementing, or polishing a web interface and the user asks for impeccable, production-ready, pixel-conscious, high-quality UI. Improve hierarchy, typography, spacing, contrast, states, accessibility, and finish without abandoning product context."
argument-hint: "Describe the screen or interface to refine"
user-invocable: true
---

# Impeccable Interface Craft

Turn a functional UI into a coherent, finished product interface. Quality means correct hierarchy and interaction details, not decorative effects.

## Workflow

1. Read the product brief, existing UI, design references, and repository-specific safety constraints before choosing a visual direction.
2. Identify the primary user task and make its entry point, current state, and next action unmistakable.
3. Define a small system of type roles, spacing, surfaces, borders, status colors, and focus states. Reuse tokens instead of accumulating one-off values.
4. Build the information architecture first. Keep supporting detail subordinate, but never hide evidence, uncertainty, error states, or consequential controls.
5. Implement loading, empty, error, success, disabled, selected, hover, keyboard-focus, and narrow-viewport states for each important interaction.
6. Test the real workflow, not just the default screenshot. Check tab order, labels, contrast, truncation, long content, and status changes.
7. Run the project build/tests and inspect the running UI at the target viewport. Refine visible defects before declaring it done.

## Quality bar

- Preserve the application's domain and reference hierarchy; do not replace a specific product with a generic dashboard.
- Favor deliberate alignment, readable line lengths, stable table columns, restrained borders and consistent component density.
- Use color semantically and redundantly (label/icon/text as well as color); never rely on color alone.
- Make interactive elements look and behave interactively. Provide visible focus and meaningful accessible names.
- Keep motion subtle, purposeful, and optional under `prefers-reduced-motion`.
- Treat failure and uncertainty as first-class states; never style an unverified outcome as success.
- Avoid ornamental gradients, glass panels, excessive roundness, gratuitous animation, oversized empty heroes, and random iconography unless the reference or product explicitly calls for them.

## Finish checklist

- Is the main task obvious within a few seconds?
- Does each region have a clear visual priority?
- Are spacing, typography, control sizes, borders, and states consistent?
- Can users distinguish observed evidence from inference and action request from verified outcome?
- Does the interface remain usable with keyboard, long text, errors, and smaller screens?
- Did browser inspection confirm the rendered result, not just a successful compile?
