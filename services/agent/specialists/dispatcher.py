"""Deterministic specialist dispatch behind the orchestrator's evidence router."""
from __future__ import annotations

from typing import Any, Callable, Dict, List

import httpx

from ..orchestrator.budgets import Budget
from ..orchestrator.models import (
    Evidence,
    EvidenceType,
    IncidentContext,
    SpecialistFinding,
)
from ..tools.bus import ToolBus

SPECIALIST_NAMES = frozenset({
    'helpdesk', 'network', 'rtsp', 'camera_nvr',
    'aibox', 'knowledge', 'evidence', 'technician',
})


class ReadOnlyTools:
    """Expose only retrieval tools and charge every call to the incident budget."""

    def __init__(self, tools: ToolBus, budget: Budget):
        self._history_search = tools.history_search
        self._doc_search = tools.doc_search
        self._site_assets = tools.site_assets
        self._budget = budget

    def history_search(self, query: str, asset_id: str = '') -> List[Dict[str, Any]]:
        self._budget.charge_tool()
        return self._history_search(query, asset_id)

    def doc_search(self, query: str) -> List[Dict[str, Any]]:
        self._budget.charge_tool()
        return self._doc_search(query)

    def site_assets(self, site_id: str) -> List[Dict[str, Any]]:
        self._budget.charge_tool()
        return self._site_assets(site_id)


class SpecialistDispatcher:
    """Run a bounded domain analysis; specialists never receive mutation tools."""

    def __init__(self, tools: ToolBus, budget: Budget):
        self.tools = ReadOnlyTools(tools, budget)
        self._specialists: Dict[str, Callable[[IncidentContext], SpecialistFinding]] = {
            'helpdesk': self._helpdesk,
            'network': self._network,
            'rtsp': self._rtsp,
            'camera_nvr': self._camera_nvr,
            'aibox': self._aibox,
            'knowledge': self._knowledge,
            'evidence': self._evidence,
            'technician': self._technician,
        }

    def run(self, name: str, ctx: IncidentContext, question: str) -> SpecialistFinding:
        if name not in self._specialists:
            raise ValueError(f'unknown specialist: {name}')
        if question:
            ctx.notes.append(f'{name} assignment: {question}')
        try:
            finding = self._specialists[name](ctx)
        except (httpx.HTTPError, OSError) as exc:
            evidence = ctx.add_evidence(
                f'{name} specialist lookup failed: {exc}',
                source=f'specialist:{name}',
            )
            return SpecialistFinding(
                agent=name,
                status='blocked',
                facts=[f'{evidence.claim} [{evidence.id}]'],
                tests_performed=[f'{name} retrieval failed: {exc}'],
                evidence=[evidence],
                confidence=0.0,
                recommendations=['Continue only with available evidence.'],
                requires_human=True,
                handoff_reason='A required read-only lookup failed.',
            )
        return finding

    @staticmethod
    def _observed(ctx: IncidentContext, *sources: str) -> List[Evidence]:
        source_set = set(sources)
        return [
            item for item in ctx.evidence
            if item.type == EvidenceType.OBSERVED and item.source in source_set
        ]

    @staticmethod
    def _facts(items: List[Evidence]) -> List[str]:
        return [
            f'{item.claim} [{item.id}]'
            for item in items
            if item.type != EvidenceType.INFERRED
        ]

    @staticmethod
    def _probe_ok(ctx: IncidentContext, name: str) -> bool:
        result = ctx.observations.get(name)
        return isinstance(result, dict) and 'error' not in result

    @staticmethod
    def _new_evidence(
        ctx: IncidentContext,
        claim: str,
        source: str,
        etype: EvidenceType = EvidenceType.RETRIEVED,
    ) -> Evidence:
        return ctx.add_evidence(claim, source=source, etype=etype)

    def _site_evidence(self, ctx: IncidentContext) -> List[Evidence]:
        if 'site_assets' not in ctx.observations:
            if not ctx.site_id:
                return []
            assets = self.tools.site_assets(ctx.site_id)
            ctx.observations['site_assets'] = assets
            self._new_evidence(
                ctx,
                f'Site {ctx.site_id} asset inventory returned {len(assets)} asset(s).',
                f'portal:site_assets:{ctx.site_id}',
                EvidenceType.OBSERVED,
            )
        return self._observed(ctx, f'portal:site_assets:{ctx.site_id}')

    def _helpdesk(self, ctx: IncidentContext) -> SpecialistFinding:
        results = self.tools.history_search(ctx.symptom, ctx.asset_id)
        evidence = [
            self._new_evidence(
                ctx,
                ' | '.join(
                    str(value) for value in (
                        f"Ticket {row.get('id', 'unknown')}",
                        row.get('title') or 'untitled',
                        row.get('root_cause') or row.get('resolution') or row.get('status') or '',
                    ) if value
                ),
                f"helpdesk:ticket:{row.get('id', 'unknown')}",
            )
            for row in results[:5]
        ]
        if not results:
            evidence.append(self._new_evidence(
                ctx,
                'Historical ticket search returned no matching tickets.',
                'helpdesk:search',
            ))
        facts = self._facts(evidence) or ['No matching historical tickets were returned.']
        return SpecialistFinding(
            agent='helpdesk',
            status='complete',
            facts=facts,
            hypotheses=[
                'Historical matches can suggest a pattern but do not prove the current root cause.'
            ] if evidence else [],
            tests_performed=[f'Historical ticket search returned {len(results)} result(s).'],
            evidence=evidence,
            confidence=0.55 if evidence else 0.0,
            recommendations=['Confirm current symptoms before using historical resolutions.'],
        )

    def _network(self, ctx: IncidentContext) -> SpecialistFinding:
        evidence = self._observed(ctx, 'health', 'ping', 'tcp')
        site_evidence = self._site_evidence(ctx)
        evidence.extend(site_evidence)
        health = ctx.observations.get('health') or {}
        ping = ctx.observations.get('ping') or {}
        tcp = ctx.observations.get('tcp') or {}
        if health.get('poe') is False:
            hypothesis = 'Power/PoE or physical connectivity is implicated; cause is unverified.'
            recommendation = 'Technician: inspect the simulated PoE port, cable, and device power.'
            human = True
        elif ping.get('ok') is False or health.get('reachable') is False:
            hypothesis = 'The host is unreachable; upstream network or device power remains possible.'
            recommendation = 'Correlate neighboring assets, then request a technician site check.'
            human = True
        elif tcp.get('open') is False:
            hypothesis = 'The host responds but the tested TCP port is closed.'
            recommendation = 'Route service-level investigation to RTSP; do not change firewall rules.'
            human = False
        else:
            hypothesis = 'The available reachability checks do not show a network-layer fault.'
            recommendation = 'Continue with the specialist responsible for the reported service.'
            human = False
        return SpecialistFinding(
            agent='network',
            status='complete' if (
                self._probe_ok(ctx, 'health')
                and self._probe_ok(ctx, 'ping')
                and (
                    health.get('type') not in {'camera', 'nvr'}
                    or self._probe_ok(ctx, 'tcp')
                )
            ) else 'partial',
            facts=self._facts(evidence),
            hypotheses=[hypothesis],
            tests_performed=['Reviewed health, ping, TCP/554, and site inventory evidence when available.'],
            evidence=evidence,
            confidence=0.75 if evidence else 0.25,
            recommendations=[recommendation],
            requires_human=human,
            handoff_reason='A physical or approval-required network check may be needed.' if human else None,
        )

    def _rtsp(self, ctx: IncidentContext) -> SpecialistFinding:
        evidence = self._observed(ctx, 'health', 'tcp', 'rtsp')
        health = ctx.observations.get('health') or {}
        rtsp = ctx.observations.get('rtsp') or {}
        auth = rtsp.get('auth')
        stream = rtsp.get('stream') or health.get('rtsp')
        if auth == 'invalid' or stream == 'auth_failed':
            hypothesis = 'RTSP authentication/configuration mismatch; credential values are unavailable.'
            recommendation = 'Technician: verify the approved stream configuration; do not change credentials.'
            human = True
        elif stream == 'unavailable' and auth == 'valid':
            hypothesis = 'RTSP stream is unavailable; distinguish transient source failure from upstream issues.'
            recommendation = 'The orchestrator may propose reconnect-rtsp; policy and verification remain mandatory.'
            human = False
        elif stream == 'unavailable':
            hypothesis = 'RTSP stream is unavailable, but authentication state is not confirmed.'
            recommendation = 'Confirm RTSP authentication state before considering a reconnect.'
            human = True
        elif stream == 'healthy':
            hypothesis = 'Current RTSP evidence is healthy; the reported symptom may be recorder/client-side.'
            recommendation = 'Route to Camera/NVR or Helpdesk to confirm the active symptom.'
            human = False
        else:
            hypothesis = 'RTSP state is not established by the available probes.'
            recommendation = 'Collect a fresh TCP/554 and RTSP result before diagnosis.'
            human = True
        return SpecialistFinding(
            agent='rtsp',
            status='complete' if (
                self._probe_ok(ctx, 'health')
                and self._probe_ok(ctx, 'rtsp')
                and (
                    health.get('type') not in {'camera', 'nvr'}
                    or self._probe_ok(ctx, 'tcp')
                )
            ) else 'partial',
            facts=self._facts(evidence),
            hypotheses=[hypothesis],
            tests_performed=['Reviewed the available TCP/554 and RTSP probe results.'],
            evidence=evidence,
            confidence=0.85 if stream in {'unavailable', 'auth_failed', 'healthy'} else 0.3,
            recommendations=[recommendation],
            requires_human=human,
            handoff_reason='Credential or additional on-site checks must remain human-controlled.' if human else None,
        )

    def _camera_nvr(self, ctx: IncidentContext) -> SpecialistFinding:
        evidence = self._observed(ctx, 'health', 'ping', 'rtsp')
        evidence.extend(self._site_evidence(ctx))
        health = ctx.observations.get('health') or {}
        assets = ctx.observations.get('site_assets') or []
        failed_assets = [
            asset.get('asset_id') for asset in assets
            if asset.get('reachable') is False
        ]
        if health.get('type') == 'nvr' and health.get('reachable') is False:
            hypothesis = 'The recorder host is unreachable; recorder or network scope needs confirmation.'
        elif len(failed_assets) > 1:
            hypothesis = f'Multiple site assets are unreachable: {failed_assets}.'
        elif ctx.asset_id and health.get('type') == 'camera':
            hypothesis = 'Evidence is limited to this camera; no recorder/channel mapping was supplied.'
        else:
            hypothesis = 'Recorder relationships and channel/recording state are not exposed by current evidence.'
        return SpecialistFinding(
            agent='camera_nvr',
            status='complete' if (
                self._probe_ok(ctx, 'health')
                and self._probe_ok(ctx, 'ping')
                and 'site_assets' in ctx.observations
            ) else 'partial',
            facts=self._facts(evidence),
            hypotheses=[hypothesis],
            tests_performed=['Reviewed asset health and site inventory; no channel map was inferred.'],
            evidence=evidence,
            confidence=0.65 if evidence else 0.25,
            recommendations=['Confirm supplied NVR/channel relationships before recorder-side changes.'],
        )

    def _aibox(self, ctx: IncidentContext) -> SpecialistFinding:
        evidence = self._observed(ctx, 'health', 'ping')
        health = ctx.observations.get('health') or {}
        service = health.get('service')
        if service == 'down':
            hypothesis = 'The AI inference service is down on the observed AI Box.'
            recommendation = 'The orchestrator may propose restart-ai-service; policy and verification remain mandatory.'
            confidence = 0.9
            human = False
        elif (health.get('cpu') or 0) >= 90:
            hypothesis = 'Observed CPU pressure may threaten service health; cause is not established.'
            recommendation = 'Review resource usage with a technician; do not restart consequential services automatically.'
            confidence = 0.8
            human = True
        elif (health.get('storage') or 0) >= 95:
            hypothesis = 'Observed storage pressure creates retention risk.'
            recommendation = 'Technician: follow the approved retention procedure; do not delete data autonomously.'
            confidence = 0.85
            human = True
        elif health.get('cloud') == 'unavailable':
            hypothesis = 'Cloud synchronization is unavailable; local versus upstream cause is unknown.'
            recommendation = 'Correlate with Network and approved cloud-service documentation.'
            confidence = 0.65
            human = False
        else:
            hypothesis = 'Available AI Box telemetry does not show a critical service fault.'
            recommendation = 'Continue with upstream camera or knowledge investigation as indicated.'
            confidence = 0.45
            human = False
        return SpecialistFinding(
            agent='aibox',
            status='complete' if (
                self._probe_ok(ctx, 'health') and self._probe_ok(ctx, 'ping')
            ) else 'partial',
            facts=self._facts(evidence),
            hypotheses=[hypothesis],
            tests_performed=['Reviewed AI Box health and reachability telemetry.'],
            evidence=evidence,
            confidence=confidence,
            recommendations=[recommendation],
            requires_human=human,
            handoff_reason='Next steps are human-only or require approval.' if human else None,
        )

    def _knowledge(self, ctx: IncidentContext) -> SpecialistFinding:
        docs = self.tools.doc_search(ctx.symptom)
        history = self.tools.history_search(ctx.symptom, ctx.asset_id)
        has_sources = bool(docs or history)
        evidence: List[Evidence] = []
        for result in docs[:3]:
            path = str(result.get('path', 'unknown'))
            excerpt = str(result.get('excerpt', '')).strip()[:300]
            claim = f"Document {path} (score {result.get('score', 0)}): {excerpt}"
            evidence.append(self._new_evidence(ctx, claim, f'docs:{path}'))
        for row in history[:3]:
            ticket_id = row.get('id', 'unknown')
            claim = (
                f"Historical ticket {ticket_id}: {row.get('title', 'untitled')}; "
                f"{row.get('root_cause') or row.get('resolution') or row.get('status', '')}"
            )
            evidence.append(self._new_evidence(ctx, claim, f'helpdesk:ticket:{ticket_id}'))
        if not evidence:
            evidence.append(self._new_evidence(
                ctx,
                'Document and historical searches returned no matching sources.',
                'knowledge:search',
            ))
        return SpecialistFinding(
            agent='knowledge',
            status='complete' if has_sources else 'partial',
            facts=self._facts(evidence) or ['No matching document or historical ticket was returned.'],
            hypotheses=[
                'Retrieved sources are contextual evidence, not proof of the current cause.'
            ] if evidence else [],
            tests_performed=[
                f'Document search returned {len(docs)} result(s).',
                f'Historical search returned {len(history)} result(s).',
            ],
            evidence=evidence,
            confidence=0.55 if evidence else 0.0,
            recommendations=['Use only directly relevant citations; prefer approved procedures over similarity.'],
        )

    def _evidence(self, ctx: IncidentContext) -> SpecialistFinding:
        proposal = ctx.proposed_action
        if proposal is None:
            return SpecialistFinding(
                agent='evidence',
                status='partial',
                facts=['No action proposal is available for a pre-execution review.'],
                recommendations=['NEEDS_MORE_TESTS'],
                confidence=0.0,
                requires_human=True,
                handoff_reason='An action cannot be reviewed without an explicit proposal.',
            )

        health = ctx.observations.get('health') or {}
        rtsp = ctx.observations.get('rtsp') or {}
        tcp = ctx.observations.get('tcp') or {}
        if proposal.name == 'reconnect-rtsp':
            supporting_agent = 'rtsp'
            required = ['health', 'rtsp', 'tcp']
            missing_evidence = (
                any(not self._probe_ok(ctx, key) for key in required)
                or rtsp.get('auth') not in {'valid', 'invalid'}
                or 'stream' not in rtsp
            )
            observation_support = (
                health.get('reachable') is True
                and rtsp.get('stream') == 'unavailable'
                and rtsp.get('auth') == 'valid'
                and tcp.get('open') is True
            )
        elif proposal.name == 'restart-ai-service':
            supporting_agent = 'aibox'
            required = ['health']
            missing_evidence = any(
                not self._probe_ok(ctx, key) for key in required)
            observation_support = (
                health.get('type') == 'ai_box'
                and health.get('reachable') is True
                and health.get('service') == 'down'
            )
        else:
            supporting_agent = ''
            required = []
            missing_evidence = False
            observation_support = False
        specialist = next(
            (item for item in ctx.findings if item.agent == supporting_agent),
            None,
        )
        specialist_support = bool(
            specialist and specialist.status == 'complete' and any(
                proposal.name in recommendation
                for recommendation in specialist.recommendations
            )
        )
        supported = observation_support and specialist_support
        evidence = self._observed(ctx, *required)
        facts = self._facts(evidence)
        if specialist is not None:
            facts.append(
                f'{supporting_agent} specialist recommendation reviewed '
                f'[{", ".join(item.id for item in specialist.evidence)}].'
            )
        if supported:
            verdict = 'GO_SAFE_ACTION'
            recommendation = 'Evidence matches the registered simulated action preconditions.'
        elif not supporting_agent:
            verdict = 'NO_GO'
            recommendation = 'The proposed action is not a registered specialist recommendation.'
        elif missing_evidence or specialist is None:
            verdict = 'NEEDS_MORE_TESTS'
            recommendation = 'Collect the missing observations or specialist finding before considering the action.'
        else:
            verdict = 'NO_GO'
            recommendation = 'The proposed action does not match the observed preconditions.'
        return SpecialistFinding(
            agent='evidence',
            status='complete' if supported else 'blocked',
            facts=facts,
            hypotheses=[recommendation],
            tests_performed=[f'Reviewed action {proposal.name} against evidence {required}.'],
            evidence=evidence,
            confidence=0.9 if supported else 0.2,
            recommendations=[verdict, recommendation],
            requires_human=not supported,
            handoff_reason=None if supported else recommendation,
        )

    def _technician(self, ctx: IncidentContext) -> SpecialistFinding:
        evidence = list(ctx.evidence)
        facts = self._facts(evidence)
        request = (
            f"Ticket {ctx.ticket_id} at {ctx.site_id}, asset {ctx.asset_id}: "
            "inspect physical power/PoE and cabling, record findings, and re-run "
            "health/ping (plus RTSP for a camera) after work."
        )
        return SpecialistFinding(
            agent='technician',
            status='complete' if evidence else 'partial',
            facts=facts or ['No observed evidence is available; the symptom remains unverified.'],
            hypotheses=[ctx.diagnosis or 'Cause is not established by the available observations.'],
            tests_performed=['Prepared a human-only handoff from the current incident evidence.'],
            evidence=evidence,
            confidence=ctx.confidence,
            recommendations=[request],
            requires_human=True,
            handoff_reason='Physical inspection and repair remain technician-controlled.',
        )
