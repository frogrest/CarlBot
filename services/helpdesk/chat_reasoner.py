"""Ticket-grounded assistant replies with an optional LLM and safe fallback."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import TYPE_CHECKING, Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from services.local_llm.client import resolve_endpoint

if TYPE_CHECKING:
    from services.local_llm.runtime import LocalLlmRuntime

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
_REPLY_INTENT = re.compile(
    r'(?i)\b(draft|write|compose|prepare|send|post|create|generate|suggest|provide|make|give)\b.*?\b(reply|response|customer|message|email)\b'
    r'|\b(reply|respond)\b.*?\b(to\s+(?:the\s+)?customer|to\s+(?:the\s+)?ticket|customer)?\b'
    r'|^\s*(?:can\s+you\s+)?(?:draft\s+)?reply[\s?.!]*$'
)
_PROMPT_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'prompts', 'chatbot_system.md')


class ChatRecommendation(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    category: Literal['check', 'technician', 'investigate']
    instruction: str = Field(min_length=1, max_length=400)
    ticket_ids: list[str] = Field(min_length=1, max_length=5)


class ChatReply(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    answer: str = Field(min_length=1, max_length=4000)
    recommendations: list[ChatRecommendation] = Field(default_factory=list, max_length=4)
    cited_ticket_ids: list[str] = Field(default_factory=list, max_length=10)
    cited_knowledge_sources: list[str] = Field(default_factory=list, max_length=4)
    ticket_reply_draft: str | None = Field(default=None, max_length=1200)


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
    message: str,
    result: dict[str, Any],
    context_ticket_id: int | None,
    knowledge_sources: list[dict[str, Any]],
) -> ChatReply:
    sources = _source_records(result, context_ticket_id)
    live_ids = [source['ticket_id'] for source in sources]
    intent = result.get('intent')
    is_conversational = bool(result.get('is_conversational'))

    if is_conversational and intent in {'greeting', 'off_topic'}:
        cited = []
        cited_docs: list[str] = []
    else:
        cited = [
            match['ticket_id']
            for match in result.get('matches', [])
            if match.get('source') == 'live_helpdesk'
            and match.get('ticket_id') in live_ids
        ]
        cited_docs = [
            f"{doc['source_path']} ({doc['locator']})"
            for doc in knowledge_sources[:3]
        ]

    # Generate reply draft if explicitly requested and a ticket is selected
    ticket_reply_draft: str | None = None
    if context_ticket_id is not None and _REPLY_INTENT.search(message):
        # Build safe deterministic customer reply draft
        ticket_source = next((s for s in sources if s['ticket_id'] == str(context_ticket_id)), None)
        if ticket_source:
            ticket_title = ticket_source.get('title', f'Ticket #{context_ticket_id}')
            ticket_status = ticket_source.get('ticket_status', 'Open')
            if ticket_status == 'Closed':
                ticket_reply_draft = (
                    f"Hello, this is an update regarding {ticket_title}. "
                    "Our records show that this issue was previously addressed. "
                    "If you are continuing to experience difficulties, please let us know so a technician can investigate further."
                )
            elif ticket_status == 'Answered' or ticket_source.get('status') == 'pending_technician':
                ticket_reply_draft = (
                    f"Hello, this is an update regarding {ticket_title}. "
                    "A technician has reviewed your report and is currently working on the necessary verification steps. "
                    "We will provide a further update once our on-site checks are complete."
                )
            else:
                ticket_reply_draft = (
                    f"Hello, thank you for contacting technical support regarding {ticket_title}. "
                    "We have received your report and our operations team has initiated an investigation. "
                    "We will update you as soon as further information is available."
                )

    answer = result.get('answer', '')
    if cited_docs and not any(doc.split()[0] in answer for doc in cited_docs):
        if len(result.get('matches', [])) <= 1:
            doc_bullets = [
                f"• *{doc['section_title']}* (`{doc['source_path']}`)"
                for doc in knowledge_sources[:2]
            ]
            if doc_bullets:
                answer = f"{answer}\n\n**Approved SOP & Technical References:**\n" + "\n".join(doc_bullets)

    recommendations = []
    if not (is_conversational and intent in {'greeting', 'off_topic'}):
        recommendations = _fallback_recommendations(result, context_ticket_id)

    return ChatReply(
        answer=answer,
        recommendations=recommendations,
        cited_ticket_ids=cited[:10],
        cited_knowledge_sources=cited_docs[:4],
        ticket_reply_draft=ticket_reply_draft,
    )


def _validate_reply(
    reply: ChatReply,
    allowed_ids: set[str],
    allowed_doc_paths: set[str],
    context_ticket_id: int | None,
    *,
    is_conversational: bool = False,
) -> ChatReply:
    citations = set(reply.cited_ticket_ids)
    if not is_conversational:
        if allowed_ids and not citations:
            raise ValueError('assistant did not cite any of the supplied ticket evidence')
    if not citations.issubset(allowed_ids):
        raise ValueError('assistant cited ticket records outside the retrieved evidence')
    if any(not set(item.ticket_ids).issubset(allowed_ids) for item in reply.recommendations if allowed_ids):
        raise ValueError('assistant recommendation cites a ticket outside retrieved evidence')

    # Validate knowledge citations
    for cited_doc in reply.cited_knowledge_sources:
        # Extract base path before any locator
        base_path = cited_doc.split()[0]
        if base_path not in allowed_doc_paths:
            raise ValueError(f'assistant cited an unapproved or unknown document: {cited_doc}')

    # Validate ticket reply draft: never permit draft without valid selected ticket
    if reply.ticket_reply_draft is not None:
        if context_ticket_id is None:
            raise ValueError('ticket_reply_draft generated without a selected ticket context')
        if not reply.ticket_reply_draft.strip():
            reply.ticket_reply_draft = None

    generated_text = ' '.join(
        [
            reply.answer,
            *(item.instruction for item in reply.recommendations),
            reply.ticket_reply_draft or '',
        ]
    )
    if _UNSAFE_ADVICE.search(generated_text):
        raise ValueError('assistant proposed a restricted or destructive procedure')
    return reply


def _ask_model(
    message: str,
    sources: list[dict[str, Any]],
    conversation_history: list[dict[str, str]],
    knowledge_sources: list[dict[str, Any]],
    context_ticket_id: int | None,
    *,
    base_url: str,
    model: str,
    client: httpx.Client,
) -> ChatReply:
    if not base_url or not model:
        raise RuntimeError('no LLM endpoint is configured for ticket chat')

    headers = {'Content-Type': 'application/json'}
    api_key = os.getenv('LLM_API_KEY')
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    bounded_history = [
        {
            'role': turn['role'],
            'content': _redact(turn['content'])[:500],
        }
        for turn in conversation_history[-6:]
        if turn.get('role') in {'user', 'assistant'} and turn.get('content')
    ]

    bounded_knowledge = [
        {
            'source_path': doc['source_path'],
            'section_title': doc['section_title'],
            'locator': doc['locator'],
            'excerpt': _redact(doc['excerpt'])[:450],
        }
        for doc in knowledge_sources[:3]
    ]

    try:
        system_prompt = _prompt()
        user_payload = {
            'question': _redact(message)[:500],
            'selected_ticket_id': context_ticket_id,
            'recent_conversation': bounded_history,
            'ticket_records': sources,
            'approved_knowledge_documents': bounded_knowledge,
        }
        response = client.post(
            f'{base_url}/chat/completions',
            headers=headers,
            json={
                'model': model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': json.dumps(user_payload, ensure_ascii=True, separators=(',', ':'))},
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
    conversation_history: list[dict[str, str]] | None = None,
    knowledge_sources: list[dict[str, Any]] | None = None,
    client: httpx.Client | None = None,
    runtime: 'LocalLlmRuntime | None' = None,
) -> dict[str, Any]:
    """Return grounded advice; never execute a model recommendation."""
    history = conversation_history or []
    k_sources = knowledge_sources or []
    base_url, model = resolve_endpoint(runtime=runtime)
    reasoning_mode: Literal['llm', 'deterministic'] = 'deterministic'
    reply = _deterministic_reply(message, result, context_ticket_id, k_sources)
    sources = _source_records(result, context_ticket_id)
    is_conversational = bool(result.get('is_conversational'))

    allowed_doc_paths = {doc['source_path'] for doc in k_sources}

    if base_url and model and (sources or is_conversational):
        owns_client = client is None
        model_client = client or httpx.Client(timeout=20.0)
        try:
            candidate = _ask_model(
                message,
                sources,
                history,
                k_sources,
                context_ticket_id,
                base_url=base_url,
                model=model,
                client=model_client,
            )
            reply = _validate_reply(
                candidate,
                {source['ticket_id'] for source in sources},
                allowed_doc_paths,
                context_ticket_id,
                is_conversational=is_conversational,
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
        not is_conversational
        and result.get('reference_export_configured')
        and result.get('reference_export_available') is False
    ):
        answer += ' The reference export is not mounted; this response searched live helpdesk records only.'

    return {
        **result,
        'answer': answer,
        'recommendations': [item.model_dump() for item in reply.recommendations],
        'cited_ticket_ids': reply.cited_ticket_ids,
        'cited_knowledge_sources': reply.cited_knowledge_sources,
        'ticket_reply_draft': reply.ticket_reply_draft,
        'knowledge_sources': k_sources,
        'reasoning_mode': reasoning_mode,
    }
