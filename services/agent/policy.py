"""Policy engine — classifies and gates every agent action.

This module is the single source of truth for what the agent is allowed to do.
It is independent of any LLM prompt and cannot be overridden by model output.
"""
from __future__ import annotations

from services.common.models import SafetyClass

# ---------------------------------------------------------------------------
# Action classification tables
# ---------------------------------------------------------------------------

READ_ACTIONS: set[str] = {
    "health",
    "ping",
    "tcp",
    "rtsp_check",
    "logs",
    "ticket_search",
    "docs_search",
    "asset_discovery",
    "site_health",
    "check_asset",
    "fault_history",
}

SAFE_REVERSIBLE_ACTIONS: set[str] = {
    "reconnect_stream",
    "restart_service",
    "retry_upload",
    "clear_transient",
}

APPROVAL_REQUIRED_ACTIONS: set[str] = {
    "credential_change",
    "network_change",
    "nvr_reboot",
    "ai_box_reboot",
    "configuration_change",
    "firmware_action",
}

HUMAN_ONLY_ACTIONS: set[str] = {
    "physical_repair",
    "cable_replacement",
    "camera_replacement",
    "camera_movement",
    "factory_reset",
    "production_security_change",
    "power_restore",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify(action: str) -> SafetyClass:
    """Return the safety class of a given action name."""
    if action in READ_ACTIONS:
        return SafetyClass.READ
    if action in SAFE_REVERSIBLE_ACTIONS:
        return SafetyClass.SAFE_REVERSIBLE
    if action in APPROVAL_REQUIRED_ACTIONS:
        return SafetyClass.APPROVAL_REQUIRED
    # Default: treat unknown actions as HUMAN_ONLY (fail-safe)
    return SafetyClass.HUMAN_ONLY


def allowed_automatically(action: str) -> bool:
    """Return True only if the action can be performed without human approval."""
    return classify(action) in {SafetyClass.READ, SafetyClass.SAFE_REVERSIBLE}


def describe_policy() -> dict[str, list[str]]:
    """Return the full policy for inspection / documentation."""
    return {
        "READ": sorted(READ_ACTIONS),
        "SAFE_REVERSIBLE": sorted(SAFE_REVERSIBLE_ACTIONS),
        "APPROVAL_REQUIRED": sorted(APPROVAL_REQUIRED_ACTIONS),
        "HUMAN_ONLY": sorted(HUMAN_ONLY_ACTIONS),
    }
