"""Monitor loop: one ticket per active episode, re-arm after recovery.

Uses the `agent_main` fixture: `services.agent.main` with its HTTP client
routed to the in-process helpdesk/portal TestClients; the background
thread is never started — `monitor_once()` is called explicitly.
"""

from services.agent.orchestrator import IncidentState, IncidentStore
from services.agent.policy import AuditLog


def _asset_tickets(helpdesk, asset_id: str):
    res = helpdesk.get('/api/tickets', params={'limit': 200})
    assert res.status_code == 200
    return [t for t in res.json()['tickets'] if t['asset_id'] == asset_id]


def test_monitor_creates_exactly_one_ticket_per_active_episode(agent_main, helpdesk, portal):
    before_ids = {t['id'] for t in _asset_tickets(helpdesk, 'CAM-027')}

    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_down'})
    agent_main.monitor_once()

    created = [t for t in _asset_tickets(helpdesk, 'CAM-027') if t['id'] not in before_ids]
    assert len(created) == 1
    assert created[0]['status'] == 'open'
    assert created[0]['site_id'] == 'SITE-104'

    # Second poll while the episode is active: no duplicate ticket.
    agent_main.monitor_once()
    created_again = [t for t in _asset_tickets(helpdesk, 'CAM-027') if t['id'] not in before_ids]
    assert len(created_again) == 1


def test_repeated_episodes_create_separate_incidents(agent_main, helpdesk, portal):
    # Episode 1
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-018', 'fault': 'rtsp_down'})
    agent_main.monitor_once()
    ids_after_ep1 = {t['id'] for t in _asset_tickets(helpdesk, 'CAM-018')}
    assert len(ids_after_ep1) >= 1  # seed 1002 (closed) + the new incident

    # Recovery: episode ends, monitor re-arms without a new ticket.
    portal.post('/api/assets/CAM-018/actions/reset-simulation')
    agent_main.monitor_once()
    ids_after_reset = {t['id'] for t in _asset_tickets(helpdesk, 'CAM-018')}
    assert ids_after_reset == ids_after_ep1

    # Episode 2: the same fault returns -> a SEPARATE incident is created.
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-018', 'fault': 'rtsp_down'})
    agent_main.monitor_once()
    ids_after_ep2 = {t['id'] for t in _asset_tickets(helpdesk, 'CAM-018')}
    new_ids = ids_after_ep2 - ids_after_ep1
    assert len(new_ids) == 1


def test_monitor_persists_run_state_tables(agent_main, helpdesk, portal):
    """monitor_events is deduplicated on event_key with an active flag."""
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-019', 'fault': 'poe_off'})
    agent_main.monitor_once()
    con = agent_main.connect()
    rows = con.execute('SELECT event_key, active FROM monitor_events').fetchall()
    con.close()
    matching = [r for r in rows if r['event_key'] == 'CAM-019:poe_off']
    assert len(matching) == 1
    assert matching[0]['active'] == 1


def test_monitor_ticket_is_investigated_and_persisted(agent_main, helpdesk, portal):
    before_ids = {t['id'] for t in _asset_tickets(helpdesk, 'CAM-027')}
    portal.post('/api/simulate/fault', json={
        'asset_id': 'CAM-027', 'fault': 'rtsp_down',
    })

    agent_main.monitor_once()
    created = [
        t for t in _asset_tickets(helpdesk, 'CAM-027')
        if t['id'] not in before_ids
    ]
    assert len(created) == 1

    ctx = agent_main.process_ticket(created[0]['id'])
    ticket = helpdesk.get(f"/api/tickets/{created[0]['id']}").json()
    assert ctx.state == IncidentState.RESOLVED
    assert ticket['status'] == 'resolved'
    assert ticket['ai_state'] == 'resolved'

    persisted_incidents = IncidentStore(agent_main.AGENT_DB).for_ticket(ticket['id'])
    assert len(persisted_incidents) == 1
    assert persisted_incidents[0].state == IncidentState.RESOLVED

    persisted_audit = AuditLog(agent_main.AGENT_DB).recent(20)
    assert any(
        row['ticket_id'] == ticket['id']
        and row['action'] == 'reconnect-rtsp'
        and row['decision'] == 'allow'
        for row in persisted_audit
    )
