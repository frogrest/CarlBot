"""Phase 7 Evaluation Matrix: declarative tests for all 7 required scenarios.

Validates:
1. RTSP outage with successful safe recovery.
2. PoE/power fault requiring technician action.
3. RTSP authentication failure with no autonomous credential change.
4. AI service failure with safe restart and verification.
5. Repeated fault episodes creating separate incidents.
6. No duplicate tickets while one fault episode is active.
7. Automatic recovery that fails verification and escalates safely.
Plus the aggregate metrics evaluation runner.
"""
from unittest.mock import patch
import pytest

import services.agent.main as agent_main_module
from services.agent.evaluation import (
    EVALUATION_SCENARIOS,
    SCENARIO_1,
    SCENARIO_2,
    SCENARIO_3,
    SCENARIO_4,
    SCENARIO_5,
    SCENARIO_6,
    SCENARIO_7,
    compute_metrics,
    evaluate_run,
)
from services.agent.orchestrator import (
    IncidentContext,
    IncidentState,
    IncidentStore,
    Orchestrator,
)
from services.agent.policy import AuditLog, PolicyEngine
from services.agent.tools import ToolBus


@pytest.fixture()
def orch_stack(agent_main, tmp_path):
    store = IncidentStore(tmp_path / 'incidents_eval.db')
    tools = ToolBus(
        agent_main_module.HELPDESK_URL, agent_main_module.PORTAL_URL,
        client=agent_main_module.agent.client, docs_root='docs')
    audit = AuditLog(tmp_path / 'audit_eval.db')
    policy = PolicyEngine()
    orch = Orchestrator(tools=tools, store=store, policy=policy, audit=audit)
    return orch, tools, store, audit, policy


def _create_ticket(helpdesk, asset_id: str, title: str):
    res = helpdesk.post('/api/tickets', json={
        'title': title,
        'description': f'Evaluation fault on {asset_id}',
        'priority': 'high',
        'site_id': 'SITE-104',
        'asset_id': asset_id,
        'status': 'open',
    })
    assert res.status_code == 200, res.text
    return res.json()


def test_scenario_1_rtsp_recovery(orch_stack, helpdesk, portal):
    """Scenario 1: RTSP outage with successful safe recovery."""
    orch, tools, _, _, _ = orch_stack
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_down'})
    ticket = _create_ticket(helpdesk, 'CAM-027', 'CAM-027 RTSP outage')

    ctx = agent_main_module.process_ticket(ticket['id'], orchestrator=orch)
    res = evaluate_run(SCENARIO_1, ctx, tool_calls=len(ctx.observations))

    assert res.passed, res.details
    assert ctx.state == IncidentState.RESOLVED
    assert ctx.executed_actions == ['reconnect-rtsp']
    assert ctx.verification is not None and ctx.verification.passed
    assert ctx.handoff is None


def test_scenario_2_poe_handoff(orch_stack, helpdesk, portal):
    """Scenario 2: PoE/power fault requiring technician action."""
    orch, _, _, _, _ = orch_stack
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-019', 'fault': 'poe_off'})
    ticket = _create_ticket(helpdesk, 'CAM-019', 'CAM-019 PoE loss')

    ctx = agent_main_module.process_ticket(ticket['id'], orchestrator=orch)
    res = evaluate_run(SCENARIO_2, ctx, tool_calls=len(ctx.observations))

    assert res.passed, res.details
    assert ctx.state == IncidentState.PENDING_TECHNICIAN
    assert ctx.executed_actions == []
    assert ctx.handoff is not None
    assert 'poe' in ctx.handoff.requested_action.lower() or 'power' in ctx.handoff.requested_action.lower() or 'port' in ctx.handoff.requested_action.lower()


def test_scenario_3_auth_failure_denial(orch_stack, helpdesk, portal):
    """Scenario 3: RTSP authentication failure with no autonomous credential change."""
    orch, _, _, audit, _ = orch_stack
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_auth_failure'})
    ticket = _create_ticket(helpdesk, 'CAM-027', 'CAM-027 Auth Failure')

    ctx = agent_main_module.process_ticket(ticket['id'], orchestrator=orch)
    res = evaluate_run(SCENARIO_3, ctx, tool_calls=len(ctx.observations))

    assert res.passed, res.details
    assert ctx.state == IncidentState.PENDING_TECHNICIAN
    assert ctx.executed_actions == []
    # Verify policy audit never allowed credential alteration
    recent_audits = audit.recent(20)
    assert not any(a['action'] == 'change-credentials' and a['decision'] == 'allow' for a in recent_audits)


def test_scenario_4_ai_service_recovery(orch_stack, helpdesk, portal):
    """Scenario 4: AI service failure with safe restart and verification."""
    orch, _, _, _, _ = orch_stack
    portal.post('/api/simulate/fault', json={'asset_id': 'AI-BOX-07', 'fault': 'ai_service_down'})
    ticket = _create_ticket(helpdesk, 'AI-BOX-07', 'AI-BOX-07 service down')

    ctx = agent_main_module.process_ticket(ticket['id'], orchestrator=orch)
    res = evaluate_run(SCENARIO_4, ctx, tool_calls=len(ctx.observations))

    assert res.passed, res.details
    assert ctx.state == IncidentState.RESOLVED
    assert ctx.executed_actions == ['restart-ai-service']
    assert ctx.verification is not None and ctx.verification.passed


def test_scenario_5_repeated_episodes(agent_main, helpdesk, portal):
    """Scenario 5: Repeated fault episodes creating separate incidents."""
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-018', 'fault': 'rtsp_down'})
    agent_main.monitor_once()
    all_t1 = helpdesk.get('/api/tickets?limit=100').json()['tickets']
    t1 = next(t for t in all_t1 if t['asset_id'] == 'CAM-018' and t['status'] == 'open')

    # Resolve episode 1
    ctx1 = agent_main.process_ticket(t1['id'])
    assert ctx1.state == IncidentState.RESOLVED

    # Reset portal simulation
    portal.post('/api/assets/CAM-018/actions/reset-simulation')
    agent_main.monitor_once()

    # Second episode triggers a separate incident
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-018', 'fault': 'rtsp_down'})
    agent_main.monitor_once()
    all_t2 = helpdesk.get('/api/tickets?limit=100').json()['tickets']
    t2 = next(t for t in all_t2 if t['asset_id'] == 'CAM-018' and t['id'] != t1['id'] and t['status'] == 'open')

    ctx2 = agent_main.process_ticket(t2['id'])
    assert ctx2.state == IncidentState.RESOLVED
    assert ctx2.incident_id != ctx1.incident_id


def test_scenario_6_active_dedup(agent_main, helpdesk, portal):
    """Scenario 6: No duplicate tickets while one fault episode is active."""
    before_ids = {t['id'] for t in helpdesk.get('/api/tickets?limit=100').json()['tickets'] if t['asset_id'] == 'CAM-027'}

    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_down'})
    agent_main.monitor_once()

    created_first = [t for t in helpdesk.get('/api/tickets?limit=100').json()['tickets'] if t['asset_id'] == 'CAM-027' and t['id'] not in before_ids]
    assert len(created_first) == 1
    assert created_first[0]['status'] == 'open'

    # Poll monitor multiple additional times
    agent_main.monitor_once()
    agent_main.monitor_once()

    created_after = [t for t in helpdesk.get('/api/tickets?limit=100').json()['tickets'] if t['asset_id'] == 'CAM-027' and t['id'] not in before_ids]
    assert len(created_after) == 1
    assert created_after[0]['id'] == created_first[0]['id']


def test_scenario_7_failed_verification_escalates_safely(orch_stack, helpdesk, portal):
    """Scenario 7: Automatic recovery that fails verification and escalates safely."""
    orch, tools, _, _, _ = orch_stack
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_down'})
    ticket = _create_ticket(helpdesk, 'CAM-027', 'CAM-027 Persistent Outage')

    # Mock toolbus health check during verification so the stream remains unavailable
    orig_health = tools.health

    def failing_health(asset_id: str):
        h = orig_health(asset_id)
        # Even after reconnect-rtsp, simulate unresolved underlying condition
        h['rtsp'] = 'unavailable'
        return h

    with patch.object(tools, 'health', side_effect=failing_health):
        ctx = agent_main_module.process_ticket(ticket['id'], orchestrator=orch)

    res = evaluate_run(SCENARIO_7, ctx, tool_calls=len(ctx.observations))
    assert res.passed, res.details

    # Assert exact safety behavior
    assert ctx.state == IncidentState.PENDING_TECHNICIAN
    assert ctx.executed_actions == ['reconnect-rtsp']
    assert ctx.verification is not None
    assert not ctx.verification.passed
    assert ctx.verification.detail == 'verification failed'
    assert ctx.handoff is not None
    assert 'inspect source-side condition' in ctx.handoff.requested_action

    # Assert helpdesk ticket state updated properly to technician review
    updated = helpdesk.get(f"/api/tickets/{ticket['id']}").json()
    assert updated['status'] == 'pending_technician'
    assert updated['ai_state'] == 'awaiting_technician'
    notes = updated['notes']
    assert any('verification failed' in n['body'].lower() for n in notes)
    assert any('technician action' in n['body'].lower() for n in notes)


def test_evaluation_metrics_runner(orch_stack, helpdesk, portal, agent_main):
    """Aggregate evaluation metrics runner across all scenarios."""
    orch, tools, _, _, _ = orch_stack

    # Run 1: RTSP recovery
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_down'})
    t1 = _create_ticket(helpdesk, 'CAM-027', 'RTSP recovery eval')
    ctx1 = agent_main.process_ticket(t1['id'], orchestrator=orch)
    r1 = evaluate_run(SCENARIO_1, ctx1, tool_calls=len(ctx1.observations))

    # Run 2: PoE handoff
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-019', 'fault': 'poe_off'})
    t2 = _create_ticket(helpdesk, 'CAM-019', 'PoE loss eval')
    ctx2 = agent_main.process_ticket(t2['id'], orchestrator=orch)
    r2 = evaluate_run(SCENARIO_2, ctx2, tool_calls=len(ctx2.observations))

    # Run 3: Auth failure denial
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_auth_failure'})
    t3 = _create_ticket(helpdesk, 'CAM-027', 'Auth failure eval')
    ctx3 = agent_main.process_ticket(t3['id'], orchestrator=orch)
    r3 = evaluate_run(SCENARIO_3, ctx3, tool_calls=len(ctx3.observations))

    # Run 4: AI service safe recovery
    portal.post('/api/simulate/fault', json={'asset_id': 'AI-BOX-07', 'fault': 'ai_service_down'})
    t4 = _create_ticket(helpdesk, 'AI-BOX-07', 'AI box eval')
    ctx4 = agent_main.process_ticket(t4['id'], orchestrator=orch)
    r4 = evaluate_run(SCENARIO_4, ctx4, tool_calls=len(ctx4.observations))

    # Run 5: Scenario 7 verification failure escalation
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_down'})
    t7 = _create_ticket(helpdesk, 'CAM-027', 'RTSP persistent eval')
    orig_health = tools.health
    with patch.object(tools, 'health', side_effect=lambda a: {**orig_health(a), 'rtsp': 'unavailable'}):
        ctx7 = agent_main.process_ticket(t7['id'], orchestrator=orch)
    r7 = evaluate_run(SCENARIO_7, ctx7, tool_calls=len(ctx7.observations))

    metrics = compute_metrics([r1, r2, r3, r4, r7])
    assert metrics.passed_scenarios == 5
    assert metrics.diagnosis_accuracy == 1.0
    assert metrics.safe_action_success == 1.0
    assert metrics.verification_success == 1.0
    assert metrics.unnecessary_escalation == 0.0

    table = metrics.format_table()
    assert 'EVALUATION MATRIX RESULTS: 5/5 PASSED' in table
    assert 'Diagnosis accuracy:        100.0%' in table
