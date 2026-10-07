"""Portal fault-injection lifecycle tests (Phase 1)."""


def test_asset_inventory(portal):
    res = portal.get('/api/assets')
    assert res.status_code == 200
    ids = {a['asset_id'] for a in res.json()['assets']}
    assert {'CAM-027', 'CAM-018', 'CAM-019', 'NVR-02', 'AI-BOX-07'} <= ids


def test_health_and_ping_healthy(portal):
    h = portal.get('/api/assets/CAM-027/health').json()
    assert h['reachable'] is True
    assert h['rtsp'] == 'healthy'
    p = portal.get('/api/assets/CAM-027/ping').json()
    assert p['ok'] is True


def test_rtsp_down_recovery_cycle(portal):
    inj = portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_down'})
    assert inj.status_code == 200

    assert portal.get('/api/assets/CAM-027/rtsp-test').json()['stream'] == 'unavailable'
    events = portal.get('/api/events').json()['events']
    assert any(e['event_id'] == 'CAM-027:rtsp_down' for e in events)

    action = portal.post('/api/assets/CAM-027/actions/reconnect-rtsp', json={'actor': 'test'})
    assert action.status_code == 200
    assert action.json()['ok'] is True

    assert portal.get('/api/assets/CAM-027/rtsp-test').json()['stream'] == 'healthy'
    events_after = portal.get('/api/events').json()['events']
    assert not any(e['event_id'] == 'CAM-027:rtsp_down' for e in events_after)


def test_auth_failure_is_not_silently_recoverable(portal):
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'rtsp_auth_failure'})
    assert portal.get('/api/assets/CAM-027/rtsp-test').json()['auth'] == 'invalid'

    action = portal.post('/api/assets/CAM-027/actions/reconnect-rtsp', json={'actor': 'test'})
    assert action.status_code == 200
    assert action.json()['ok'] is False
    # Fault persists: no autonomous credential recovery.
    assert portal.get('/api/assets/CAM-027/rtsp-test').json()['auth'] == 'invalid'

    reset = portal.post('/api/assets/CAM-027/actions/reset-simulation')
    assert reset.status_code == 200
    assert portal.get('/api/assets/CAM-027/rtsp-test').json()['auth'] == 'valid'


def test_poe_off_marks_unreachable(portal):
    portal.post('/api/simulate/fault', json={'asset_id': 'CAM-019', 'fault': 'poe_off'})
    assert portal.get('/api/assets/CAM-019/ping').json()['ok'] is False
    h = portal.get('/api/assets/CAM-019/health').json()
    assert h['reachable'] is False
    assert h['poe'] is False

    portal.post('/api/assets/CAM-019/actions/reset-simulation')
    assert portal.get('/api/assets/CAM-019/ping').json()['ok'] is True


def test_ai_service_restart_cycle(portal):
    portal.post('/api/simulate/fault', json={'asset_id': 'AI-BOX-07', 'fault': 'ai_service_down'})
    assert portal.get('/api/assets/AI-BOX-07/health').json()['service'] == 'down'

    restart = portal.post('/api/assets/AI-BOX-07/actions/restart-ai-service', json={'actor': 'test'})
    assert restart.status_code == 200
    assert restart.json()['ok'] is True
    assert portal.get('/api/assets/AI-BOX-07/health').json()['service'] == 'healthy'


def test_restart_rejected_for_wrong_asset(portal):
    res = portal.post('/api/assets/CAM-027/actions/restart-ai-service', json={'actor': 'test'})
    assert res.status_code == 400


def test_unknown_fault_and_asset(portal):
    bad_fault = portal.post('/api/simulate/fault', json={'asset_id': 'CAM-027', 'fault': 'nope'})
    assert bad_fault.status_code == 400
    bad_asset = portal.post('/api/simulate/fault', json={'asset_id': 'CAM-999', 'fault': 'rtsp_down'})
    assert bad_asset.status_code == 404
    assert portal.get('/api/assets/CAM-999/health').status_code == 404
