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


def test_chat_filters_by_answered_status_and_named_site(helpdesk):
    response = helpdesk.post('/api/chat/query', json={
        'message': "Show answered tickets at Freddy Fazbear's.",
    })

    assert response.status_code == 200
    matches = response.json()['matches']
    assert matches
    assert all(match['ticket_status'] == 'Answered' for match in matches)
    assert all(match['site_id'] == "Freddy Fazbear's" for match in matches)


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


def test_chat_uses_selected_ticket_conversation_even_when_question_is_broad(helpdesk):
    ticket_id = 1002
    helpdesk.post(
        f'/api/tickets/{ticket_id}/notes',
        json={'author': 'technician', 'body': 'Second inspection confirmed stream is stable.'},
    )

    response = helpdesk.post('/api/chat/query', json={
        'message': 'What should we do next?',
        'ticket_id': ticket_id,
    })

    assert response.status_code == 200
    result = response.json()
    assert result['matches'][0]['ticket_id'] == str(ticket_id)
    assert 'RTSP username/password was wrong.' in result['matches'][0]['details']
    assert 'Second inspection confirmed stream is stable.' in result['matches'][0]['details']
    assert result['cited_ticket_ids'] == [str(ticket_id)]
    assert result['reasoning_mode'] == 'deterministic'
    assert result['recommendations'][0]['category'] == 'check'


def test_chat_rejects_unknown_selected_ticket(helpdesk):
    response = helpdesk.post('/api/chat/query', json={
        'message': 'What happened?',
        'ticket_id': 999999,
    })

    assert response.status_code == 404


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


def test_chat_retrieves_and_cites_approved_knowledge_documents(helpdesk, monkeypatch, tmp_path):
    # Setup a mock docs folder with approved and unapproved folders
    docs_dir = tmp_path / 'docs'
    docs_dir.mkdir()
    sop_dir = docs_dir / 'SOP'
    sop_dir.mkdir()
    (sop_dir / 'rtsp_stream_guide.md').write_text(
        "# RTSP Stream Procedure\n\n## Verification\nCheck video reception in emulator for 60 seconds.",
        encoding='utf-8',
    )
    unapproved_dir = docs_dir / 'internal_secrets'
    unapproved_dir.mkdir()
    (unapproved_dir / 'admin_notes.md').write_text(
        "# Top Secret\nDo not expose this information.",
        encoding='utf-8',
    )

    monkeypatch.setenv('DOCS_ROOT', str(docs_dir))

    # Query for RTSP Stream Procedure
    response = helpdesk.post('/api/chat/query', json={
        'message': 'What is the RTSP stream verification procedure?',
    })
    assert response.status_code == 200
    data = response.json()
    assert 'knowledge_sources' in data
    assert any('rtsp_stream_guide.md' in doc['source_path'] for doc in data['knowledge_sources'])
    assert all('admin_notes.md' not in doc['source_path'] for doc in data['knowledge_sources'])
    assert any('RTSP Stream Procedure' in doc['section_title'] or 'Verification' in doc['section_title'] for doc in data['knowledge_sources'])


def test_chat_multi_turn_history_context_used(helpdesk):
    ticket_id = 1002
    response = helpdesk.post('/api/chat/query', json={
        'message': 'Tell me more about the credentials problem.',
        'ticket_id': ticket_id,
        'history': [
            {'role': 'user', 'content': 'Is there an issue with camera 18?'},
            {'role': 'assistant', 'content': 'Yes, ticket 1002 records an RTSP credentials issue.'},
        ],
    })
    assert response.status_code == 200
    data = response.json()
    assert data['cited_ticket_ids'] == ['1002']
    assert '1002' in data['answer']


def test_chat_drafts_reply_only_on_explicit_request_with_selected_ticket(helpdesk):
    ticket_id = 1001
    # 1. Without explicit reply request, draft is None
    res1 = helpdesk.post('/api/chat/query', json={
        'message': 'What is the current status of this camera?',
        'ticket_id': ticket_id,
    })
    assert res1.status_code == 200
    assert res1.json().get('ticket_reply_draft') is None

    # 2. With explicit reply request and selected ticket, draft is generated
    res2 = helpdesk.post('/api/chat/query', json={
        'message': 'Please draft a reply to the customer explaining the status.',
        'ticket_id': ticket_id,
    })
    assert res2.status_code == 200
    draft = res2.json().get('ticket_reply_draft')
    assert draft is not None
    assert 'CAM-027' in draft or '1001' in draft or 'investigation' in draft.lower()

    # 3. With explicit reply request but NO ticket selected, draft is None
    res3 = helpdesk.post('/api/chat/query', json={
        'message': 'Draft a response for the customer.',
    })
    assert res3.status_code == 200
    assert res3.json().get('ticket_reply_draft') is None


def test_customer_reply_publish_and_idempotency(helpdesk):
    ticket_id = 1001
    # Check ticket initial customer replies
    ticket_before = helpdesk.get(f'/api/tickets/{ticket_id}').json()
    initial_count = len(ticket_before.get('customer_replies', []))

    # Publish reply
    reply_payload = {
        'author': 'technician',
        'body': 'A technician has been dispatched to inspect the camera.',
        'idempotency_key': 'test-idemp-key-1',
    }
    publish_res = helpdesk.post(f'/api/tickets/{ticket_id}/customer-replies', json=reply_payload)
    assert publish_res.status_code == 200
    data = publish_res.json()
    assert data['ok'] is True
    assert data['reply']['body'] == reply_payload['body']
    assert data.get('duplicate') is not True

    # Check that ticket contains this customer reply separately from notes
    ticket_after = helpdesk.get(f'/api/tickets/{ticket_id}').json()
    assert len(ticket_after['customer_replies']) == initial_count + 1
    new_reply = ticket_after['customer_replies'][-1]
    assert new_reply['body'] == reply_payload['body']
    # Confirm it was not added to technician notes
    assert all(n['body'] != reply_payload['body'] for n in ticket_after['notes'])

    # Duplicate publish with same idempotency key returns cleanly without creating a second record
    dup_res = helpdesk.post(f'/api/tickets/{ticket_id}/customer-replies', json=reply_payload)
    assert dup_res.status_code == 200
    assert dup_res.json().get('duplicate') is True

    ticket_dup_check = helpdesk.get(f'/api/tickets/{ticket_id}').json()
    assert len(ticket_dup_check['customer_replies']) == initial_count + 1


def test_chat_greeting_companion_response(helpdesk):
    # Greeting without ticket context
    res1 = helpdesk.post('/api/chat/query', json={'message': 'hello'})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1['answer'] == "Hello, I'm Carlbot, ask me anything about the Helpdesk"

    # Greeting with ticket context
    res2 = helpdesk.post('/api/chat/query', json={'message': 'hi CarlBot', 'ticket_id': 1001})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2['answer'] == "Hello, I'm Carlbot, ask me anything about the Helpdesk" 


def test_chat_terminology_explanations(helpdesk):
    # RTSP explanation
    rtsp_res = helpdesk.post('/api/chat/query', json={'message': 'whats rtsp'})
    assert rtsp_res.status_code == 200
    rtsp_data = rtsp_res.json()
    assert 'Real-Time Streaming Protocol' in rtsp_data['answer']
    assert 'port 554' in rtsp_data['answer']
    assert 'reconnect-rtsp' in rtsp_data['answer']

    # NVR explanation
    nvr_res = helpdesk.post('/api/chat/query', json={'message': 'what is an nvr'})
    assert nvr_res.status_code == 200
    nvr_data = nvr_res.json()
    assert 'Network Video Recorder' in nvr_data['answer']
    assert 'Multi-Channel Ingestion' in nvr_data['answer']

    # AI Box explanation
    aibox_res = helpdesk.post('/api/chat/query', json={'message': 'what does ai box do'})
    assert aibox_res.status_code == 200
    aibox_data = aibox_res.json()
    assert 'AI Box is an on-premises edge computing' in aibox_data['answer']
    assert 'restart-ai-service' in aibox_data['answer']

    # PoE explanation
    poe_res = helpdesk.post('/api/chat/query', json={'message': 'explain poe'})
    assert poe_res.status_code == 200
    poe_data = poe_res.json()
    assert 'Power over Ethernet' in poe_data['answer']
    assert '802.3af' in poe_data['answer']
    assert 'pending_technician' in poe_data['answer']


def test_chat_off_topic_guardrail(helpdesk):
    res = helpdesk.post('/api/chat/query', json={'message': 'write a poem about flowers'})
    assert res.status_code == 200
    data = res.json()
    assert "dedicated to this surveillance and helpdesk lab" in data['answer']
    assert "not able to assist with general topics" in data['answer']


def test_chat_cites_approved_knowledge_for_terminologies(helpdesk):
    res = helpdesk.post('/api/chat/query', json={'message': 'what is rtsp'})
    assert res.status_code == 200
    data = res.json()
    assert any('docs/RTSP/RTSP_STREAMING.md' in doc['source_path'] for doc in data['knowledge_sources'])
    assert any('docs/RTSP/RTSP_STREAMING.md' in cited for cited in data['cited_knowledge_sources'])

def test_chat_network_protocols_and_ip_commands(helpdesk):
    # Network protocols
    proto_res = helpdesk.post('/api/chat/query', json={'message': 'what network protocols are used in the system'})
    assert proto_res.status_code == 200
    proto_data = proto_res.json()
    assert 'TCP vs. UDP' in proto_data['answer']
    assert 'RTSP (Port 554)' in proto_data['answer']
    assert 'NTP (Port 123)' in proto_data['answer']
    assert any('NETWORK_PROTOCOLS_AND_COMMANDS.md' in doc['source_path'] for doc in proto_data['knowledge_sources'])

    # IP commands
    cmd_res = helpdesk.post('/api/chat/query', json={'message': 'what ip commands should a technician use'})
    assert cmd_res.status_code == 200
    cmd_data = cmd_res.json()
    assert 'ping <ip>' in cmd_data['answer']
    assert 'arp -a' in cmd_data['answer']
    assert 'ipconfig' in cmd_data['answer']
    assert 'traceroute' in cmd_data['answer']


def test_chat_reboot_vs_powercycle(helpdesk):
    res = helpdesk.post('/api/chat/query', json={'message': 'what is the difference between reboot and power cycle'})
    assert res.status_code == 200
    data = res.json()
    assert 'Reboot (Soft Reboot' in data['answer']
    assert 'Power Cycle (Hard Reboot' in data['answer']
    assert '15–30 seconds' in data['answer']
    assert 'poe_bounce' in data['answer']
    assert any('REBOOT_VS_POWERCYCLE.md' in doc['source_path'] for doc in data['knowledge_sources'])


def test_chat_offline_incident_sops(helpdesk):
    # Offline Camera
    cam_res = helpdesk.post('/api/chat/query', json={'message': 'what to do when a camera is offline'})
    assert cam_res.status_code == 200
    cam_data = cam_res.json()
    assert 'Layer 1 (Physical & PoE)' in cam_data['answer']
    assert 'ping <camera_ip>' in cam_data['answer']
    assert 'port 554' in cam_data['answer']
    assert 'pending_technician' in cam_data['answer']
    assert any('OFFLINE_INCIDENT_PLAYBOOK.md' in doc['source_path'] for doc in cam_data['knowledge_sources'])

    # Offline System / AI Box
    sys_res = helpdesk.post('/api/chat/query', json={'message': 'what should the technician do when a system is offline'})
    assert sys_res.status_code == 200
    sys_data = sys_res.json()
    assert 'ping <server_ip>' in sys_data['answer']
    assert 'docker compose ps' in sys_data['answer']
    assert 'restart-ai-service' in sys_data['answer']

    # Offline Remote Desktop
    rdp_res = helpdesk.post('/api/chat/query', json={'message': 'what to do when remote desktop is offline'})
    assert rdp_res.status_code == 200
    rdp_data = rdp_res.json()
    assert 'port 3389' in rdp_data['answer']
    assert 'Test-NetConnection' in rdp_data['answer']
    assert 'KVM' in rdp_data['answer']
