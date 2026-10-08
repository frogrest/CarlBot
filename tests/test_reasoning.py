import json
import os

import httpx
import pytest
from pydantic import ValidationError

from services.agent.orchestrator.models import Evidence, IncidentContext
from services.agent.reasoning import (
    ActionProposal,
    DeterministicReasoner,
    FallbackReasoner,
    LLMReasoner,
    Plan,
    configured_reasoner,
)
from services.agent.reasoning.llm_adapter import _validate_plan_context
from services.agent.reasoning.base import ReasoningError


def _incident() -> IncidentContext:
    return IncidentContext(
        incident_id='INC-test',
        ticket_id=7,
        asset_id='CAM-TEST',
        site_id='SITE-TEST',
        symptom='RTSP unavailable',
        fault='rtsp_down',
        observations={
            'health': {'type': 'camera', 'reachable': True, 'rtsp': 'unavailable'},
            'rtsp': {'stream': 'unavailable'},
        },
        evidence=[
            Evidence(
                id='E1', type='observed', source='health',
                claim='CAM-TEST is reachable; RTSP is unavailable'),
        ],
    )


def test_plan_schema_accepts_registered_action():
    plan = Plan.model_validate({
        'diagnosis': 'Transient RTSP interruption',
        'confidence': 0.8,
        'action': {
            'name': 'reconnect-rtsp',
            'asset_id': 'CAM-TEST',
            'reason': 'Observed transient outage',
            'evidence_ids': ['E1'],
        },
        'requires_human': False,
    })

    assert plan.action is not None
    assert plan.action.name == 'reconnect-rtsp'


@pytest.mark.parametrize('bad_action', ['change-credentials', 'unknown-tool'])
def test_plan_schema_rejects_unregistered_action_or_tool(bad_action):
    with pytest.raises(ValidationError):
        Plan.model_validate({
            'diagnosis': 'Untrusted proposal',
            'confidence': 0.8,
            'action': {
                'name': bad_action,
                'asset_id': 'CAM-TEST',
                'reason': 'Not registered',
                'evidence_ids': ['E1'],
            },
            'requires_human': False,
        })

    with pytest.raises(ValidationError):
        Plan.model_validate({
            'diagnosis': 'Untrusted proposal',
            'confidence': 0.8,
            'action': None,
            'requires_human': True,
            'requested_action': 'Ask a technician',
            'why_stopped': 'The model attempted an extra field',
            'tool': 'shell',
        })


def test_plan_context_rejects_foreign_asset_and_evidence():
    ctx = _incident()
    proposal = ActionProposal(
        name='reconnect-rtsp',
        asset_id='CAM-OTHER',
        reason='Test',
        evidence_ids=['E1'],
    )
    plan = Plan(
        diagnosis='Transient RTSP interruption',
        confidence=0.8,
        action=proposal,
        requires_human=False,
    )

    with pytest.raises(ReasoningError):
        _validate_plan_context(plan, ctx)

    proposal.asset_id = ctx.asset_id
    proposal.evidence_ids = ['E999']
    with pytest.raises(ReasoningError):
        _validate_plan_context(plan, ctx)


@pytest.mark.parametrize(
    'model_content',
    [
        'not json',
        json.dumps({
            'diagnosis': 'Untrusted proposal',
            'confidence': 0.8,
            'action': {
                'name': 'change-credentials',
                'asset_id': 'CAM-TEST',
                'reason': 'Not registered',
                'evidence_ids': ['E1'],
            },
            'requires_human': False,
        }),
    ],
)
def test_malformed_llm_output_falls_back_to_deterministic(model_content, caplog):
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, json={
            'choices': [{'message': {'content': model_content}}],
        }))
    client = httpx.Client(transport=transport)
    llm = LLMReasoner('https://llm.invalid/v1', 'test-model', client=client)
    reasoner = FallbackReasoner(llm)
    ctx = _incident()

    result = reasoner.propose(ctx)

    assert result == DeterministicReasoner().propose(ctx)
    assert 'using deterministic reasoning' in caplog.text
    reasoner.close()
    client.close()


def test_llm_request_uses_env_key_and_versioned_prompts(monkeypatch):
    requests = []
    response_content = json.dumps({
        'diagnosis': 'Transient RTSP interruption',
        'confidence': 0.8,
        'action': {
            'name': 'reconnect-rtsp',
            'asset_id': 'CAM-TEST',
            'reason': 'Observed transient outage',
            'evidence_ids': ['E1'],
        },
        'requires_human': False,
    })

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json={
            'choices': [{'message': {'content': response_content}}],
        })

    monkeypatch.setenv('LLM_BASE_URL', 'https://llm.invalid/v1')
    monkeypatch.setenv('LLM_MODEL', 'test-model')
    monkeypatch.setenv('LLM_API_KEY', 'test-only-key')
    client = httpx.Client(transport=httpx.MockTransport(handle))
    reasoner = LLMReasoner.from_env(client=client)

    plan = reasoner.propose(_incident())

    request = requests[0]
    payload = json.loads(request.content)
    messages = payload['messages']
    assert plan.action is not None
    assert request.headers['Authorization'] == 'Bearer test-only-key'
    assert 'Orchestrator System Prompt' in messages[0]['content']
    assert 'Common Specialist Prompt' in messages[0]['content']
    assert set(json.loads(messages[1]['content'])) == {'incident', 'evidence'}
    assert payload['response_format'] == {'type': 'json_object'}
    client.close()


def test_llm_context_redacts_credential_values():
    ctx = _incident()
    ctx.evidence[0].claim = 'password: synthetic-placeholder Authorization: Bearer synthetic-token'

    payload = LLMReasoner._incident_payload(ctx)

    assert 'synthetic-placeholder' not in payload
    assert 'synthetic-token' not in payload
    assert payload.count('[REDACTED]') == 2


def test_unconfigured_reasoner_is_deterministic(monkeypatch):
    monkeypatch.delenv('LLM_BASE_URL', raising=False)
    monkeypatch.delenv('LLM_MODEL', raising=False)
    monkeypatch.delenv('LLM_API_KEY', raising=False)

    reasoner = configured_reasoner()

    assert isinstance(reasoner, DeterministicReasoner)
    reasoner.close()


@pytest.mark.llm
@pytest.mark.skipif(
    os.getenv('RUN_LLM_TESTS') != '1'
    or not os.getenv('LLM_BASE_URL')
    or not os.getenv('LLM_MODEL'),
    reason='set RUN_LLM_TESTS=1, LLM_BASE_URL, and LLM_MODEL to opt into live replay',
)
def test_optional_live_llm_replay_returns_valid_plan():
    reasoner = LLMReasoner.from_env()
    try:
        plan = reasoner.propose(_incident())
    finally:
        reasoner.close()

    assert isinstance(plan, Plan)
