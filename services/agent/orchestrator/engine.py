"""Deterministic orchestrator engine: observe -> evidence -> review ->
decide -> policy -> execute -> verify (or technician handoff).

ORCHESTRATOR layer (AGENTS.md): plans routes, enforces budgets, gates on
evidence review, asks policy before any action — it never grants itself
permission. Specialists plug in behind the router in Phase 3.
"""
from __future__ import annotations

import uuid
from typing import Any, Callable, Dict

from ..policy.audit import AuditLog
from ..policy.engine import PolicyEngine
from .budgets import Budget
from .models import (ActionProposal, EvidenceType, Handoff, IncidentContext,
                     IncidentState, SpecialistFinding, VerificationResult)
from .router import derive_signals, route
from .state import SUPPRESS_STATES, IncidentStore, StateMachine, can_transition

P = IncidentState


class Orchestrator:
    def __init__(self, tools, store: IncidentStore, policy: PolicyEngine,
                 audit: AuditLog, budget_factory: Callable[[], Budget] = Budget):
        self.tools = tools
        self.store = store
        self.policy = policy
        self.audit = audit
        self.machine = StateMachine(store)
        self.budget_factory = budget_factory

    def run(self, ticket: Dict[str, Any]) -> IncidentContext:
        """Drive one ticket through the state machine (idempotent)."""
        ctx = self.store.latest_active_for_ticket(ticket['id'])
        if ctx is not None and ctx.state in SUPPRESS_STATES:
            # Duplicate suppression: waiting on a human or already resolved.
            return ctx
        if ctx is None:
            ctx = IncidentContext(
                incident_id=f"INC-{ticket['id']}-{uuid.uuid4().hex[:8]}",
                ticket_id=int(ticket['id']),
                budget=self.budget_factory(),
            )
            self.store.save(ctx)
            self.machine.transition(ctx, P.CLASSIFYING, 'ticket received')

        steps = 0
        while ctx.state not in SUPPRESS_STATES and steps < 16:
            reason = ctx.budget.exhausted_reason()
            if reason:
                self._escalate(ctx, f'abort: {reason}')
                break
            getattr(self, f'_stage_{ctx.state.value}')(ctx, ticket)
            steps += 1
        self.store.save(ctx)
        return ctx

    def _stage_classifying(self, ctx: IncidentContext, ticket: Dict[str, Any]) -> None:
        ctx.asset_id = ticket.get('asset_id') or ''
        ctx.site_id = ticket.get('site_id') or ''
        ctx.symptom = f"{ticket.get('title', '')}. {ticket.get('description', '')}".strip('. ')
        ctx.add_evidence(
            f'ticket {ticket["id"]} symptom: {ctx.symptom}',
            source=f'helpdesk:{ticket["id"]}', etype=EvidenceType.RETRIEVED,
        )
        self.machine.transition(ctx, P.INVESTIGATING, 'context normalized')

    def _probe(self, ctx: IncidentContext, name: str, fn, *args, **kwargs):
        ctx.budget.charge_tool()
        try:
            result = fn(*args, **kwargs)
        except Exception as exc:  # probe errors are evidence, not crashes
            ctx.observations[name] = {'error': str(exc)}
            ctx.add_evidence(f'{name} probe failed: {exc}', source=name)
            return None
        ctx.observations[name] = result
        ctx.add_evidence(f'{name}: {result}', source=name)
        return result

    def _stage_investigating(self, ctx: IncidentContext, ticket: Dict[str, Any]) -> None:
        health = self._probe(ctx, 'health', self.tools.health, ctx.asset_id)
        self._probe(ctx, 'ping', self.tools.ping, ctx.asset_id)
        asset_type = (health or {}).get('type')
        if asset_type in ('camera', 'nvr'):
            self._probe(ctx, 'tcp', self.tools.tcp_test, ctx.asset_id)
            self._probe(ctx, 'rtsp', self.tools.rtsp_test, ctx.asset_id)
        else:
            ctx.add_evidence('rtsp/tcp probes skipped: not a camera/NVR',
                             source='router', etype=EvidenceType.INFERRED)
        ctx.fault = (health or {}).get('fault')
        ctx.route = route(derive_signals(ctx.observations))
        for _ in ctx.route:
            ctx.budget.charge_specialist()
        self.machine.transition(ctx, P.EVIDENCE_REVIEW,
                                f'{len(ctx.route)} specialist(s) planned')

    def _stage_evidence_review(self, ctx: IncidentContext, ticket: Dict[str, Any]) -> None:
        """Review gate before any diagnosis/action (Evidence Agent rules)."""
        required = ('health', 'ping')
        missing = [k for k in required
                   if not ctx.observations.get(k) or 'error' in (ctx.observations.get(k) or {})]
        if len(missing) >= 2:
            ctx.findings.append(SpecialistFinding(
                agent='evidence', status='blocked',
                facts=[f'missing required probes: {", ".join(missing)}'],
                confidence=0.2, recommendations=['NEEDS_MORE_TESTS'],
                requires_human=True, handoff_reason='insufficient evidence',
            ))
            ctx.handoff = self._build_handoff(
                ctx,
                requested_action='Collect missing evidence on site with a technician.',
                why='evidence review blocked: required probes unavailable',
                uncertainty='no live telemetry available for this asset')
            self.machine.transition(ctx, P.PENDING_TECHNICIAN, 'evidence review blocked')
            return
        ctx.findings.append(SpecialistFinding(
            agent='evidence', status='complete',
            facts=[f'{len(ctx.evidence)} evidence items reviewed',
                   f'planned route: {[r["agent"] for r in ctx.route]}'],
            hypotheses=['leading hypothesis formed in diagnosis stage'],
            confidence=0.7, recommendations=['GO']))
        self.machine.transition(ctx, P.DIAGNOSED, 'evidence review passed')

    def _stage_diagnosed(self, ctx: IncidentContext, ticket: Dict[str, Any]) -> None:
        """Rule table ported from legacy core.investigate(), now gated by
        the state machine and (next stage) the policy engine."""
        h = ctx.observations.get('health') or {}
        rtsp = ctx.observations.get('rtsp') or {}

        if h.get('poe') is False:
            self._diagnose_handoff(
                ctx, 'PoE/power fault: camera unreachable with PoE off', 0.9,
                requested_action='Inspect PoE port link, Ethernet cable and camera '
                                 'power; move to a known-good port if needed.',
                why='physical repair is human-only',
                unverifiable=['cable and PoE status are not observable in monitoring'],
                uncertainty='power loss observed; root physical cause unknown')
        elif h.get('reachable') is False:
            self._diagnose_handoff(
                ctx, 'Network reachability failure (host unreachable)', 0.8,
                requested_action='Check upstream switch, patch panel and device power; '
                                 'do not change IP configuration without approval.',
                why='network/physical next steps are approval-required or human-only',
                unverifiable=['physical link state beyond simulated reachability'],
                uncertainty='single-host view; site-wide correlation not yet available')
        elif rtsp.get('auth') == 'invalid' or h.get('rtsp') == 'auth_failed':
            self._diagnose_handoff(
                ctx, 'Likely RTSP authentication/configuration mismatch', 0.9,
                requested_action='Verify approved RTSP credentials/stream configuration '
                                 'against the internal procedure (never change '
                                 'credentials autonomously).',
                why='credential changes are class C/D (approval required)',
                unverifiable=['credential values are not readable in the simulator'],
                uncertainty='auth rejection observed; mismatching side unproven')
        elif h.get('rtsp') == 'unavailable' or rtsp.get('stream') == 'unavailable':
            ctx.diagnosis = 'Transient RTSP interruption'
            ctx.confidence = 0.8
            ctx.proposed_action = ActionProposal(
                name='reconnect-rtsp', asset_id=ctx.asset_id,
                reason='transient RTSP outage with valid auth (registered safe action)',
                evidence_ids=[e.id for e in ctx.evidence])
            self.machine.transition(ctx, P.ACTION_PROPOSED, ctx.diagnosis)
        elif h.get('type') == 'ai_box' and h.get('service') == 'down':
            ctx.diagnosis = 'AI inference service is down'
            ctx.confidence = 0.9
            ctx.proposed_action = ActionProposal(
                name='restart-ai-service', asset_id=ctx.asset_id,
                reason='AI service down on reachable host (registered safe action)',
                evidence_ids=[e.id for e in ctx.evidence])
            self.machine.transition(ctx, P.ACTION_PROPOSED, ctx.diagnosis)
        elif (h.get('cpu') or 0) >= 90:
            self._diagnose_handoff(
                ctx, 'High resource utilization threatening service health', 0.8,
                requested_action='Inspect active processes/load and trend before any '
                                 'consequential restart; plan capacity relief.',
                why='consequential restarts and config changes need human approval',
                unverifiable=['process-level detail is not exposed by the simulator'],
                uncertainty='cause of the load unknown')
        elif (h.get('storage') or 0) >= 95:
            self._diagnose_handoff(
                ctx, 'Storage capacity critically high (retention at risk)', 0.9,
                requested_action='Free or rotate storage per the site SOP; storage '
                                 'deletion is human-only.',
                why='destructive storage work is human-only',
                unverifiable=['what occupies the storage'],
                uncertainty='only capacity level is observable')
        elif h.get('cloud') == 'unavailable':
            self._diagnose_handoff(
                ctx, 'Cloud synchronization unavailable', 0.7,
                requested_action='Check upstream connectivity and cloud service status '
                                 'before changing local configuration.',
                why='upstream diagnosis and config changes are out of autonomous scope',
                unverifiable=['cloud-side service health'],
                uncertainty='local vs cloud side unknown')
        else:
            self._diagnose_handoff(
                ctx, 'No critical fault reproduced by current checks', 0.3,
                requested_action='Review logs and continue guided troubleshooting '
                                 'with the technician.',
                why='evidence insufficient for an autonomous action',
                unverifiable=['reported symptom not reproducible from telemetry'],
                uncertainty='low confidence; symptom may be client-side/intermittent')

    def _stage_new(self, ctx: IncidentContext, ticket: Dict[str, Any]) -> None:
        # Only reachable if a previous run crashed before classifying.
        self.machine.transition(ctx, P.CLASSIFYING, 'resumed')

    def _diagnose_handoff(self, ctx: IncidentContext, diagnosis: str, confidence: float,
                          *, requested_action: str, why: str,
                          unverifiable=None, uncertainty: str = '') -> None:
        ctx.diagnosis = diagnosis
        ctx.confidence = confidence
        ctx.handoff = self._build_handoff(
            ctx, requested_action=requested_action, why=why,
            unverifiable=unverifiable, uncertainty=uncertainty)
        self.machine.transition(ctx, P.PENDING_TECHNICIAN, diagnosis)

    def _build_handoff(self, ctx: IncidentContext, *, requested_action: str, why: str,
                       uncertainty: str = '', unverifiable=None) -> Handoff:
        return Handoff(
            observed_facts=[e.claim for e in ctx.evidence
                            if e.type == EvidenceType.OBSERVED][:8],
            evidence=[f'{e.id} ({e.source}): {e.claim}' for e in ctx.evidence][:12],
            diagnosis=ctx.diagnosis or 'unknown',
            confidence=ctx.confidence,
            uncertainty=uncertainty,
            requested_action=requested_action,
            why_stopped=why,
            unverifiable=unverifiable or [],
            verification_steps=[
                'Re-run health/ping (and RTSP where applicable) checks.',
                'Confirm the originally reported symptom no longer occurs.'])

    def _stage_action_proposed(self, ctx: IncidentContext, ticket: Dict[str, Any]) -> None:
        proposal = ctx.proposed_action
        decision = self.policy.decide(proposal, fault=ctx.fault)
        self.audit.record(
            incident_id=ctx.incident_id, ticket_id=ctx.ticket_id, action=proposal.name,
            reason=proposal.reason, evidence_ids=proposal.evidence_ids,
            decision='allow' if decision.allowed else 'deny', result=decision.reason)
        if not decision.allowed:
            ctx.handoff = self._build_handoff(
                ctx,
                requested_action=f'{proposal.name} denied by policy; technician to '
                                 'perform or escalate the next step manually.',
                why=decision.reason,
                uncertainty=f'policy decision: {decision.reason}')
            target = P.HUMAN_REQUIRED if decision.requires_human else P.PENDING_TECHNICIAN
            self.machine.transition(ctx, target, f'policy denied: {decision.reason}')
            return
        self.machine.transition(ctx, P.SAFE_EXECUTION, 'policy allowed')

    def _stage_safe_execution(self, ctx: IncidentContext, ticket: Dict[str, Any]) -> None:
        proposal = ctx.proposed_action
        ctx.budget.charge_action()
        try:
            result = self.tools.execute_action(proposal.name, proposal.asset_id)
        except Exception as exc:
            result = {'ok': False, 'error': str(exc)}
        ctx.observations['last_action'] = result
        ctx.executed_actions.append(proposal.name)
        self.audit.record(
            incident_id=ctx.incident_id, ticket_id=ctx.ticket_id, action=proposal.name,
            reason=proposal.reason, decision='allow', result=str(result),
            verification='pending')
        self.machine.transition(ctx, P.VERIFYING, 'action executed; verifying')

    def _stage_verifying(self, ctx: IncidentContext, ticket: Dict[str, Any]) -> None:
        ctx.budget.charge_tool()
        try:
            health = self.tools.health(ctx.asset_id)
        except Exception as exc:
            health = {'error': str(exc)}
        ctx.observations['verify_health'] = health
        ctx.add_evidence(f'verify health: {health}', source='health')
        passed = False
        if ctx.executed_actions:
            last = ctx.executed_actions[-1]
            if last == 'reconnect-rtsp':
                passed = health.get('rtsp') == 'healthy'
            elif last == 'restart-ai-service':
                passed = health.get('service') == 'healthy'
        else:
            passed = bool(health.get('fault') is None and health.get('reachable', True)
                          and health.get('rtsp', 'healthy') == 'healthy'
                          and health.get('service', 'healthy') == 'healthy')
        detail = 'verification ' + ('passed' if passed else 'failed')
        ctx.verification = VerificationResult(performed=True, passed=passed, detail=detail)
        action = ctx.proposed_action.name if ctx.proposed_action else 'verify-ticket'
        self.audit.record(
            incident_id=ctx.incident_id, ticket_id=ctx.ticket_id, action=action,
            decision='verify',
            result='executed' if ctx.executed_actions else 'technician-work',
            verification=detail)
        if passed:
            ctx.confidence = max(ctx.confidence, 0.9)
            self.machine.transition(ctx, P.RESOLVED, detail)
        else:
            ctx.handoff = self._build_handoff(
                ctx,
                requested_action='Technician: inspect source-side condition; automatic '
                                 'recovery did not verify.',
                why='post-action verification failed',
                uncertainty='recovery not observed after the action')
            self.machine.transition(ctx, P.PENDING_TECHNICIAN, detail)

    def _stage_human_required(self, ctx: IncidentContext, ticket: Dict[str, Any]) -> None:
        self.machine.transition(ctx, P.PENDING_TECHNICIAN, 'human action required')

    def _stage_ready_for_verification(self, ctx: IncidentContext, ticket: Dict[str, Any]) -> None:
        self.machine.transition(ctx, P.VERIFYING, 'technician done; re-verifying')

    def _escalate(self, ctx: IncidentContext, reason: str) -> None:
        if ctx.handoff is None:
            ctx.handoff = self._build_handoff(
                ctx, requested_action='Continue diagnostics with a technician.',
                why=reason, uncertainty=reason)
        if can_transition(ctx.state, P.PENDING_TECHNICIAN):
            self.machine.transition(ctx, P.PENDING_TECHNICIAN, reason)
        else:
            ctx.notes.append(reason)
