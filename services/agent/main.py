import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from .core import Agent

HELPDESK_URL = os.getenv('HELPDESK_URL', 'http://localhost:8000')
PORTAL_URL = os.getenv('PORTAL_URL', 'http://localhost:8001')
DOCS_ROOT = os.getenv('DOCS_ROOT', '/app/docs')
POLL_INTERVAL = int(os.getenv('AGENT_POLL_INTERVAL', '5'))
AGENT_DB = Path(os.getenv('AGENT_DB', '/app/data/agent.db'))

app = FastAPI(title='Autonomous AI Ops Agent', version='0.2.0')
agent = Agent(HELPDESK_URL, PORTAL_URL, DOCS_ROOT)
stop_event = threading.Event()
worker_thread: threading.Thread | None = None


def connect():
    AGENT_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(AGENT_DB)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = connect()
    con.executescript('''
    CREATE TABLE IF NOT EXISTS runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ticket_id INTEGER NOT NULL,
      started_at TEXT NOT NULL,
      finished_at TEXT,
      status TEXT NOT NULL,
      diagnosis TEXT,
      confidence TEXT,
      auto_action TEXT,
      error TEXT
    );
    CREATE TABLE IF NOT EXISTS monitor_events (
      event_key TEXT PRIMARY KEY,
      last_seen TEXT NOT NULL,
      ticket_id INTEGER,
      active INTEGER NOT NULL DEFAULT 1
    );
    ''')
    cols = {row[1] for row in con.execute('PRAGMA table_info(monitor_events)').fetchall()}
    if 'active' not in cols:
        con.execute('ALTER TABLE monitor_events ADD COLUMN active INTEGER NOT NULL DEFAULT 1')
    con.commit(); con.close()


def now():
    return datetime.now(timezone.utc).isoformat()


def record_run(ticket_id, status='running', **kwargs):
    con = connect()
    cur = con.execute('INSERT INTO runs(ticket_id,started_at,status,diagnosis,confidence,auto_action,error) VALUES (?,?,?,?,?,?,?)', (ticket_id, now(), status, kwargs.get('diagnosis'), kwargs.get('confidence'), kwargs.get('auto_action'), kwargs.get('error')))
    con.commit(); rid = cur.lastrowid; con.close(); return rid


def finish_run(run_id, status, result=None, error=None):
    con = connect()
    con.execute('UPDATE runs SET finished_at=?, status=?, diagnosis=?, confidence=?, auto_action=?, error=? WHERE id=?', (now(), status, getattr(result, 'diagnosis', None), getattr(result, 'confidence', None), getattr(result, 'auto_action', None), error, run_id))
    con.commit(); con.close()


def monitor_once():
    """Create one helpdesk ticket per active fault episode and re-arm after recovery."""
    events = agent.client.get(f'{PORTAL_URL}/api/events').raise_for_status().json()['events']
    active_keys = {event['event_id'] for event in events}
    con = connect()
    if active_keys:
        placeholders = ','.join('?' for _ in active_keys)
        con.execute(f'UPDATE monitor_events SET active=0 WHERE event_key NOT IN ({placeholders})', tuple(active_keys))
    else:
        con.execute('UPDATE monitor_events SET active=0')
    con.commit(); con.close()

    for event in events:
        key = event['event_id']
        con = connect()
        existing = con.execute('SELECT ticket_id, active FROM monitor_events WHERE event_key=?', (key,)).fetchone()
        con.close()
        if existing and existing['active']:
            continue
        title = f"{event['asset_id']} health alert: {event.get('fault') or 'degraded'}"
        payload = {
            'title': title,
            'description': f"Automated monitor observed fault={event.get('fault')} on asset {event['asset_id']}.",
            'priority': 'high' if event.get('fault') in {'network_down','poe_off','ai_service_down'} else 'medium',
            'site_id': event['site_id'],
            'asset_id': event['asset_id'],
            'status': 'open',
        }
        ticket = agent.client.post(f'{HELPDESK_URL}/api/tickets', json=payload).raise_for_status().json()
        con = connect()
        if existing:
            con.execute('UPDATE monitor_events SET last_seen=?, ticket_id=?, active=1 WHERE event_key=?', (now(), ticket['id'], key))
        else:
            con.execute('INSERT INTO monitor_events(event_key,last_seen,ticket_id,active) VALUES (?,?,?,1)', (key, now(), ticket['id']))
        con.commit(); con.close()
        print(f'[monitor] created ticket {ticket["id"]} for {event["asset_id"]}', flush=True)


def worker():
    while not stop_event.is_set():
        try:
            monitor_once()
            tickets = agent.open_tickets()
            for t in tickets:
                # Do not re-run pending technician tickets until a technician explicitly requests verification.
                if t['status'] == 'pending_technician':
                    continue
                run_id = record_run(t['id'])
                try:
                    result = agent.process(t['id'])
                    finish_run(run_id, 'success', result=result)
                    print(f'[agent] ticket={t["id"]} diagnosis={result.diagnosis} status={result.next_status}', flush=True)
                except Exception as exc:
                    finish_run(run_id, 'error', error=str(exc))
                    print(f'[agent] ticket={t["id"]} error={exc}', flush=True)
        except Exception as exc:
            print(f'[worker] loop error: {exc}', flush=True)
        stop_event.wait(POLL_INTERVAL)


@app.on_event('startup')
def startup():
    global worker_thread
    init_db()
    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()


@app.on_event('shutdown')
def shutdown():
    stop_event.set()
    if worker_thread:
        worker_thread.join(timeout=2)
    agent.close()


@app.get('/', response_class=HTMLResponse)
def home():
    return '''<!doctype html><html><head><meta charset="utf-8"><title>AI Ops Agent</title>
    <style>body{font-family:system-ui;margin:2rem}pre{background:#111;color:#0f0;padding:1rem;overflow:auto}</style></head>
    <body><h1>Autonomous AI Ops Agent</h1><p>The worker continuously monitors the fake portal, creates helpdesk incidents, investigates tickets, performs only safe actions, and waits for technicians when human work is required.</p><p>API: <a href="/docs">/docs</a></p><p>Status: <a href="/api/status">/api/status</a></p></body></html>'''


@app.get('/api/health')
def health():
    return {'service': 'agent', 'ok': True}


@app.get('/api/status')
def status():
    con = connect()
    last_runs = con.execute('SELECT * FROM runs ORDER BY id DESC LIMIT 20').fetchall()
    con.close()
    return {'poll_interval': POLL_INTERVAL, 'running': not stop_event.is_set(), 'recent_runs': [dict(r) for r in last_runs]}


@app.post('/api/tickets/{ticket_id}/run')
def manual_run(ticket_id: int):
    try:
        run_id = record_run(ticket_id)
        try:
            result = agent.process(ticket_id)
            finish_run(run_id, 'success', result=result)
            return {'ticket_id': ticket_id, 'diagnosis': result.diagnosis, 'confidence': result.confidence, 'recommended_action': result.recommended_action, 'auto_action': result.auto_action, 'next_status': result.next_status, 'evidence': result.evidence}
        except Exception as exc:
            finish_run(run_id, 'error', error=str(exc))
            raise
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.post('/api/monitor/run')
def manual_monitor():
    monitor_once()
    return {'ok': True}


if __name__ == '__main__':
    uvicorn.run('services.agent.main:app', host='0.0.0.0', port=8002, reload=False)
