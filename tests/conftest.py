"""Shared fixtures for deterministic in-process tests.

No network, no Docker, no real devices: the FastAPI apps run through
starlette's TestClient, and the agent's httpx client is re-pointed at a
MockTransport that routes its calls to those in-process apps.
"""
import copy

import httpx
import pytest

from services.helpdesk import app as helpdesk_module
from services.portal import app as portal_module

# Pristine snapshot of portal state, taken before any test mutates it.
PORTAL_ASSETS_INITIAL = copy.deepcopy(portal_module.ASSETS)


@pytest.fixture()
def helpdesk(monkeypatch, tmp_path):
    """Fresh seeded helpdesk DB per test (25 synthetic tickets + notes)."""
    monkeypatch.setenv('HELPDESK_DB', str(tmp_path / 'helpdesk.db'))
    from fastapi.testclient import TestClient
    with TestClient(helpdesk_module.app) as client:
        yield client


@pytest.fixture()
def portal(monkeypatch):
    """Portal with pristine asset state per test."""
    monkeypatch.setattr(portal_module, 'ASSETS', copy.deepcopy(PORTAL_ASSETS_INITIAL))
    from fastapi.testclient import TestClient
    with TestClient(portal_module.app) as client:
        yield client


@pytest.fixture()
def agent_main(helpdesk, portal, monkeypatch, tmp_path):
    """`services.agent.main` wired to the in-process helpdesk/portal apps.

    The background worker thread is NOT started; tests call
    `init_db()` / `monitor_once()` directly for deterministic behavior.
    """
    import services.agent.main as agent_main_module

    monkeypatch.setattr(agent_main_module, 'AGENT_DB', tmp_path / 'agent.db')
    monkeypatch.setattr(agent_main_module, 'HELPDESK_URL', 'http://helpdesk')
    monkeypatch.setattr(agent_main_module, 'PORTAL_URL', 'http://portal')
    monkeypatch.setattr(agent_main_module.agent, 'helpdesk', 'http://helpdesk')
    monkeypatch.setattr(agent_main_module.agent, 'portal', 'http://portal')

    _DROP_HEADERS = {'host', 'content-length', 'transfer-encoding', 'connection'}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.url.query:
            path += '?' + request.url.query.decode('ascii')
        host = request.url.host
        if host == 'helpdesk':
            target = helpdesk
        elif host == 'portal':
            target = portal
        else:
            return httpx.Response(502, json={'detail': f'unrouted host: {host}'})
        # Forward the full body and headers; without this, POSTs lose their
        # payload and FastAPI answers 422 (missing required fields).
        body = request.read()
        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in _DROP_HEADERS
        }
        return target.request(
            request.method, path,
            content=body or None,
            headers=headers,
        )

    try:
        agent_main_module.agent.client.close()
    except Exception:
        pass
    monkeypatch.setattr(
        agent_main_module.agent,
        'client',
        httpx.Client(transport=httpx.MockTransport(handler), timeout=10),
    )
    agent_main_module.init_db()
    yield agent_main_module
