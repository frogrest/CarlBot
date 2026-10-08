"""Strict structured output contracts for reasoning adapters."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ActionProposal(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    name: Literal['reconnect-rtsp', 'restart-ai-service']
    asset_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)


class Plan(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    diagnosis: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    action: ActionProposal | None = None
    requires_human: bool
    requested_action: str = ''
    why_stopped: str = ''
    unverifiable: list[str] = Field(default_factory=list)
    uncertainty: str = ''

    @model_validator(mode='after')
    def validate_decision_shape(self) -> Plan:
        if self.action is not None:
            if self.requires_human or self.requested_action or self.why_stopped:
                raise ValueError('an action plan cannot also request a human handoff')
        elif not self.requires_human or not self.requested_action or not self.why_stopped:
            raise ValueError('a non-action plan must include a human handoff')
        return self
