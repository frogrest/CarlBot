"""Shared Pydantic models and enums used across all services."""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SafetyClass(str, Enum):
    """Action safety classification — enforced by the policy engine."""
    READ = "READ"
    SAFE_REVERSIBLE = "SAFE_REVERSIBLE"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    HUMAN_ONLY = "HUMAN_ONLY"


class TicketStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    PENDING_TECHNICIAN = "pending_technician"
    PENDING_APPROVAL = "pending_approval"
    RESOLVED = "resolved"
    CLOSED = "closed"


class AssetKind(str, Enum):
    CAMERA = "camera"
    NVR = "nvr"
    AI_BOX = "ai_box"


# ---------------------------------------------------------------------------
# Helpdesk models
# ---------------------------------------------------------------------------

class Comment(BaseModel):
    author: str
    body: str
    at: str = ""


class Ticket(BaseModel):
    id: str = ""
    title: str
    description: str
    status: str = TicketStatus.OPEN.value
    site_id: str = ""
    asset_id: str | None = None
    root_cause: str | None = None
    resolution: str | None = None
    created_at: str = ""
    updated_at: str = ""
    comments: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    technician_notes: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Portal models
# ---------------------------------------------------------------------------

class Asset(BaseModel):
    id: str
    site_id: str
    name: str
    kind: str  # camera | nvr | ai_box
    ip: str
    state: dict[str, Any] = Field(default_factory=dict)


class FaultSpec(BaseModel):
    fault: str


class ActionSpec(BaseModel):
    action: str


# ---------------------------------------------------------------------------
# Agent models
# ---------------------------------------------------------------------------

class Finding(BaseModel):
    """A single piece of evidence or observation."""
    category: str  # observed_fact | historical | documentation | hypothesis
    statement: str
    evidence: list[str] = Field(default_factory=list)


class Diagnosis(BaseModel):
    """Structured diagnosis produced by the agent."""
    fault: str
    confidence: float
    observed_facts: list[str] = Field(default_factory=list)
    historical_evidence: list[str] = Field(default_factory=list)
    documentation_hits: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    safety_class: SafetyClass = SafetyClass.HUMAN_ONLY
    performed_actions: list[str] = Field(default_factory=list)
    verification: str = "pending"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()
