"""OpenAI-compatible HTTP adapter with a deterministic fallback."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import ValidationError

from services.local_llm.client import resolve_endpoint

from .base import Reasoner, ReasoningError
from .deterministic import DeterministicReasoner
from .schemas import Plan

if TYPE_CHECKING:
    from services.local_llm.runtime import LocalLlmRuntime

    from ..orchestrator.models import IncidentContext

logger = logging.getLogger(__name__)
_PROMPT_ROOT = Path(__file__).resolve().parents[3] / 'prompts'
_SECRET_ASSIGNMENT = re.compile(
    r'(?i)\b(password|passwd|token|secret|api[_-]?key|authorization)\b'
    r'(\s*[:=]\s*)((?:Bearer\s+)?[^\s,;]+)')
_URL_CREDENTIALS = re.compile(r'(?i)(https?://)([^/@\s:]+):([^/@\s]+)@')


def _redact(value: str) -> str:
    value = _URL_CREDENTIALS.sub(r'\1[REDACTED]@', value)
    return _SECRET_ASSIGNMENT.sub(r'\1\2[REDACTED]', value)


def _validate_plan_context(plan: Plan, ctx: IncidentContext) -> None:
    if plan.action is None:
        return
    if plan.action.asset_id != ctx.asset_id:
        raise ReasoningError('action proposal targets an asset outside this incident')
    evidence_ids = {item.id for item in ctx.evidence}
    evidence_ids.update(
        f'{finding.agent}:{item.id}'
        for finding in ctx.findings
        for item in finding.evidence
    )
    if not set(plan.action.evidence_ids).issubset(evidence_ids):
        raise ReasoningError('action proposal cites evidence outside this incident')


class LLMReasoner:
    """Call a configured chat-completions endpoint; it cannot call tools."""

    def __init__(self, base_url: str, model: str, *,
                 client: httpx.Client | None = None,
                 prompt_root: Path = _PROMPT_ROOT):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.api_key = os.getenv('LLM_API_KEY') or None
        self.client = client or httpx.Client(timeout=20.0)
        self._owns_client = client is None
        self.prompt_root = prompt_root

    @classmethod
    def from_env(cls, *, client: httpx.Client | None = None) -> LLMReasoner:
        base_url = os.getenv('LLM_BASE_URL', '').strip()
        model = os.getenv('LLM_MODEL', '').strip()
        if not base_url or not model:
            raise ReasoningError('LLM_BASE_URL and LLM_MODEL are required')
        return cls(base_url, model, client=client)

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def _system_prompt(self) -> str:
        try:
            orchestrator = (self.prompt_root / 'orchestrator_system.md').read_text(
                encoding='utf-8')
            common = (self.prompt_root / 'specialist_common.md').read_text(
                encoding='utf-8')
        except OSError as exc:
            raise ReasoningError('version-controlled reasoning prompts are unavailable') from exc
        return (
            f'{orchestrator}\n\n{common}\n\n'
            'Adapter response contract: return exactly one JSON object matching the '
            'Plan schema below. This contract replaces the example output shapes above. '
            'Do not call tools or invent evidence. Propose only registered actions. '
            'The deterministic policy engine independently decides whether any '
            'proposed action may execute.\n\n'
            f'Plan JSON schema:\n{json.dumps(Plan.model_json_schema())}'
        )

    @staticmethod
    def _incident_payload(ctx: IncidentContext) -> str:
        raw_evidence = [
            (item.id, item)
            for item in ctx.evidence
        ]
        raw_evidence.extend(
            (f'{finding.agent}:{item.id}', item)
            for finding in ctx.findings
            for item in finding.evidence
        )
        evidence = [
            {
                'id': evidence_id,
                'type': item.type.value,
                'source': _redact(item.source)[:300],
                'claim': _redact(item.claim)[:1000],
            }
            for evidence_id, item in raw_evidence[:50]
        ]
        incident: dict[str, Any] = {
            'incident_id': _redact(ctx.incident_id)[:200],
            'ticket_id': ctx.ticket_id,
            'asset_id': _redact(ctx.asset_id)[:200],
            'site_id': _redact(ctx.site_id)[:200],
            'symptom': _redact(ctx.symptom)[:2000],
            'fault': _redact(ctx.fault or '')[:200],
        }
        return json.dumps(
            {'incident': incident, 'evidence': evidence},
            ensure_ascii=True,
            separators=(',', ':'),
        )

    def propose(self, ctx: IncidentContext) -> Plan:
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        try:
            response = self.client.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json={
                    'model': self.model,
                    'messages': [
                        {'role': 'system', 'content': self._system_prompt()},
                        {'role': 'user', 'content': self._incident_payload(ctx)},
                    ],
                    'response_format': {'type': 'json_object'},
                    'temperature': 0,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ReasoningError('LLM service request failed') from exc

        try:
            payload = response.json()
            content = payload['choices'][0]['message']['content']
            if not isinstance(content, str):
                raise TypeError('model content is not text')
            plan = Plan.model_validate_json(content)
        except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
            raise ReasoningError('LLM returned malformed or invalid plan output') from exc

        _validate_plan_context(plan, ctx)
        return plan


class FallbackReasoner:
    def __init__(self, primary: Reasoner,
                 fallback: Reasoner | None = None):
        self.primary = primary
        self.fallback = fallback or DeterministicReasoner()

    def propose(self, ctx: IncidentContext) -> Plan:
        try:
            plan = self.primary.propose(ctx)
            _validate_plan_context(plan, ctx)
            return plan
        except ReasoningError as exc:
            logger.warning(
                'LLM reasoning rejected (%s); using deterministic reasoning',
                str(exc),
            )
            return self.fallback.propose(ctx)

    def close(self) -> None:
        self.primary.close()
        self.fallback.close()


def configured_reasoner(runtime: 'LocalLlmRuntime | None' = None) -> Reasoner:
    """Pick the reasoner: ready local runtime, external endpoint, or deterministic."""
    base_url, model = resolve_endpoint(runtime=runtime)
    if not base_url and not model:
        return DeterministicReasoner()
    if not base_url or not model:
        logger.warning(
            'LLM reasoning disabled: both a base URL and model are required')
        return DeterministicReasoner()
    return FallbackReasoner(LLMReasoner(base_url, model))
