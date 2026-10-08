import json

import httpx
import pytest

from services.helpdesk.chat_reasoner import answer_with_reasoning
from services.helpdesk.ticket_chat import query_tickets


def _result():
    ticket = {
        'id': 1002,
        'title': 'CAM-018 RTSP failure',
        'description': 'AI box stopped receiving RTSP from camera 18.',
        'status': 'closed',
        'priority': 'medium',
        'site_id': 'SITE-104',
        'asset_id': 'CAM-018',
        'resolution': 'Corrected RTSP credentials.',
        'root_cause': 'RTSP authentication mismatch',
        'ai_summary': None,
        'notes': [
            {
                'author': 'technician',
                'body': 'Confirmed approved stream settings; stream returned healthy.',
                'created_at': '2026-10-08T10:00:00Z',
            },
        ],
    }
    return query_tickets('what happened in ticket 1002', [ticket], context_ticket_id=1002)


def _llm_response(**overrides):
    body = {
        'answer': 'The notes record an RTSP authentication issue, then a healthy stream after technician review.',
        'recommendations': [{
            'category': 'check',
            'instruction': 'Compare the current symptom with the verification recorded in the ticket.',
            'ticket_ids': ['1002'],
        }],
        'cited_ticket_ids': ['1002'],
    }
    body.update(overrides)
    return json.dumps(body)


def test_llm_chat_answers_from_ticket_conversation_and_cites_ticket(monkeypatch):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json={
            'choices': [{'message': {'content': _llm_response()}}],
        })

    monkeypatch.setenv('LLM_BASE_URL', 'https://llm.invalid/v1')
    monkeypatch.setenv('LLM_MODEL', 'test-model')
    monkeypatch.setenv('LLM_API_KEY', 'test-only-key')
    client = httpx.Client(transport=httpx.MockTransport(handle))

    response = answer_with_reasoning(
        'What does the ticket conversation say?',
        _result(),
        context_ticket_id=1002,
        client=client,
    )

    request = requests[0]
    payload = json.loads(request.content)
    context = json.loads(payload['messages'][1]['content'])
    assert response['reasoning_mode'] == 'llm'
    assert response['answer'].startswith('The notes record')
    assert response['recommendations'][0]['ticket_ids'] == ['1002']
    assert response['cited_ticket_ids'] == ['1002']
    assert request.headers['Authorization'] == 'Bearer test-only-key'
    assert 'Response JSON schema' in payload['messages'][0]['content']
    assert len(context['ticket_records']) == 1
    assert 'Confirmed approved stream settings' in str(context['ticket_records'])
    assert 'RTSP username/password was wrong.' not in str(context['ticket_records'])
    client.close()


@pytest.mark.parametrize(
    'model_reply',
    [
        'not json',
        _llm_response(cited_ticket_ids=['9999']),
        _llm_response(recommendations=[{
            'category': 'technician',
            'instruction': 'Factory reset the device.',
            'ticket_ids': ['1002'],
        }]),
    ],
)
def test_invalid_or_restricted_llm_advice_falls_back(monkeypatch, model_reply, caplog):
    monkeypatch.setenv('LLM_BASE_URL', 'https://llm.invalid/v1')
    monkeypatch.setenv('LLM_MODEL', 'test-model')
    client = httpx.Client(transport=httpx.MockTransport(
        lambda _request: httpx.Response(200, json={
            'choices': [{'message': {'content': model_reply}}],
        })))

    response = answer_with_reasoning(
        'What should I do?',
        _result(),
        context_ticket_id=1002,
        client=client,
    )

    assert response['reasoning_mode'] == 'deterministic'
    assert response['cited_ticket_ids'] == ['1002']
    assert 'using grounded fallback' in caplog.text
    client.close()


def test_ticket_context_is_redacted_before_model_request(monkeypatch):
    result = _result()
    result['matches'][0]['details'].extend([
        'API_KEY: synthetic-secret-value',
        'Contact technician@example.invalid for access.',
    ])
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json={
            'choices': [{'message': {'content': _llm_response()}}],
        })

    monkeypatch.setenv('LLM_BASE_URL', 'https://llm.invalid/v1')
    monkeypatch.setenv('LLM_MODEL', 'test-model')
    client = httpx.Client(transport=httpx.MockTransport(handle))
    answer_with_reasoning('Summarize the conversation', result, client=client)

    assert 'synthetic-secret-value' not in requests[0].content.decode()
    assert 'technician@example.invalid' not in requests[0].content.decode()
    client.close()


def test_unconfigured_chat_uses_grounded_recommendation(monkeypatch):
    monkeypatch.delenv('LLM_BASE_URL', raising=False)
    monkeypatch.delenv('LLM_MODEL', raising=False)
    result = answer_with_reasoning(
        'What should I do?',
        _result(),
        context_ticket_id=1002,
    )

    assert result['reasoning_mode'] == 'deterministic'
    assert result['cited_ticket_ids'] == ['1002']
    assert 'historical context only' in result['recommendations'][0]['instruction']
    assert 'policy-gated' not in result['answer']
