"""Centralised configuration. Environment variables override defaults."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RUNTIME = DATA / "runtime"
KNOWLEDGE = DATA / "knowledge"

# Ensure directories exist at import time
for _p in (RUNTIME, KNOWLEDGE):
    _p.mkdir(parents=True, exist_ok=True)

HELPDESK_URL = os.getenv("HELPDESK_URL", "http://127.0.0.1:8001")
PORTAL_URL = os.getenv("PORTAL_URL", "http://127.0.0.1:8002")
AGENT_POLL_SECONDS = float(os.getenv("AGENT_POLL_SECONDS", "5"))
AGENT_MAX_RETRIES = int(os.getenv("AGENT_MAX_RETRIES", "3"))
AGENT_RETRY_BACKOFF = float(os.getenv("AGENT_RETRY_BACKOFF", "2"))
