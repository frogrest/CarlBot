"""Audit trail: every action decision / execution / verification.

Fields follow docs/architecture/SAFETY_POLICY.md 'Audit record'.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

_SCHEMA = '''
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  incident_id TEXT NOT NULL,
  ticket_id INTEGER NOT NULL,
  action TEXT NOT NULL,
  requester TEXT NOT NULL DEFAULT 'orchestrator',
  reason TEXT,
  evidence_ids TEXT,
  decision TEXT,
  result TEXT,
  verification TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_incident ON audit_log(incident_id);
'''


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditLog:
    def __init__(self, db_path):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.executescript(_SCHEMA)
        return con

    def record(self, *, incident_id: str, ticket_id: int, action: str,
               requester: str = 'orchestrator', reason: str = '',
               evidence_ids: Optional[List[str]] = None, decision: str = '',
               result: str = '', verification: str = '') -> int:
        con = self._connect()
        cur = con.execute(
            '''INSERT INTO audit_log(incident_id,ticket_id,action,requester,reason,
               evidence_ids,decision,result,verification,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (incident_id, ticket_id, action, requester, reason,
             ','.join(evidence_ids or []), decision, str(result)[:500],
             verification, _now()),
        )
        con.commit()
        row_id = cur.lastrowid
        con.close()
        return row_id

    def recent(self, limit: int = 50) -> List[dict]:
        con = self._connect()
        rows = con.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
        con.close()
        return [dict(r) for r in rows]
