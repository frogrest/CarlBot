"""Shared reasoner contract and expected adapter failures."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from .schemas import Plan

if TYPE_CHECKING:
    from ..orchestrator.models import IncidentContext


class ReasoningError(Exception):
    """A model response or request could not produce a trusted plan."""


class Reasoner(Protocol):
    def propose(self, ctx: IncidentContext) -> Plan:
        """Propose a structured plan; this never grants execution permission."""

    def close(self) -> None:
        """Release adapter resources."""
