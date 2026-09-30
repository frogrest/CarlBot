"""Autonomous CCTV Support Agent — persistent poll loop with in-process test mode.

Behaviour cycle:
  Observe → Understand → Gather Evidence → Retrieve Knowledge →
  Form Hypothesis → Test Hypothesis → Decide →
  Execute Safe Action or Request Technician Action →
  Verify → Document → Learn from Actual Resolution.

Key design decisions:
  - The agent never invents device state, ticket history, or tool results.
  - Every automatic action is verified after execution.
  - The policy engine (policy.py) is the sole authority on what is allowed.
  - Retry attempts are bounded; the agent escalates after MAX_RETRIES.
  - Fault deduplication: one active incident per asset; re-arm after recovery.
  - LAB_IN_PROCESS=1 enables ASGI transport for zero-network testing.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import UTC
from typing import Any, Self

import httpx

from services.agent.knowledge import search as knowledge_search
from services.agent.policy import allowed_automatically
from services.common.config import (
    AGENT_MAX_RETRIES,
    AGENT_POLL_SECONDS,
    HELPDESK_URL,
    PORTAL_URL,
    RUNTIME,
)

logger = logging.getLogger("agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

STATE_FILE = RUNTIME / "agent_state.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    from datetime import datetime
    return datetime.now(UTC).isoformat()


def _load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        _save_state({"active": {}, "history": []})
    for attempt in range(5):
        try:
            content = STATE_FILE.read_text(encoding="utf-8")
            if not content.strip():
                _save_state({"active": {}, "history": []})
                content = STATE_FILE.read_text(encoding="utf-8")
            return json.loads(content)
        except (json.JSONDecodeError, OSError):
            if attempt < 4:
                time.sleep(0.02 * (attempt + 1))
            else:
                _save_state({"active": {}, "history": []})
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def _save_state(state: dict[str, Any]) -> None:
    text = json.dumps(state, indent=2, ensure_ascii=False)
    temp_path = STATE_FILE.with_suffix(f".tmp.{os.getpid()}.{time.time_ns()}")
    temp_path.write_text(text, encoding="utf-8")
    for attempt in range(5):
        try:
            temp_path.replace(STATE_FILE)
            return
        except OSError:
            if attempt < 4:
                time.sleep(0.01 * (attempt + 1))
            else:
                STATE_FILE.write_text(text, encoding="utf-8")
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Diagnosis engine (deterministic, no LLM required)
# ---------------------------------------------------------------------------

def diagnose(
    asset: dict[str, Any],
    check: dict[str, Any],
    historical: list[dict[str, Any]],
) -> tuple[str, float, str, str]:
    """Return (fault, confidence, recommendation, safety_class) for an asset.

    Uses the effective state and check results to produce a deterministic
    diagnosis. Historical evidence enriches context but does not change the
    diagnosis logic.
    """
    kind = asset["kind"]
    state = asset.get("effective_state", asset.get("state", {}))

    # --- Camera faults ---
    if kind == "camera":
        # Intermittent connectivity (check effective_state for the flag)
        if state.get("intermittent"):
            return (
                "intermittent_connectivity",
                0.85,
                "Clear transient state and retest connectivity",
                "SAFE_REVERSIBLE",
            )
        # PoE / power off (unreachable + poe off)
        if not check.get("ping") and check.get("poe") is False:
            return (
                "poe_power_off",
                0.99,
                "Physical repair / restore PoE power",
                "HUMAN_ONLY",
            )
        # Network down (unreachable, but not specifically PoE)
        if not check.get("ping"):
            return (
                "network_down",
                0.98,
                "Inspect network path and site connectivity",
                "HUMAN_ONLY",
            )
        # RTSP auth failure
        if check.get("rtsp_auth") is False:
            return (
                "rtsp_auth_failure",
                0.99,
                "Technician: verify and correct RTSP credentials",
                "HUMAN_ONLY",
            )
        # Wrong RTSP path
        if check.get("rtsp_path") is False:
            return (
                "wrong_rtsp_path",
                0.98,
                "Technician: verify configured RTSP stream path",
                "HUMAN_ONLY",
            )
        # RTSP down (stream issue, host reachable)
        if check.get("rtsp") is False or check.get("rtsp") == "down":
            return (
                "rtsp_down",
                0.95,
                "Reconnect simulated RTSP stream",
                "SAFE_REVERSIBLE",
            )

    # --- NVR faults ---
    if kind == "nvr":
        if not check.get("ping"):
            return (
                "nvr_unavailable",
                0.98,
                "Technician: investigate NVR / network availability",
                "HUMAN_ONLY",
            )
        if check.get("storage_used", 0) >= 95:
            return (
                "storage_full",
                0.99,
                "Technician: review retention policy and free storage",
                "HUMAN_ONLY",
            )

    # --- AI Box faults ---
    if kind == "ai_box":
        if check.get("service") == "down":
            return (
                "ai_box_service_failure",
                0.99,
                "Restart simulated AI detection service",
                "SAFE_REVERSIBLE",
            )
        if check.get("cpu", 0) >= 90:
            return (
                "high_cpu",
                0.97,
                "Technician: investigate workload / resource pressure",
                "HUMAN_ONLY",
            )
        if check.get("cloud_sync") == "down":
            return (
                "cloud_sync_failure",
                0.95,
                "Retry simulated cloud upload",
                "SAFE_REVERSIBLE",
            )

    return ("unknown", 0.4, "Technician investigation required", "HUMAN_ONLY")


# ---------------------------------------------------------------------------
# Fault → safe-action mapping
# ---------------------------------------------------------------------------

FAULT_TO_ACTION: dict[str, str] = {
    "rtsp_down": "reconnect_stream",
    "ai_box_service_failure": "restart_service",
    "cloud_sync_failure": "retry_upload",
    "intermittent_connectivity": "clear_transient",
}

FAULT_VERIFICATION: dict[str, tuple[str, str, object]] = {
    # fault → (field_name, success_description, expected_value)
    "rtsp_down": ("rtsp", "RTSP check recovered", True),
    "ai_box_service_failure": ("service", "AI Box service recovered", "up"),
    "cloud_sync_failure": ("cloud_sync", "Cloud sync recovered", "up"),
    "intermittent_connectivity": ("ping", "Connectivity recovered", True),
}


# ---------------------------------------------------------------------------
# Asset processing
# ---------------------------------------------------------------------------

def _is_problem(asset: dict[str, Any], check: dict[str, Any]) -> bool:
    """Return True if the asset's check results indicate a problem."""
    kind = asset["kind"]
    state = asset.get("effective_state", asset.get("state", {}))

    if kind == "camera":
        if state.get("intermittent"):
            return True
        return not check.get("ping") or check.get("rtsp") is False or check.get("rtsp") == "down"
    if kind == "nvr":
        return not check.get("ping") or check.get("storage_used", 0) >= 95
    if kind == "ai_box":
        return (
            check.get("service") != "up"
            or check.get("cloud_sync") != "up"
            or check.get("cpu", 0) >= 90
        )
    return False


async def process_asset(
    client: Any,
    asset: dict[str, Any],
    state: dict[str, Any],
) -> None:
    """Investigate one asset: detect problems, diagnose, act, verify, document."""
    aid = asset["id"]
    site_id = asset["site_id"]

    # --- Check ---
    check_resp = await client.get(f"{PORTAL_URL}/check/{aid}")
    check: dict[str, Any] = check_resp.json()

    problem = _is_problem(asset, check)

    # --- Recovery path: fault cleared ---
    if not problem:
        if aid in state["active"]:
            ticket_id = state["active"][aid].get("ticket_id")
            if ticket_id:
                await client.patch(
                    f"{HELPDESK_URL}/tickets/{ticket_id}",
                    json={
                        "status": "resolved",
                        "resolution": "Verified: active fault no longer observed on subsequent health checks.",
                    },
                )
                await client.post(
                    f"{HELPDESK_URL}/tickets/{ticket_id}/comments",
                    json={
                        "author": "autonomous-agent",
                        "body": "Recovery verified — the previously active fault is no longer detected.",
                    },
                )
            state["history"].append({
                "asset_id": aid,
                "event": "recovered",
                "ticket_id": ticket_id,
                "at": _now(),
            })
            state["active"].pop(aid, None)
            _save_state(state)
            logger.info("Asset %s recovered (ticket %s resolved)", aid, ticket_id)
        return

    # --- Retry limit ---
    attempts = state["active"].get(aid, {}).get("attempts", 0)
    if attempts >= AGENT_MAX_RETRIES:
        logger.info("Asset %s: retry limit reached (%d), awaiting human", aid, attempts)
        return

    # --- Gather evidence ---
    site_resp = await client.get(f"{PORTAL_URL}/sites/{site_id}/health")
    site_info = site_resp.json()

    hist_resp = await client.get(f"{HELPDESK_URL}/search", params={"q": asset["kind"]})
    historical = hist_resp.json()

    # --- Diagnose ---
    fault, confidence, recommendation, safety = diagnose(asset, check, historical)

    # --- Knowledge retrieval ---
    docs = knowledge_search(f"{fault} {asset['kind']}")

    # --- Execute safe action (if allowed) ---
    action = FAULT_TO_ACTION.get(fault)
    performed: list[str] = []
    verification = "pending"

    if action and allowed_automatically(action):
        action_resp = await client.post(
            f"{PORTAL_URL}/assets/{aid}/actions",
            json={"action": action},
        )
        if action_resp.is_success:
            performed.append(action)
            # --- Verify ---
            verify_resp = await client.get(f"{PORTAL_URL}/check/{aid}")
            verify = verify_resp.json()

            vspec = FAULT_VERIFICATION.get(fault)
            if vspec:
                field, desc, expected = vspec
                actual = verify.get(field)
                if actual == expected:
                    verification = f"verified: {desc}"
                else:
                    verification = f"failed: {field}={actual}, expected {expected}"
            else:
                verification = "action executed; manual verification recommended"
        else:
            verification = f"action failed: HTTP {action_resp.status_code}"
    else:
        verification = "human action required; no automatic change performed"

    # --- Document: build structured evidence comment ---
    evidence_body = json.dumps(
        {
            "observed_facts": [
                f"check_result={check}",
                f"site_health={site_info}",
            ],
            "historical_evidence": [
                {"id": t.get("id"), "root_cause": t.get("root_cause"), "status": t.get("status")}
                for t in historical[:3]
            ],
            "documentation": docs,
            "hypothesis": fault,
            "confidence": confidence,
            "recommended_action": recommendation,
            "safety_class": safety,
            "actions_performed": performed,
            "verification": verification,
        },
        indent=2,
    )

    comment_payload = {"author": "autonomous-agent", "body": evidence_body}

    # Decide ticket status
    if performed and verification.startswith("verified"):
        new_status = "resolved"
    elif safety == "HUMAN_ONLY":
        new_status = "pending_technician"
    elif safety == "APPROVAL_REQUIRED":
        new_status = "pending_approval"
    else:
        new_status = "investigating"

    # --- Find or create ticket ---
    tickets_resp = await client.get(f"{HELPDESK_URL}/tickets")
    tickets: list[dict[str, Any]] = tickets_resp.json()
    existing = next(
        (
            t
            for t in tickets
            if t.get("asset_id") == aid
            and t.get("status") in {"open", "pending_technician", "pending_approval", "investigating"}
        ),
        None,
    )

    if existing:
        ticket_id = existing["id"]
        await client.post(f"{HELPDESK_URL}/tickets/{ticket_id}/comments", json=comment_payload)
        await client.patch(
            f"{HELPDESK_URL}/tickets/{ticket_id}",
            json={"status": new_status, "root_cause": fault, "resolution": verification},
        )
    else:
        title = f"AI Investigation: {fault} on {aid}"
        desc = (
            f"Automated investigation for asset {aid} ({asset.get('name', '')}) at site {site_id}. "
            f"Diagnosis: {fault} (confidence {confidence:.0%}). Safety class: {safety}."
        )
        create_resp = await client.post(
            f"{HELPDESK_URL}/tickets",
            json={
                "title": title,
                "description": desc,
                "site_id": site_id,
                "asset_id": aid,
                "tags": ["ai-agent", fault],
            },
        )
        new_ticket = create_resp.json()
        ticket_id = new_ticket["id"]
        await client.post(f"{HELPDESK_URL}/tickets/{ticket_id}/comments", json=comment_payload)
        await client.patch(
            f"{HELPDESK_URL}/tickets/{ticket_id}",
            json={"status": new_status, "root_cause": fault, "resolution": verification},
        )

    # --- Update agent state ---
    state["active"][aid] = {
        "ticket_id": ticket_id,
        "fault": fault,
        "attempts": attempts + 1,
        "last_at": _now(),
        "verification": verification,
    }
    state["history"].append({
        "asset_id": aid,
        "fault": fault,
        "ticket_id": ticket_id,
        "at": _now(),
        "verification": verification,
    })
    _save_state(state)
    logger.info("Asset %s: fault=%s status=%s verification=%s", aid, fault, new_status, verification)


# ---------------------------------------------------------------------------
# In-process ASGI client facade (for testing without live servers)
# ---------------------------------------------------------------------------

class _InProcessClient:
    """Routes absolute URLs to the in-process ASGI apps."""

    def __init__(self) -> None:
        from httpx import ASGITransport

        from services.helpdesk.app import app as helpdesk_app
        from services.portal.app import app as portal_app

        self._helpdesk = httpx.AsyncClient(
            transport=ASGITransport(app=helpdesk_app),
            base_url=HELPDESK_URL,
        )
        self._portal = httpx.AsyncClient(
            transport=ASGITransport(app=portal_app),
            base_url=PORTAL_URL,
        )

    def _pick(self, url: str) -> httpx.AsyncClient:
        return self._helpdesk if url.startswith(HELPDESK_URL) else self._portal

    def _strip(self, url: str) -> str:
        for base in (HELPDESK_URL, PORTAL_URL):
            if url.startswith(base):
                return url[len(base):]
        return url

    async def get(self, url: str, **kw: Any) -> httpx.Response:
        return await self._pick(url).get(self._strip(url), **kw)

    async def post(self, url: str, **kw: Any) -> httpx.Response:
        return await self._pick(url).post(self._strip(url), **kw)

    async def patch(self, url: str, **kw: Any) -> httpx.Response:
        return await self._pick(url).patch(self._strip(url), **kw)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self._helpdesk.aclose()
        await self._portal.aclose()


# ---------------------------------------------------------------------------
# Run-once and persistent loop
# ---------------------------------------------------------------------------

async def run_once() -> dict[str, Any]:
    """Execute one full agent cycle across all assets."""
    state = _load_state()

    if os.getenv("LAB_IN_PROCESS") == "1":
        async with _InProcessClient() as client:
            assets = (await client.get(f"{PORTAL_URL}/assets")).json()
            for asset in assets:
                await process_asset(client, asset, state)
    else:
        async with httpx.AsyncClient(timeout=10) as client:
            assets = (await client.get(f"{PORTAL_URL}/assets")).json()
            for asset in assets:
                await process_asset(client, asset, state)

    return state


async def investigate_single_asset(aid: str) -> dict[str, Any]:
    """Execute a structured investigation for one asset and return a full report with timeline."""
    state = _load_state()

    async def _do_investigate(client: Any) -> dict[str, Any]:
        asset_resp = await client.get(f"{PORTAL_URL}/assets/{aid}")
        if asset_resp.status_code == 404:
            return {"error": f"Asset {aid} not found", "found": False}
        asset = asset_resp.json()
        site_id = asset["site_id"]
        kind = asset["kind"]

        # Telemetry / Health check
        check_resp = await client.get(f"{PORTAL_URL}/check/{aid}")
        check = check_resp.json()
        is_prob = _is_problem(asset, check)

        timeline: list[dict[str, Any]] = []
        timeline.append({
            "step": "observation",
            "title": f"Telemetry and subsystem check for {aid}",
            "status": "FAIL" if is_prob else "PASS",
            "details": check,
            "timestamp": _now(),
        })

        # Historical retrieval & site health
        site_resp = await client.get(f"{PORTAL_URL}/sites/{site_id}/health")
        site_info = site_resp.json() if site_resp.is_success else {}

        hist_resp = await client.get(f"{HELPDESK_URL}/search", params={"q": kind})
        historical = hist_resp.json() if hist_resp.is_success else []
        timeline.append({
            "step": "history_retrieval",
            "title": f"Retrieved historical tickets for {kind}",
            "status": "PASS",
            "details": {"matches_count": len(historical), "sample": historical[:3]},
            "timestamp": _now(),
        })

        # Diagnosis
        fault, confidence, recommendation, safety = diagnose(asset, check, historical)
        timeline.append({
            "step": "hypothesis",
            "title": f"Formed diagnostic hypothesis: {fault}",
            "status": "PASS",
            "details": {
                "fault": fault,
                "confidence": confidence,
                "recommendation": recommendation,
                "safety_class": safety,
            },
            "timestamp": _now(),
        })

        # Knowledge retrieval
        docs = knowledge_search(f"{fault} {kind}")
        timeline.append({
            "step": "knowledge_retrieval",
            "title": f"Retrieved documentation for {fault}",
            "status": "PASS",
            "details": {"documents_count": len(docs), "documents": docs},
            "timestamp": _now(),
        })

        # Policy evaluation
        action = FAULT_TO_ACTION.get(fault)
        policy_allowed = bool(action and allowed_automatically(action))
        timeline.append({
            "step": "policy_evaluation",
            "title": f"Policy check for action '{action or 'none'}'",
            "status": "ALLOWED" if policy_allowed else ("BLOCKED" if action else "INFO"),
            "details": {
                "action": action,
                "safety_class": safety,
                "allowed_automatically": policy_allowed,
            },
            "timestamp": _now(),
        })

        # Process the asset through standard agent flow
        await process_asset(client, asset, state)

        # Verification check
        verify_resp = await client.get(f"{PORTAL_URL}/check/{aid}")
        verify_check = verify_resp.json()

        # Ticket lookup
        tickets_resp = await client.get(f"{HELPDESK_URL}/tickets")
        tickets = tickets_resp.json() if tickets_resp.is_success else []
        asset_tickets = [t for t in tickets if t.get("asset_id") == aid]
        current_ticket = asset_tickets[0] if asset_tickets else None

        if policy_allowed:
            vspec = FAULT_VERIFICATION.get(fault)
            verified = False
            if vspec:
                field, _desc, expected = vspec
                verified = (verify_check.get(field) == expected)
            timeline.append({
                "step": "recovery_and_verification",
                "title": f"Recovery action '{action}' executed",
                "status": "PASS" if verified else "FAIL",
                "details": {
                    "action": action,
                    "verified": verified,
                    "post_check": verify_check,
                },
                "timestamp": _now(),
            })
        elif is_prob:
            timeline.append({
                "step": "escalation",
                "title": f"Technician action required: {recommendation}",
                "status": "ESCALATED",
                "details": {
                    "reason": f"Safety policy classifies '{action or fault}' as {safety}",
                    "ticket_id": current_ticket.get("id") if current_ticket else None,
                },
                "timestamp": _now(),
            })
        else:
            timeline.append({
                "step": "verification",
                "title": f"Asset {aid} is healthy and operational",
                "status": "PASS",
                "details": {"check": verify_check},
                "timestamp": _now(),
            })

        return {
            "found": True,
            "asset": asset,
            "check": check,
            "post_check": verify_check,
            "is_problem": is_prob,
            "diagnosis": {
                "fault": fault,
                "confidence": confidence,
                "recommendation": recommendation,
                "safety_class": safety,
            },
            "policy": {
                "action": action,
                "safety_class": safety,
                "allowed_automatically": policy_allowed,
            },
            "action_executed": action if policy_allowed else None,
            "ticket": current_ticket,
            "historical_matches": historical[:3],
            "knowledge_sources": docs,
            "timeline": timeline,
            "site_info": site_info,
        }

    if os.getenv("LAB_IN_PROCESS") == "1":
        async with _InProcessClient() as client:
            return await _do_investigate(client)
    else:
        async with httpx.AsyncClient(timeout=10) as client:
            return await _do_investigate(client)


async def main() -> None:
    """Persistent polling loop."""
    logger.info("Agent starting (poll every %.1fs, max retries %d)", AGENT_POLL_SECONDS, AGENT_MAX_RETRIES)
    while True:
        try:
            await run_once()
        except Exception:
            logger.exception("Agent loop error")
        await asyncio.sleep(AGENT_POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
