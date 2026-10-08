from copy import deepcopy
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title='Fake Video/AI Portal', version='0.2.0')

ASSETS = {
    'CAM-027': {
        'asset_id': 'CAM-027', 'type': 'camera', 'site_id': 'SITE-104',
        'ip': '192.168.30.27', 'nvr_id': 'NVR-02', 'ai_box_id': 'AI-BOX-07',
        'reachable': True, 'rtsp': 'healthy', 'auth': 'valid', 'cpu': 22,
        'storage': 41, 'poe': True, 'last_seen': '2026-09-29T20:55:00Z', 'fault': None
    },
    'CAM-018': {
        'asset_id': 'CAM-018', 'type': 'camera', 'site_id': 'SITE-104',
        'ip': '192.168.30.18', 'nvr_id': 'NVR-02', 'ai_box_id': 'AI-BOX-07',
        'reachable': True, 'rtsp': 'healthy', 'auth': 'valid', 'cpu': 18,
        'storage': 36, 'poe': True, 'last_seen': '2026-09-29T20:55:00Z', 'fault': None
    },
    'CAM-019': {
        'asset_id': 'CAM-019', 'type': 'camera', 'site_id': 'SITE-104',
        'ip': '192.168.30.19', 'nvr_id': 'NVR-02', 'ai_box_id': 'AI-BOX-07',
        'reachable': True, 'rtsp': 'healthy', 'auth': 'valid', 'cpu': 21,
        'storage': 39, 'poe': True, 'last_seen': '2026-09-29T20:55:00Z', 'fault': None
    },
    'NVR-02': {
        'asset_id': 'NVR-02', 'type': 'nvr', 'site_id': 'SITE-104',
        'ip': '192.168.30.10', 'reachable': True, 'rtsp': 'healthy', 'cpu': 29,
        'storage': 61, 'fault': None
    },
    'AI-BOX-07': {
        'asset_id': 'AI-BOX-07', 'type': 'ai_box', 'site_id': 'SITE-104',
        'ip': '192.168.30.70', 'reachable': True, 'service': 'healthy', 'cpu': 34,
        'ram': 47, 'storage': 55, 'cloud': 'healthy', 'fault': None
    },
    'CAM-101': {
        'asset_id': 'CAM-101', 'type': 'camera', 'site_id': "Freddy Fazbear's",
        'ip': '10.10.1.101', 'nvr_id': 'NVR-101', 'ai_box_id': 'AI-BOX-101',
        'reachable': True, 'rtsp': 'healthy', 'auth': 'valid', 'cpu': 24,
        'storage': 38, 'poe': True, 'last_seen': '2026-10-08T10:00:00Z', 'fault': None
    },
    'CAM-102': {
        'asset_id': 'CAM-102', 'type': 'camera', 'site_id': "Freddy Fazbear's",
        'ip': '10.10.1.102', 'nvr_id': 'NVR-101', 'ai_box_id': 'AI-BOX-101',
        'reachable': True, 'rtsp': 'healthy', 'auth': 'valid', 'cpu': 28,
        'storage': 42, 'poe': True, 'last_seen': '2026-10-08T10:00:00Z', 'fault': None
    },
    'NVR-101': {
        'asset_id': 'NVR-101', 'type': 'nvr', 'site_id': "Freddy Fazbear's",
        'ip': '10.10.1.10', 'reachable': True, 'rtsp': 'healthy', 'cpu': 31,
        'storage': 63, 'fault': None
    },
    'AI-BOX-101': {
        'asset_id': 'AI-BOX-101', 'type': 'ai_box', 'site_id': "Freddy Fazbear's",
        'ip': '10.10.1.70', 'reachable': True, 'service': 'healthy', 'cpu': 37,
        'ram': 51, 'storage': 58, 'cloud': 'healthy', 'fault': None
    },
    'CAM-201': {
        'asset_id': 'CAM-201', 'type': 'camera', 'site_id': 'Centerpark Tower 1',
        'ip': '10.20.1.201', 'nvr_id': 'NVR-201', 'ai_box_id': 'AI-BOX-201',
        'reachable': True, 'rtsp': 'healthy', 'auth': 'valid', 'cpu': 22,
        'storage': 40, 'poe': True, 'last_seen': '2026-10-08T10:00:00Z', 'fault': None
    },
    'CAM-202': {
        'asset_id': 'CAM-202', 'type': 'camera', 'site_id': 'Centerpark Tower 1',
        'ip': '10.20.1.202', 'nvr_id': 'NVR-201', 'ai_box_id': 'AI-BOX-201',
        'reachable': True, 'rtsp': 'healthy', 'auth': 'valid', 'cpu': 26,
        'storage': 43, 'poe': True, 'last_seen': '2026-10-08T10:00:00Z', 'fault': None
    },
    'NVR-201': {
        'asset_id': 'NVR-201', 'type': 'nvr', 'site_id': 'Centerpark Tower 1',
        'ip': '10.20.1.10', 'reachable': True, 'rtsp': 'healthy', 'cpu': 33,
        'storage': 66, 'fault': None
    },
    'AI-BOX-201': {
        'asset_id': 'AI-BOX-201', 'type': 'ai_box', 'site_id': 'Centerpark Tower 1',
        'ip': '10.20.1.70', 'reachable': True, 'service': 'healthy', 'cpu': 40,
        'ram': 55, 'storage': 61, 'cloud': 'healthy', 'fault': None
    },
    'CAM-301': {
        'asset_id': 'CAM-301', 'type': 'camera', 'site_id': 'Pacman',
        'ip': '10.30.1.31', 'nvr_id': 'NVR-301', 'ai_box_id': 'AI-BOX-301',
        'reachable': True, 'rtsp': 'healthy', 'auth': 'valid', 'cpu': 25,
        'storage': 37, 'poe': True, 'last_seen': '2026-10-08T10:00:00Z', 'fault': None
    },
    'CAM-302': {
        'asset_id': 'CAM-302', 'type': 'camera', 'site_id': 'Pacman',
        'ip': '10.30.1.32', 'nvr_id': 'NVR-301', 'ai_box_id': 'AI-BOX-301',
        'reachable': True, 'rtsp': 'healthy', 'auth': 'valid', 'cpu': 29,
        'storage': 45, 'poe': True, 'last_seen': '2026-10-08T10:00:00Z', 'fault': None
    },
    'NVR-301': {
        'asset_id': 'NVR-301', 'type': 'nvr', 'site_id': 'Pacman',
        'ip': '10.30.1.10', 'reachable': True, 'rtsp': 'healthy', 'cpu': 35,
        'storage': 68, 'fault': None
    },
    'AI-BOX-301': {
        'asset_id': 'AI-BOX-301', 'type': 'ai_box', 'site_id': 'Pacman',
        'ip': '10.30.1.70', 'reachable': True, 'service': 'healthy', 'cpu': 32,
        'ram': 46, 'storage': 53, 'cloud': 'healthy', 'fault': None
    }
}

class Fault(BaseModel):
    asset_id: str
    fault: str

class Action(BaseModel):
    actor: str = 'agent'

FAULTS = {
    'network_down', 'rtsp_auth_failure', 'rtsp_down', 'high_cpu',
    'storage_full', 'poe_off', 'ai_service_down', 'cloud_down'
}


def current(asset):
    a = deepcopy(asset)
    f = a.get('fault')
    if f == 'network_down':
        a['reachable'] = False; a['last_seen'] = None
    elif f == 'rtsp_auth_failure':
        a['rtsp'] = 'auth_failed'; a['auth'] = 'invalid'
    elif f == 'rtsp_down':
        a['rtsp'] = 'unavailable'
    elif f == 'high_cpu':
        a['cpu'] = 97
    elif f == 'storage_full':
        a['storage'] = 99
    elif f == 'poe_off':
        a['poe'] = False; a['reachable'] = False; a['last_seen'] = None
    elif f == 'ai_service_down':
        a['service'] = 'down'
    elif f == 'cloud_down':
        a['cloud'] = 'unavailable'
    return a


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_asset(asset_id):
    if asset_id not in ASSETS:
        raise HTTPException(404, 'Asset not found')
    return current(ASSETS[asset_id])


@app.get('/', response_class=HTMLResponse)
def home():
    rows = ''.join(
        f'<tr><td>{a["asset_id"]}</td><td>{a["type"]}</td><td>{a["ip"]}</td><td>{a.get("reachable")}</td><td>{a.get("rtsp", "-")}</td><td>{a.get("service", "-")}</td><td>{a.get("fault") or "none"}</td></tr>'
        for a in [current(v) for v in ASSETS.values()]
    )
    return f'''<!doctype html><html><head><meta charset="utf-8"><title>Fake Portal</title>
    <style>body{{font-family:system-ui;margin:2rem}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:.5rem;text-align:left}}code{{background:#eee;padding:.15rem .3rem}}</style></head>
    <body><h1>Fake Video/AI Portal</h1><p>Emulated cameras, NVR and AI Box with controllable faults.</p><p>API: <a href="/docs">/docs</a></p>
    <table><tr><th>Asset</th><th>Type</th><th>IP</th><th>Reachable</th><th>RTSP</th><th>Service</th><th>Fault</th></tr>{rows}</table></body></html>'''


@app.get('/api/health')
def api_health():
    return {'service': 'portal', 'ok': True, 'time': now()}


@app.get('/api/assets')
def assets():
    return {'assets': [current(v) for v in ASSETS.values()]}


@app.get('/api/assets/{asset_id}/health')
def health(asset_id: str):
    a = get_asset(asset_id)
    out = {
        'asset_id': asset_id,
        'type': a['type'],
        'reachable': a.get('reachable', False),
        'fault': a.get('fault'),
        'ip': a.get('ip'),
        'site_id': a.get('site_id'),
    }
    if a['type'] == 'camera':
        out.update({'rtsp': a.get('rtsp'), 'auth': a.get('auth'), 'poe': a.get('poe'), 'cpu': a.get('cpu'), 'nvr_id': a.get('nvr_id'), 'ai_box_id': a.get('ai_box_id')})
    if a['type'] == 'nvr':
        out.update({'rtsp': a.get('rtsp'), 'cpu': a.get('cpu'), 'storage': a.get('storage')})
    if a['type'] == 'ai_box':
        out.update({'service': a.get('service'), 'cpu': a.get('cpu'), 'ram': a.get('ram'), 'storage': a.get('storage'), 'cloud': a.get('cloud')})
    return out


@app.get('/api/assets/{asset_id}/ping')
def ping(asset_id: str):
    a = get_asset(asset_id)
    return {'asset_id': asset_id, 'ok': bool(a.get('reachable', False)), 'latency_ms': 7 if a.get('reachable') else None}


@app.get('/api/assets/{asset_id}/tcp-test')
def tcp_test(asset_id: str, port: int = 554):
    a = get_asset(asset_id)
    ok = bool(a.get('reachable', False)) and not (a.get('fault') == 'network_down')
    if a['type'] not in {'camera', 'nvr'} and port == 554:
        ok = False
    return {'asset_id': asset_id, 'port': port, 'open': ok}


@app.get('/api/assets/{asset_id}/rtsp-test')
def rtsp_test(asset_id: str):
    a = get_asset(asset_id)
    if a['type'] not in {'camera', 'nvr'}:
        raise HTTPException(400, 'RTSP is not supported for this asset')
    return {
        'asset_id': asset_id,
        'stream': a.get('rtsp'),
        'auth': a.get('auth', 'not_applicable'),
        'reachable': a.get('reachable', False),
        'url_hint': f'rtsp://{a.get("ip")}:554/live/main',
    }


@app.get('/api/site/{site_id}/assets')
def site_assets(site_id: str):
    return {'assets': [current(v) for v in ASSETS.values() if v['site_id'] == site_id]}


@app.get('/api/events')
def events():
    result = []
    for asset in ASSETS.values():
        a = current(asset)
        unhealthy = (
            a.get('reachable') is False
            or a.get('rtsp') in {'auth_failed', 'unavailable'}
            or a.get('service') == 'down'
            or a.get('cloud') == 'unavailable'
            or a.get('cpu', 0) >= 90
            or a.get('storage', 0) >= 95
            or a.get('poe') is False
        )
        if unhealthy:
            result.append({'event_id': f'{a["asset_id"]}:{a.get("fault")}', 'asset_id': a['asset_id'], 'site_id': a['site_id'], 'fault': a.get('fault'), 'observed_at': now()})
    return {'events': result}


@app.post('/api/simulate/fault')
def simulate_fault(payload: Fault):
    if payload.asset_id not in ASSETS:
        raise HTTPException(404, 'Asset not found')
    if payload.fault not in FAULTS:
        raise HTTPException(400, f'Unknown fault. Use one of {sorted(FAULTS)}')
    ASSETS[payload.asset_id]['fault'] = payload.fault
    return {'ok': True, 'asset': current(ASSETS[payload.asset_id])}


@app.post('/api/assets/{asset_id}/actions/reset-simulation')
def reset(asset_id: str):
    a = get_asset(asset_id)
    ASSETS[asset_id]['fault'] = None
    return {'ok': True, 'asset': current(a)}


@app.post('/api/assets/{asset_id}/actions/reconnect-rtsp')
def reconnect_rtsp(asset_id: str, payload: Action | None = None):
    a = get_asset(asset_id)
    if a['type'] not in {'camera', 'nvr'}:
        raise HTTPException(400, 'Unsupported')
    if ASSETS[asset_id].get('fault') == 'rtsp_down':
        ASSETS[asset_id]['fault'] = None
        return {'ok': True, 'action': 'reconnect-rtsp', 'message': 'RTSP recovered', 'actor': (payload.actor if payload else 'agent')}
    return {'ok': False, 'action': 'reconnect-rtsp', 'message': 'No safe transient RTSP recovery available', 'asset': current(a)}


@app.post('/api/assets/{asset_id}/actions/restart-ai-service')
def restart_ai_service(asset_id: str, payload: Action | None = None):
    a = get_asset(asset_id)
    if a['type'] != 'ai_box':
        raise HTTPException(400, 'Asset is not an AI Box')
    if ASSETS[asset_id].get('fault') == 'ai_service_down':
        ASSETS[asset_id]['fault'] = None
        return {'ok': True, 'action': 'restart-ai-service', 'message': 'AI service recovered', 'actor': (payload.actor if payload else 'agent')}
    return {'ok': False, 'action': 'restart-ai-service', 'message': 'No simulated AI service recovery needed', 'asset': current(a)}
