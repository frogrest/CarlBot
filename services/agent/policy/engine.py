"""Deterministic policy engine (Phase 3 extends with full action contracts).

A recommendation is not permission. Only actions with a registered
contract may run, only against simulated state, and only when their
precondition is observed (docs/architecture/SAFETY_POLICY.md).
"""
from __future__ import annotations

from typing import Optional

from ..orchestrator.models import ActionProposal, PolicyDecision


class PolicyEngine:
    # Class B — safe simulated actions with preconditions.
    SAFE_ACTIONS = {'reconnect-rtsp', 'restart-ai-service'}
    PRECONDITIONS = {
        'reconnect-rtsp': 'rtsp_down',
        'restart-ai-service': 'ai_service_down',
    }
    # Class C/D — approval-required or human-only: never autonomous here.
    HUMAN_ONLY = {
        'change-credentials', 'change-network-config', 'change-firewall',
        'firmware-update', 'factory-reset', 'delete-storage', 'physical-repair',
    }

    def decide(self, proposal: ActionProposal, *, fault: Optional[str] = None) -> PolicyDecision:
        name = proposal.name
        if name in self.HUMAN_ONLY:
            return PolicyDecision(
                allowed=False,
                reason=f'{name} is class C/D (approval or human-only)',
                requires_human=True,
            )
        if name not in self.SAFE_ACTIONS:
            return PolicyDecision(
                allowed=False,
                reason=f'unregistered action rejected: {name}',
                requires_human=True,
            )
        required = self.PRECONDITIONS.get(name)
        if required and fault != required:
            return PolicyDecision(
                allowed=False,
                reason=f'precondition not met: {name} requires observed fault {required!r}, got {fault!r}',
                requires_human=False,
            )
        return PolicyDecision(
            allowed=True,
            reason=f'registered safe simulated action, precondition {required!r} observed',
        )
