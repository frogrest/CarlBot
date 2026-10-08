"""Deterministic plan selection, preserving the pre-LLM decision table."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .schemas import ActionProposal, Plan

if TYPE_CHECKING:
    from ..orchestrator.models import IncidentContext


class DeterministicReasoner:
    def close(self) -> None:
        return None

    def propose(self, ctx: IncidentContext) -> Plan:
        health = ctx.observations.get('health') or {}
        rtsp = ctx.observations.get('rtsp') or {}

        if health.get('poe') is False:
            return self._handoff(
                'PoE/power fault: camera unreachable with PoE off', 0.9,
                'Inspect PoE port link, Ethernet cable and camera power; move to a '
                'known-good port if needed.',
                'physical repair is human-only',
                ['cable and PoE status are not observable in monitoring'],
                'power loss observed; root physical cause unknown')
        if health.get('reachable') is False:
            return self._handoff(
                'Network reachability failure (host unreachable)', 0.8,
                'Check upstream switch, patch panel and device power; do not change '
                'IP configuration without approval.',
                'network/physical next steps are approval-required or human-only',
                ['physical link state beyond simulated reachability'],
                'single-host view; site-wide correlation not yet available')
        if rtsp.get('auth') == 'invalid' or health.get('rtsp') == 'auth_failed':
            return self._handoff(
                'Likely RTSP authentication/configuration mismatch', 0.9,
                'Verify approved RTSP credentials/stream configuration against the '
                'internal procedure (never change credentials autonomously).',
                'credential changes are class C/D (approval required)',
                ['credential values are not readable in the simulator'],
                'auth rejection observed; mismatching side unproven')
        if health.get('rtsp') == 'unavailable' or rtsp.get('stream') == 'unavailable':
            return self._action(
                ctx, 'Transient RTSP interruption', 0.8, 'reconnect-rtsp',
                'transient RTSP outage with valid auth (registered safe action)')
        if health.get('type') == 'ai_box' and health.get('service') == 'down':
            return self._action(
                ctx, 'AI inference service is down', 0.9, 'restart-ai-service',
                'AI service down on reachable host (registered safe action)')
        if (health.get('cpu') or 0) >= 90:
            return self._handoff(
                'High resource utilization threatening service health', 0.8,
                'Inspect active processes/load and trend before any consequential '
                'restart; plan capacity relief.',
                'consequential restarts and config changes need human approval',
                ['process-level detail is not exposed by the simulator'],
                'cause of the load unknown')
        if (health.get('storage') or 0) >= 95:
            return self._handoff(
                'Storage capacity critically high (retention at risk)', 0.9,
                'Free or rotate storage per the site SOP; storage deletion is '
                'human-only.',
                'destructive storage work is human-only',
                ['what occupies the storage'],
                'only capacity level is observable')
        if health.get('cloud') == 'unavailable':
            return self._handoff(
                'Cloud synchronization unavailable', 0.7,
                'Check upstream connectivity and cloud service status before changing '
                'local configuration.',
                'upstream diagnosis and config changes are out of autonomous scope',
                ['cloud-side service health'],
                'local vs cloud side unknown')
        return self._handoff(
            'No critical fault reproduced by current checks', 0.3,
            'Review logs and continue guided troubleshooting with the technician.',
            'evidence insufficient for an autonomous action',
            ['reported symptom not reproducible from telemetry'],
            'low confidence; symptom may be client-side/intermittent')

    @staticmethod
    def _action(ctx: IncidentContext, diagnosis: str, confidence: float,
                name: str, reason: str) -> Plan:
        return Plan(
            diagnosis=diagnosis,
            confidence=confidence,
            action=ActionProposal(
                name=name,
                asset_id=ctx.asset_id,
                reason=reason,
                evidence_ids=[item.id for item in ctx.evidence],
            ),
            requires_human=False,
        )

    @staticmethod
    def _handoff(diagnosis: str, confidence: float, requested_action: str,
                 why_stopped: str, unverifiable: list[str],
                 uncertainty: str) -> Plan:
        return Plan(
            diagnosis=diagnosis,
            confidence=confidence,
            requires_human=True,
            requested_action=requested_action,
            why_stopped=why_stopped,
            unverifiable=unverifiable,
            uncertainty=uncertainty,
        )
