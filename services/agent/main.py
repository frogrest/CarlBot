import os
import sqlite3
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from .core import Agent
from .orchestrator import Budget, IncidentState, IncidentStore, Orchestrator
from .policy import AuditLog, PolicyEngine
from .reasoning import configured_reasoner
from .tools import ToolBus

HELPDESK_URL = os.getenv('HELPDESK_URL', 'http://localhost:8000')
PORTAL_URL = os.getenv('PORTAL_URL', 'http://localhost:8001')
DOCS_ROOT = os.getenv('DOCS_ROOT', '/app/docs')
POLL_INTERVAL = int(os.getenv('AGENT_POLL_INTERVAL', '5'))
AGENT_DB = Path(os.getenv('AGENT_DB', '/app/data/agent.db'))

app = FastAPI(title='Autonomous AI Ops Agent', version='0.2.0')
agent = Agent(HELPDESK_URL, PORTAL_URL, DOCS_ROOT)
reasoner = configured_reasoner()
stop_event = threading.Event()
worker_thread: threading.Thread | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global worker_thread
    init_db()
    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()
    try:
        yield
    finally:
        stop_event.set()
        if worker_thread:
            worker_thread.join(timeout=2)
        reasoner.close()
        agent.close()


app.router.lifespan_context = lifespan


def build_orchestrator() -> Orchestrator:
    """Assemble the orchestrator stack on shared paths (tests inject their own)."""
    store = IncidentStore(AGENT_DB)
    return Orchestrator(
        tools=ToolBus(HELPDESK_URL, PORTAL_URL, client=agent.client, docs_root=DOCS_ROOT),
        store=store,
        policy=PolicyEngine(),
        audit=AuditLog(AGENT_DB),
        reasoner=reasoner,
    )


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


def _incident_to_ticket_fields(ctx) -> dict:
    """Map orchestrator outcome onto helpdesk ticket fields (Phase 2)."""
    if ctx.state == IncidentState.RESOLVED:
        return {
            'status': 'resolved', 'ai_state': 'resolved',
            'ai_summary': ctx.notes[-1] if ctx.notes else ctx.diagnosis or '',
            'root_cause': ctx.diagnosis,
            'resolution': (ctx.verification.detail if ctx.verification else None),
        }
    if ctx.state == IncidentState.PENDING_TECHNICIAN:
        return {
            'status': 'pending_technician', 'ai_state': 'awaiting_technician',
            'ai_summary': ctx.notes[-1] if ctx.notes else ctx.diagnosis or '',
            'root_cause': ctx.diagnosis,
        }
    return {'status': 'in_progress', 'ai_state': 'investigating'}


def process_ticket(ticket_id: int, orchestrator=None):
    """Run one ticket through the orchestrator and reflect the outcome."""
    ticket = agent.ticket(ticket_id)
    agent._update_ticket(ticket_id, status='in_progress', ai_state='investigating')
    orch = orchestrator or build_orchestrator()
    ctx = orch.run(ticket)
    fields = _incident_to_ticket_fields(ctx)
    note = (
        f'Diagnosis: {ctx.diagnosis}\nConfidence: {ctx.confidence}\n'
        f'Route: {[r["agent"] for r in ctx.route]}\n'
        f'State: {ctx.state.value}'
    )
    if ctx.verification is not None:
        outcome = 'passed' if ctx.verification.passed else 'failed'
        note += f'\nVerification {outcome}: {ctx.verification.detail}'
    else:
        note += '\nVerification not performed'
    if ctx.handoff:
        note += f'\nTechnician action: {ctx.handoff.requested_action}'
    agent._note(ticket_id, note)
    agent._update_ticket(ticket_id, **fields)
    return ctx


def worker():
    while not stop_event.is_set():
        try:
            monitor_once()
            tickets = agent.open_tickets()
            for t in tickets:
                # Do not re-run pending technician tickets until a technician explicitly requests verification.
                if t['status'] == 'pending_technician':
                    # Technician-approved re-entry: orchestrator resumes via READY_FOR_VERIFICATION.
                    if t.get('ai_state') == 'verify_requested':
                        try:
                            orch = build_orchestrator()
                            ctx = orch.store.latest_active_for_ticket(t['id'])
                            if ctx is not None and ctx.state == IncidentState.PENDING_TECHNICIAN:
                                orch.machine.transition(ctx, IncidentState.READY_FOR_VERIFICATION, 'technician requested verification')
                                agent._update_ticket(t['id'], status='in_progress', ai_state='investigating')
                        except Exception as exc:
                            print(f'[agent] ticket={t["id"]} verify handoff error={exc}', flush=True)
                            continue
                    else:
                        continue
                run_id = record_run(t['id'])
                try:
                    ctx = process_ticket(t['id'])
                    finish_run(run_id, 'success', result=type('R', (), {
                        'diagnosis': ctx.diagnosis,
                        'confidence': str(ctx.confidence),
                        'auto_action': ctx.executed_actions[-1] if ctx.executed_actions else None,
                    })())
                    print(f'[agent] ticket={t["id"]} diagnosis={ctx.diagnosis} state={ctx.state.value}', flush=True)
                except Exception as exc:
                    finish_run(run_id, 'error', error=str(exc))
                    print(f'[agent] ticket={t["id"]} error={exc}', flush=True)
        except Exception as exc:
            print(f'[worker] loop error: {exc}', flush=True)
        stop_event.wait(POLL_INTERVAL)


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
            ctx = process_ticket(ticket_id)
            finish_run(run_id, 'success', result=type('R', (), {
                'diagnosis': ctx.diagnosis,
                'confidence': str(ctx.confidence),
                'auto_action': ctx.executed_actions[-1] if ctx.executed_actions else None,
            })())
            return {'ticket_id': ticket_id, 'diagnosis': ctx.diagnosis, 'confidence': str(ctx.confidence),
                    'state': ctx.state.value, 'route': ctx.route,
                    'auto_action': ctx.executed_actions[-1] if ctx.executed_actions else None}
        except Exception as exc:
            finish_run(run_id, 'error', error=str(exc))
            raise
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.get('/api/incidents/{ticket_id}')
def incident_for_ticket(ticket_id: int):
    """Inspect the latest orchestrator incident for a ticket (Phase 2 debugging)."""
    try:
        ctx = IncidentStore(AGENT_DB).latest_active_for_ticket(ticket_id)
    except Exception as exc:
        raise HTTPException(500, str(exc))
    if ctx is None:
        raise HTTPException(404, 'No incident for this ticket')
    return ctx.model_dump()


@app.post('/api/monitor/run')
def manual_monitor():
    monitor_once()
    return {'ok': True}


if __name__ == '__main__':
    uvicorn.run('services.agent.main:app', host='0.0.0.0', port=8002, reload=False)
