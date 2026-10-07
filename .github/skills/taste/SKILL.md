---
name: taste
description: "Use when a web design feels generic, visually flat, overdecorated, or lacks a clear art direction. Establish an intentional visual point of view from the product and references, then refine layout, typography, palette, and density with restraint."
argument-hint: "Describe the product, audience, references, and desired feeling"
user-invocable: true
---

# Product Taste and Art Direction

Make the interface feel like it belongs to this product and this audience. Taste is contextual judgment: choose a few coherent signals and remove choices that compete with them.

## Workflow

1. Name the user's job, environment, and emotional need (for example, a calm, reliable service desk during an incident).
2. Study supplied screenshots and existing product conventions. Record what is distinctive and what must stay recognizable.
3. Pick one visual thesis in plain language, such as "compact, dependable operations console with paper-like work surfaces and precise blue links."
4. Choose a restrained palette, typography voice, density, and component shape that reinforce that thesis. Explain intentional departures from a reference.
5. Apply the thesis consistently across navigation, tables, forms, badges, empty/error states, and the copilot.
6. Remove visual noise: redundant labels, competing accent colors, gratuitous cards, unmotivated gradients, placeholder decoration, and inconsistent icon styles.
7. Compare the running result to the reference at the same viewport. Adjust the most visible mismatch first.

## Decision rules

- Specific reference beats fashionable defaults.
- Readability and operational trust beat novelty.
- A single purposeful accent beats a rainbow of competing colors.
- Density should match the user's work: compact data tables can be right for a helpdesk; generous spacing can be right for a review panel.
- Synthetic branding and examples must not imply a real customer or live system.
- Do not mimic a logo or invent customer-facing copy when the repository has not authorized it; use neutral synthetic labels.
- Every visual flourish must improve hierarchy, feedback, or orientation. Otherwise omit it.

## Review prompts

- What makes this screen recognizably part of its product?
- Which area should attract the eye first, and why?
- Does the page feel coherent at a glance and when scanning row by row?
- Is the AI area visibly subordinate to technician judgment and evidence?
- What can be removed without losing clarity or useful personality?
