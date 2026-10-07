"""Investigation budgets (ORCHESTRATOR.md 'Budgets').

When a budget is exhausted the orchestrator must stop and hand off
instead of looping.
"""
from __future__ import annotations

import time
from typing import Optional

from pydantic import BaseModel, Field


class BudgetExhausted(Exception):
    """Raised internally when a stage cannot spend any more budget."""


class Budget(BaseModel):
    max_tool_calls: int = 24
    max_specialist_calls: int = 8
    max_autonomous_actions: int = 2
    max_retries: int = 2
    max_wall_seconds: float = 120.0

    tool_calls: int = 0
    specialist_calls: int = 0
    autonomous_actions: int = 0
    retries: int = 0
    started_monotonic: float = Field(default_factory=time.monotonic, exclude=True)

    def charge_tool(self, n: int = 1) -> None:
        self.tool_calls += n

    def charge_specialist(self, n: int = 1) -> None:
        self.specialist_calls += n

    def charge_action(self, n: int = 1) -> None:
        self.autonomous_actions += n

    def charge_retry(self, n: int = 1) -> None:
        self.retries += n

    def exhausted_reason(self) -> Optional[str]:
        if self.tool_calls >= self.max_tool_calls:
            return 'tool budget exhausted'
        if self.specialist_calls >= self.max_specialist_calls:
            return 'specialist budget exhausted'
        if self.autonomous_actions >= self.max_autonomous_actions:
            return 'autonomous action budget exhausted'
        if time.monotonic() - self.started_monotonic > self.max_wall_seconds:
            return 'wall-clock budget exhausted'
        if self.retries > self.max_retries:
            return 'retry budget exhausted'
        return None

    def usage(self) -> dict:
        return {
            'tool_calls': self.tool_calls,
            'specialist_calls': self.specialist_calls,
            'autonomous_actions': self.autonomous_actions,
            'retries': self.retries,
        }
