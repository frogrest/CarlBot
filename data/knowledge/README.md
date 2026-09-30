# Knowledge Base

Place user-provided authoritative troubleshooting documents here as **Markdown** (`.md`) or **plain text** (`.txt`) files.

The current retrieval layer uses simple keyword matching. It is deterministic and designed to be replaced by an embedding/vector-search backend later while keeping the same interface.

## Included Documents

- `troubleshooting.md` — Comprehensive CCTV fault diagnosis knowledge
- `equipment_reference.md` — Simulated site/asset/credential reference

## Adding Your Own

1. Create a `.md` or `.txt` file in this directory (subdirectories work too).
2. Write troubleshooting knowledge in plain language.
3. The agent will automatically search your documents during investigation.

## Safety

> ⚠️ Do **NOT** place real customer credentials, production secrets, or sensitive operational data in this lab.
> All data in this directory is simulated.
