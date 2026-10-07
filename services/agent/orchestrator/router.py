"""Evidence-based specialist routing (ORCHESTRATOR.md 'Routing rules').

Route on observed evidence, not keywords. Phase 3 swaps the planned
route for real specialist invocations; the plan shape is already stable.
"""
from __future__ import annotations

from typing import Any, Dict, List, Set


def derive_signals(observations: Dict[str, Any]) -> Set[str]:
    signals: Set[str] = set()
    health = observations.get('health') or {}
    ping = observations.get('ping') or {}
    tcp = observations.get('tcp') or {}
    rtsp = observations.get('rtsp') or {}

    if ping.get('ok') is False or health.get('reachable') is False:
        signals.add('ping_failure')
    if health.get('poe') is False:
        signals.add('poe_off')
    if tcp.get('open') is False and ping.get('ok') is True:
        signals.add('tcp_closed')
    if rtsp.get('auth') == 'invalid' or health.get('rtsp') == 'auth_failed':
        signals.add('rtsp_auth_failed')
    if rtsp.get('stream') == 'unavailable' or health.get('rtsp') == 'unavailable':
        signals.add('rtsp_fail')
    if health.get('service') == 'down':
        signals.add('ai_service_down')
    if (health.get('cpu') or 0) >= 90:
        signals.add('high_cpu')
    if (health.get('storage') or 0) >= 95:
        signals.add('storage_high')
    if health.get('cloud') == 'unavailable':
        signals.add('cloud_down')
    if observations.get('multi_camera_down'):
        signals.add('multi_camera_down')
    if not signals:
        signals.add('no_fault_visible')
    return signals


# (signal, specialists, focused question) — priority order matters.
ROUTING_TABLE = [
    ('poe_off', ['network', 'technician'],
     'Confirm a physical/power fault from telemetry and prepare a technician handoff.'),
    ('ping_failure', ['network', 'camera_nvr'],
     'Determine whether the failure is addressing/routing or recorder-side.'),
    ('tcp_closed', ['rtsp'],
     'Determine why TCP/554 is closed while the host still responds.'),
    ('rtsp_auth_failed', ['rtsp', 'knowledge'],
     'Confirm the RTSP authentication failure and find the approved credential procedure.'),
    ('rtsp_fail', ['rtsp'],
     'Determine whether the stream failure is transient, source-side or path-related.'),
    ('multi_camera_down', ['network', 'camera_nvr'],
     'Determine whether the shared NVR or the shared network is the common cause.'),
    ('ai_service_down', ['aibox', 'network'],
     'Determine whether the AI Box service or its upstream is at fault.'),
    ('high_cpu', ['aibox'],
     'Assess resource pressure and whether it threatens service health.'),
    ('storage_high', ['aibox', 'camera_nvr'],
     'Assess recording/retention risk from storage pressure.'),
    ('cloud_down', ['aibox', 'knowledge'],
     'Determine whether the sync failure is upstream connectivity or service-side.'),
    ('no_fault_visible', ['helpdesk', 'knowledge'],
     'Re-check the reported symptom against history and documentation.'),
]


def route(signals: Set[str]) -> List[Dict[str, str]]:
    planned: List[Dict[str, str]] = []
    seen: Set[str] = set()
    for signal, agents, question in ROUTING_TABLE:
        if signal in signals:
            for agent in agents:
                if agent not in seen:
                    seen.add(agent)
                    planned.append({'agent': agent, 'question': question})
    return planned
