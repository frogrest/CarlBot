"""Helpdesk API contract tests (Phase 1)."""
import sqlite3

from services.helpdesk import app as helpdesk_module
from services.helpdesk.app import STATUS_VALUES


def test_list_seeded_tickets(helpdesk):
    res = helpdesk.get('/api/tickets')
    assert res.status_code == 200
    tickets = res.json()['tickets']
    assert len(tickets) >= 25
    ids = {t['id'] for t in tickets}
    assert {1001, 1002, 1003, 1004, 1005} <= ids
    assert all(t['status'] in STATUS_VALUES for t in tickets)
    assert {ticket['ticket_status'] for ticket in tickets} == {'Open', 'Answered', 'Closed'}
    assert {"Freddy Fazbear's", 'Centerpark Tower 1', 'Pacman'} <= {
        ticket['site_id'] for ticket in tickets
    }


def test_get_ticket_includes_notes(helpdesk):
    res = helpdesk.get('/api/tickets/1002')
    assert res.status_code == 200
    ticket = res.json()
    assert ticket['asset_id'] == 'CAM-018'
    assert isinstance(ticket['notes'], list)
    assert any('RTSP' in n['body'] for n in ticket['notes'])


def test_get_missing_ticket_404(helpdesk):
    assert helpdesk.get('/api/tickets/999999').status_code == 404


def test_create_patch_and_status_validation(helpdesk):
    created = helpdesk.post('/api/tickets', json={
        'title': 'CAM-019 no video',
        'description': 'Simulated report for contract test.',
        'priority': 'high',
        'site_id': 'SITE-104',
        'asset_id': 'CAM-019',
    })
    assert created.status_code == 200
    body = created.json()
    ticket_id = body['id']
    assert body['status'] == 'open'
    assert body['ticket_status'] == 'Open'
    assert body['ai_state'] == 'new'

    patched = helpdesk.patch(f'/api/tickets/{ticket_id}', json={
        'status': 'in_progress', 'ai_state': 'investigating',
    })
    assert patched.status_code == 200
    assert patched.json()['status'] == 'in_progress'
    assert patched.json()['ai_state'] == 'investigating'

    bad = helpdesk.patch(f'/api/tickets/{ticket_id}', json={'status': 'not_a_status'})
    assert bad.status_code == 400


def test_ticket_status_choices_are_independent_of_agent_workflow(helpdesk):
    response = helpdesk.patch('/api/tickets/1001', json={'ticket_status': 'Answered'})
    assert response.status_code == 200
    assert response.json()['ticket_status'] == 'Answered'
    assert response.json()['status'] == 'open'

    workflow_update = helpdesk.patch('/api/tickets/1001', json={'status': 'pending_technician'})
    assert workflow_update.json()['ticket_status'] == 'Answered'

    invalid = helpdesk.patch('/api/tickets/1001', json={'ticket_status': 'In Progress'})
    assert invalid.status_code == 400


def test_existing_helpdesk_database_gets_ticket_status_migration(monkeypatch, tmp_path):
    path = tmp_path / 'legacy-helpdesk.db'
    con = sqlite3.connect(path)
    con.execute('''CREATE TABLE tickets (
        id INTEGER PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
        status TEXT NOT NULL, priority TEXT NOT NULL, site_id TEXT NOT NULL,
        asset_id TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        resolution TEXT, root_cause TEXT, ai_summary TEXT, ai_state TEXT
    )''')
    con.execute(
        '''INSERT INTO tickets VALUES (77, 'Legacy ticket', 'Existing row',
        'resolved', 'medium', 'SITE-104', 'CAM-027', '2026-01-01', '2026-01-01',
        NULL, NULL, NULL, 'resolved')'''
    )
    con.commit()
    con.close()
    monkeypatch.setenv('HELPDESK_DB', str(path))

    helpdesk_module.init_db()

    assert helpdesk_module.get_ticket(77)['ticket_status'] == 'Answered'


def test_search_by_keyword_and_asset(helpdesk):
    res = helpdesk.get('/api/search', params={'q': 'RTSP'})
    assert res.status_code == 200
    assert any(r['id'] == 1002 for r in res.json()['results'])

    res2 = helpdesk.get('/api/search', params={'q': 'offline', 'asset_id': 'CAM-027'})
    assert res2.status_code == 200
    results = res2.json()['results']
    assert results and all(r['asset_id'] == 'CAM-027' for r in results)


def test_add_note_and_missing_ticket(helpdesk):
    ok = helpdesk.post('/api/tickets/1001/notes', json={'author': 'tester', 'body': 'checked cable'})
    assert ok.status_code == 200
    assert ok.json()['ok'] is True
    after = helpdesk.get('/api/tickets/1001').json()
    assert any(n['body'] == 'checked cable' for n in after['notes'])

    missing = helpdesk.post('/api/tickets/999999/notes', json={'author': 'x', 'body': 'y'})
    assert missing.status_code == 404


def test_request_verification_flow(helpdesk):
    assert helpdesk.get('/api/tickets/1001').json()['status'] == 'open'
    res = helpdesk.post('/api/tickets/1001/request-verification')
    assert res.status_code == 200
    assert res.json()['status'] == 'ready_for_verification'
