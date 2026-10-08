"""Ticket-grounded assistant replies with an optional LLM and safe fallback."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)
_SECRET_ASSIGNMENT = re.compile(
    r'(?i)\b(password|passwd|username|user_name|token|secret|api[_-]?key|authorization)\b'
    r'(\s*(?:[:=]|\bis\b)\s*)((?:Bearer\s+)?[^\s,;]+)')
_URL_CREDENTIALS = re.compile(r'(?i)(https?://)([^/@\s:]+):([^/@\s]+)@')
_EMAIL_ADDRESS = re.compile(r'(?i)\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b')
_UNSAFE_ADVICE = re.compile(
    r'(?i)\b(factory\s+reset|firmware|delete|erase|wipe|'
    r'change\s+(?:credentials|password|ip|subnet|gateway|firewall)|'
    r'disable\s+(?:security|firewall)|'
    r'reboot\s+(?:the\s+)?(?:device|camera|nvr|ai\s*box))\b')
_PROMPT_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'prompts', 'chatbot_system.md')


class ChatRecommendation(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    category: Literal['check', 'technician', 'investigate']
    instruction: str = Field(min_length=1, max_length=400)
    ticket_ids: list[str] = Field(min_length=1, max_length=5)


class ChatReply(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    answer: str = Field(min_length=1, max_length=1600)
    recommendations: list[ChatRecommendation] = Field(default_factory=list, max_length=4)
    cited_ticket_ids: list[str] = Field(default_factory=list, max_length=10)


def _redact(value: str) -> str:
    value = _URL_CREDENTIALS.sub(r'\1[REDACTED]@', value)
    value = _SECRET_ASSIGNMENT.sub(r'\1\2[REDACTED]', value)
    return _EMAIL_ADDRESS.sub('[REDACTED_EMAIL]', value)


def _prompt() -> str:
    from pathlib import Path

    path = Path(_PROMPT_PATH).resolve()
    return (
        path.read_text(encoding='utf-8')
        + '\n\nResponse JSON schema:\n'
        + json.dumps(ChatReply.model_json_schema())
    )


def _source_records(result: dict[str, Any], context_ticket_id: int | None) -> list[dict[str, Any]]:
    matches = [
        match for match in result.get('matches', [])
        if match.get('source') == 'live_helpdesk'
    ]
    if context_ticket_id is not None:
        matches = [
            match for match in matches
            if match.get('ticket_id') == str(context_ticket_id)
        ]
    return [
        {
            'ticket_id': str(match.get('ticket_id') or '')[:30],
            'title': _redact(str(match.get('title') or ''))[:300],
            'status': str(match.get('status') or '')[:50],
            'ticket_status': str(match.get('ticket_status') or '')[:20],
            'priority': str(match.get('priority') or '')[:50],
            'site_id': _redact(str(match.get('site_id') or ''))[:100],
            'asset_id': _redact(str(match.get('asset_id') or ''))[:100],
            'details_and_conversation': [
                _redact(str(detail))[:1200]
                for detail in (match.get('details') or [])[:24]
            ],
        }
        for match in matches[:5]
    ]


def _fallback_recommendations(
    result: dict[str, Any],
    context_ticket_id: int | None,
) -> list[dict[str, Any]]:
    sources = _source_records(result, context_ticket_id)
    if not sources:
        return []

    recommendations = []
    for source in sources[:2]:
        ticket_id = source['ticket_id']
        if source['ticket_status'] == 'Closed' or source['status'] in {'closed', 'resolved'}:
            instruction = (
                'Use this as historical context only; compare it with current observations before reusing its resolution.'
            )
            category = 'check'
        elif source['ticket_status'] == 'Answered' or source['status'] == 'pending_technician':
            instruction = (
                'Review the recorded technician notes and complete the requested human checks; re-verify before resolving.'
            )
            category = 'technician'
        else:
            instruction = (
                'Open the ticket and run the agent investigation to collect fresh evidence; any safe simulated action remains policy-gated.'
            )
            category = 'investigate'
        recommendations.append({
            'category': category,
            'instruction': instruction,
            'ticket_ids': [ticket_id],
        })
    return recommendations


def _deterministic_reply(
    result: dict[str, Any],
    context_ticket_id: int | None,
) -> ChatReply:
    sources = _source_records(result, context_ticket_id)
    live_ids = [source['ticket_id'] for source in sources]
    cited = [
        match['ticket_id']
        for match in result.get('matches', [])
        if match.get('source') == 'live_helpdesk'
        and match.get('ticket_id') in live_ids
    ]
    return ChatReply(
        answer=result['answer'],
        recommendations=_fallback_recommendations(result, context_ticket_id),
        cited_ticket_ids=cited[:10],
    )


def _validate_reply(reply: ChatReply, allowed_ids: set[str]) -> ChatReply:
    citations = set(reply.cited_ticket_ids)
    if allowed_ids and not citations:
        raise ValueError('assistant did not cite any of the supplied ticket evidence')
    if not citations.issubset(allowed_ids):
        raise ValueError('assistant cited ticket records outside the retrieved evidence')
    if any(not set(item.ticket_ids).issubset(allowed_ids) for item in reply.recommendations):
        raise ValueError('assistant recommendation cites a ticket outside retrieved evidence')
    generated_text = ' '.join(
        [reply.answer, *(item.instruction for item in reply.recommendations)]
    )
    if _UNSAFE_ADVICE.search(generated_text):
        raise ValueError('assistant proposed a restricted or destructive procedure')
    return reply


def _ask_model(
    message: str,
    sources: list[dict[str, Any]],
    *,
    client: httpx.Client,
) -> ChatReply:
    base_url = os.getenv('LLM_BASE_URL', '').strip().rstrip('/')
    model = os.getenv('LLM_MODEL', '').strip()
    if not base_url or not model:
        raise RuntimeError('LLM_BASE_URL and LLM_MODEL are not configured')

    headers = {'Content-Type': 'application/json'}
    api_key = os.getenv('LLM_API_KEY')
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    try:
        system_prompt = _prompt()
        response = client.post(
            f'{base_url}/chat/completions',
            headers=headers,
            json={
                'model': model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': json.dumps({
                        'question': _redact(message)[:500],
                        'ticket_records': sources,
                    }, ensure_ascii=True, separators=(',', ':'))},
                ],
                'response_format': {'type': 'json_object'},
                'temperature': 0,
            },
        )
        response.raise_for_status()
    except (httpx.HTTPError, OSError) as exc:
        raise RuntimeError('LLM chat request or prompt loading failed') from exc

    try:
        payload = response.json()
        content = payload['choices'][0]['message']['content']
        if not isinstance(content, str):
            raise TypeError('model content is not text')
        return ChatReply.model_validate_json(content)
    except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
        raise RuntimeError('LLM chat returned malformed or invalid output') from exc


def answer_with_reasoning(
    message: str,
    result: dict[str, Any],
    *,
    context_ticket_id: int | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Return grounded advice; never execute a model recommendation."""
    base_url = os.getenv('LLM_BASE_URL', '').strip()
    model = os.getenv('LLM_MODEL', '').strip()
    reasoning_mode: Literal['llm', 'deterministic'] = 'deterministic'
    reply = _deterministic_reply(result, context_ticket_id)
    sources = _source_records(result, context_ticket_id)

    if base_url and model and sources:
        owns_client = client is None
        model_client = client or httpx.Client(timeout=20.0)
        try:
            candidate = _ask_model(message, sources, client=model_client)
            reply = _validate_reply(
                candidate,
                {source['ticket_id'] for source in sources},
            )
            reasoning_mode = 'llm'
        except (RuntimeError, ValueError) as exc:
            logger.warning(
                'LLM ticket chat unavailable or rejected (%s); using grounded fallback',
                exc,
            )
        finally:
            if owns_client:
                model_client.close()

    answer = reply.answer
    if (
        result.get('reference_export_configured')
        and result.get('reference_export_available') is False
    ):
        answer += ' The reference export is not mounted; this response searched live helpdesk records only.'
    return {
        **result,
        'answer': answer,
        'recommendations': [item.model_dump() for item in reply.recommendations],
        'cited_ticket_ids': reply.cited_ticket_ids,
        'reasoning_mode': reasoning_mode,
    }
