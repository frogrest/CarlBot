import pytest

from services.agent.orchestrator import Budget, IncidentContext
from services.agent.orchestrator.models import ActionProposal, EvidenceType
from services.agent.specialists import SPECIALIST_NAMES, SpecialistDispatcher
from services.agent.tools import ToolBus


def _context():
    ctx = IncidentContext(
        incident_id='INC-SPECIALISTS',
        ticket_id=7,
        asset_id='CAM-027',
        site_id='SITE-104',
        symptom='CAM-027 RTSP stream unavailable',
    )
    ctx.observations = {
        'health': {
            'asset_id': 'CAM-027',
            'type': 'camera',
            'reachable': True,
            'poe': True,
            'rtsp': 'unavailable',
            'fault': 'rtsp_down',
        },
        'ping': {'ok': True},
        'tcp': {'open': True, 'port': 554},
        'rtsp': {'stream': 'unavailable', 'auth': 'valid'},
    }
    for name, result in ctx.observations.items():
        ctx.add_evidence(str(result), source=name, etype=EvidenceType.OBSERVED)
    ctx.proposed_action = ActionProposal(
        name='reconnect-rtsp',
        asset_id='CAM-027',
        reason='transient stream outage',
    )
    return ctx


def test_all_specialists_are_dispatched_with_evidence_only_tools(agent_main):
    tools = ToolBus(
        agent_main.HELPDESK_URL,
        agent_main.PORTAL_URL,
        client=agent_main.agent.client,
        docs_root='docs',
    )
    ctx = _context()
    dispatcher = SpecialistDispatcher(tools, ctx.budget)

    findings = {}
    ordered_names = (
        'rtsp',
        *sorted(SPECIALIST_NAMES - {'rtsp', 'evidence'}),
        'evidence',
    )
    for name in ordered_names:
        findings[name] = dispatcher.run(name, ctx, f'Investigate {name}.')
        ctx.findings.append(findings[name])

    assert set(findings) == {
        'helpdesk', 'network', 'rtsp', 'camera_nvr',
        'aibox', 'knowledge', 'evidence', 'technician',
    }
    assert all(finding.agent == name for name, finding in findings.items())
    assert findings['rtsp'].status == 'complete'
    assert findings['technician'].requires_human
    assert findings['evidence'].recommendations[0] == 'GO_SAFE_ACTION'
    assert not hasattr(dispatcher.tools, 'execute_action')
    assert ctx.executed_actions == []
    assert ctx.budget.tool_calls >= 4
    assert any(note.startswith('rtsp assignment:') for note in ctx.notes)


@pytest.mark.parametrize(
    ('auth', 'stream', 'verdict'),
    [
        ('invalid', 'auth_failed', 'NO_GO'),
        ('unknown', 'unavailable', 'NEEDS_MORE_TESTS'),
    ],
)
def test_evidence_specialist_rejects_rtsp_reconnect_without_valid_auth(
    agent_main, auth, stream, verdict,
):
    tools = ToolBus(
        agent_main.HELPDESK_URL,
        agent_main.PORTAL_URL,
        client=agent_main.agent.client,
        docs_root='docs',
    )
    ctx = _context()
    ctx.observations['rtsp']['auth'] = auth
    ctx.observations['rtsp']['stream'] = stream
    ctx.proposed_action = ActionProposal(
        name='reconnect-rtsp',
        asset_id='CAM-027',
        reason='test mismatch',
    )
    dispatcher = SpecialistDispatcher(tools, ctx.budget)
    ctx.findings.append(dispatcher.run('rtsp', ctx, 'Review RTSP authentication.'))
    finding = dispatcher.run('evidence', ctx, 'Check action/evidence fit.')

    assert finding.status == 'blocked'
    assert finding.recommendations[0] == verdict
    assert ctx.executed_actions == []
