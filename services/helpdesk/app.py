import os
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from services.helpdesk.ticket_chat import query_tickets

app = FastAPI(title='Fake Helpdesk', version='0.2.0')

SCHEMA = '''
CREATE TABLE IF NOT EXISTS tickets (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  status TEXT NOT NULL,
  priority TEXT NOT NULL,
  site_id TEXT NOT NULL,
  asset_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  resolution TEXT,
  root_cause TEXT,
  ai_summary TEXT,
  ai_state TEXT
);
CREATE TABLE IF NOT EXISTS notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER NOT NULL,
  author TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_asset ON tickets(asset_id);
CREATE INDEX IF NOT EXISTS idx_tickets_updated ON tickets(updated_at);
'''

NOW = '2026-09-29T20:55:00+00:00'
SEED = [
    (1001, 'CAM-027 offline', 'Customer reports camera 27 is unavailable.', 'open', 'high', 'SITE-104', 'CAM-027', NOW, NOW, None, None, None, 'new'),
    (1002, 'CAM-018 RTSP failure', 'AI box stopped receiving RTSP from camera 18.', 'closed', 'medium', 'SITE-104', 'CAM-018', NOW, NOW, 'Corrected RTSP credentials.', 'RTSP authentication mismatch', None, 'resolved'),
    (1003, 'CAM-027 offline', 'Camera 27 lost connectivity after a switch port issue.', 'closed', 'high', 'SITE-104', 'CAM-027', NOW, NOW, 'Moved cable to a known-good PoE port.', 'Unresponsive PoE switch port', None, 'resolved'),
    (1004, 'CAM-027 intermittent', 'Camera 27 repeatedly disconnects.', 'closed', 'medium', 'SITE-104', 'CAM-027', NOW, NOW, 'Replaced Ethernet cable.', 'Damaged Ethernet cable', None, 'resolved'),
    (1005, 'AI-BOX-07 CPU warning', 'AI box CPU usage is elevated and detections are delayed.', 'closed', 'medium', 'SITE-104', 'AI-BOX-07', NOW, NOW, 'Restarted the AI inference worker after confirming a resource leak.', 'High CPU utilization', None, 'resolved'),
]

STATUS_VALUES = {'open', 'in_progress', 'pending_technician', 'ready_for_verification', 'resolved', 'closed'}


class TicketCreate(BaseModel):
    title: str
    description: str
    priority: str = 'medium'
    site_id: str
    asset_id: str
    status: str = 'open'


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    resolution: Optional[str] = None
    root_cause: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_state: Optional[str] = None


class NoteCreate(BaseModel):
    author: str
    body: str = Field(min_length=1)


class TicketChatQuery(BaseModel):
    message: str = Field(min_length=1, max_length=500)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_path() -> Path:
    """Resolve the SQLite path per call so tests can point at a temp file."""
    return Path(os.getenv('HELPDESK_DB', '/app/data/helpdesk.db'))


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    con = connect()
    con.executescript(SCHEMA)
    count = con.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
    if count == 0:
        con.executemany(
            'INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
            SEED,
        )
        con.executemany(
            'INSERT INTO notes(ticket_id,author,body,created_at) VALUES (?,?,?,?)',
            [
                (1002, 'technician', 'RTSP username/password was wrong.', NOW),
                (1003, 'technician', 'PoE port had no usable link. Known-good port restored camera.', NOW),
                (1004, 'technician', 'Cable replacement stabilized the camera.', NOW),
                (1005, 'technician', 'Resource leak was cleared by restarting the inference worker.', NOW),
            ],
        )
    con.commit()
    con.close()


@app.on_event('startup')
def startup() -> None:
    init_db()


@app.get('/', response_class=HTMLResponse)
def home():
    con = connect()
    rows = con.execute('SELECT id,title,status,priority,site_id,asset_id,updated_at,ai_state FROM tickets ORDER BY id DESC').fetchall()
    con.close()
    items = ''.join(
        f'<tr><td>{r["id"]}</td><td>{r["title"]}</td><td>{r["status"]}</td><td>{r["priority"]}</td><td>{r["site_id"]}</td><td>{r["asset_id"]}</td><td>{r["ai_state"] or "-"}</td></tr>'
        for r in rows
    )
    return HTMLResponse(f'''<!doctype html><html><head><meta charset="utf-8"><title>Fake Helpdesk</title>
    <style>body{{font-family:system-ui;margin:2rem}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:.5rem;text-align:left}}code{{background:#eee;padding:.15rem .3rem}}</style></head>
    <body><h1>Fake Helpdesk</h1><p>Tickets, technician notes, AI state and resolution history.</p>
    <p>API docs: <a href="/docs">/docs</a></p><table><tr><th>ID</th><th>Title</th><th>Status</th><th>Priority</th><th>Site</th><th>Asset</th><th>AI State</th></tr>{items}</table></body></html>''')


@app.get('/api/health')
def api_health():
    return {'service': 'helpdesk', 'ok': True}


@app.get('/api/tickets')
def list_tickets(status: Optional[str] = None, limit: int = 50):
    con = connect()
    if status:
        rows = con.execute('SELECT * FROM tickets WHERE status=? ORDER BY updated_at DESC LIMIT ?', (status, limit)).fetchall()
    else:
        rows = con.execute('SELECT * FROM tickets ORDER BY updated_at DESC LIMIT ?', (limit,)).fetchall()
    con.close()
    return {'tickets': [dict(r) for r in rows]}


@app.post('/api/tickets')
def create_ticket(payload: TicketCreate):
    if payload.status not in STATUS_VALUES:
        raise HTTPException(400, f'Unsupported status: {payload.status}')
    con = connect()
    now = utc_now()
    cur = con.execute(
        '''INSERT INTO tickets(title,description,status,priority,site_id,asset_id,created_at,updated_at,ai_state)
           VALUES (?,?,?,?,?,?,?,?,?)''',
        (payload.title, payload.description, payload.status, payload.priority, payload.site_id, payload.asset_id, now, now, 'new'),
    )
    con.commit()
    ticket_id = cur.lastrowid
    con.close()
    return get_ticket(ticket_id)


@app.get('/api/tickets/{ticket_id}')
def get_ticket(ticket_id: int):
    con = connect()
    row = con.execute('SELECT * FROM tickets WHERE id=?', (ticket_id,)).fetchone()
    if not row:
        con.close()
        raise HTTPException(404, 'Ticket not found')
    notes = con.execute('SELECT author,body,created_at FROM notes WHERE ticket_id=? ORDER BY id', (ticket_id,)).fetchall()
    con.close()
    result = dict(row)
    result['notes'] = [dict(n) for n in notes]
    return result


@app.get('/api/search')
def search(q: str, asset_id: Optional[str] = None, limit: int = 10):
    con = connect()
    like = f'%{q}%'
    base = '(title LIKE ? OR description LIKE ? OR resolution LIKE ? OR root_cause LIKE ? OR ai_summary LIKE ?)'
    params = [like, like, like, like, like]
    if asset_id:
        query = f'SELECT * FROM tickets WHERE {base} AND asset_id=? ORDER BY id DESC LIMIT ?'
        params.extend([asset_id, limit])
    else:
        query = f'SELECT * FROM tickets WHERE {base} ORDER BY id DESC LIMIT ?'
        params.append(limit)
    rows = con.execute(query, params).fetchall()
    con.close()
    return {'results': [dict(r) for r in rows]}


@app.post('/api/chat/query')
def chat_query(payload: TicketChatQuery):
    message = payload.message.strip()
    if not message:
        raise HTTPException(422, 'Message must not be blank')

    con = connect()
    try:
        tickets = [dict(row) for row in con.execute(
            'SELECT * FROM tickets ORDER BY updated_at DESC'
        ).fetchall()]
        for ticket in tickets:
            notes = con.execute(
                'SELECT author,body,created_at FROM notes WHERE ticket_id=? ORDER BY id',
                (ticket['id'],),
            ).fetchall()
            ticket['notes'] = [dict(note) for note in notes]
    finally:
        con.close()

    return query_tickets(message, tickets)


@app.patch('/api/tickets/{ticket_id}')
def update_ticket(ticket_id: int, payload: TicketUpdate):
    changes = payload.model_dump(exclude_none=True)
    if 'status' in changes and changes['status'] not in STATUS_VALUES:
        raise HTTPException(400, f'Unsupported status: {changes["status"]}')
    if not changes:
        return get_ticket(ticket_id)
    changes['updated_at'] = utc_now()
    con = connect()
    fields = [f'{k}=?' for k in changes]
    values = list(changes.values()) + [ticket_id]
    cur = con.execute(f'UPDATE tickets SET {", ".join(fields)} WHERE id=?', values)
    if cur.rowcount == 0:
        con.close()
        raise HTTPException(404, 'Ticket not found')
    con.commit()
    con.close()
    return get_ticket(ticket_id)


@app.post('/api/tickets/{ticket_id}/notes')
def add_note(ticket_id: int, payload: NoteCreate):
    con = connect()
    if con.execute('SELECT 1 FROM tickets WHERE id=?', (ticket_id,)).fetchone() is None:
        con.close()
        raise HTTPException(404, 'Ticket not found')
    con.execute('INSERT INTO notes(ticket_id,author,body,created_at) VALUES (?,?,?,?)', (ticket_id, payload.author, payload.body, utc_now()))
    con.commit()
    con.close()
    return {'ok': True, 'ticket_id': ticket_id}


@app.post('/api/tickets/{ticket_id}/request-verification')
def request_verification(ticket_id: int):
    return update_ticket(ticket_id, TicketUpdate(status='ready_for_verification'))
