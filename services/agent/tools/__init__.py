"""Tool layer — narrow, auditable capabilities (AGENTS.md).

The bus wraps the HTTP client; specialists and the orchestrator call the
bus, never raw endpoints. Mutating actions stay sequential and go through
the policy engine first — the bus itself executes only registered safe
simulated actions and rejects anything else.
"""
from .bus import ToolBus

__all__ = ['ToolBus']
