"""Fake Operations Portal — simulated CCTV/NVR/AI-Box infrastructure.

Provides:
 - Asset inventory (cameras, NVRs, AI Boxes) with simulated state
 - Health/check/ping/TCP/RTSP endpoints
 - Fault injection and clearance
 - Site-level health overview
 - Allow-listed safe actions (reconnect, restart, retry, clear)
 - Logs and fault history

All state is stored in data/runtime/portal.json.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.common.config import RUNTIME
from services.common.models import utcnow_iso

app = FastAPI(
    title="Fake Operations Portal",
    description="Simulated IP camera / NVR / AI Box infrastructure with fault injection.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = RUNTIME / "portal.json"

# All supported fault types
SUPPORTED_FAULTS: set[str] = {
    "network_down",
    "rtsp_down",
    "rtsp_auth_failure",
    "wrong_rtsp_path",
    "poe_power_off",
    "high_cpu",
    "storage_full",
    "intermittent_connectivity",
    "nvr_unavailable",
    "ai_box_service_failure",
    "cloud_sync_failure",
    "multi_camera_site_outage",
}

# Actions that the portal will execute (allow-listed)
ALLOWED_ACTIONS: set[str] = {
    "reconnect_stream",
    "restart_service",
    "retry_upload",
    "clear_transient",
}


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _seed() -> None:
    """Create the simulated infrastructure if no state file exists."""
    if DB.exists():
        return
    assets: list[dict[str, Any]] = [
        {
            "id": "CAM-001",
            "site_id": "SITE-001",
            "name": "Lobby Camera",
            "kind": "camera",
            "ip": "10.10.1.11",
            "state": {
                "reachable": True,
                "rtsp": "up",
                "rtsp_auth": True,
                "rtsp_path": True,
                "poe": True,
            },
        },
        {
            "id": "CAM-002",
            "site_id": "SITE-002",
            "name": "Parking Camera",
            "kind": "camera",
            "ip": "10.10.2.11",
            "state": {
                "reachable": True,
                "rtsp": "up",
                "rtsp_auth": True,
                "rtsp_path": True,
                "poe": True,
            },
        },
        {
            "id": "CAM-003",
            "site_id": "SITE-002",
            "name": "Loading Dock Camera",
            "kind": "camera",
            "ip": "10.10.2.12",
            "state": {
                "reachable": True,
                "rtsp": "up",
                "rtsp_auth": True,
                "rtsp_path": True,
                "poe": True,
            },
        },
        {
            "id": "CAM-004",
            "site_id": "SITE-003",
            "name": "Server Room Camera",
            "kind": "camera",
            "ip": "10.10.3.11",
            "state": {
                "reachable": True,
                "rtsp": "up",
                "rtsp_auth": True,
                "rtsp_path": True,
                "poe": True,
            },
        },
        {
            "id": "NVR-001",
            "site_id": "SITE-003",
            "name": "Main NVR",
            "kind": "nvr",
            "ip": "10.10.3.10",
            "state": {
                "reachable": True,
                "storage_used": 55,
            },
        },
        {
            "id": "NVR-002",
            "site_id": "SITE-001",
            "name": "Lobby NVR",
            "kind": "nvr",
            "ip": "10.10.1.10",
            "state": {
                "reachable": True,
                "storage_used": 42,
            },
        },
        {
            "id": "AIBOX-001",
            "site_id": "SITE-001",
            "name": "Detection Box Alpha",
            "kind": "ai_box",
            "ip": "10.10.1.20",
            "state": {
                "reachable": True,
                "service": "up",
                "cpu": 35,
                "cloud_sync": "up",
            },
        },
        {
            "id": "AIBOX-002",
            "site_id": "SITE-002",
            "name": "Detection Box Beta",
            "kind": "ai_box",
            "ip": "10.10.2.20",
            "state": {
                "reachable": True,
                "service": "up",
                "cpu": 28,
                "cloud_sync": "up",
            },
        },
    ]
    data = {
        "assets": assets,
        "faults": {},
        "fault_history": [],
        "action_log": [],
    }
    _save(data)


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


_seed()


# ---------------------------------------------------------------------------
# Effective state calculation
# ---------------------------------------------------------------------------

def _effective_state(asset: dict[str, Any], faults: dict[str, list[str]]) -> dict[str, Any]:
    """Compute the effective (observed) state of an asset given active faults."""
    state = asset["state"].copy()
    active = faults.get(asset["id"], [])

    for fault in active:
        if fault == "network_down":
            state["reachable"] = False
        elif fault == "rtsp_down":
            state["rtsp"] = "down"
        elif fault == "rtsp_auth_failure":
            state["rtsp_auth"] = False
        elif fault == "wrong_rtsp_path":
            state["rtsp_path"] = False
        elif fault == "poe_power_off":
            state["poe"] = False
            state["reachable"] = False
            state["rtsp"] = "down"
        elif fault == "high_cpu":
            state["cpu"] = 96
        elif fault == "storage_full":
            state["storage_used"] = 99
        elif fault == "intermittent_connectivity":
            state["reachable"] = False
            state["intermittent"] = True
        elif fault == "nvr_unavailable":
            state["reachable"] = False
        elif fault == "ai_box_service_failure":
            state["service"] = "down"
        elif fault == "cloud_sync_failure":
            state["cloud_sync"] = "down"
        elif fault == "multi_camera_site_outage":
            state["reachable"] = False
            state["rtsp"] = "down"

    return state


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class FaultRequest(BaseModel):
    fault: str


class ActionRequest(BaseModel):
    action: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["system"])
def health():
    return {"ok": True, "service": "portal"}


@app.get("/assets", tags=["assets"])
def list_assets(site_id: str | None = None, kind: str | None = None):
    """List all assets with their effective (fault-adjusted) state."""
    data = _load()
    assets = data["assets"]
    if site_id:
        assets = [a for a in assets if a["site_id"] == site_id]
    if kind:
        assets = [a for a in assets if a["kind"] == kind]
    return [
        {**a, "effective_state": _effective_state(a, data["faults"])}
        for a in assets
    ]


@app.get("/assets/{asset_id}", tags=["assets"])
def get_asset(asset_id: str):
    data = _load()
    for a in data["assets"]:
        if a["id"] == asset_id:
            return {
                **a,
                "effective_state": _effective_state(a, data["faults"]),
                "active_faults": data["faults"].get(asset_id, []),
            }
    raise HTTPException(status_code=404, detail="Asset not found")


@app.get("/check/{asset_id}", tags=["checks"])
def check_asset(asset_id: str):
    """Simulated health/connectivity/RTSP check for one asset."""
    info = get_asset(asset_id)
    state = info["effective_state"]
    kind = info["kind"]
    now = utcnow_iso()

    result: dict[str, Any] = {
        "asset_id": asset_id,
        "timestamp": now,
        "ping": state.get("reachable", False),
        "tcp": state.get("reachable", False),
        "logs": [],
    }

    if kind == "camera":
        rtsp_ok = (
            state.get("rtsp") == "up"
            and state.get("rtsp_auth", True)
            and state.get("rtsp_path", True)
        )
        result.update(
            rtsp=rtsp_ok,
            rtsp_auth=state.get("rtsp_auth", True),
            rtsp_path=state.get("rtsp_path", True),
            poe=state.get("poe", True),
        )

    if kind == "nvr":
        result["storage_used"] = state.get("storage_used", 0)

    if kind == "ai_box":
        result.update(
            service=state.get("service", "up"),
            cpu=state.get("cpu", 0),
            cloud_sync=state.get("cloud_sync", "up"),
        )

    return result


@app.get("/sites", tags=["sites"])
def list_sites():
    """Return all unique site IDs."""
    data = _load()
    return sorted({a["site_id"] for a in data["assets"]})


@app.get("/sites/{site_id}/health", tags=["sites"])
def site_health(site_id: str):
    data = _load()
    site_assets = [a for a in data["assets"] if a["site_id"] == site_id]
    if not site_assets:
        raise HTTPException(status_code=404, detail="Site not found")
    enriched = [
        {**a, "effective_state": _effective_state(a, data["faults"])}
        for a in site_assets
    ]
    reachable = sum(1 for a in enriched if a["effective_state"].get("reachable", False))
    healthy = sum(
        1 for a in enriched
        if a["effective_state"].get("reachable", False)
        and a["effective_state"].get("rtsp", "up") != "down"
        and a["effective_state"].get("service", "up") != "down"
        and a["effective_state"].get("poe", True) is not False
    )
    return {
        "site_id": site_id,
        "total_assets": len(enriched),
        "reachable_assets": reachable,
        "healthy_assets": healthy,
        "assets": enriched,
    }


# ---------------------------------------------------------------------------
# Fault injection
# ---------------------------------------------------------------------------

@app.get("/faults", tags=["faults"])
def list_faults():
    """Return all currently active faults."""
    data = _load()
    return data["faults"]


@app.get("/faults/supported", tags=["faults"])
def supported_faults():
    """Return the list of supported fault types."""
    return sorted(SUPPORTED_FAULTS)


@app.post("/faults/clear-all", tags=["faults"])
def clear_all_faults():
    """Clear all active faults on all assets."""
    data = _load()
    cleared = dict(data["faults"])
    data["faults"] = {}
    data["fault_history"].append({
        "faults_cleared": cleared,
        "at": utcnow_iso(),
        "event": "clear_all",
    })
    _save(data)
    return {"ok": True, "cleared": cleared}


@app.post("/faults/site/{site_id}", tags=["faults"])
def inject_site_fault(site_id: str, payload: FaultRequest):
    """Inject the same fault on all cameras at a site (site-wide outage)."""
    if payload.fault not in SUPPORTED_FAULTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported fault '{payload.fault}'.",
        )
    data = _load()
    camera_ids = [a["id"] for a in data["assets"] if a["site_id"] == site_id and a["kind"] == "camera"]
    if not camera_ids:
        raise HTTPException(status_code=404, detail="Site or camera assets not found")

    for aid in camera_ids:
        data["faults"].setdefault(aid, [])
        if payload.fault not in data["faults"][aid]:
            data["faults"][aid].append(payload.fault)
        data["fault_history"].append({
            "asset_id": aid,
            "site_id": site_id,
            "fault": payload.fault,
            "at": utcnow_iso(),
            "event": "site_fault_injected",
        })
    _save(data)
    return {"ok": True, "site_id": site_id, "affected_assets": camera_ids, "fault": payload.fault}


@app.post("/faults/{asset_id}", tags=["faults"])
def inject_fault(asset_id: str, payload: FaultRequest):
    if payload.fault not in SUPPORTED_FAULTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported fault '{payload.fault}'. Use one of: {sorted(SUPPORTED_FAULTS)}",
        )
    data = _load()
    if not any(a["id"] == asset_id for a in data["assets"]):
        raise HTTPException(status_code=404, detail="Asset not found")

    data["faults"].setdefault(asset_id, [])
    if payload.fault not in data["faults"][asset_id]:
        data["faults"][asset_id].append(payload.fault)

    data["fault_history"].append({
        "asset_id": asset_id,
        "fault": payload.fault,
        "at": utcnow_iso(),
        "event": "injected",
    })
    _save(data)
    return {"ok": True, "asset_id": asset_id, "fault": payload.fault}


@app.post("/faults/{asset_id}/clear", tags=["faults"])
def clear_faults(asset_id: str):
    """Clear all active faults on one asset."""
    data = _load()
    cleared = data["faults"].pop(asset_id, [])
    data["fault_history"].append({
        "asset_id": asset_id,
        "faults_cleared": cleared,
        "at": utcnow_iso(),
        "event": "cleared",
    })
    _save(data)
    return {"ok": True, "cleared": cleared}


# ---------------------------------------------------------------------------
# Safe actions
# ---------------------------------------------------------------------------

@app.post("/assets/{asset_id}/actions", tags=["actions"])
def perform_action(asset_id: str, payload: ActionRequest):
    """Execute an allow-listed, reversible action on a simulated asset."""
    data = _load()
    asset = next((a for a in data["assets"] if a["id"] == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if payload.action not in ALLOWED_ACTIONS:
        raise HTTPException(
            status_code=403,
            detail=f"Action '{payload.action}' is not allow-listed. Allowed: {sorted(ALLOWED_ACTIONS)}",
        )

    faults = data["faults"].get(asset_id, [])

    if payload.action == "reconnect_stream":
        faults[:] = [f for f in faults if f not in {"rtsp_down"}]
    elif payload.action == "restart_service":
        faults[:] = [f for f in faults if f != "ai_box_service_failure"]
    elif payload.action == "retry_upload":
        faults[:] = [f for f in faults if f != "cloud_sync_failure"]
    elif payload.action == "clear_transient":
        faults[:] = [f for f in faults if f != "intermittent_connectivity"]

    if not faults:
        data["faults"].pop(asset_id, None)
    else:
        data["faults"][asset_id] = faults

    log_entry = {
        "asset_id": asset_id,
        "action": payload.action,
        "at": utcnow_iso(),
        "event": "safe_action",
        "remaining_faults": list(faults),
    }
    data.setdefault("action_log", []).append(log_entry)
    data["fault_history"].append(log_entry)
    _save(data)

    return {"ok": True, "action": payload.action, "remaining_faults": faults}


@app.get("/action-log", tags=["actions"])
def action_log():
    """Return the history of executed safe actions."""
    data = _load()
    return data.get("action_log", [])


@app.get("/fault-history", tags=["faults"])
def fault_history():
    """Return the full fault injection/clearance history."""
    return _load().get("fault_history", [])
