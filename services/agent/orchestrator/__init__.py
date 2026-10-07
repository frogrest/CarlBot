"""Orchestrator layer — the deterministic supervisor (AGENTS.md).

Reasoner proposes, orchestrator routes and supervises, policy permits,
tools act. The orchestrator never grants itself permission.
"""
from .budgets import Budget, BudgetExhausted
from .engine import Orchestrator
from .models import (ActionProposal, Evidence, EvidenceType, Handoff,
                     IncidentContext, IncidentState, PolicyDecision,
                     SpecialistFinding, VerificationResult)
from .router import derive_signals, route
from .state import (SUPPRESS_STATES, IllegalTransition, IncidentStore,
                    StateMachine, can_transition)

__all__ = [
    'Budget', 'BudgetExhausted', 'Orchestrator', 'ActionProposal',
    'Evidence', 'EvidenceType', 'Handoff', 'IncidentContext',
    'IncidentState', 'PolicyDecision', 'SpecialistFinding',
    'VerificationResult', 'derive_signals', 'route', 'SUPPRESS_STATES',
    'IllegalTransition', 'IncidentStore', 'StateMachine',
    'can_transition',
]
