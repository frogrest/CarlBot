"""Tool bus: the only path from orchestrator/specialists to the outside world.

Read-only probes (health/ping/tcp/rtsp/site/search) may run in any order;
mutating actions go through execute_action(), which only knows the two
registered safe simulated actions and raises on anything else — a second
barrier behind the policy engine.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from ..knowledge import KnowledgeBase


class ToolBus:
    SAFE_ACTIONS = {'reconnect-rtsp', 'restart-ai-service'}

    def __init__(self, helpdesk_url: str, portal_url: str,
                 client: Optional[httpx.Client] = None,
                 docs_root: str = '/app/docs'):
        self.helpdesk = helpdesk_url.rstrip('/')
        self.portal = portal_url.rstrip('/')
        self.client = client or httpx.Client(timeout=10)
        self.owns_client = client is None
        self.kb = KnowledgeBase(docs_root)

    def close(self) -> None:
        if self.owns_client:
            self.client.close()

    # -- read-only probes -------------------------------------------------
    def health(self, asset_id: str) -> Dict[str, Any]:
        return self.client.get(
            f'{self.portal}/api/assets/{asset_id}/health').raise_for_status().json()

    def ping(self, asset_id: str) -> Dict[str, Any]:
        return self.client.get(
            f'{self.portal}/api/assets/{asset_id}/ping').raise_for_status().json()

    def tcp_test(self, asset_id: str, port: int = 554) -> Dict[str, Any]:
        return self.client.get(
            f'{self.portal}/api/assets/{asset_id}/tcp-test',
            params={'port': port}).raise_for_status().json()

    def rtsp_test(self, asset_id: str) -> Dict[str, Any]:
        return self.client.get(
            f'{self.portal}/api/assets/{asset_id}/rtsp-test').raise_for_status().json()

    def site_assets(self, site_id: str) -> List[Dict[str, Any]]:
        return self.client.get(
            f'{self.portal}/api/site/{site_id}/assets').raise_for_status().json()['assets']

    def search_history(self, asset_id: str, query: str) -> List[Dict[str, Any]]:
        return self.client.get(
            f'{self.helpdesk}/api/search',
            params={'q': query, 'asset_id': asset_id}).raise_for_status().json()['results']

    def history_search(self, query: str, asset_id: str = '') -> List[Dict[str, Any]]:
        """Engine-facing alias (query-first) over search_history."""
        return self.search_history(asset_id, query)

    def search_docs(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        return self.kb.search(query, limit=limit)

    def doc_search(self, query: str) -> List[Dict[str, Any]]:
        """Engine-facing alias over search_docs."""
        return self.search_docs(query, limit=3)

    # -- mutating actions (policy must allow first) ------------------------
    def execute_action(self, name: str, asset_id: str) -> Dict[str, Any]:
        if name not in self.SAFE_ACTIONS:
            raise ValueError(f'tool bus refuses unregistered action: {name}')
        endpoint = {
            'reconnect-rtsp': f'/api/assets/{asset_id}/actions/reconnect-rtsp',
            'restart-ai-service': f'/api/assets/{asset_id}/actions/restart-ai-service',
        }[name]
        return self.client.post(
            f'{self.portal}{endpoint}',
            json={'actor': 'autonomous-agent'}).raise_for_status().json()
