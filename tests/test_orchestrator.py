"""Orchestrator Phase 2: state machine, routing, policy gate, budgets.

Runs against the same in-process fixtures as the Phase 1 suite
(helpdesk/portal TestClients + a ToolBus pointed at the agent's
MockTransport-routed client). No network, no Docker.
"""
import pytest

import services.agent.main as agent_main_module
from services.agent.orchestrator import (
    Budget, IncidentState, IncidentStore, Orchestrator,
    can_transition, derive_signals, route,
)
from services.agent.policy import AuditLog, PolicyEngine
from services.agent.tools import ToolBus


@pytest.fixture()
def stack(agent_main, tmp_path):
    store = IncidentStore(tmp_path / 'incidents.db')
    tools = ToolBus(
        agent_main_module.HELPDESK_URL, agent_main_module.PORTAL_URL,
        client=agent_main_module.agent.client, docs_root='docs')
    audit = AuditLog(tmp_path / 'audit.db')
    return store, tools, PolicyEngine(), audit


def _make_ticket(helpdesk, asset_id: str, title: str = 'Camera fault'):
    res = helpdesk.post('/api/tickets', json={
        'title': title, 'description': f'{asset_id} fault injected by test',
        'priority': 'high', 'site_id': 'SITE-104', 'asset_id': asset_id,
    })
    assert res.status_code == 200, res.text
    return res.json()


def _run(stack, ticket):
    store, tools, policy, audit = stack
    orchestrator = Orchestrator(tools=tools, store=store, policy=policy, audit=audit)
    return agent_main_module.process_ticket(ticket['id'], orchestrator=orchestrator)


def test_orchestrator_recovers_rtsp_down(stack, helpdesk, portal):
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_down'})
    ctx = _run(stack, _make_ticket(helpdesk, 'CAM-027'))
    assert ctx.state == IncidentState.RESOLVED
    assert ctx.verification is not None and ctx.verification.passed
    assert ctx.executed_actions == ['reconnect-rtsp']
    assert [r['agent'] for r in ctx.route] == ['rtsp']
    assert {finding.agent for finding in ctx.findings} >= {'rtsp', 'evidence'}
    assert any(
        finding.agent == 'evidence'
        and finding.recommendations[0] == 'GO_SAFE_ACTION'
        for finding in ctx.findings
    )
    audit = AuditLog(stack[3].db_path)
    assert any(
        row['action'] == 'reconnect-rtsp' and row['decision'] == 'allow'
        for row in audit.recent(10)
    )
    final = helpdesk.get(f"/api/tickets/{ctx.ticket_id}").json()
    assert final['status'] == 'resolved'
    assert final['ai_state'] == 'resolved'
    assert final['root_cause'] == ctx.diagnosis
    notes = helpdesk.get(f"/api/tickets/{ctx.ticket_id}").json()['notes']
    assert any('verification passed' in n['body'] for n in notes)


def test_orchestrator_parks_poe_off_with_technician_handoff(stack, helpdesk, portal):
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'poe_off'})
    ctx = _run(stack, _make_ticket(helpdesk, 'CAM-027'))
    assert ctx.state == IncidentState.PENDING_TECHNICIAN
    assert ctx.handoff is not None
    assert ctx.handoff.requested_action
    assert ctx.handoff.why_stopped
    assert ctx.executed_actions == []  # no autonomous action on physical faults
    final = helpdesk.get(f"/api/tickets/{ctx.ticket_id}").json()
    assert final['status'] == 'pending_technician'
    assert final['ai_summary'] is not None


def test_orchestrator_denies_auth_failure_credential_change(stack, helpdesk, portal):
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_auth_failure'})
    ctx = _run(stack, _make_ticket(helpdesk, 'CAM-027'))
    assert ctx.state == IncidentState.PENDING_TECHNICIAN
    assert ctx.executed_actions == []
    assert any('credential' in (n or '').lower() or 'auth' in (n or '').lower()
               for n in [ctx.diagnosis, ctx.handoff.requested_action if ctx.handoff else ''])


def test_orchestrator_recovers_ai_service(stack, helpdesk, portal):
    portal.post('/api/simulate/fault', json={'asset_id': 'AI-BOX-07', 'fault': 'ai_service_down'})
    ctx = _run(stack, _make_ticket(helpdesk, 'AI-BOX-07', title='AI box fault'))
    assert ctx.state == IncidentState.RESOLVED
    assert ctx.executed_actions == ['restart-ai-service']
    assert ctx.verification is not None and ctx.verification.passed


def test_budget_exhaustion_forces_handoff(stack, helpdesk, portal):
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_down'})
    ticket = _make_ticket(helpdesk, 'CAM-027')
    store, tools, policy, audit = stack
    orch = Orchestrator(tools=tools, store=store, policy=policy, audit=audit,
                        budget_factory=lambda: Budget(max_tool_calls=0))
    ctx = orch.run(ticket)
    assert ctx.state == IncidentState.PENDING_TECHNICIAN
    assert ctx.handoff is not None


def test_illegal_transition_rejected(tmp_path):
    store = IncidentStore(tmp_path / 'incidents.db')
    machine_state = __import__('services.agent.orchestrator.state', fromlist=['StateMachine']).StateMachine(store)
    from services.agent.orchestrator.models import IncidentContext
    ctx = IncidentContext(incident_id='INC-1', ticket_id=1)
    with pytest.raises(Exception):
        machine_state.transition(ctx, IncidentState.RESOLVED, 'skipping is illegal')
    assert len(store.for_ticket(1)) == 0  # nothing persisted on failure


def test_router_evidence_based():
    signals = derive_signals({'health': {'reachable': False, 'poe': False}})
    planned = route(signals)
    agents = [r['agent'] for r in planned]
    assert 'network' in agents and 'technician' in agents
    signals = derive_signals({'health': {'reachable': True, 'rtsp': 'unavailable'},
                              'rtsp': {'stream': 'unavailable'}})
    assert [r['agent'] for r in route(signals)] == ['rtsp']


def test_policy_unknown_action_denied():
    policy = PolicyEngine()
    from services.agent.orchestrator.models import ActionProposal
    decision = policy.decide(ActionProposal(name='change-credentials', asset_id='CAM-027', reason='x'))
    assert not decision.allowed and decision.requires_human
