import os
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from services.helpdesk.chat_knowledge import KnowledgeRetriever
from services.helpdesk.chat_reasoner import answer_with_reasoning
from services.helpdesk.ticket_chat import query_tickets
from services.local_llm import (
    ModelDownloader,
    ModelStore,
    build_llm_router,
    LocalLlmRuntime,
)
from services.local_llm.config import DEFAULT_MODELS_DIR

# Managed local model server (no API key). Non-blocking when unconfigured.
# The store/downloader add the curated choose-and-download surface; the runtime
# uses the store's selection when one is installed.
local_llm_store = ModelStore(os.getenv('LOCAL_LLM_MODELS_DIR') or DEFAULT_MODELS_DIR)
local_llm_downloader = ModelDownloader(local_llm_store)
local_llm_runtime = LocalLlmRuntime.from_env(store=local_llm_store)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    local_llm_runtime.ensure_started()
    try:
        yield
    finally:
        local_llm_runtime.stop()


app = FastAPI(title='Fake Helpdesk', version='0.2.0', lifespan=lifespan)
app.include_router(build_llm_router(local_llm_store, local_llm_downloader, local_llm_runtime))

SCHEMA = '''
CREATE TABLE IF NOT EXISTS tickets (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  status TEXT NOT NULL,
  ticket_status TEXT NOT NULL DEFAULT 'Open',
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
CREATE TABLE IF NOT EXISTS customer_replies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ticket_id INTEGER NOT NULL,
  author TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL,
  idempotency_key TEXT UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_asset ON tickets(asset_id);
CREATE INDEX IF NOT EXISTS idx_tickets_updated ON tickets(updated_at);
CREATE INDEX IF NOT EXISTS idx_customer_replies_ticket ON customer_replies(ticket_id);
'''

NOW = '2026-09-29T20:55:00+00:00'
SEED = [
    (1001, 'CAM-027 offline', 'Customer reports camera 27 is unavailable.', 'open', 'Open', 'high', 'SITE-104', 'CAM-027', NOW, NOW, None, None, None, 'new'),
    (1002, 'CAM-018 RTSP failure', 'AI box stopped receiving RTSP from camera 18.', 'closed', 'Closed', 'medium', 'SITE-104', 'CAM-018', NOW, NOW, 'Corrected RTSP credentials.', 'RTSP authentication mismatch', None, 'resolved'),
    (1003, 'CAM-027 offline', 'Camera 27 lost connectivity after a switch port issue.', 'closed', 'Closed', 'high', 'SITE-104', 'CAM-027', NOW, NOW, 'Moved cable to a known-good PoE port.', 'Unresponsive PoE switch port', None, 'resolved'),
    (1004, 'CAM-027 intermittent', 'Camera 27 repeatedly disconnects.', 'closed', 'Closed', 'medium', 'SITE-104', 'CAM-027', NOW, NOW, 'Replaced Ethernet cable.', 'Damaged Ethernet cable', None, 'resolved'),
    (1005, 'AI-BOX-07 CPU warning', 'AI box CPU usage is elevated and detections are delayed.', 'closed', 'Answered', 'medium', 'SITE-104', 'AI-BOX-07', NOW, NOW, 'Restarted the AI inference worker after confirming a resource leak.', 'High CPU utilization', None, 'resolved'),
]

STATUS_VALUES = {'open', 'in_progress', 'pending_technician', 'ready_for_verification', 'resolved', 'closed'}
TICKET_STATUS_VALUES = {'Open', 'Answered', 'Closed'}


def ticket_status_for_workflow(status: str) -> str:
    if status == 'closed':
        return 'Closed'
    if status in {'pending_technician', 'ready_for_verification', 'resolved'}:
        return 'Answered'
    return 'Open'


DEMO_SEED = [
    (1020, 'CAM-101 live view is unavailable', "The front dining-room camera at Freddy Fazbear's stopped loading in the operator console.", 'open', 'Open', 'high', "Freddy Fazbear's", 'CAM-101', '2026-10-01T09:10:00+00:00', '2026-10-01T09:10:00+00:00', None, None, None, 'new'),
    (1021, 'AI-BOX-101 processing delay', 'Motion events from the east hall are arriving several minutes late.', 'pending_technician', 'Answered', 'medium', "Freddy Fazbear's", 'AI-BOX-101', '2026-10-01T10:20:00+00:00', '2026-10-02T11:30:00+00:00', None, 'High inference queue latency', 'Queue delay observed; waiting for an on-site workload review.', 'awaiting_technician'),
    (1022, 'NVR-101 clock drift', 'Recorded clips appear about four minutes ahead of the site clock.', 'closed', 'Closed', 'low', "Freddy Fazbear's", 'NVR-101', '2026-10-01T11:45:00+00:00', '2026-10-03T13:00:00+00:00', 'Time synchronization was corrected and clip timestamps were checked.', 'NTP offset', None, 'resolved'),
    (1023, 'CAM-102 repeated motion alerts', 'The kitchen entry camera creates multiple alerts for one person passing through.', 'ready_for_verification', 'Answered', 'medium', "Freddy Fazbear's", 'CAM-102', '2026-10-02T08:05:00+00:00', '2026-10-04T08:05:00+00:00', None, 'Possible overlapping detection zones', 'Updated zone review recorded; verify alert count with the site operator.', 'ready_for_verification'),
    (1024, 'CAM-201 lobby stream drops', 'The lobby feed at Centerpark Tower 1 freezes briefly throughout the afternoon.', 'open', 'Open', 'urgent', 'Centerpark Tower 1', 'CAM-201', '2026-10-02T09:15:00+00:00', '2026-10-02T09:15:00+00:00', None, None, None, 'new'),
    (1025, 'NVR-201 storage nearing capacity', 'Recorder storage is above the alert threshold; retention status needs review.', 'closed', 'Closed', 'high', 'Centerpark Tower 1', 'NVR-201', '2026-10-02T12:30:00+00:00', '2026-10-05T14:10:00+00:00', 'Retention report reviewed with the site operator; no recordings were deleted.', 'Storage utilization warning', None, 'resolved'),
    (1026, 'AI-BOX-201 analytics running slowly', 'People-count summaries for the north entrance are delayed compared with live video.', 'in_progress', 'Open', 'high', 'Centerpark Tower 1', 'AI-BOX-201', '2026-10-03T07:50:00+00:00', '2026-10-03T09:00:00+00:00', None, 'Possible inference backlog', 'Investigation is collecting fresh service and load evidence.', 'investigating'),
    (1027, 'CAM-202 night image is too dark', 'The parking-level camera image is difficult to interpret after sunset.', 'pending_technician', 'Answered', 'medium', 'Centerpark Tower 1', 'CAM-202', '2026-10-03T18:20:00+00:00', '2026-10-04T08:45:00+00:00', None, None, 'A technician needs to compare the image with the approved site view.', 'awaiting_technician'),
    (1028, 'CAM-301 intermittent connection', 'The arcade entrance feed at Pacman disconnects and reconnects during busy hours.', 'open', 'Open', 'medium', 'Pacman', 'CAM-301', '2026-10-04T08:00:00+00:00', '2026-10-04T08:00:00+00:00', None, None, None, 'new'),
    (1029, 'AI-BOX-301 cloud sync delay', 'Event summaries are visible locally but are late in the synthetic cloud dashboard.', 'closed', 'Closed', 'medium', 'Pacman', 'AI-BOX-301', '2026-10-04T10:10:00+00:00', '2026-10-05T11:25:00+00:00', 'Synchronization recovered in the emulator and a follow-up check passed.', 'Temporary cloud synchronization interruption', None, 'resolved'),
    (1030, 'CAM-302 false motion alerts', 'Reflections from the prize counter trigger motion alerts when the room is empty.', 'ready_for_verification', 'Answered', 'high', 'Pacman', 'CAM-302', '2026-10-04T11:40:00+00:00', '2026-10-06T09:30:00+00:00', None, 'Reflection may overlap the detection region', 'A technician reviewed the view; confirm behavior during the next quiet period.', 'ready_for_verification'),
    (1031, 'NVR-301 fan warning', 'The recorder reports a fan warning, but recordings remain available.', 'pending_technician', 'Answered', 'medium', 'Pacman', 'NVR-301', '2026-10-04T14:00:00+00:00', '2026-10-04T15:00:00+00:00', None, None, 'Physical inspection is required; no hardware change was made.', 'awaiting_technician'),
    (1032, 'CAM-101 packet loss report', 'The dining-room camera image is occasionally choppy during evening service.', 'closed', 'Closed', 'low', "Freddy Fazbear's", 'CAM-101', '2026-10-05T08:20:00+00:00', '2026-10-06T13:50:00+00:00', 'A short-lived emulator network fault cleared; playback was verified afterward.', 'Transient packet loss', None, 'resolved'),
    (1033, 'CAM-201 timestamps differ from lobby display', 'Camera event timestamps do not line up with the lobby clock shown by staff.', 'open', 'Open', 'medium', 'Centerpark Tower 1', 'CAM-201', '2026-10-05T09:30:00+00:00', '2026-10-05T09:30:00+00:00', None, None, None, 'new'),
    (1034, 'AI-BOX-301 missed event summaries', 'The operator reports that a few expected event summaries are absent from the daily view.', 'open', 'Open', 'urgent', 'Pacman', 'AI-BOX-301', '2026-10-05T11:05:00+00:00', '2026-10-05T11:05:00+00:00', None, None, None, 'new'),
    (1035, 'CAM-102 stream authentication check', 'The technician reports an authentication error on the west hallway test stream.', 'closed', 'Closed', 'medium', "Freddy Fazbear's", 'CAM-102', '2026-10-05T13:15:00+00:00', '2026-10-06T10:00:00+00:00', 'Approved stream settings were verified by a technician; credentials were not changed by automation.', 'Stream authentication mismatch reported', None, 'resolved'),
    (1036, 'NVR-201 duplicate channel listing', 'Two recorder entries appear to reference the same synthetic camera channel.', 'pending_technician', 'Answered', 'low', 'Centerpark Tower 1', 'NVR-201', '2026-10-06T07:30:00+00:00', '2026-10-06T08:15:00+00:00', None, None, 'Requesting a human review of the site channel inventory.', 'awaiting_technician'),
    (1037, 'CAM-302 image focus concern', 'The back arcade camera image looks softer than last week in the attached synthetic report.', 'closed', 'Closed', 'low', 'Pacman', 'CAM-302', '2026-10-06T12:00:00+00:00', '2026-10-07T10:15:00+00:00', 'Technician confirmed the current emulator image is stable; physical focus cannot be assessed here.', 'No focus fault observable in emulator', None, 'resolved'),
    (1038, 'CAM-202 cloud event upload delayed', 'Motion events appear locally before they show up in the site summary.', 'in_progress', 'Open', 'high', 'Centerpark Tower 1', 'CAM-202', '2026-10-07T08:25:00+00:00', '2026-10-07T09:10:00+00:00', None, 'Possible upload queue delay', 'Collecting current portal evidence; no configuration changes made.', 'investigating'),
    (1039, 'AI-BOX-101 alert backlog review', 'The daily report contains a larger-than-usual backlog of routine detections.', 'ready_for_verification', 'Answered', 'medium', "Freddy Fazbear's", 'AI-BOX-101', '2026-10-07T14:45:00+00:00', '2026-10-08T08:00:00+00:00', None, 'Backlog reduced during last observation', 'Review the next scheduled report before closing.', 'ready_for_verification'),
]

DEMO_NOTES = {
    1020: ['The simulated portal reports the asset healthy at last check; collect a fresh stream probe before diagnosing.'],
    1021: ['Operator confirmed that live video is available while the event summary is delayed.'],
    1022: ['Technician compared a new clip timestamp with the synthetic site clock.'],
    1023: ['One test walk produced two alerts near the zone boundary.'],
    1024: ['The report affects the lobby view only; no physical network has been contacted.'],
    1025: ['Retention settings were reviewed only; no footage was removed.'],
    1026: ['Current investigation is read-only and limited to the emulated service.'],
    1027: ['Image quality needs an on-site visual check; the emulator cannot inspect lens condition.'],
    1028: ['The caller noticed brief gaps but did not report a complete outage.'],
    1029: ['Local event history remained available during the reported sync delay.'],
    1030: ['Alert timing overlaps with bright reflections in the reported camera view.'],
    1031: ['Recorder is still reachable; fan service is a technician task.'],
    1032: ['Playback was checked after the simulated transient cleared.'],
    1033: ['The time source for the staff display has not yet been confirmed.'],
    1034: ['No missing recordings have been established; this is a report awaiting evidence.'],
    1035: ['No password or credential values are stored in this ticket.'],
    1036: ['Channel mapping requires confirmation against an approved inventory.'],
    1037: ['Physical focus and lens condition cannot be verified using this emulator.'],
    1038: ['The synthetic portal remains the only source used for diagnostics.'],
    1039: ['No action has been reported as complete; verification is still pending.'],
}


class TicketCreate(BaseModel):
    title: str
    description: str
    priority: str = 'medium'
    site_id: str
    asset_id: str
    status: str = 'open'


class TicketUpdate(BaseModel):
    status: Optional[str] = None
    ticket_status: Optional[str] = None
    resolution: Optional[str] = None
    root_cause: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_state: Optional[str] = None


class NoteCreate(BaseModel):
    author: str
    body: str = Field(min_length=1)


class CustomerReplyCreate(BaseModel):
    author: str = 'technician'
    body: str = Field(min_length=1, max_length=1500)
    idempotency_key: Optional[str] = Field(default=None, max_length=100)


class ChatTurn(BaseModel):
    role: str = Field(pattern=r'^(user|assistant)$')
    content: str = Field(min_length=1, max_length=1000)


class TicketChatQuery(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    ticket_id: Optional[int] = Field(default=None, gt=0)
    history: list[ChatTurn] = Field(default_factory=list, max_length=10)


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
    columns = {row['name'] for row in con.execute('PRAGMA table_info(tickets)')}
    if 'ticket_status' not in columns:
        con.execute("ALTER TABLE tickets ADD COLUMN ticket_status TEXT NOT NULL DEFAULT 'Open'")
        con.execute(
            """UPDATE tickets SET ticket_status = CASE
                WHEN status = 'closed' THEN 'Closed'
                WHEN status IN ('pending_technician', 'ready_for_verification', 'resolved') THEN 'Answered'
                ELSE 'Open'
            END"""
        )
    count = con.execute('SELECT COUNT(*) FROM tickets').fetchone()[0]
    if count == 0:
        con.executemany(
            '''INSERT INTO tickets(
                id,title,description,status,ticket_status,priority,site_id,asset_id,
                created_at,updated_at,resolution,root_cause,ai_summary,ai_state
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
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
    for ticket in DEMO_SEED:
        inserted = con.execute(
            '''INSERT OR IGNORE INTO tickets(
                id,title,description,status,ticket_status,priority,site_id,asset_id,
                created_at,updated_at,resolution,root_cause,ai_summary,ai_state
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            ticket,
        )
        if inserted.rowcount:
            con.executemany(
                'INSERT INTO notes(ticket_id,author,body,created_at) VALUES (?,?,?,?)',
                [(ticket[0], 'technician', body, ticket[9]) for body in DEMO_NOTES.get(ticket[0], [])],
            )
    con.commit()
    con.close()


@app.get('/', response_class=HTMLResponse)
def home():
    con = connect()
    rows = con.execute('SELECT id,title,status,ticket_status,priority,site_id,asset_id,updated_at,ai_state FROM tickets ORDER BY id DESC').fetchall()
    con.close()
    items = ''.join(
        f'<tr><td>{r["id"]}</td><td>{r["title"]}</td><td>{r["ticket_status"]}</td><td>{r["status"]}</td><td>{r["priority"]}</td><td>{r["site_id"]}</td><td>{r["asset_id"]}</td><td>{r["ai_state"] or "-"}</td></tr>'
        for r in rows
    )
    return HTMLResponse(f'''<!doctype html><html><head><meta charset="utf-8"><title>Fake Helpdesk</title>
    <style>body{{font-family:system-ui;margin:2rem}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:.5rem;text-align:left}}code{{background:#eee;padding:.15rem .3rem}}</style></head>
    <body><h1>Fake Helpdesk</h1><p>Tickets, technician notes, helpdesk status, AI workflow state and resolution history.</p>
    <p>API docs: <a href="/docs">/docs</a></p><table><tr><th>ID</th><th>Title</th><th>Ticket Status</th><th>Workflow Status</th><th>Priority</th><th>Site</th><th>Asset</th><th>AI State</th></tr>{items}</table></body></html>''')


@app.get('/api/health')
def api_health():
    return {'service': 'helpdesk', 'ok': True}


@app.get('/api/llm/status')
def llm_status():
    """Truthful managed-runtime state (no secrets exposed)."""
    return local_llm_runtime.status().as_dict()


@app.post('/api/llm/start')
def llm_start():
    """Retry loading the configured local model. Idempotent; takes no body."""
    return local_llm_runtime.ensure_started().as_dict()


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
        '''INSERT INTO tickets(title,description,status,ticket_status,priority,site_id,asset_id,created_at,updated_at,ai_state)
           VALUES (?,?,?,?,?,?,?,?,?,?)''',
        (payload.title, payload.description, payload.status, ticket_status_for_workflow(payload.status), payload.priority, payload.site_id, payload.asset_id, now, now, 'new'),
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
    replies = con.execute(
        'SELECT id,ticket_id,author,body,created_at,idempotency_key FROM customer_replies WHERE ticket_id=? ORDER BY id',
        (ticket_id,),
    ).fetchall()
    con.close()
    result = dict(row)
    result['notes'] = [dict(n) for n in notes]
    result['customer_replies'] = [dict(r) for r in replies]
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


@app.get('/api/knowledge')
def get_knowledge_documents():
    retriever = KnowledgeRetriever()
    if not retriever.root.is_dir():
        return {'documents': []}

    from services.helpdesk.chat_knowledge import APPROVED_SUBDIRS, _parse_sections
    docs = []
    for path in sorted(retriever.root.rglob('*.md')):
        try:
            rel = path.relative_to(retriever.root)
        except ValueError:
            continue
        parts = rel.parts
        if not parts or parts[0] not in APPROVED_SUBDIRS:
            continue
        try:
            text = path.read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        sections = _parse_sections(text, rel.as_posix())
        title = path.stem.replace('_', ' ').replace('-', ' ').title()
        if sections and sections[0].get('title'):
            title = sections[0]['title']
        docs.append({
            'id': rel.as_posix().replace('/', '-').replace('.', '-').lower(),
            'title': title,
            'category': parts[0],
            'source_path': f'docs/{rel.as_posix()}',
            'sections': sections,
            'raw_text': text,
        })
    return {'documents': docs}


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
            replies = con.execute(
                'SELECT author,body,created_at FROM customer_replies WHERE ticket_id=? ORDER BY id',
                (ticket['id'],),
            ).fetchall()
            ticket['notes'] = [dict(note) for note in notes]
            ticket['customer_replies'] = [dict(reply) for reply in replies]
    finally:
        con.close()

    try:
        result = query_tickets(message, tickets, context_ticket_id=payload.ticket_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

    # Retrieve approved local knowledge documentation
    retriever = KnowledgeRetriever()
    # Search using user query and any issue words
    knowledge_sources = retriever.search(message, limit=3)

    return answer_with_reasoning(
        message,
        result,
        context_ticket_id=payload.ticket_id,
        conversation_history=[turn.model_dump() for turn in payload.history],
        knowledge_sources=knowledge_sources,
        runtime=local_llm_runtime,
    )


@app.patch('/api/tickets/{ticket_id}')
def update_ticket(ticket_id: int, payload: TicketUpdate):
    changes = payload.model_dump(exclude_none=True)
    if 'status' in changes and changes['status'] not in STATUS_VALUES:
        raise HTTPException(400, f'Unsupported status: {changes["status"]}')
    if 'ticket_status' in changes and changes['ticket_status'] not in TICKET_STATUS_VALUES:
        raise HTTPException(400, f'Unsupported ticket status: {changes["ticket_status"]}')
    if 'status' in changes and 'ticket_status' not in changes:
        changes['ticket_status'] = ticket_status_for_workflow(changes['status'])
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


@app.post('/api/tickets/{ticket_id}/customer-replies')
def add_customer_reply(ticket_id: int, payload: CustomerReplyCreate):
    con = connect()
    if con.execute('SELECT 1 FROM tickets WHERE id=?', (ticket_id,)).fetchone() is None:
        con.close()
        raise HTTPException(404, 'Ticket not found')

    # If idempotency_key is supplied and already recorded, return the existing reply safely
    if payload.idempotency_key:
        existing = con.execute(
            'SELECT id,ticket_id,author,body,created_at,idempotency_key FROM customer_replies WHERE idempotency_key=?',
            (payload.idempotency_key,),
        ).fetchone()
        if existing:
            con.close()
            return {'ok': True, 'ticket_id': ticket_id, 'reply': dict(existing), 'duplicate': True}

    now = utc_now()
    try:
        cur = con.execute(
            'INSERT INTO customer_replies(ticket_id,author,body,created_at,idempotency_key) VALUES (?,?,?,?,?)',
            (ticket_id, payload.author, payload.body, now, payload.idempotency_key),
        )
        con.commit()
        reply_id = cur.lastrowid
    except sqlite3.IntegrityError:
        # Idempotency collision
        existing = con.execute(
            'SELECT id,ticket_id,author,body,created_at,idempotency_key FROM customer_replies WHERE idempotency_key=?',
            (payload.idempotency_key,),
        ).fetchone()
        con.close()
        if existing:
            return {'ok': True, 'ticket_id': ticket_id, 'reply': dict(existing), 'duplicate': True}
        raise HTTPException(409, 'Conflict on idempotency key')
    con.close()
    return {
        'ok': True,
        'ticket_id': ticket_id,
        'reply': {
            'id': reply_id,
            'ticket_id': ticket_id,
            'author': payload.author,
            'body': payload.body,
            'created_at': now,
            'idempotency_key': payload.idempotency_key,
        },
    }


@app.post('/api/tickets/{ticket_id}/request-verification')
def request_verification(ticket_id: int):
    return update_ticket(ticket_id, TicketUpdate(status='ready_for_verification'))
