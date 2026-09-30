"""Provider-neutral LLM reasoning boundary.

The deterministic agent works without any LLM. This module defines the
contract that a future model adapter must implement to add LLM-powered
reasoning. Tool intents produced by the model are proposals only — they
must pass through the policy engine before execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SYSTEM_PROMPT = """
You are a technical-support reasoning component inside a safety-controlled
CCTV / AI-Box / NVR lab environment.

RULES:
1. Use ONLY the supplied observations, retrieved historical evidence, and
   supplied documentation to form hypotheses.
2. Strictly separate:  observed facts · historical evidence · hypotheses ·
   confidence · recommended action · actions actually performed.
3. NEVER invent tool results, device state, or claim an action succeeded
   without verification data.
4. Request human action for: credentials, network/configuration changes,
   consequential reboots, firmware, physical repairs.
5. Your tool_intents are PROPOSALS — the independent policy engine decides
   whether each is allowed. You may not bypass it.
6. Output valid JSON matching the ReasoningResponse schema.
""".strip()


@dataclass
class ReasoningRequest:
    """Input to the reasoning provider."""
    asset_id: str = ""
    asset_kind: str = ""
    observations: list[dict[str, Any]] = field(default_factory=list)
    historical_evidence: list[dict[str, Any]] = field(default_factory=list)
    knowledge: list[dict[str, Any]] = field(default_factory=list)
    active_faults: list[str] = field(default_factory=list)


@dataclass
class ReasoningResponse:
    """Output from the reasoning provider."""
    hypotheses: list[dict[str, Any]] = field(default_factory=list)
    tool_intents: list[dict[str, Any]] = field(default_factory=list)
    recommended_action: str = ""
    confidence: float = 0.0
    safety_class: str = "HUMAN_ONLY"


class ReasoningProvider:
    """Base class for LLM reasoning adapters.

    Subclass this and implement `reason()` to connect a model provider.
    The runtime will validate the response and check every tool_intent
    against the policy engine before execution.
    """

    def reason(self, request: ReasoningRequest) -> ReasoningResponse:
        raise NotImplementedError(
            "Connect a model provider here. "
            "Keep tool execution behind policy.py."
        )

    @staticmethod
    def system_prompt() -> str:
        return SYSTEM_PROMPT
