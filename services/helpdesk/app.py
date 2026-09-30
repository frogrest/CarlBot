"""Fake Helpdesk Service — ticket CRUD, comments, technician notes, search.

All data is stored in a local JSON file under data/runtime/helpdesk.json.
On first start the store is seeded with realistic historical incidents.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services.common.config import RUNTIME
from services.common.models import utcnow_iso

app = FastAPI(
    title="Fake Helpdesk",
    description="Simulated helpdesk with ticket CRUD, comments, technician notes, and full-text search.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB: Path = RUNTIME / "helpdesk.json"


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _load() -> dict[str, Any]:
    if not DB.exists():
        _seed()
    for attempt in range(5):
        try:
            content = DB.read_text(encoding="utf-8")
            if not content.strip():
                _seed()
                content = DB.read_text(encoding="utf-8")
            return json.loads(content)
        except (json.JSONDecodeError, OSError):
            if attempt < 4:
                time.sleep(0.02 * (attempt + 1))
            else:
                _seed()
                return json.loads(DB.read_text(encoding="utf-8"))


def _save(data: dict[str, Any]) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    temp_path = DB.with_suffix(f".tmp.{os.getpid()}.{time.time_ns()}")
    temp_path.write_text(text, encoding="utf-8")
    for attempt in range(5):
        try:
            temp_path.replace(DB)
            return
        except OSError:
            if attempt < 4:
                time.sleep(0.01 * (attempt + 1))
            else:
                DB.write_text(text, encoding="utf-8")
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)


def _seed() -> None:
    """Create the database with realistic historical incidents."""
    if DB.exists():
        try:
            data = json.loads(DB.read_text(encoding="utf-8"))
            if data.get("tickets"):
                return
        except (json.JSONDecodeError, OSError):
            data = {"tickets": []}
    else:
        data = {"tickets": []}

    ts = utcnow_iso()
    historical: list[dict[str, Any]] = [
        {
            "id": "HIST-001",
            "title": "Lobby camera RTSP stream unavailable",
            "description": (
                "Camera CAM-001 at SITE-001 stopped publishing its RTSP stream. "
                "Ping OK, RTSP connection refused. Automated reconnect restored the stream."
            ),
            "status": "resolved",
            "site_id": "SITE-001",
            "asset_id": "CAM-001",
            "root_cause": "rtsp_down",
            "resolution": "Reconnected simulated RTSP stream worker; stream recovered within 15 seconds.",
            "created_at": ts,
            "updated_at": ts,
            "comments": [
                {"author": "autonomous-agent", "body": "RTSP check failed; ping OK. Diagnosed as stream-level issue.", "at": ts},
                {"author": "autonomous-agent", "body": "Executed reconnect_stream; verification confirmed RTSP up.", "at": ts},
            ],
            "tags": ["rtsp", "camera", "auto-resolved"],
            "technician_notes": [],
        },
        {
            "id": "HIST-002",
            "title": "Parking camera RTSP authentication failure",
            "description": (
                "Camera CAM-002 at SITE-002 reachable but RTSP authentication is rejected. "
                "Credentials may have been rotated without updating the NVR/monitoring config."
            ),
            "status": "resolved",
            "site_id": "SITE-002",
            "asset_id": "CAM-002",
            "root_cause": "rtsp_auth_failure",
            "resolution": "Technician corrected RTSP credentials in camera and NVR configuration.",
            "created_at": ts,
            "updated_at": ts,
            "comments": [
                {"author": "autonomous-agent", "body": "RTSP auth check failed. Escalated to technician.", "at": ts},
                {"author": "tech-john", "body": "Updated credentials on camera web UI and NVR config page.", "at": ts},
            ],
            "tags": ["rtsp", "auth", "technician-resolved"],
            "technician_notes": [
                {"author": "tech-john", "body": "Password had been changed during scheduled maintenance. Updated NVR profile.", "at": ts}
            ],
        },
        {
            "id": "HIST-003",
            "title": "AI Box detection service crashed",
            "description": (
                "AIBOX-001 at SITE-001 host reachable but the AI detection service was not responding. "
                "Automated service restart resolved the issue."
            ),
            "status": "resolved",
            "site_id": "SITE-001",
            "asset_id": "AIBOX-001",
            "root_cause": "ai_box_service_failure",
            "resolution": "Restarted simulated AI detection service; health check passed.",
            "created_at": ts,
            "updated_at": ts,
            "comments": [
                {"author": "autonomous-agent", "body": "AI Box service=down, host reachable. Auto-restart executed.", "at": ts},
            ],
            "tags": ["ai-box", "service", "auto-resolved"],
            "technician_notes": [],
        },
        {
            "id": "HIST-004",
            "title": "Loading camera offline — PoE power failure",
            "description": (
                "Camera CAM-003 at SITE-002 completely unreachable. PoE telemetry confirms power off. "
                "Physical investigation and PoE switch check required."
            ),
            "status": "resolved",
            "site_id": "SITE-002",
            "asset_id": "CAM-003",
            "root_cause": "poe_power_off",
            "resolution": "Technician found tripped PoE port; re-enabled and verified camera came back.",
            "created_at": ts,
            "updated_at": ts,
            "comments": [
                {"author": "autonomous-agent", "body": "Ping failed, PoE=off. Escalated: physical/power investigation.", "at": ts},
                {"author": "tech-maria", "body": "PoE port was disabled on the switch. Re-enabled port 14.", "at": ts},
            ],
            "tags": ["power", "poe", "technician-resolved"],
            "technician_notes": [
                {"author": "tech-maria", "body": "PoE port 14 on SW-SITE002-01 was in err-disabled state. Cleared and bounced.", "at": ts}
            ],
        },
        {
            "id": "HIST-005",
            "title": "NVR storage critical — 99 % utilisation",
            "description": (
                "NVR-001 at SITE-003 storage utilisation reached 99 %. Recording may stop if not addressed."
            ),
            "status": "resolved",
            "site_id": "SITE-003",
            "asset_id": "NVR-001",
            "root_cause": "storage_full",
            "resolution": "Technician adjusted retention policy from 90 to 60 days; freed 1.2 TB.",
            "created_at": ts,
            "updated_at": ts,
            "comments": [
                {"author": "autonomous-agent", "body": "Storage at 99 %. Escalated to technician for retention review.", "at": ts},
            ],
            "tags": ["storage", "nvr", "technician-resolved"],
            "technician_notes": [
                {"author": "tech-john", "body": "Changed retention from 90 to 60 days. Current usage now 62 %.", "at": ts}
            ],
        },
        {
            "id": "HIST-006",
            "title": "Intermittent connectivity to lobby camera",
            "description": (
                "CAM-001 at SITE-001 showing intermittent packet loss. Possibly a cabling or switch issue."
            ),
            "status": "resolved",
            "site_id": "SITE-001",
            "asset_id": "CAM-001",
            "root_cause": "intermittent_connectivity",
            "resolution": "Cleared transient state; connectivity stabilised after simulated network recovery.",
            "created_at": ts,
            "updated_at": ts,
            "comments": [],
            "tags": ["network", "intermittent", "auto-resolved"],
            "technician_notes": [],
        },
        {
            "id": "HIST-007",
            "title": "Cloud sync failure on AI Box",
            "description": (
                "AIBOX-001 cloud upload queue stalled. Local detections are buffered but not synced."
            ),
            "status": "resolved",
            "site_id": "SITE-001",
            "asset_id": "AIBOX-001",
            "root_cause": "cloud_sync_failure",
            "resolution": "Retried cloud upload; sync recovered.",
            "created_at": ts,
            "updated_at": ts,
            "comments": [],
            "tags": ["cloud", "sync", "auto-resolved"],
            "technician_notes": [],
        },
    ]
    data["tickets"] = historical
    _save(data)


# Run seed on module load so the DB is always available
_seed()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class TicketCreate(BaseModel):
    title: str
    description: str
    site_id: str
    asset_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class CommentCreate(BaseModel):
    author: str
    body: str


class TechnicianNote(BaseModel):
    author: str
    body: str


class TicketUpdate(BaseModel):
    status: str | None = None
    root_cause: str | None = None
    resolution: str | None = None
    tags: list[str] | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
def health():
    return {"ok": True, "service": "helpdesk"}


@app.get("/tickets", tags=["tickets"])
def list_tickets(status: str | None = None, asset_id: str | None = None, site_id: str | None = None):
    """List tickets, optionally filtered by status, asset_id, or site_id."""
    tickets = _load()["tickets"]
    if status:
        tickets = [t for t in tickets if t["status"] == status]
    if asset_id:
        tickets = [t for t in tickets if t.get("asset_id") == asset_id]
    if site_id:
        tickets = [t for t in tickets if t.get("site_id") == site_id]
    return tickets


@app.get("/tickets/{ticket_id}", tags=["tickets"])
def get_ticket(ticket_id: str):
    for t in _load()["tickets"]:
        if t["id"] == ticket_id:
            return t
    raise HTTPException(status_code=404, detail="Ticket not found")


@app.post("/tickets", status_code=201, tags=["tickets"])
def create_ticket(payload: TicketCreate):
    data = _load()
    now = utcnow_iso()
    ticket: dict[str, Any] = payload.model_dump()
    ticket.update(
        id=f"T-{uuid.uuid4().hex[:8]}",
        status="open",
        root_cause=None,
        resolution=None,
        created_at=now,
        updated_at=now,
        comments=[],
        technician_notes=[],
    )
    data["tickets"].append(ticket)
    _save(data)
    return ticket


@app.post("/tickets/{ticket_id}/comments", tags=["tickets"])
def add_comment(ticket_id: str, payload: CommentCreate):
    data = _load()
    for t in data["tickets"]:
        if t["id"] == ticket_id:
            t.setdefault("comments", []).append(
                {**payload.model_dump(), "at": utcnow_iso()}
            )
            t["updated_at"] = utcnow_iso()
            _save(data)
            return t
    raise HTTPException(status_code=404, detail="Ticket not found")


@app.post("/tickets/{ticket_id}/technician-notes", tags=["tickets"])
def add_technician_note(ticket_id: str, payload: TechnicianNote):
    """Technicians can add their own notes, separate from agent comments."""
    data = _load()
    for t in data["tickets"]:
        if t["id"] == ticket_id:
            t.setdefault("technician_notes", []).append(
                {**payload.model_dump(), "at": utcnow_iso()}
            )
            t["updated_at"] = utcnow_iso()
            _save(data)
            return t
    raise HTTPException(status_code=404, detail="Ticket not found")


@app.patch("/tickets/{ticket_id}", tags=["tickets"])
def update_ticket(ticket_id: str, payload: TicketUpdate):
    data = _load()
    for t in data["tickets"]:
        if t["id"] == ticket_id:
            for key, value in payload.model_dump(exclude_none=True).items():
                t[key] = value
            t["updated_at"] = utcnow_iso()
            _save(data)
            return t
    raise HTTPException(status_code=404, detail="Ticket not found")


@app.get("/search", tags=["tickets"])
def search_tickets(q: str = Query(..., min_length=1)):
    """Full-text search across all ticket fields."""
    query = q.lower()
    return [t for t in _load()["tickets"] if query in json.dumps(t).lower()]


@app.get("/stats", tags=["system"])
def stats():
    """Quick overview stats for the helpdesk."""
    tickets = _load()["tickets"]
    by_status: dict[str, int] = {}
    for t in tickets:
        by_status[t["status"]] = by_status.get(t["status"], 0) + 1
    return {"total": len(tickets), "by_status": by_status}
