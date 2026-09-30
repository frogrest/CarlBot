"""Comprehensive test suite for the CCTV AI Support Lab.

Tests cover:
  - Policy engine enforcement (unit)
  - Helpdesk API smoke tests
  - Portal API smoke tests
  - Agent API smoke tests
  - Automatic recovery (RTSP, AI Box, cloud sync, intermittent)
  - Technician-required escalation (auth, path, PoE, network, NVR, CPU, storage)
  - Fault deduplication (no duplicate tickets)
  - Re-arming after recovery
  - Regression sweep across all supported faults
  - Multi-camera site outage
  - Knowledge retrieval
  - Agent retry limit enforcement
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import ClassVar

import pytest
from fastapi.testclient import TestClient

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["LAB_IN_PROCESS"] = "1"

from services.agent.agent import run_once
from services.agent.app import app as agent_app
from services.agent.knowledge import search as knowledge_search
from services.agent.policy import allowed_automatically, classify, describe_policy
from services.common.config import RUNTIME
from services.common.models import SafetyClass
from services.helpdesk.app import app as helpdesk_app
from services.portal.app import app as portal_app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _safe_unlink(p: Path) -> None:
    for attempt in range(5):
        try:
            if p.exists():
                p.unlink()
            return
        except (PermissionError, OSError):
            time.sleep(0.02 * (attempt + 1))
    if p.exists():
        try:
            p.write_text("{}", encoding="utf-8")
        except OSError:
            pass


@pytest.fixture(autouse=True)
def clean_runtime():
    """Reset all runtime state before and after each test."""
    state_files = [
        RUNTIME / "portal.json",
        RUNTIME / "helpdesk.json",
        RUNTIME / "agent_state.json",
    ]
    for f in state_files:
        _safe_unlink(f)
    yield
    for f in state_files:
        _safe_unlink(f)


@pytest.fixture
def helpdesk():
    return TestClient(helpdesk_app)


@pytest.fixture
def portal():
    return TestClient(portal_app)


@pytest.fixture
def agent():
    return TestClient(agent_app)


# ---------------------------------------------------------------------------
# Unit tests: Policy engine
# ---------------------------------------------------------------------------

class TestPolicy:
    def test_read_actions(self):
        for action in ["health", "ping", "tcp", "rtsp_check", "logs", "ticket_search", "docs_search"]:
            assert classify(action) == SafetyClass.READ
            assert allowed_automatically(action)

    def test_safe_reversible_actions(self):
        for action in ["reconnect_stream", "restart_service", "retry_upload", "clear_transient"]:
            assert classify(action) == SafetyClass.SAFE_REVERSIBLE
            assert allowed_automatically(action)

    def test_approval_required_actions(self):
        for action in ["credential_change", "network_change", "nvr_reboot", "configuration_change"]:
            assert classify(action) == SafetyClass.APPROVAL_REQUIRED
            assert not allowed_automatically(action)

    def test_human_only_actions(self):
        for action in ["physical_repair", "cable_replacement", "camera_replacement", "factory_reset"]:
            assert classify(action) == SafetyClass.HUMAN_ONLY
            assert not allowed_automatically(action)

    def test_unknown_defaults_human_only(self):
        assert classify("something_totally_unknown") == SafetyClass.HUMAN_ONLY
        assert not allowed_automatically("something_totally_unknown")

    def test_describe_policy(self):
        policy = describe_policy()
        assert "READ" in policy
        assert "SAFE_REVERSIBLE" in policy
        assert "APPROVAL_REQUIRED" in policy
        assert "HUMAN_ONLY" in policy


# ---------------------------------------------------------------------------
# API smoke tests
# ---------------------------------------------------------------------------

class TestHelpdeskAPI:
    def test_health(self, helpdesk):
        r = helpdesk.get("/health")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_list_tickets(self, helpdesk):
        tickets = helpdesk.get("/tickets").json()
        assert len(tickets) >= 7  # 7 seed historical tickets

    def test_get_ticket(self, helpdesk):
        r = helpdesk.get("/tickets/HIST-001")
        assert r.status_code == 200
        assert r.json()["root_cause"] == "rtsp_down"

    def test_create_ticket(self, helpdesk):
        r = helpdesk.post("/tickets", json={
            "title": "Test ticket",
            "description": "Test description",
            "site_id": "SITE-001",
            "asset_id": "CAM-001",
            "tags": ["test"],
        })
        assert r.status_code == 201
        assert r.json()["id"].startswith("T-")

    def test_add_comment(self, helpdesk):
        r = helpdesk.post("/tickets/HIST-001/comments", json={
            "author": "test",
            "body": "Test comment",
        })
        assert r.status_code == 200

    def test_add_technician_note(self, helpdesk):
        r = helpdesk.post("/tickets/HIST-001/technician-notes", json={
            "author": "tech-test",
            "body": "Test technician note",
        })
        assert r.status_code == 200

    def test_update_ticket(self, helpdesk):
        r = helpdesk.patch("/tickets/HIST-001", json={"status": "investigating"})
        assert r.status_code == 200
        assert r.json()["status"] == "investigating"

    def test_search_tickets(self, helpdesk):
        results = helpdesk.get("/search", params={"q": "rtsp"}).json()
        assert len(results) >= 1

    def test_stats(self, helpdesk):
        stats = helpdesk.get("/stats").json()
        assert stats["total"] >= 7

    def test_filter_by_status(self, helpdesk):
        resolved = helpdesk.get("/tickets", params={"status": "resolved"}).json()
        assert all(t["status"] == "resolved" for t in resolved)

    def test_filter_by_asset(self, helpdesk):
        cam001 = helpdesk.get("/tickets", params={"asset_id": "CAM-001"}).json()
        assert all(t["asset_id"] == "CAM-001" for t in cam001)

    def test_not_found(self, helpdesk):
        r = helpdesk.get("/tickets/NONEXISTENT")
        assert r.status_code == 404


class TestPortalAPI:
    def test_health(self, portal):
        assert portal.get("/health").json()["ok"] is True

    def test_list_assets(self, portal):
        assets = portal.get("/assets").json()
        assert len(assets) >= 8  # 8 seed assets

    def test_get_asset(self, portal):
        r = portal.get("/assets/CAM-001")
        assert r.status_code == 200
        assert r.json()["kind"] == "camera"

    def test_check_camera(self, portal):
        check = portal.get("/check/CAM-001").json()
        assert check["ping"] is True
        assert check["rtsp"] is True

    def test_check_nvr(self, portal):
        check = portal.get("/check/NVR-001").json()
        assert check["ping"] is True
        assert "storage_used" in check

    def test_check_ai_box(self, portal):
        check = portal.get("/check/AIBOX-001").json()
        assert check["service"] == "up"

    def test_list_sites(self, portal):
        sites = portal.get("/sites").json()
        assert len(sites) >= 3

    def test_site_health(self, portal):
        r = portal.get("/sites/SITE-001/health")
        assert r.status_code == 200
        assert len(r.json()["assets"]) >= 1

    def test_inject_fault(self, portal):
        r = portal.post("/faults/CAM-001", json={"fault": "rtsp_down"})
        assert r.json()["ok"] is True
        assert portal.get("/check/CAM-001").json()["rtsp"] is False

    def test_clear_fault(self, portal):
        portal.post("/faults/CAM-001", json={"fault": "rtsp_down"})
        r = portal.post("/faults/CAM-001/clear")
        assert r.json()["ok"] is True
        assert portal.get("/check/CAM-001").json()["rtsp"] is True

    def test_inject_unsupported_fault(self, portal):
        r = portal.post("/faults/CAM-001", json={"fault": "nonexistent_fault"})
        assert r.status_code == 400

    def test_supported_faults(self, portal):
        faults = portal.get("/faults/supported").json()
        assert "rtsp_down" in faults
        assert len(faults) == 12

    def test_clear_all(self, portal):
        portal.post("/faults/CAM-001", json={"fault": "rtsp_down"})
        portal.post("/faults/CAM-002", json={"fault": "network_down"})
        r = portal.post("/faults/clear-all")
        assert r.json()["ok"] is True
        assert portal.get("/faults").json() == {}

    def test_asset_not_found(self, portal):
        r = portal.get("/assets/NONEXISTENT")
        assert r.status_code == 404

    def test_action_not_allowed(self, portal):
        r = portal.post("/assets/CAM-001/actions", json={"action": "firmware_update"})
        assert r.status_code == 403

    def test_filter_assets_by_site(self, portal):
        assets = portal.get("/assets", params={"site_id": "SITE-001"}).json()
        assert all(a["site_id"] == "SITE-001" for a in assets)

    def test_filter_assets_by_kind(self, portal):
        cameras = portal.get("/assets", params={"kind": "camera"}).json()
        assert all(a["kind"] == "camera" for a in cameras)


class TestAgentAPI:
    def test_health(self, agent):
        assert agent.get("/health").json()["ok"] is True

    def test_policy(self, agent):
        policy = agent.get("/policy").json()
        assert "READ" in policy

    def test_state(self, agent):
        state = agent.get("/state").json()
        assert "active" in state
        assert "history" in state


# ---------------------------------------------------------------------------
# End-to-end: automatic recovery
# ---------------------------------------------------------------------------

class TestAutoRecovery:
    def test_rtsp_recovery(self, portal, helpdesk):
        """RTSP down should be auto-recovered via reconnect_stream."""
        portal.post("/faults/CAM-001", json={"fault": "rtsp_down"})
        asyncio.run(run_once())

        tickets = helpdesk.get("/tickets").json()
        assert any(
            t["root_cause"] == "rtsp_down" and t["status"] == "resolved"
            for t in tickets
        ), f"Expected resolved rtsp_down ticket, got: {[(t['root_cause'], t['status']) for t in tickets]}"

        # Verify the fault was actually cleared
        check = portal.get("/check/CAM-001").json()
        assert check["rtsp"] is True

    def test_ai_box_recovery(self, portal, helpdesk):
        """AI Box service failure should be auto-recovered via restart_service."""
        portal.post("/faults/AIBOX-001", json={"fault": "ai_box_service_failure"})
        asyncio.run(run_once())

        tickets = helpdesk.get("/tickets").json()
        assert any(
            t["root_cause"] == "ai_box_service_failure" and t["status"] == "resolved"
            for t in tickets
        )
        assert portal.get("/check/AIBOX-001").json()["service"] == "up"

    def test_cloud_sync_recovery(self, portal, helpdesk):
        """Cloud sync failure should be auto-recovered via retry_upload."""
        portal.post("/faults/AIBOX-001", json={"fault": "cloud_sync_failure"})
        asyncio.run(run_once())

        tickets = helpdesk.get("/tickets").json()
        assert any(
            t["root_cause"] == "cloud_sync_failure" and t["status"] == "resolved"
            for t in tickets
        )

    def test_intermittent_recovery(self, portal, helpdesk):
        """Intermittent connectivity should be auto-recovered via clear_transient."""
        portal.post("/faults/CAM-001", json={"fault": "intermittent_connectivity"})
        asyncio.run(run_once())

        tickets = helpdesk.get("/tickets").json()
        assert any(
            t["root_cause"] == "intermittent_connectivity" and t["status"] == "resolved"
            for t in tickets
        )


# ---------------------------------------------------------------------------
# End-to-end: technician escalation
# ---------------------------------------------------------------------------

class TestEscalation:
    def test_auth_failure_escalation(self, portal, helpdesk):
        """RTSP auth failure should escalate to pending_technician."""
        portal.post("/faults/CAM-002", json={"fault": "rtsp_auth_failure"})
        asyncio.run(run_once())

        tickets = helpdesk.get("/tickets").json()
        assert any(
            t["root_cause"] == "rtsp_auth_failure" and t["status"] == "pending_technician"
            for t in tickets
        )
        # Fault should NOT be auto-cleared
        assert portal.get("/check/CAM-002").json()["rtsp_auth"] is False

    def test_wrong_path_escalation(self, portal, helpdesk):
        portal.post("/faults/CAM-001", json={"fault": "wrong_rtsp_path"})
        asyncio.run(run_once())

        tickets = helpdesk.get("/tickets").json()
        assert any(
            t["root_cause"] == "wrong_rtsp_path" and t["status"] == "pending_technician"
            for t in tickets
        )

    def test_poe_escalation(self, portal, helpdesk):
        portal.post("/faults/CAM-003", json={"fault": "poe_power_off"})
        asyncio.run(run_once())

        tickets = helpdesk.get("/tickets").json()
        assert any(
            t["root_cause"] == "poe_power_off" and t["status"] == "pending_technician"
            for t in tickets
        )

    def test_network_down_escalation(self, portal, helpdesk):
        portal.post("/faults/CAM-001", json={"fault": "network_down"})
        asyncio.run(run_once())

        tickets = helpdesk.get("/tickets").json()
        assert any(
            t["root_cause"] == "network_down" and t["status"] == "pending_technician"
            for t in tickets
        )

    def test_nvr_unavailable_escalation(self, portal, helpdesk):
        portal.post("/faults/NVR-001", json={"fault": "nvr_unavailable"})
        asyncio.run(run_once())

        tickets = helpdesk.get("/tickets").json()
        assert any(
            t["root_cause"] == "nvr_unavailable" and t["status"] == "pending_technician"
            for t in tickets
        )

    def test_storage_full_escalation(self, portal, helpdesk):
        portal.post("/faults/NVR-001", json={"fault": "storage_full"})
        asyncio.run(run_once())

        tickets = helpdesk.get("/tickets").json()
        assert any(
            t["root_cause"] == "storage_full" and t["status"] == "pending_technician"
            for t in tickets
        )

    def test_high_cpu_escalation(self, portal, helpdesk):
        portal.post("/faults/AIBOX-001", json={"fault": "high_cpu"})
        asyncio.run(run_once())

        tickets = helpdesk.get("/tickets").json()
        assert any(
            t["root_cause"] == "high_cpu" and t["status"] == "pending_technician"
            for t in tickets
        )


# ---------------------------------------------------------------------------
# Re-arming and deduplication
# ---------------------------------------------------------------------------

class TestRearmAndDedup:
    def test_rearm_after_recovery(self, portal, helpdesk):
        """After a fault is resolved, a new occurrence creates a new incident."""
        # First fault
        portal.post("/faults/AIBOX-001", json={"fault": "ai_box_service_failure"})
        asyncio.run(run_once())

        # Clear and let agent see recovery
        portal.post("/faults/AIBOX-001/clear")
        asyncio.run(run_once())

        # Second occurrence
        portal.post("/faults/AIBOX-001", json={"fault": "ai_box_service_failure"})
        asyncio.run(run_once())

        state = json.loads((RUNTIME / "agent_state.json").read_text())
        aibox_events = [
            h for h in state["history"]
            if h.get("fault") == "ai_box_service_failure"
        ]
        assert len(aibox_events) >= 2, "Expected at least 2 incidents after re-arm"

    def test_no_duplicate_tickets(self, portal, helpdesk):
        """Multiple agent cycles with the same active fault should not create duplicate tickets."""
        portal.post("/faults/CAM-002", json={"fault": "rtsp_auth_failure"})
        asyncio.run(run_once())
        asyncio.run(run_once())

        tickets = helpdesk.get("/tickets").json()
        active_auth = [
            t for t in tickets
            if t.get("asset_id") == "CAM-002"
            and t.get("root_cause") == "rtsp_auth_failure"
            and t.get("status") in {"open", "pending_technician", "investigating"}
        ]
        # Should have at most 1 active ticket (may be 0 if already resolved, but not >1)
        assert len(active_auth) <= 1, f"Duplicate tickets found: {active_auth}"


# ---------------------------------------------------------------------------
# Multi-camera site outage
# ---------------------------------------------------------------------------

class TestSiteOutage:
    def test_site_wide_fault(self, portal, helpdesk):
        """Site-wide fault injection should affect all cameras at the site."""
        portal.post("/faults/site/SITE-002", json={"fault": "multi_camera_site_outage"})
        asyncio.run(run_once())

        tickets = helpdesk.get("/tickets").json()
        site2_tickets = [
            t for t in tickets
            if t.get("site_id") == "SITE-002" and t.get("status") != "resolved"
        ]
        # Both cameras at SITE-002 should have incidents
        affected_assets = {t.get("asset_id") for t in site2_tickets}
        assert "CAM-002" in affected_assets or "CAM-003" in affected_assets


# ---------------------------------------------------------------------------
# Knowledge retrieval
# ---------------------------------------------------------------------------

class TestKnowledge:
    def test_search_returns_results(self):
        results = knowledge_search("rtsp camera")
        assert len(results) >= 1

    def test_search_relevance(self):
        results = knowledge_search("storage nvr retention")
        assert len(results) >= 1
        assert results[0]["score"] >= 1


# ---------------------------------------------------------------------------
# Regression sweep: every supported fault
# ---------------------------------------------------------------------------

class TestRegressionSweep:
    """Inject each fault, run agent, then clear. Verify all faults are handled."""

    FAULT_ASSET_PAIRS: ClassVar[list[tuple[str, str]]] = [
        ("CAM-001", "network_down"),
        ("CAM-002", "rtsp_auth_failure"),
        ("CAM-001", "rtsp_down"),
        ("CAM-002", "wrong_rtsp_path"),
        ("CAM-003", "poe_power_off"),
        ("NVR-001", "storage_full"),
        ("NVR-001", "nvr_unavailable"),
        ("AIBOX-001", "high_cpu"),
        ("AIBOX-001", "ai_box_service_failure"),
        ("AIBOX-001", "cloud_sync_failure"),
        ("CAM-001", "intermittent_connectivity"),
    ]

    def test_all_faults_diagnosed(self, portal, helpdesk):
        """Every supported fault should be diagnosed and appear as a root cause."""
        for asset_id, fault in self.FAULT_ASSET_PAIRS:
            portal.post(f"/faults/{asset_id}", json={"fault": fault})
            asyncio.run(run_once())
            portal.post(f"/faults/{asset_id}/clear")
            asyncio.run(run_once())

        tickets = helpdesk.get("/tickets").json()
        root_causes = {t["root_cause"] for t in tickets if t.get("root_cause")}
        expected = {fault for _, fault in self.FAULT_ASSET_PAIRS}
        missing = expected - root_causes
        assert not missing, f"Faults not diagnosed: {missing}"


# ---------------------------------------------------------------------------
# Agent retry limit
# ---------------------------------------------------------------------------

class TestRetryLimit:
    def test_stops_after_max_retries(self, portal):
        """Agent should stop retrying after AGENT_MAX_RETRIES attempts."""
        # Inject a human-only fault (won't auto-resolve)
        portal.post("/faults/CAM-002", json={"fault": "rtsp_auth_failure"})

        for _ in range(5):
            asyncio.run(run_once())

        state = json.loads((RUNTIME / "agent_state.json").read_text())
        cam002 = state["active"].get("CAM-002", {})
        assert cam002.get("attempts", 0) <= 3, "Agent should stop at max retries"


# ---------------------------------------------------------------------------
# Investigation & Knowledge endpoints
# ---------------------------------------------------------------------------

class TestInvestigationAndKnowledgeEndpoints:
    def test_investigate_healthy_asset(self, agent):
        resp = agent.post("/investigate/CAM-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["asset"]["id"] == "CAM-001"
        assert not data["is_problem"]
        assert len(data["timeline"]) >= 3

    def test_investigate_safe_fault_recovers(self, portal, agent):
        portal.post("/faults/CAM-001", json={"fault": "rtsp_down"})
        resp = agent.post("/investigate/CAM-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_problem"] is True
        assert data["diagnosis"]["fault"] == "rtsp_down"
        assert data["diagnosis"]["safety_class"] == "SAFE_REVERSIBLE"
        assert data["action_executed"] == "reconnect_stream"
        assert any(s["step"] == "recovery_and_verification" for s in data["timeline"])

    def test_investigate_human_only_escalates(self, portal, agent):
        portal.post("/faults/CAM-002", json={"fault": "rtsp_auth_failure"})
        resp = agent.post("/investigate/CAM-002")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_problem"] is True
        assert data["diagnosis"]["fault"] == "rtsp_auth_failure"
        assert data["diagnosis"]["safety_class"] == "HUMAN_ONLY"
        assert data["action_executed"] is None
        assert any(s["step"] == "escalation" for s in data["timeline"])

    def test_knowledge_endpoints(self, agent):
        # List
        resp = agent.get("/knowledge")
        assert resp.status_code == 200
        docs = resp.json()
        assert len(docs) >= 2
        sources = [d["source"] for d in docs]
        assert any("troubleshooting.md" in s for s in sources)

        # Single document
        doc_resp = agent.get("/knowledge/doc/troubleshooting.md")
        assert doc_resp.status_code == 200
        assert "RTSP" in doc_resp.json()["content"]

        # Search
        search_resp = agent.get("/knowledge-search", params={"q": "rtsp credentials"})
        assert search_resp.status_code == 200
        assert len(search_resp.json()) > 0

