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


def _live_matches(
    message: str,
    tickets: list[dict[str, Any]],
    *,
    context_ticket_id: int | None = None,
) -> list[dict[str, Any]]:
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
        searchable += ' ' + ' '.join(str(note.get('body') or '') for note in notes)
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
        details = [
            str(ticket.get(key) or '').strip()
            for key in ('resolution', 'root_cause', 'description')
            if str(ticket.get(key) or '').strip()
        ]
        note_limit = 20 if ticket.get('id') == context_ticket_id else 3
        details.extend(
            str(note.get('body') or '').strip()
            for note in notes[:note_limit]
            if str(note.get('body') or '').strip()
        )
        matches.append((score, {
            'ticket_id': str(ticket['id']),
            'title': str(ticket.get('title') or ''),
            'status': status,
            'ticket_status': ticket_status,
            'priority': str(ticket.get('priority') or ''),
            'site_id': site_id,
            'asset_id': str(ticket.get('asset_id') or ''),
            'site_match': site_match,
            'source': 'live_helpdesk',
            'has_conversation': bool(notes),
            'details': details,
        }))

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
            answer += f' {detail}'
        elif match['source'] == 'reference_export':
            answer += ' The reference list has no notes.'
        if has_partial_site or (not exact_site and _site_query(message)):
            answer += ' The site is not confirmed.'
        return answer

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
