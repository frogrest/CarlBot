"""Incident state machine + SQLite persistence.

Transitions follow docs/architecture/ORCHESTRATOR.md, plus one explicit
escalation edge: any active investigation state may fall through to
PENDING_TECHNICIAN when a budget is exhausted or evidence is blocked.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from .models import IncidentContext, IncidentState, utc_now

P = IncidentState

ALLOWED_TRANSITIONS: dict = {
    P.NEW: {P.CLASSIFYING, P.PENDING_TECHNICIAN},
    P.CLASSIFYING: {P.INVESTIGATING, P.PENDING_TECHNICIAN},
    P.INVESTIGATING: {P.EVIDENCE_REVIEW, P.PENDING_TECHNICIAN},
    P.EVIDENCE_REVIEW: {P.DIAGNOSED, P.INVESTIGATING, P.PENDING_TECHNICIAN},
    P.DIAGNOSED: {P.ACTION_PROPOSED, P.PENDING_TECHNICIAN},
    P.ACTION_PROPOSED: {P.SAFE_EXECUTION, P.HUMAN_REQUIRED, P.PENDING_TECHNICIAN},
    P.SAFE_EXECUTION: {P.VERIFYING, P.PENDING_TECHNICIAN},
    P.VERIFYING: {P.RESOLVED, P.PENDING_TECHNICIAN},
    P.HUMAN_REQUIRED: {P.PENDING_TECHNICIAN},
    P.PENDING_TECHNICIAN: {P.READY_FOR_VERIFICATION},
    P.READY_FOR_VERIFICATION: {P.VERIFYING, P.PENDING_TECHNICIAN},
    P.RESOLVED: set(),
}

# States where work must NOT be repeated (duplicate suppression).
SUPPRESS_STATES = {P.PENDING_TECHNICIAN, P.RESOLVED}

_SCHEMA = '''
CREATE TABLE IF NOT EXISTS incidents (
  incident_id TEXT PRIMARY KEY,
  ticket_id INTEGER NOT NULL,
  asset_id TEXT NOT NULL,
  state TEXT NOT NULL,
  diagnosis TEXT,
  confidence REAL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  context_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_incidents_ticket ON incidents(ticket_id);
CREATE INDEX IF NOT EXISTS idx_incidents_state ON incidents(state);
'''


class IllegalTransition(Exception):
    pass


def can_transition(frm: IncidentState, to: IncidentState) -> bool:
    return to in ALLOWED_TRANSITIONS.get(frm, set())


class IncidentStore:
    """Persist/load IncidentContext rows. All paths injected (tests use tmp)."""

    def __init__(self, db_path):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.executescript(_SCHEMA)
        return con

    def save(self, ctx: IncidentContext) -> None:
        ctx.updated_at = utc_now()
        active = 0 if ctx.state == IncidentState.RESOLVED else 1
        con = self._connect()
        con.execute(
            '''INSERT INTO incidents(incident_id,ticket_id,asset_id,state,diagnosis,confidence,
               active,created_at,updated_at,context_json) VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(incident_id) DO UPDATE SET state=excluded.state,
               diagnosis=excluded.diagnosis, confidence=excluded.confidence,
               active=excluded.active, updated_at=excluded.updated_at,
               context_json=excluded.context_json''',
            (ctx.incident_id, ctx.ticket_id, ctx.asset_id, ctx.state.value, ctx.diagnosis,
             ctx.confidence, active, ctx.created_at, ctx.updated_at,
             ctx.model_dump_json()),
        )
        con.commit()
        con.close()

    def get(self, incident_id: str) -> Optional[IncidentContext]:
        con = self._connect()
        row = con.execute('SELECT context_json FROM incidents WHERE incident_id=?',
                          (incident_id,)).fetchone()
        con.close()
        return IncidentContext.model_validate_json(row['context_json']) if row else None

    def latest_active_for_ticket(self, ticket_id: int) -> Optional[IncidentContext]:
        con = self._connect()
        row = con.execute(
            '''SELECT context_json FROM incidents WHERE ticket_id=? AND active=1
               ORDER BY updated_at DESC LIMIT 1''', (ticket_id,)).fetchone()
        con.close()
        return IncidentContext.model_validate_json(row['context_json']) if row else None

    def for_ticket(self, ticket_id: int) -> List[IncidentContext]:
        con = self._connect()
        rows = con.execute('SELECT context_json FROM incidents WHERE ticket_id=? ORDER BY created_at',
                           (ticket_id,)).fetchall()
        con.close()
        return [IncidentContext.model_validate_json(r['context_json']) for r in rows]


class StateMachine:
    def __init__(self, store: IncidentStore):
        self.store = store

    def transition(self, ctx: IncidentContext, to: IncidentState, reason: str = '') -> IncidentContext:
        if not can_transition(ctx.state, to):
            raise IllegalTransition(f'{ctx.state.value} -> {to.value} is not allowed')
        ctx.state = to
        if reason:
            ctx.notes.append(f'{to.value}: {reason}')
        self.store.save(ctx)
        return ctx
