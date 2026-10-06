from dataclasses import dataclass, field
from typing import Any, Dict, List
import httpx

from .knowledge import KnowledgeBase

@dataclass
class AgentResult:
    ticket_id: int
    diagnosis: str
    confidence: str
    evidence: Dict[str, Any]
    recommended_action: str
    auto_action: str | None = None
    technician_required: bool = False
    next_status: str = 'in_progress'
    notes: List[str] = field(default_factory=list)

class Agent:
    AUTO_ACTIONS = {'reconnect-rtsp', 'restart-ai-service'}

    def __init__(self, helpdesk_url: str, portal_url: str, docs_root: str = '/app/docs'):
        self.helpdesk = helpdesk_url.rstrip('/')
        self.portal = portal_url.rstrip('/')
        self.client = httpx.Client(timeout=10)
        self.kb = KnowledgeBase(docs_root)

    def close(self):
        self.client.close()

    def ticket(self, ticket_id: int):
        return self.client.get(f'{self.helpdesk}/api/tickets/{ticket_id}').raise_for_status().json()

    def open_tickets(self):
        statuses = ['open', 'ready_for_verification', 'pending_technician']
        out = []
        for status in statuses:
            out.extend(self.client.get(f'{self.helpdesk}/api/tickets', params={'status': status, 'limit': 50}).raise_for_status().json()['tickets'])
        return sorted(out, key=lambda t: t['id'])

    def search_history(self, asset_id: str, q: str):
        return self.client.get(f'{self.helpdesk}/api/search', params={'q': q, 'asset_id': asset_id}).raise_for_status().json()['results']

    def health(self, asset_id: str):
        return self.client.get(f'{self.portal}/api/assets/{asset_id}/health').raise_for_status().json()

    def ping(self, asset_id: str):
        return self.client.get(f'{self.portal}/api/assets/{asset_id}/ping').raise_for_status().json()

    def tcp_test(self, asset_id: str, port: int = 554):
        return self.client.get(f'{self.portal}/api/assets/{asset_id}/tcp-test', params={'port': port}).raise_for_status().json()

    def rtsp_test(self, asset_id: str):
        return self.client.get(f'{self.portal}/api/assets/{asset_id}/rtsp-test').raise_for_status().json()

    def site_assets(self, site_id: str):
        return self.client.get(f'{self.portal}/api/site/{site_id}/assets').raise_for_status().json()['assets']

    def allowed_auto_action(self, action: str) -> bool:
        return action in self.AUTO_ACTIONS

    def _auto_action(self, asset: str, action: str):
        endpoint = {
            'reconnect-rtsp': f'/api/assets/{asset}/actions/reconnect-rtsp',
            'restart-ai-service': f'/api/assets/{asset}/actions/restart-ai-service',
        }[action]
        return self.client.post(f'{self.portal}{endpoint}', json={'actor': 'autonomous-agent'}).raise_for_status().json()

    def _update_ticket(self, ticket_id: int, **fields):
        return self.client.patch(f'{self.helpdesk}/api/tickets/{ticket_id}', json=fields).raise_for_status().json()

    def _note(self, ticket_id: int, body: str):
        self.client.post(f'{self.helpdesk}/api/tickets/{ticket_id}/notes', json={'author': 'ai-agent', 'body': body}).raise_for_status()

    def investigate(self, ticket_id: int) -> AgentResult:
        t = self.ticket(ticket_id)
        asset = t['asset_id']; site = t['site_id']
        h = self.health(asset)
        evidence: Dict[str, Any] = {'ticket': t, 'health': h}
        try:
            evidence['ping'] = self.ping(asset)
        except Exception as exc:
            evidence['ping_error'] = str(exc)

        if h.get('type') in {'camera', 'nvr'}:
            try:
                evidence['tcp_554'] = self.tcp_test(asset, 554)
                evidence['rtsp'] = self.rtsp_test(asset)
            except Exception as exc:
                evidence['rtsp_error'] = str(exc)

        try:
            siblings = self.site_assets(site)
            evidence['site_context'] = {
                'healthy_other_assets': [a['asset_id'] for a in siblings if a['asset_id'] != asset and a.get('reachable', False)],
                'unhealthy_other_assets': [a['asset_id'] for a in siblings if a['asset_id'] != asset and not a.get('reachable', True)],
            }
        except Exception as exc:
            evidence['site_context_error'] = str(exc)

        history = self.search_history(asset, t['title'])
        evidence['history'] = history
        evidence['knowledge'] = self.kb.search(f'{t["title"]} {t["description"]} {h.get("fault", "")}')

        if h.get('reachable') is False:
            if h.get('poe') is False:
                return AgentResult(ticket_id, 'Likely PoE/power or physical connectivity issue', 'high', evidence, 'Inspect PoE port, Ethernet cable, and camera power.', technician_required=True, next_status='pending_technician')
            return AgentResult(ticket_id, 'Likely network or physical connectivity issue', 'medium', evidence, 'Check switch/PoE link, cable, and camera power.', technician_required=True, next_status='pending_technician')

        if h.get('rtsp') == 'auth_failed':
            return AgentResult(ticket_id, 'Likely RTSP authentication/configuration mismatch', 'high', evidence, 'Verify RTSP credentials and stream configuration.', technician_required=True, next_status='pending_technician')

        if h.get('rtsp') == 'unavailable':
            if self.allowed_auto_action('reconnect-rtsp'):
                resp = self._auto_action(asset, 'reconnect-rtsp')
                evidence['auto_action_result'] = resp
                if resp.get('ok') and self.health(asset).get('rtsp') == 'healthy':
                    return AgentResult(ticket_id, 'Transient RTSP interruption recovered automatically', 'high', evidence, 'No technician action unless the issue recurs.', 'reconnect-rtsp', technician_required=False, next_status='resolved')
            return AgentResult(ticket_id, 'RTSP stream unavailable', 'medium', evidence, 'Reconnect/restart the RTSP source and verify the stream.', technician_required=True, next_status='pending_technician')

        if h.get('type') == 'ai_box' and h.get('service') == 'down':
            resp = self._auto_action(asset, 'restart-ai-service') if self.allowed_auto_action('restart-ai-service') else {'ok': False}
            evidence['auto_action_result'] = resp
            if resp.get('ok') and self.health(asset).get('service') == 'healthy':
                return AgentResult(ticket_id, 'AI service recovered after safe restart', 'high', evidence, 'No technician action unless the issue recurs.', 'restart-ai-service', technician_required=False, next_status='resolved')
            return AgentResult(ticket_id, 'AI inference service is unavailable', 'high', evidence, 'Inspect the AI Box service and host health.', technician_required=True, next_status='pending_technician')

        if h.get('cpu', 0) >= 90:
            return AgentResult(ticket_id, 'High resource utilization', 'high', evidence, 'Inspect resource usage and active processes before restarting services.', technician_required=True, next_status='pending_technician')

        if h.get('storage', 0) >= 95:
            return AgentResult(ticket_id, 'Storage capacity is critically high', 'high', evidence, 'Free or rotate storage according to the site SOP, then verify services.', technician_required=True, next_status='pending_technician')

        if h.get('cloud') == 'unavailable':
            return AgentResult(ticket_id, 'Cloud synchronization is unavailable', 'medium', evidence, 'Check upstream connectivity and cloud service status before changing local configuration.', technician_required=True, next_status='pending_technician')

        return AgentResult(ticket_id, 'No critical fault reproduced by current checks', 'low', evidence, 'Review logs and continue guided troubleshooting with the technician.', technician_required=True, next_status='pending_technician')

    def process(self, ticket_id: int) -> AgentResult:
        t = self.ticket(ticket_id)
        self._update_ticket(ticket_id, status='in_progress', ai_state='investigating')
        result = self.investigate(ticket_id)
        summary = f'Diagnosis: {result.diagnosis}\nConfidence: {result.confidence}\nRecommended action: {result.recommended_action}\nAutomatic action: {result.auto_action or "none"}'
        self._note(ticket_id, summary)
        self._update_ticket(ticket_id, status=result.next_status, ai_state='resolved' if result.next_status == 'resolved' else 'awaiting_technician', ai_summary=summary, root_cause=result.diagnosis if result.confidence == 'high' else None, resolution=result.recommended_action if result.next_status == 'resolved' else None)
        return result
