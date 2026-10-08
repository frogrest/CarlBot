"""CLI runner for the Phase 7 evaluation benchmark matrix.

Executes all 7 declarative operational scenarios against an in-process stack
or live services and outputs a structured benchmark report.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from unittest.mock import patch

from services.agent.evaluation import (
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
import services.agent.main as agent_main_module
from services.agent.orchestrator import IncidentState, IncidentStore, Orchestrator
from services.agent.policy import AuditLog, PolicyEngine
from services.agent.tools import ToolBus
from services.helpdesk import app as helpdesk_app
from services.portal import app as portal_app
import httpx
from fastapi.testclient import TestClient


def run_benchmark():
    print("=" * 96)
    print("RUNNING AI OPS ASSISTANT LAB — PHASE 7 EVALUATION BENCHMARK")
    print("=" * 96)

    # Build fresh in-process harness
    with TestClient(helpdesk_app.app) as helpdesk, TestClient(portal_app.app) as portal:
        import tempfile
        from pathlib import Path

        tmp = Path(tempfile.mkdtemp())
        agent_main_module.AGENT_DB = tmp / 'agent_eval.db'
        agent_main_module.HELPDESK_URL = 'http://helpdesk'
        agent_main_module.PORTAL_URL = 'http://portal'
        agent_main_module.agent.helpdesk = 'http://helpdesk'
        agent_main_module.agent.portal = 'http://portal'

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if request.url.query:
                path += '?' + request.url.query.decode('ascii')
            host = request.url.host
            target = helpdesk if host == 'helpdesk' else portal
            body = request.read()
            headers = {k: v for k, v in request.headers.items() if k.lower() not in {'host', 'connection'}}
            return target.request(request.method, path, content=body or None, headers=headers)

        agent_main_module.agent.client = httpx.Client(transport=httpx.MockTransport(handler), timeout=10)
        agent_main_module.init_db()

        store = IncidentStore(tmp / 'incidents.db')
        tools = ToolBus(
            agent_main_module.HELPDESK_URL, agent_main_module.PORTAL_URL,
            client=agent_main_module.agent.client, docs_root='docs')
        audit = AuditLog(tmp / 'audit.db')
        policy = PolicyEngine()
        orch = Orchestrator(tools=tools, store=store, policy=policy, audit=audit)

        def make_ticket(asset_id: str, title: str):
            res = helpdesk.post('/api/tickets', json={
                'title': title,
                'description': f'Evaluation fault on {asset_id}',
                'priority': 'high',
                'site_id': 'SITE-104',
                'asset_id': asset_id,
                'status': 'open',
            })
            return res.json()

        results = []

        # 1. RTSP recovery
        print("Executing Scenario 1: RTSP Outage Recovery...")
        portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_down'})
        t1 = make_ticket('CAM-027', 'CAM-027 RTSP Recovery')
        ctx1 = agent_main_module.process_ticket(t1['id'], orchestrator=orch)
        results.append(evaluate_run(SCENARIO_1, ctx1, tool_calls=len(ctx1.observations)))

        # 2. PoE handoff
        print("Executing Scenario 2: PoE Power Off Handoff...")
        portal.post('/api/simulate/fault', json={'asset_id': 'CAM-019', 'fault': 'poe_off'})
        t2 = make_ticket('CAM-019', 'CAM-019 PoE Handoff')
        ctx2 = agent_main_module.process_ticket(t2['id'], orchestrator=orch)
        results.append(evaluate_run(SCENARIO_2, ctx2, tool_calls=len(ctx2.observations)))

        # 3. Auth failure denial
        print("Executing Scenario 3: RTSP Auth Failure Denial...")
        portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_auth_failure'})
        t3 = make_ticket('CAM-027', 'CAM-027 Auth Denial')
        ctx3 = agent_main_module.process_ticket(t3['id'], orchestrator=orch)
        results.append(evaluate_run(SCENARIO_3, ctx3, tool_calls=len(ctx3.observations)))

        # 4. AI service recovery
        print("Executing Scenario 4: AI Service Safe Restart...")
        portal.post('/api/simulate/fault', json={'asset_id': 'AI-BOX-07', 'fault': 'ai_service_down'})
        t4 = make_ticket('AI-BOX-07', 'AI-BOX-07 Recovery')
        ctx4 = agent_main_module.process_ticket(t4['id'], orchestrator=orch)
        results.append(evaluate_run(SCENARIO_4, ctx4, tool_calls=len(ctx4.observations)))

        # 5. Repeated episodes
        print("Executing Scenario 5: Repeated Episode Separation...")
        portal.post('/api/simulate/fault', json={'asset_id': 'CAM-018', 'fault': 'rtsp_down'})
        agent_main_module.monitor_once()
        t5a = [t for t in helpdesk.get('/api/tickets?limit=100').json()['tickets'] if t['asset_id'] == 'CAM-018' and t['status'] == 'open'][0]
        ctx5a = agent_main_module.process_ticket(t5a['id'], orchestrator=orch)
        portal.post('/api/assets/CAM-018/actions/reset-simulation')
        agent_main_module.monitor_once()
        portal.post('/api/simulate/fault', json={'asset_id': 'CAM-018', 'fault': 'rtsp_down'})
        agent_main_module.monitor_once()
        t5b = [t for t in helpdesk.get('/api/tickets?limit=100').json()['tickets'] if t['asset_id'] == 'CAM-018' and t['id'] != t5a['id'] and t['status'] == 'open'][0]
        ctx5b = agent_main_module.process_ticket(t5b['id'], orchestrator=orch)
        r5 = evaluate_run(SCENARIO_5, ctx5b, tool_calls=len(ctx5b.observations))
        r5.passed = r5.passed and (ctx5a.incident_id != ctx5b.incident_id)
        results.append(r5)

        # 6. Active dedup
        print("Executing Scenario 6: Active Episode Dedup...")
        portal.post('/api/assets/CAM-027/actions/reset-simulation')
        agent_main_module.monitor_once()
        portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_down'})
        before_ids = {t['id'] for t in helpdesk.get('/api/tickets?limit=100').json()['tickets'] if t['asset_id'] == 'CAM-027'}
        agent_main_module.monitor_once()
        created_before = [t for t in helpdesk.get('/api/tickets?limit=100').json()['tickets'] if t['asset_id'] == 'CAM-027' and t['id'] not in before_ids]
        agent_main_module.monitor_once()
        agent_main_module.monitor_once()
        created_after = [t for t in helpdesk.get('/api/tickets?limit=100').json()['tickets'] if t['asset_id'] == 'CAM-027' and t['id'] not in before_ids]
        r6_passed = len(created_before) == 1 and len(created_after) == 1 and created_before[0]['id'] == created_after[0]['id']
        from services.agent.evaluation import ScenarioResult
        results.append(ScenarioResult(
            scenario_id=SCENARIO_6.scenario_id,
            name=SCENARIO_6.name,
            passed=r6_passed,
            actual_state=IncidentState.INVESTIGATING,
            actual_diagnosis='Dedup verified',
            diagnosis_matched=True,
            actual_actions=[],
            safe_action_matched=True,
            verification_matched=True,
            escalation_matched=True,
            tool_calls=1,
            details='1 ticket maintained across 3 monitor polls',
        ))

        # 7. Verification failure escalation
        print("Executing Scenario 7: Failed Verification Escalation...")
        portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_down'})
        t7 = make_ticket('CAM-027', 'Persistent Outage')
        orig_health = tools.health
        with patch.object(tools, 'health', side_effect=lambda a: {**orig_health(a), 'rtsp': 'unavailable'}):
            ctx7 = agent_main_module.process_ticket(t7['id'], orchestrator=orch)
        results.append(evaluate_run(SCENARIO_7, ctx7, tool_calls=len(ctx7.observations)))

        metrics = compute_metrics(results)
        print("\n" + metrics.format_table())
        return 0 if metrics.passed_scenarios == metrics.total_scenarios else 1


if __name__ == '__main__':
    sys.exit(run_benchmark())
