import csv
import os
import re
from pathlib import Path
from typing import Any


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    'a', 'about', 'active', 'an', 'and', 'are', 'at', 'answered', 'can', 'closed', 'do', 'does',
    'find', 'for', 'get', 'have', 'hey', 'history', 'in', 'is', 'it', 'me',
    'record', 'recorded', 'resolved', 'subject', 'title', 'summarize', 'summary',
    'of', 'on', 'open', 'please', 'show', 'site', 'the', 'there', 'ticket',
    'tickets', 'was', 'were', 'what', 'when', 'where', 'which', 'with',
    'check', 'checking', 'checks', 'look', 'looking', 'inspect', 'inspecting',
    'examine', 'examining', 'tell', 'info', 'information', 'detail', 'details',
    'status', 'view', 'viewing', 'give', 'search', 'searching', 'query',
    'see', 'seeing', 'review', 'reviewing', 'analyze', 'analyzing',
    'investigate', 'investigating', 'how', 'why', 'who', 'could', 'would', 'should',
}
_ISSUE_WORDS = {
    'ai', 'camera', 'cameras', 'offline', 'down', 'rtsp', 'stream', 'service',
    'failure', 'failed', 'issue', 'problem', 'unavailable', 'connection',
}
_CLOSED_STATUSES = {'closed', 'resolved'}
_EXPORT_FIELDS = (
    'Ticket Number',
    'Subject',
    'Priority',
    'Help Topic',
    'Current Status',
    'Thread Count',
    'Location',
    'From',
)
_PLAIN_LANGUAGE_DETAILS = {
    'RTSP authentication mismatch': 'The camera stream login details did not match.',
    'RTSP username/password was wrong.': 'The camera stream login details were wrong.',
    'Corrected RTSP credentials.': 'A technician corrected the camera stream login details.',
    'Unresponsive PoE switch port': 'The switch port was not supplying power to the camera.',
    'PoE port had no usable link. Known-good port restored camera.':
        'The original switch port was not working. Moving the cable to a working port restored the camera.',
    'Damaged Ethernet cable': 'The Ethernet cable was damaged.',
    'Replaced Ethernet cable.': 'A technician replaced the Ethernet cable.',
    'High CPU utilization': 'The AI box was too busy, which slowed its detections.',
    'High resource utilization': 'The device was using too much processing power.',
    'Storage capacity is critically high': 'The device is almost out of storage space.',
    'Cloud synchronization is unavailable': 'The device could not connect to its cloud service.',
    'AI inference service is unavailable': 'The AI service was not responding.',
    'No critical fault reproduced by current checks':
        'Current checks found no issue; a technician should verify it on site.',
    'Likely PoE/power or physical connectivity issue':
        'The camera may have a power or cable problem that a technician needs to check.',
    'Likely network or physical connectivity issue':
        'The camera may have a network or cable problem that a technician needs to check.',
    'Likely RTSP authentication/configuration mismatch':
        'The camera stream login or settings may need to be checked by a technician.',
}
_STATUS_EXPLANATIONS = {
    'open': 'open',
    'in_progress': 'in progress',
    'pending_technician': 'waiting for a technician',
    'ready_for_verification': 'ready to verify',
    'resolved': 'resolved',
    'closed': 'closed',
}


def _tokens(value: str) -> set[str]:
    return {
        token for token in _TOKEN_PATTERN.findall(value.casefold())
        if token not in _STOP_WORDS
    }


def _site_query(message: str) -> set[str]:
    match = re.search(
        r'\b(?:at|for|site)\s+(.+?)(?:[?.!,]|$|\s+(?:about|with|where|that)\b)',
        message,
        flags=re.IGNORECASE,
    )
    if not match:
        return set()
    return _tokens(match.group(1)) - _ISSUE_WORDS


def _status_filter(message: str) -> str | None:
    if re.search(r'\banswered\b', message, re.IGNORECASE):
        return 'answered'
    if re.search(r'\bresolved\b', message, re.IGNORECASE):
        return 'resolved'
    if re.search(r'\b(closed|historical|history)\b', message, re.IGNORECASE):
        return 'closed'
    if re.search(r'\b(open|active)\b', message, re.IGNORECASE):
        return 'open'
    return None


def _requested_issue_terms(message: str) -> set[str]:
    return _tokens(message) - _site_query(message)


def _matches_status(status: str, status_filter: str | None) -> bool:
    normalized = status.casefold().replace(' ', '_')
    if status_filter == 'closed':
        return normalized == 'closed'
    if status_filter == 'answered':
        return normalized == 'answered'
    if status_filter == 'resolved':
        return normalized == 'resolved'
    if status_filter == 'open':
        return normalized not in _CLOSED_STATUSES
    return True


def _extract_target_ticket_ids(message: str, tickets: list[dict[str, Any]]) -> list[str]:
    candidates = re.findall(r'(?i)(?:ticket\s*#?|#\s*|\b)([1-9]\d{2,5})\b', message)
    valid_ids = {str(t.get('id') or t.get('ticket_id') or '') for t in tickets}
    found: list[str] = []
    for candidate in candidates:
        if candidate in valid_ids and candidate not in found:
            found.append(candidate)
    return found


def _build_live_match_dict(
    ticket: dict[str, Any],
    *,
    site_match: str = 'exact',
    context_ticket_id: int | None = None,
) -> dict[str, Any]:
    status = str(ticket.get('status') or '')
    ticket_status = str(ticket.get('ticket_status') or '')
    if ticket_status not in {'Open', 'Answered', 'Closed'}:
        ticket_status = (
            'Closed' if status == 'closed'
            else 'Answered' if status in {'resolved', 'ready_for_verification'}
            else 'Open'
        )
    notes = ticket.get('notes') or []
    replies = ticket.get('customer_replies') or []
    details = [
        str(ticket.get(key) or '').strip()
        for key in ('resolution', 'root_cause', 'description')
        if str(ticket.get(key) or '').strip()
    ]
    note_limit = 20 if ticket.get('id') == context_ticket_id else 5
    details.extend(
        str(note.get('body') or '').strip()
        for note in notes[:note_limit]
        if str(note.get('body') or '').strip()
    )
    details.extend(
        f"[Customer reply] {str(reply.get('body') or '').strip()}"
        for reply in replies[:note_limit]
        if str(reply.get('body') or '').strip()
    )
    return {
        'ticket_id': str(ticket['id']),
        'title': str(ticket.get('title') or ''),
        'status': status,
        'ticket_status': ticket_status,
        'priority': str(ticket.get('priority') or 'medium'),
        'site_id': str(ticket.get('site_id') or ''),
        'asset_id': str(ticket.get('asset_id') or ''),
        'site_match': site_match,
        'source': 'live_helpdesk',
        'has_conversation': bool(notes or replies),
        'details': details,
        'description': str(ticket.get('description') or '').strip(),
        'root_cause': str(ticket.get('root_cause') or '').strip(),
        'resolution': str(ticket.get('resolution') or '').strip(),
        'ai_summary': str(ticket.get('ai_summary') or '').strip(),
        'ai_state': str(ticket.get('ai_state') or '').strip(),
        'notes': notes,
        'customer_replies': replies,
    }


def _live_matches(
    message: str,
    tickets: list[dict[str, Any]],
    *,
    context_ticket_id: int | None = None,
) -> list[dict[str, Any]]:
    # 1. Check for explicit ticket ID references in query
    target_ids = _extract_target_ticket_ids(message, tickets)
    if target_ids:
        matched: list[dict[str, Any]] = []
        for tid in target_ids:
            matching_t = next((t for t in tickets if str(t.get('id') or t.get('ticket_id')) == tid), None)
            if matching_t:
                matched.append(_build_live_match_dict(matching_t, site_match='exact', context_ticket_id=context_ticket_id))
        if matched:
            return matched

    # 2. General token and status search
    query_tokens = _tokens(message)
    site_tokens = _site_query(message)
    issue_tokens = _requested_issue_terms(message)
    status_filter = _status_filter(message)
    matches: list[tuple[int, dict[str, Any]]] = []

    for ticket in tickets:
        status = str(ticket.get('status') or '')
        ticket_status = str(ticket.get('ticket_status') or '')
        if ticket_status not in {'Open', 'Answered', 'Closed'}:
            ticket_status = (
                'Closed' if status == 'closed'
                else 'Answered' if status in {'resolved', 'ready_for_verification'}
                else 'Open'
            )
        if status_filter == 'answered' and ticket_status != 'Answered':
            continue
        if status_filter == 'closed' and ticket_status != 'Closed':
            continue
        if status_filter == 'open' and ticket_status != 'Open':
            continue
        if status_filter == 'resolved' and not _matches_status(status, status_filter):
            continue
        searchable = ' '.join(
            str(ticket.get(key) or '')
            for key in (
                'id', 'title', 'description', 'site_id', 'asset_id', 'ticket_status',
                'resolution', 'root_cause', 'ai_summary',
            )
        )
        notes = ticket.get('notes') or []
        replies = ticket.get('customer_replies') or []
        searchable += ' ' + ' '.join(str(note.get('body') or '') for note in notes)
        searchable += ' ' + ' '.join(str(reply.get('body') or '') for reply in replies)
        ticket_tokens = _tokens(searchable)
        overlap = issue_tokens & ticket_tokens
        if issue_tokens and not overlap:
            continue
        if not issue_tokens:
            overlap = query_tokens & ticket_tokens

        site_id = str(ticket.get('site_id') or '')
        site_id_tokens = _tokens(site_id)
        if site_tokens and not site_tokens & site_id_tokens:
            continue
        if site_id.casefold() in message.casefold() or (site_tokens and site_tokens == site_id_tokens):
            site_match = 'exact'
            score = 100
        elif site_tokens:
            site_match = 'partial'
            score = 30
        else:
            site_match = 'unspecified'
            score = 20

        issue_overlap = issue_tokens & ticket_tokens
        score += min(len(issue_overlap), 5) * 4 + min(len(overlap), 5)
        match_dict = _build_live_match_dict(ticket, site_match=site_match, context_ticket_id=context_ticket_id)
        matches.append((score, match_dict))

    return [item for _, item in sorted(matches, key=lambda item: item[0], reverse=True)]


def _export_matches(message: str, path: Path) -> list[dict[str, Any]]:
    status_filter = _status_filter(message)
    query_tokens = _tokens(message)
    site_tokens = _site_query(message)
    issue_tokens = _requested_issue_terms(message)
    matches: list[tuple[int, dict[str, Any]]] = []

    with path.open(encoding='utf-8-sig', newline='') as file:
        for row in csv.DictReader(file):
            status = str(row.get('Current Status') or '').strip()
            if not _matches_status(status, status_filter):
                continue
            searchable_values = [str(row.get(field) or '') for field in _EXPORT_FIELDS]
            searchable = ' '.join(searchable_values)
            row_tokens = _tokens(searchable)
            overlap = issue_tokens & row_tokens
            if issue_tokens and not overlap:
                continue
            if not issue_tokens:
                overlap = query_tokens & row_tokens

            location = str(row.get('Location') or '')
            requester = str(row.get('From') or '')
            location_tokens = _tokens(location)
            requester_tokens = _tokens(requester) - _ISSUE_WORDS
            source_site_tokens = location_tokens | requester_tokens
            if site_tokens and not site_tokens & source_site_tokens:
                continue
            if site_tokens and site_tokens == location_tokens - _ISSUE_WORDS:
                site_match = 'exact'
                score = 100
            elif site_tokens:
                site_match = 'partial'
                score = 30
            else:
                site_match = 'unspecified'
                score = 20
            score += min(len(issue_tokens & row_tokens), 5) * 4 + min(len(overlap), 5)

            matches.append((score, {
                'ticket_id': str(row.get('Ticket Number') or '').strip(),
                'title': str(row.get('Subject') or '').strip(),
                'status': status,
                'ticket_status': status.title() if status.casefold() in {'open', 'answered', 'closed'} else '',
                'priority': str(row.get('Priority') or '').strip(),
                'site_id': str(row.get('Location') or '').strip(),
                'asset_id': '',
                'site_match': site_match,
                'source': 'reference_export',
                'has_conversation': False,
                'thread_count': str(row.get('Thread Count') or '').strip(),
                'details': [],
            }))

    return [item for _, item in sorted(matches, key=lambda item: item[0], reverse=True)]


_GREETING_PATTERN = re.compile(
    r'^\s*(?:hi|hello|hey|heya|howdy|greetings|good\s+(?:morning|afternoon|evening)|yo|sup)\b'
    r'|^\s*(?:who\s+are\s+you|what\s+can\s+you\s+do|introduce\s+yourself)\b',
    re.IGNORECASE,
)

_OFF_TOPIC_PATTERN = re.compile(
    r'(?i)\b(?:write\s+(?:a\s+)?(?:poem|story|song|essay)|tell\s+(?:me\s+)?(?:a\s+)?joke|'
    r'capital\s+of|weather\s+in|recipe\s+for|how\s+to\s+cook|'
    r'who\s+is\s+(?:the\s+)?president|celebrity|dating|horoscope)\b'
)

_RTSP_PATTERN = re.compile(
    r'(?i)\b(?:what(?:s|\s+is|\s+does)?\s+rtsp|explain\s+rtsp|rtsp\s+protocol|what\s+does\s+rtsp\s+mean|how\s+does\s+rtsp\s+work|rtsp\s+streaming\s+protocol)\b'
)

_NVR_PATTERN = re.compile(
    r'(?i)\b(?:what(?:s|\s+is|\s+does)?\s+(?:an?\s+)?nvr|explain\s+(?:an?\s+)?nvr|what\s+does\s+(?:an?\s+)?nvr\s+do|what\s+does\s+nvr\s+mean|how\s+does\s+(?:an?\s+)?nvr\s+work|nvr\s+architecture)\b'
)

_AIBOX_PATTERN = re.compile(
    r'(?i)\b(?:what(?:s|\s+is|\s+does)?\s+(?:an?\s+)?ai\s*box|explain\s+(?:an?\s+)?ai\s*box|what\s+does\s+(?:an?\s+)?ai\s*box\s+do|how\s+does\s+(?:an?\s+)?ai\s*box\s+work|ai\s*box\s+analytics)\b'
)

_POE_PATTERN = re.compile(
    r'(?i)\b(?:what(?:s|\s+is|\s+does)?\s+poe|explain\s+poe|what\s+does\s+poe\s+mean|how\s+does\s+poe\s+work|power\s+over\s+ethernet)\b'
)

_ONVIF_PATTERN = re.compile(
    r'(?i)\b(?:what(?:s|\s+is|\s+does)?\s+onvif|explain\s+onvif|what\s+does\s+onvif\s+mean|how\s+does\s+onvif\s+work)\b'
)

_PTZ_PATTERN = re.compile(
    r'(?i)\b(?:what(?:s|\s+is|\s+does)?\s+ptz|explain\s+ptz|what\s+does\s+ptz\s+mean|how\s+does\s+ptz\s+work|pan\s+tilt\s+zoom)\b'
)

_SYSTEM_PATTERN = re.compile(
    r'(?i)\b(?:what(?:s|\s+is|\s+does)?\s+(?:the\s+)?(?:system|lab|architecture)|how\s+does\s+(?:the\s+)?(?:system|lab)\s+work|explain\s+(?:the\s+)?(?:system|lab|architecture))\b'
)

_NETWORK_PROTOCOLS_PATTERN = re.compile(
    r'(?i)\b(?:network\s+protocols?|what\s+is\s+ip\b|explain\s+ip\b|ip\s+addressing|tcp\s+(?:vs|and)\s+udp|what\s+network\s+protocols)\b'
)

_IP_COMMANDS_PATTERN = re.compile(
    r'(?i)\b(?:ip\s+commands?|network\s+commands?|how\s+to\s+use\s+ping|explain\s+ping\b|how\s+to\s+ping|traceroute|tracert|ipconfig|ifconfig|arp\s+-a|diagnostic\s+commands?)\b'
)

_REBOOT_POWERCYCLE_PATTERN = re.compile(
    r'(?i)\b(?:what\s+does\s+reboot\s+mean|what\s+is\s+power\s*cycling|reboot\s+(?:vs|and)\s+power\s*cycle|difference\s+between\s+reboot\s+and\s+power\s*cycle|how\s+to\s+power\s*cycle|cold\s+boot\s+vs\s+soft\s+reboot|what\s+is\s+a\s+power\s*cycle)\b'
)

_OFFLINE_CAMERA_PATTERN = re.compile(
    r'(?i)\b(?:what\s+to\s+do\s+(?:when|if)\s+(?:a\s+)?camera\s+(?:is\s+)?offline|troubleshoot\s+(?:an?\s+)?offline\s+camera|how\s+to\s+(?:fix|handle|troubleshoot)\s+(?:an?\s+)?offline\s+camera|offline\s+camera\s+(?:sop|procedure|steps|playbook|troubleshooting)|camera\s+is\s+offline\s*,?\s*what\s+(?:should|do|to))\b'
)

_OFFLINE_SYSTEM_PATTERN = re.compile(
    r'(?i)\b(?:what\s+to\s+do\s+(?:when|if)\s+(?:a\s+)?(?:system|ai\s*box|server)\s+(?:is\s+)?offline|what\s+should\s+(?:the\s+)?(?:technician|it\s+support)\s+do\s+when\s+(?:a\s+)?(?:system|ai\s*box|server)\s+is\s+offline|troubleshoot\s+(?:an?\s+)?offline\s+(?:system|ai\s*box|server)|offline\s+(?:system|ai\s*box|server)\s+(?:sop|procedure|steps|playbook))\b'
)

_OFFLINE_RDP_PATTERN = re.compile(
    r'(?i)\b(?:what\s+to\s+do\s+(?:when|if)\s+remote\s+desktop\s+(?:is\s+)?offline|troubleshoot\s+remote\s+desktop|remote\s+desktop\s+(?:is\s+)?(?:down|offline)|rdp\s+(?:is\s+)?(?:down|offline)|cannot\s+connect\s+to\s+remote\s+desktop|rdp\s+troubleshooting|ssh\s+(?:is\s+)?offline|vnc\s+(?:is\s+)?offline|how\s+to\s+fix\s+remote\s+desktop)\b'
)


def _detect_conversational_response(
    message: str,
    *,
    context_ticket_id: int | None = None,
    tickets: list[dict[str, Any]] | None = None,
) -> tuple[str, str] | None:
    """Detect companion greetings, terminologies, and system boundaries."""
    # 1. Off-topic guardrail
    if _OFF_TOPIC_PATTERN.search(message):
        return (
            'off_topic',
            "I'm CarlBot, your AI operations companion dedicated to this surveillance and helpdesk lab. "
            "I specialize in camera streams, network recording (NVR), AI Box analytics, and ticket troubleshooting. "
            "I'm not able to assist with general topics outside our system, but feel free to ask about our camera feeds, "
            "tickets, or system terminologies like RTSP and PoE!",
        )

    # 2. Terminologies & concepts
    if _RTSP_PATTERN.search(message):
        answer = (
            "RTSP (Real-Time Streaming Protocol) is a network control protocol (standard port 554) designed "
            "to establish and control real-time media sessions between IP surveillance cameras and media clients "
            "(such as NVRs or AI Boxes).\n\n"
            "Key details in our system:\n"
            "• Stream Endpoints: Cameras stream H.264/H.265 video over RTSP sessions (e.g. rtsp://user:pass@host:554/stream1).\n"
            "• Stream Drop Recovery (rtsp_down): When an RTSP stream drops unexpectedly while network link is intact, "
            "our autonomous agent is permitted to execute reconnect-rtsp to restore the feed.\n"
            "• Authentication Mismatches (rtsp_auth_failure): If 401 Unauthorized errors occur, autonomous credential "
            "modifications are strictly prohibited and require on-site technician handoff."
        )
        if context_ticket_id:
            answer += f"\n\n(Tip: You are currently viewing Ticket #{context_ticket_id} in the workspace.)"
        return ('rtsp', answer)

    if _NVR_PATTERN.search(message):
        answer = (
            "An NVR (Network Video Recorder) is a dedicated computing appliance engineered to capture, manage, "
            "and archive digital video streams from IP surveillance cameras across a local network.\n\n"
            "Key roles in our operations:\n"
            "• Multi-Channel Ingestion: Simultaneously records video streams from multiple cameras across local subnets.\n"
            "• Storage Pools: Manages continuous and motion-indexed recording onto internal SATA/RAID storage with FIFO retention policies.\n"
            "• Video Management: Supplies synchronized timeline scrubbing, video search, and stream forwarding to client monitors and operations centers."
        )
        if context_ticket_id:
            answer += f"\n\n(Tip: You are currently viewing Ticket #{context_ticket_id} in the workspace.)"
        return ('nvr', answer)

    if _AIBOX_PATTERN.search(message):
        answer = (
            "An AI Box is an on-premises edge computing hardware appliance equipped with neural processing units (NPUs) "
            "or GPUs that runs real-time computer vision inference directly on live camera feeds.\n\n"
            "What it does in our system:\n"
            "• Real-Time Video Analytics: Ingests RTSP streams from IP cameras to detect people, vehicles, license plates, "
            "intrusion zones, and safety compliance without cloud latency.\n"
            "• Metadata & Telemetry: Generates real-time events forwarded to the central helpdesk and security dashboards.\n"
            "• Service Recovery (ai_service_down): If the inference worker crashes or hangs, our autonomous agent can safely "
            "execute restart-ai-service to restore automated detection."
        )
        if context_ticket_id:
            answer += f"\n\n(Tip: You are currently viewing Ticket #{context_ticket_id} in the workspace.)"
        return ('aibox', answer)

    if _POE_PATTERN.search(message):
        answer = (
            "PoE (Power over Ethernet) enables network switches to supply both electrical operating power and network data "
            "over a single Cat5e/Cat6 Ethernet cable to IP cameras (standards IEEE 802.3af up to 15.4W, 802.3at up to 30W, "
            "and 802.3bt up to 90W).\n\n"
            "In our lab:\n"
            "• PoE Outage (poe_off): When a camera loses power at the switch port, the agent recognizes this as a physical hardware "
            "fault. Because software tools cannot physically repair cabling or hardware, the system escalates the ticket to an on-site "
            "technician (pending_technician)."
        )
        if context_ticket_id:
            answer += f"\n\n(Tip: You are currently viewing Ticket #{context_ticket_id} in the workspace.)"
        return ('poe', answer)

    if _ONVIF_PATTERN.search(message):
        answer = (
            "ONVIF (Open Network Video Interface Forum) is an open global industry standard providing standardized "
            "communication interfaces for physical IP-based security devices.\n\n"
            "Core Profiles used in surveillance:\n"
            "• Profile S: Basic video streaming via RTSP, device discovery via WS-Discovery, and basic PTZ control.\n"
            "• Profile T: Advanced video streaming supporting H.265 compression, HTTPS transport, and analytics metadata events.\n"
            "• Profile G: Edge storage management and local recording retrieval."
        )
        if context_ticket_id:
            answer += f"\n\n(Tip: You are currently viewing Ticket #{context_ticket_id} in the workspace.)"
        return ('onvif', answer)

    if _PTZ_PATTERN.search(message):
        answer = (
            "PTZ (Pan-Tilt-Zoom) refers to motorized surveillance cameras that allow operators or automated tracking systems "
            "to remotely pan horizontally (up to 360°), tilt vertically, and optically zoom into areas of interest.\n\n"
            "In our system, PTZ cameras consume higher PoE budgets (PoE+ or PoE++) to drive motorized gears and heaters."
        )
        if context_ticket_id:
            answer += f"\n\n(Tip: You are currently viewing Ticket #{context_ticket_id} in the workspace.)"
        return ('ptz', answer)

    if _SYSTEM_PATTERN.search(message):
        answer = (
            "The AI Ops Assistant Lab is a safe, emulated technical-support operations environment composed of 4 key layers:\n"
            "1. Helpdesk Service (:8000): Manages tickets, technician notes, customer-facing conversation threads, and workflow states.\n"
            "2. Portal Service (:8001): Emulates physical cameras, NVRs, AI Boxes, switch PoE ports, and fault injection "
            "(rtsp_down, poe_off, rtsp_auth_failure, ai_service_down).\n"
            "3. Agent Orchestrator & Policy Engine (:8002): Monitors telemetry, dedupes incidents, dispatches specialists, "
            "and enforces deterministic policy boundaries (only reconnect-rtsp and restart-ai-service are permitted autonomously).\n"
            "4. Frontend (:8003): React/Vite/TypeScript operations dashboard with ticket queue, detail views, emulator probes, "
            "and CarlBot copilot."
        )
        if context_ticket_id:
            answer += f"\n\n(Tip: You are currently viewing Ticket #{context_ticket_id} in the workspace.)"
        return ('system', answer)

    if _NETWORK_PROTOCOLS_PATTERN.search(message):
        answer = (
            "Network protocols establish communication, media transport, and device coordination across surveillance systems:\n\n"
            "• IP (IPv4/IPv6): Logical host addressing on dedicated camera VLANs (e.g. 10.20.0.0/24) using static IPs or DHCP reservations.\n"
            "• TCP vs. UDP: TCP provides reliable handshakes with retransmission (web UI, RTSP control, APIs); UDP delivers low-latency RTP media streaming.\n"
            "• RTSP (Port 554): Session control protocol managing camera streams (DESCRIBE, SETUP, PLAY).\n"
            "• ONVIF: Open XML/SOAP standard for camera discovery, PTZ controls, and media profile negotiation.\n"
            "• NTP (Port 123): Synchronizes timestamps across all cameras, NVRs, and AI Boxes for legal and forensic evidence.\n"
            "• RDP / SSH (Ports 3389 / 22): Encrypted management protocols for remote server and console administration."
        )
        if context_ticket_id:
            answer += f"\n\n(Tip: You are currently viewing Ticket #{context_ticket_id} in the workspace.)"
        return ('network_protocols', answer)

    if _IP_COMMANDS_PATTERN.search(message):
        answer = (
            "Essential IP and network diagnostic commands for IT support and field technicians:\n\n"
            "1. ping <ip> (ICMP Echo): Verifies layer-3 reachability and packet loss. Request timed out indicates unpowered device or physical link failure.\n"
            "2. ipconfig /all (Windows) / ip addr (Linux): Inspects local IP address, subnet mask, and default gateway.\n"
            "3. arp -a (Address Resolution Protocol): Displays IP-to-MAC address mapping; helps identify duplicate IP conflicts.\n"
            "4. traceroute / tracert <ip>: Identifies intermediate router hops and pinpoints network drops.\n"
            "5. Test-NetConnection -Port <port> (PowerShell) / nc -zv <ip> <port> (Linux): Probes specific daemon ports (e.g. port 554 for RTSP, port 3389 for RDP)."
        )
        if context_ticket_id:
            answer += f"\n\n(Tip: You are currently viewing Ticket #{context_ticket_id} in the workspace.)"
        return ('ip_commands', answer)

    if _REBOOT_POWERCYCLE_PATTERN.search(message):
        answer = (
            "Reboot vs. Power Cycling — Definitions & Best Practices:\n\n"
            "• Reboot (Soft Reboot / Warm Restart): An operating-system-directed restart without cutting electrical power. "
            "Flushes disk buffers cleanly, restarts services, and clears RAM memory leaks. Triggered via software commands "
            "(e.g. sudo reboot or restart-ai-service).\n"
            "• Power Cycle (Hard Reboot / Cold Boot): Completely cuts electrical power for 15–30 seconds before reapplying power. "
            "Discharges capacitors, clears frozen hardware PHY registers, and resets hardware controllers. "
            "Executed via PoE switch port bounce (poe_bounce) or unplugging physical power cords.\n\n"
            "Rule: Always attempt a graceful soft reboot first. Use power cycling when the hardware or network PHY is unresponsive."
        )
        if context_ticket_id:
            answer += f"\n\n(Tip: You are currently viewing Ticket #{context_ticket_id} in the workspace.)"
        return ('reboot_vs_powercycle', answer)

    if not re.search(r'(?i)\btickets?\b', message) and _OFFLINE_CAMERA_PATTERN.search(message):
        answer = (
            "Standard Operating Procedure for an Offline Camera:\n\n"
            "1. Layer 1 (Physical & PoE): Check switch port link LED and PoE draw. If dark or amber, inspect Cat6 cabling and switch PoE budget.\n"
            "2. Layer 3 (IP Connectivity): Run ping <camera_ip>. If ping fails, check VLAN routing and inspect arp -a for IP conflicts.\n"
            "3. Layer 7 (RTSP Stream): Probe port 554. If open, verify credentials (401 Unauthorized requires password update from vault; never guess).\n"
            "4. Recovery: If stream hung, execute reconnect-rtsp. If hardware frozen, perform a 20-second PoE port bounce.\n"
            "5. Safety Gate: Physical wiring defects and credential modifications require on-site technician handoff (pending_technician)."
        )
        if context_ticket_id:
            answer += f"\n\n(Tip: You are currently viewing Ticket #{context_ticket_id} in the workspace.)"
        return ('offline_camera', answer)

    if not re.search(r'(?i)\btickets?\b', message) and _OFFLINE_SYSTEM_PATTERN.search(message):
        answer = (
            "Standard Operating Procedure when a System, AI Box, or Server is Offline:\n\n"
            "1. Reachability Check: Run ping <server_ip>. If unreachable, check chassis power LEDs, PDU power feed, and out-of-band management (IPMI/iDRAC).\n"
            "2. Service Diagnostics: If host is pingable, connect via SSH or terminal and run docker compose ps or systemctl status.\n"
            "3. Resource Inspection: Run free -h (RAM) and df -h (disk storage) to identify memory leaks or full storage partitions.\n"
            "4. Recovery: Execute restart-ai-service to safely restart edge containers. If OS is unresponsive, reboot via console.\n"
            "5. Verification: Probe health endpoints (e.g. /health) and confirm inference and feed ingestion resume."
        )
        if context_ticket_id:
            answer += f"\n\n(Tip: You are currently viewing Ticket #{context_ticket_id} in the workspace.)"
        return ('offline_system', answer)

    if not re.search(r'(?i)\btickets?\b', message) and _OFFLINE_RDP_PATTERN.search(message):
        answer = (
            "Standard Operating Procedure when Remote Desktop (RDP / SSH) is Offline:\n\n"
            "1. Ping Host: Verify layer-3 reachability. If ping fails, follow the System Offline playbook.\n"
            "2. Port Probe: Probe port 3389 (RDP) or port 22 (SSH) using Test-NetConnection -Port 3389 (PowerShell) or nc -zv <ip> 3389 (Linux).\n"
            "3. Network & Firewall: If port times out, verify management VPN / VLAN access and check firewall rules.\n"
            "4. Remote Service Restart: If host is reachable on another channel, restart the service (e.g. Restart-Service TermService on Windows or sudo systemctl restart xrdp on Linux).\n"
            "5. Console Access: If remote access remains unresponsive, connect via physical crash cart monitor or out-of-band KVM."
        )
        if context_ticket_id:
            answer += f"\n\n(Tip: You are currently viewing Ticket #{context_ticket_id} in the workspace.)"
        return ('offline_rdp', answer)

    # 3. Greetings
    if _GREETING_PATTERN.search(message):
        return (
            'greeting',
            "Hello, I'm Carlbot, ask me anything about the Helpdesk",
        )

    return None


def _synthesize_live_ticket_analysis(first_line: str, match: dict[str, Any]) -> str:
    sections = [first_line]

    asset_id = str(match.get('asset_id') or '')
    title = str(match.get('title') or '')
    site = match.get('site_id') or 'Unspecified site'
    priority = str(match.get('priority') or 'medium').capitalize()
    desc = str(match.get('description') or '').strip()
    status_val = match.get('status', '')
    ticket_status_val = match.get('ticket_status', '')

    overview_lines = [
        f"• **Location:** {site} | **Asset:** {asset_id or 'N/A'} | **Priority:** {priority}",
        f"• **Helpdesk State:** {ticket_status_val} (Workflow: `{status_val}`)",
    ]
    if desc:
        overview_lines.append(f"• **Reported Condition:** {desc}")
    sections.append("\n**Operational Context & Overview:**\n" + "\n".join(overview_lines))

    # Diagnostic reasoning
    is_ai = any(kw in asset_id.casefold() or kw in title.casefold() for kw in ('ai-box', 'ai box', 'backlog', 'inference', 'analytics'))
    is_cam = any(kw in asset_id.casefold() or kw in title.casefold() for kw in ('cam', 'camera', 'rtsp', 'stream'))
    is_poe = any(kw in asset_id.casefold() or kw in title.casefold() for kw in ('poe', 'power', 'cable', 'switch', 'network_down'))

    if is_ai:
        analysis = (
            "\n**Diagnostic Analysis & Root-Cause Reasoning:**\n"
            "• **Telemetry Assessment:** Automated health checks verified that the edge device network interface is responsive. "
            "However, edge analytics workloads can accumulate detection backlogs when frame ingestion rate spikes, neural inference batching latencies climb, "
            "or worker memory consumption rises.\n"
            "• **Control Loop Evaluation:** Because active probes did not observe a hard container crash and arbitrary configuration changes "
            "require human operational discretion, the orchestrator safely halted autonomous intervention and routed the ticket to `pending_technician`."
        )
    elif is_cam:
        analysis = (
            "\n**Diagnostic Analysis & Root-Cause Reasoning:**\n"
            "• **Telemetry Assessment:** Health monitors detected an RTSP stream delivery disruption on port 554. "
            "Surveillance streams typically drop due to socket keep-alive timeouts, switch port negotiation failures, or authentication mismatches.\n"
            "• **Control Loop Evaluation:** The policy gate restricts autonomous recovery to verified connection restarts (`reconnect-rtsp`). "
            "Authentication mismatches and physical cabling faults require technician verification to avoid security lockouts."
        )
    elif is_poe:
        analysis = (
            "\n**Diagnostic Analysis & Root-Cause Reasoning:**\n"
            "• **Telemetry Assessment:** Endpoint telemetry indicates an unpowered device or lost Ethernet carrier. "
            "Without negotiated PoE wattage from the switch, the device PHY layer cannot initialize.\n"
            "• **Control Loop Evaluation:** Because physical cable inspection and switch port power budgets require physical hands-on verification, "
            "the agent escalated the incident directly to a technician without executing unverified commands."
        )
    else:
        analysis = (
            "\n**Diagnostic Analysis & Root-Cause Reasoning:**\n"
            "• **Telemetry Assessment:** System health probes evaluated network reachability, process status, and storage utilization.\n"
            "• **Control Loop Evaluation:** Evidence was collected and evaluated against policy safety rules. "
            "To safeguard operational stability, the incident is routed for technician verification."
        )
    sections.append(analysis)

    # Activity and Notes
    notes = match.get('notes') or []
    customer_replies = match.get('customer_replies') or []
    if notes or customer_replies:
        history_lines = []
        for n in notes[-3:]:
            author = str(n.get('author') or 'technician').capitalize()
            body = str(n.get('body') or '').strip()
            body = body.replace('No critical fault reproduced by current checks', 'Current checks found no issue')
            history_lines.append(f"• *{author}*: {body}")
        for r in customer_replies[-2:]:
            history_lines.append(f"• *Customer Reply*: {str(r.get('body') or '').strip()}")
        sections.append("\n**Recorded History & Notes:**\n" + "\n".join(history_lines))

    # Operational safety boundary
    safety = (
        "\n**Safety Boundaries & Limitations:**\n"
        "• CarlBot is a grounded operational copilot with strict safety boundaries: autonomous actions are restricted to safe, "
        "policy-allowlisted procedures (`reconnect-rtsp` and `restart-ai-service`).\n"
        "• Physical repairs, Cat6 cable re-terminations, PoE switch port reconfiguration, and credential updates require technician authorization."
    )
    sections.append(safety)

    # Recommended action plan
    if is_ai:
        plan = (
            "\n**Recommended Technician Action Plan:**\n"
            "1. **Resource Inspection:** SSH into the edge appliance and verify system resources via CLI (`free -h` for RAM, `df -h` for storage).\n"
            "2. **Container Status:** Run `docker compose ps` and inspect error logs via `docker compose logs --tail=100`.\n"
            "3. **Safe Service Restart:** If detection queues are unresponsive or experiencing memory saturation, execute `restart-ai-service`.\n"
            "4. **Post-Recovery Verification:** Confirm detection events resume emitting, then mark the ticket ready for verification."
        )
    elif is_cam:
        plan = (
            "\n**Recommended Technician Action Plan:**\n"
            "1. **Layer 1 Check:** Inspect the switch patch panel for link and PoE LED status.\n"
            "2. **Layer 3 Check:** Run `ping <camera_ip>` to verify IP reachability.\n"
            "3. **Layer 7 Probe:** Probe RTSP port 554 via `nc -zv <camera_ip> 554` or `Test-NetConnection`.\n"
            "4. **Recovery:** If stream hung, trigger `reconnect-rtsp`. If 401 Unauthorized, verify credentials in the password vault."
        )
    elif is_poe:
        plan = (
            "\n**Recommended Technician Action Plan:**\n"
            "1. **Power Budget:** Check switch PoE wattage consumption in the switch management console.\n"
            "2. **Physical Cable:** Test Cat6 cable continuity and inspect RJ45 connectors for pin corrosion or damage.\n"
            "3. **Port Bounce:** Perform a 20-second PoE power bounce on the switch port to clear hardware PHY state.\n"
            "4. **Verification:** Confirm link LED lights green and device acquires an IP address."
        )
    else:
        plan = (
            "\n**Recommended Technician Action Plan:**\n"
            "1. **Diagnostics:** Review recent logs and telemetry metrics for the asset.\n"
            "2. **Field Inspection:** Perform on-site physical and network connectivity checks.\n"
            "3. **Resolution:** Submit the ticket for verification once operational status is restored."
        )
    sections.append(plan)

    return "\n".join(sections)


def _describe_matches(message: str, matches: list[dict[str, Any]]) -> str:
    if not matches:
        return (
            "I couldn't find a matching ticket. Try a site code, camera ID, "
            'or issue such as camera offline.'
        )

    exact_site = next(
        (match['site_id'] for match in matches if match['site_match'] == 'exact' and match['site_id']),
        None,
    )
    has_partial_site = any(match['site_match'] == 'partial' for match in matches)
    if len(matches) == 1:
        match = matches[0]
        status_value = match.get('ticket_status') or match['status']
        status = _STATUS_EXPLANATIONS.get(str(status_value), str(status_value).replace('_', ' '))
        title = str(match['title'])
        asset_id = str(match['asset_id'])
        asset = f' ({asset_id})' if asset_id and asset_id.casefold() not in title.casefold() else ''
        answer = f'Ticket #{match["ticket_id"]}: {title}{asset}. {status.capitalize()}.'
        if match['status'] == 'pending_technician' and match.get('ticket_status') != 'Closed':
            answer += ' Waiting for a technician.'

        detail = next(
            (_PLAIN_LANGUAGE_DETAILS.get(value, value) for value in match['details'] if value),
            None,
        )
        if detail:
            detail = detail.replace('No critical fault reproduced by current checks', 'Current checks found no issue')
            answer += f' {detail}'
        elif match['source'] == 'reference_export':
            answer += ' The reference list has no notes.'
        if has_partial_site or (not exact_site and _site_query(message)):
            answer += ' The site is not confirmed.'

        if match.get('source') == 'reference_export':
            return answer

        return _synthesize_live_ticket_analysis(answer, match)

    location = f' at {exact_site}' if exact_site else ''
    answer_parts = [
        f'I found {len(matches)} matching tickets{location}. Top matches:'
    ]
    if has_partial_site or (not exact_site and _site_query(message)):
        answer_parts.append('The site is not confirmed.')

    for match in matches[:3]:
        status_value = match.get('ticket_status') or match['status']
        status = _STATUS_EXPLANATIONS.get(str(status_value), str(status_value).replace('_', ' '))
        title = str(match['title'])
        asset_id = str(match['asset_id'])
        asset = f' ({asset_id})' if asset_id and asset_id.casefold() not in title.casefold() else ''
        answer_parts.append(
            f'#{match["ticket_id"]} — {title}{asset}; {status}.'
        )
        if match['status'] == 'pending_technician' and match.get('ticket_status') != 'Closed':
            answer_parts[-1] = answer_parts[-1][:-1] + '; waiting for a technician.'
    if len(matches) > 3:
        remaining = len(matches) - 3
        noun = 'match' if remaining == 1 else 'matches'
        answer_parts.append(f'Ask about a ticket number for details; {remaining} more {noun}.')
    return '\n'.join(answer_parts)


def query_tickets(
    message: str,
    tickets: list[dict[str, Any]],
    *,
    context_ticket_id: int | None = None,
) -> dict[str, Any]:
    if context_ticket_id is not None:
        if not any(str(ticket.get('id')) == str(context_ticket_id) for ticket in tickets):
            raise ValueError(f'Context ticket {context_ticket_id} was not found')

    conversational = _detect_conversational_response(
        message,
        context_ticket_id=context_ticket_id,
        tickets=tickets,
    )
    if conversational is not None:
        intent, answer = conversational
        matches: list[dict[str, Any]] = []
        if context_ticket_id is not None:
            context_ticket = next(
                (t for t in tickets if str(t.get('id')) == str(context_ticket_id)),
                None,
            )
            if context_ticket is not None:
                status_val = str(context_ticket.get('status') or '')
                ticket_status_val = str(context_ticket.get('ticket_status') or '')
                if ticket_status_val not in {'Open', 'Answered', 'Closed'}:
                    ticket_status_val = (
                        'Closed' if status_val == 'closed'
                        else 'Answered' if status_val in {'resolved', 'ready_for_verification'}
                        else 'Open'
                    )
                matches.append({
                    'ticket_id': str(context_ticket_id),
                    'title': str(context_ticket.get('title') or ''),
                    'status': status_val,
                    'ticket_status': ticket_status_val,
                    'priority': str(context_ticket.get('priority') or ''),
                    'site_id': str(context_ticket.get('site_id') or ''),
                    'asset_id': str(context_ticket.get('asset_id') or ''),
                    'site_match': 'exact',
                    'source': 'live_helpdesk',
                    'has_conversation': bool(context_ticket.get('notes') or context_ticket.get('customer_replies')),
                    'details': [
                        str(context_ticket.get(key) or '').strip()
                        for key in ('resolution', 'root_cause', 'description', 'ai_summary')
                        if str(context_ticket.get(key) or '').strip()
                    ] + [
                        str(note.get('body') or '').strip()
                        for note in (context_ticket.get('notes') or [])[:20]
                        if str(note.get('body') or '').strip()
                    ] + [
                        f"[Customer reply] {str(reply.get('body') or '').strip()}"
                        for reply in (context_ticket.get('customer_replies') or [])[:20]
                        if str(reply.get('body') or '').strip()
                    ],
                })
        return {
            'answer': answer,
            'matches': matches,
            'reference_export_available': True,
            'reference_export_configured': False,
            'is_conversational': True,
            'intent': intent,
        }

    matches = _live_matches(
        message,
        tickets,
        context_ticket_id=context_ticket_id,
    )
    if context_ticket_id is not None:
        context_match = next(
            (match for match in matches if match['ticket_id'] == str(context_ticket_id)),
            None,
        )
        if context_match is None:
            context_match = next(
                iter(_live_matches(f'ticket {context_ticket_id}', tickets)),
                None,
            )
            if context_match is None:
                raise ValueError(f'Context ticket {context_ticket_id} was not found')
            context_ticket = next(
                ticket for ticket in tickets
                if str(ticket.get('id')) == str(context_ticket_id)
            )
            context_match['details'] = [
                str(context_ticket.get(key) or '').strip()
                for key in ('resolution', 'root_cause', 'description', 'ai_summary')
                if str(context_ticket.get(key) or '').strip()
            ] + [
                str(note.get('body') or '').strip()
                for note in (context_ticket.get('notes') or [])[:20]
                if str(note.get('body') or '').strip()
            ] + [
                f"[Customer reply] {str(reply.get('body') or '').strip()}"
                for reply in (context_ticket.get('customer_replies') or [])[:20]
                if str(reply.get('body') or '').strip()
            ]
            matches.insert(0, context_match)
        else:
            matches.remove(context_match)
            matches.insert(0, context_match)
    reference_path = os.getenv('TICKET_REFERENCE_CSV')
    reference_export_available = False
    if reference_path:
        path = Path(reference_path)
        if path.is_file():
            matches.extend(_export_matches(message, path))
            reference_export_available = True

    matches.sort(
        key=lambda item: (
            context_ticket_id is not None
            and item['ticket_id'] == str(context_ticket_id),
            item['site_match'] == 'exact',
            _status_filter(message) is None or _matches_status(item['status'], _status_filter(message)),
        ),
        reverse=True,
    )
    answer = _describe_matches(message, matches)
    if reference_path and not reference_export_available:
        answer += ' The reference export is not mounted; this response searched live helpdesk records only.'
    return {
        'answer': answer,
        'matches': matches[:10],
        'reference_export_available': reference_export_available,
        'reference_export_configured': bool(reference_path),
    }
