"""Orchestrator data contracts.

Mirrors docs/architecture/ARCHITECTURE.md (specialist result schema),
docs/architecture/ORCHESTRATOR.md (state machine + handoff elements) and
prompts/specialist_common.md (evidence labels + confidence scale).
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .budgets import Budget


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class IncidentState(str, Enum):
    """Lifecycle states (ORCHESTRATOR.md 'State machine')."""

    NEW = 'new'
    CLASSIFYING = 'classifying'
    INVESTIGATING = 'investigating'
    EVIDENCE_REVIEW = 'evidence_review'
    DIAGNOSED = 'diagnosed'
    ACTION_PROPOSED = 'action_proposed'
    SAFE_EXECUTION = 'safe_execution'
    VERIFYING = 'verifying'
    HUMAN_REQUIRED = 'human_required'
    PENDING_TECHNICIAN = 'pending_technician'
    READY_FOR_VERIFICATION = 'ready_for_verification'
    RESOLVED = 'resolved'


class EvidenceType(str, Enum):
    OBSERVED = 'observed'
    RETRIEVED = 'retrieved'
    INFERRED = 'inferred'


class Evidence(BaseModel):
    id: str
    type: EvidenceType = EvidenceType.OBSERVED
    source: str = ''
    claim: str


class SpecialistFinding(BaseModel):
    """Structured result per ARCHITECTURE.md / prompts/specialist_common.md."""

    agent: str
    status: str = 'complete'  # complete | partial | blocked
    facts: List[str] = Field(default_factory=list)
    hypotheses: List[str] = Field(default_factory=list)
    tests_performed: List[str] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    confidence: float = 0.0
    recommendations: List[str] = Field(default_factory=list)
    requires_human: bool = False
    handoff_reason: Optional[str] = None


class Handoff(BaseModel):
    """The 7-element technician handoff (ORCHESTRATOR.md 'Human handoff')."""

    observed_facts: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    diagnosis: str = ''
    confidence: float = 0.0
    uncertainty: str = ''
    requested_action: str = ''
    why_stopped: str = ''
    unverifiable: List[str] = Field(default_factory=list)
    verification_steps: List[str] = Field(default_factory=list)


class ActionProposal(BaseModel):
    name: str
    asset_id: str
    reason: str
    evidence_ids: List[str] = Field(default_factory=list)


class PolicyDecision(BaseModel):
    allowed: bool
    reason: str
    requires_human: bool = False


class VerificationResult(BaseModel):
    performed: bool = False
    passed: bool = False
    detail: str = ''


class IncidentContext(BaseModel):
    incident_id: str
    ticket_id: int
    asset_id: str = ''
    site_id: str = ''
    symptom: str = ''
    state: IncidentState = IncidentState.NEW
    fault: Optional[str] = None
    observations: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[Evidence] = Field(default_factory=list)
    findings: List[SpecialistFinding] = Field(default_factory=list)
    route: List[Dict[str, str]] = Field(default_factory=list)
    diagnosis: Optional[str] = None
    confidence: float = 0.0
    proposed_action: Optional[ActionProposal] = None
    executed_actions: List[str] = Field(default_factory=list)
    verification: Optional[VerificationResult] = None
    handoff: Optional[Handoff] = None
    budget: Budget = Field(default_factory=Budget)
    notes: List[str] = Field(default_factory=list)
    active: bool = True
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)

    def add_evidence(self, claim: str, *, etype: EvidenceType = EvidenceType.OBSERVED,
                     source: str = 'tool') -> Evidence:
        item = Evidence(id=f'E{len(self.evidence) + 1}', type=etype, source=source, claim=claim)
        self.evidence.append(item)
        return item
