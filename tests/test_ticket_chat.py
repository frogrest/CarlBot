import csv


REFERENCE_FIELDS = [
    'Ticket Number',
    'Subject',
    'Priority',
    'Help Topic',
    'Current Status',
    'Thread Count',
    'Location',
    'From',
    'From Email',
]


def write_reference_csv(path, records):
    with path.open('w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=REFERENCE_FIELDS)
        writer.writeheader()
        writer.writerows(records)


def test_chat_finds_reference_ticket_and_does_not_expose_sender_email(helpdesk, monkeypatch, tmp_path):
    reference = tmp_path / 'ticket-reference.csv'
    write_reference_csv(reference, [{
        'Ticket Number': 'EG-222331',
        'Subject': 'Camera(s) offline - North annex',
        'Priority': 'High',
        'Help Topic': 'Camera(s) Offline',
        'Current Status': 'Open',
        'Thread Count': '4',
        'Location': 'Sample Camera Site',
        'From': 'Site Technician',
        'From Email': 'technician@example.invalid',
    }])
    monkeypatch.setenv('TICKET_REFERENCE_CSV', str(reference))
    before = helpdesk.get('/api/tickets').json()['tickets']

    response = helpdesk.post('/api/chat/query', json={
        'message': 'Is there an open ticket about an offline camera at Sample Camera Site?',
    })

    assert response.status_code == 200
    result = response.json()
    assert result['matches'][0]['ticket_id'] == 'EG-222331'
    assert result['matches'][0]['site_match'] == 'exact'
    assert result['matches'][0]['has_conversation'] is False
    assert 'Ticket #EG-222331' in result['answer']
    assert 'The reference list has no notes.' in result['answer']
    assert 'EG-222331' in result['answer']
    assert 'technician@example.invalid' not in response.text
    assert helpdesk.get('/api/tickets').json()['tickets'] == before


def test_chat_marks_partial_site_match_as_unconfirmed(helpdesk, monkeypatch, tmp_path):
    reference = tmp_path / 'ticket-reference.csv'
    write_reference_csv(reference, [{
        'Ticket Number': 'EG-222331',
        'Subject': 'Camera(s) offline - North annex',
        'Priority': 'High',
        'Help Topic': 'Camera(s) Offline',
        'Current Status': 'Open',
        'Thread Count': '4',
        'Location': 'Austin-TX',
        'From': 'Fazbears Pizzeria',
    }])
    monkeypatch.setenv('TICKET_REFERENCE_CSV', str(reference))

    response = helpdesk.post('/api/chat/query', json={
        'message': "Is there an open offline camera ticket at Freddy's Pizzeria?",
    })

    assert response.status_code == 200
    result = response.json()
    assert result['matches'][0]['site_match'] == 'partial'
    assert 'site is not confirmed' in result['answer']


def test_chat_reads_live_closed_ticket_notes(helpdesk, monkeypatch, tmp_path):
    reference = tmp_path / 'ticket-reference.csv'
    write_reference_csv(reference, [])
    monkeypatch.setenv('TICKET_REFERENCE_CSV', str(reference))

    response = helpdesk.post('/api/chat/query', json={
        'message': 'Find the closed RTSP ticket at SITE-104 and summarize what was recorded.',
    })

    assert response.status_code == 200
    result = response.json()
    ticket = next(match for match in result['matches'] if match['ticket_id'] == '1002')
    assert ticket['status'] == 'closed'
    assert ticket['has_conversation'] is True
    assert 'RTSP username/password was wrong.' in ticket['details']
    assert '1002' in result['answer']
    assert all(match['status'] == 'closed' for match in result['matches'])
    assert all(match['ticket_id'] != '1005' for match in result['matches'])
    assert 'A technician corrected the camera stream login details.' in result['answer']
    assert 'Closed.' in result['answer']


def test_chat_can_return_a_ticket_subject_when_asked_for_it(helpdesk):
    response = helpdesk.post('/api/chat/query', json={
        'message': 'What is the subject of ticket 1002?',
    })

    assert response.status_code == 200
    result = response.json()
    assert len(result['matches']) == 1
    assert result['matches'][0]['ticket_id'] == '1002'
    assert result['matches'][0]['title'] == 'CAM-018 RTSP failure'
    assert 'CAM-018 RTSP failure' in result['answer']


def test_chat_closed_search_does_not_treat_open_export_rows_as_closed(helpdesk, monkeypatch, tmp_path):
    reference = tmp_path / 'ticket-reference.csv'
    write_reference_csv(reference, [{
        'Ticket Number': 'EG-222331',
        'Subject': 'Camera(s) offline - North annex',
        'Priority': 'High',
        'Help Topic': 'Camera(s) Offline',
        'Current Status': 'Open',
        'Thread Count': '4',
        'Location': 'Austin-TX',
        'From': 'Sample Camera Site',
    }])
    monkeypatch.setenv('TICKET_REFERENCE_CSV', str(reference))

    response = helpdesk.post('/api/chat/query', json={
        'message': 'Show closed offline camera tickets at Sample Camera Site.',
    })

    assert response.status_code == 200
    result = response.json()
    assert all(match['source'] != 'reference_export' for match in result['matches'])
    assert "couldn't find a matching ticket" in result['answer']


def test_chat_explains_ticket_status_and_diagnosis_in_plain_language(helpdesk):
    created = helpdesk.post('/api/tickets', json={
        'title': 'Camera reported offline - CAM-018',
        'description': 'CAM-018 appeared offline during a site check.',
        'priority': 'medium',
        'site_id': 'SITE-104',
        'asset_id': 'CAM-018',
        'status': 'pending_technician',
    }).json()
    helpdesk.patch(f"/api/tickets/{created['id']}", json={
        'root_cause': 'No critical fault reproduced by current checks',
    })

    response = helpdesk.post('/api/chat/query', json={
        'message': f"What happened with ticket {created['id']}?",
    })

    assert response.status_code == 200
    answer = response.json()['answer']
    assert 'Waiting for a technician.' in answer
    assert 'Current checks found no issue' in answer
    assert 'No critical fault reproduced by current checks' not in answer
    assert 'DEMO' not in answer


def test_chat_keeps_broad_search_results_brief(helpdesk):
    for asset_id in ('CAM-027', 'CAM-018', 'CAM-019'):
        helpdesk.post('/api/tickets', json={
            'title': f'Camera offline - {asset_id}',
            'description': f'{asset_id} was reported offline.',
            'priority': 'medium',
            'site_id': 'SITE-104',
            'asset_id': asset_id,
            'status': 'pending_technician',
        })

    response = helpdesk.post('/api/chat/query', json={
        'message': 'Are there camera offline tickets at SITE-104?',
    })

    assert response.status_code == 200
    answer = response.json()['answer']
    result_lines = [line for line in answer.splitlines() if line.startswith('#')]
    assert len(result_lines) == 3
    assert 'more match' in answer
    assert 'What the ticket says' not in answer
    assert len(answer) < 500
