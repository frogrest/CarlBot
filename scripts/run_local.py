"""One-command local launcher — starts all four backend services and the Vite frontend.

Usage:
    python scripts/run_local.py           # Starts backend + web UI on port 5173
    python scripts/run_local.py --no-ui   # Starts backend services only

Ctrl+C stops all child processes cleanly.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"

parser = argparse.ArgumentParser(description="Start the EG CCTV Support Lab services and Web UI.")
parser.add_argument("--ui", action="store_true", default=True, help="Start the Vite frontend web UI (default: True)")
parser.add_argument("--no-ui", dest="ui", action="store_false", help="Run backend services only")
args = parser.parse_args()

env = os.environ.copy()
env["PYTHONPATH"] = str(ROOT)

commands = [
    [sys.executable, "-m", "uvicorn", "services.helpdesk.app:app", "--host", "127.0.0.1", "--port", "8001"],
    [sys.executable, "-m", "uvicorn", "services.portal.app:app", "--host", "127.0.0.1", "--port", "8002"],
    [sys.executable, "-m", "uvicorn", "services.agent.app:app", "--host", "127.0.0.1", "--port", "8003"],
    [sys.executable, "-m", "services.agent.agent"],
]

procs: list[subprocess.Popen] = []

try:
    for cmd in commands:
        procs.append(subprocess.Popen(cmd, cwd=ROOT, env=env))

    ui_running = False
    if args.ui and FRONTEND.exists() and (FRONTEND / "node_modules").exists():
        npm_cmd = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
        procs.append(subprocess.Popen([npm_cmd, "run", "dev"], cwd=FRONTEND))
        ui_running = True

    print(
        "\nEG CCTV Support Lab is RUNNING:\n"
        + ("  Web Platform UI : http://localhost:5173/\n" if ui_running else "")
        + "  Helpdesk Docs   : http://127.0.0.1:8001/docs\n"
        + "  Portal Docs     : http://127.0.0.1:8002/docs\n"
        + "  Agent API Docs  : http://127.0.0.1:8003/docs\n"
        + "  Agent Poll Loop : running in background\n"
        + "\nPress Ctrl+C to stop all processes cleanly.\n",
        flush=True,
    )
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    for p in procs:
        p.terminate()
    for p in procs:
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.kill()
    print("All services stopped.")
