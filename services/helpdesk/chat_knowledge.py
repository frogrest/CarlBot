import os
import re
from pathlib import Path
from typing import Any

STOPWORDS = {
    'the', 'and', 'for', 'with', 'that', 'this', 'from', 'into', 'when', 'then',
    'have', 'has', 'are', 'was', 'were', 'your', 'you', 'our', 'their', 'not',
    'can', 'but', 'use', 'used', 'using', 'what', 'how', 'why', 'where', 'which',
    'will', 'should', 'must', 'may', 'all', 'any', 'a', 'an', 'to', 'of', 'in',
    'on', 'at', 'is', 'it', 'as', 'or', 'by', 'be', 'if', 'we', 'do', 'does',
}

_TOKEN_PATTERN = re.compile(r'[a-z0-9_-]{2,}')

# Approved documentation directories relative to the docs root.
# Only approved technical documentation and SOPs may be searched.
# Internal planning, prompt templates, architecture specs, and arbitrary folders are excluded.
APPROVED_SUBDIRS = {'SOP', 'RTSP', 'Networking', 'Cameras', 'NVR', 'AI-Box', 'Alarm-EG', 'AI-Cloud', 'Vendor', 'Escalation', 'Known-Issues'}


def _extract_tokens(text: str) -> set[str]:
    return {token for token in _TOKEN_PATTERN.findall(text.lower()) if token not in STOPWORDS}


def _parse_sections(text: str, relative_path: str) -> list[dict[str, Any]]:
    """Parse Markdown text into sections based on headers, recording line numbers."""
    lines = text.splitlines()
    sections: list[dict[str, Any]] = []
    current_title = Path(relative_path).stem.replace('_', ' ').replace('-', ' ').title()
    current_start = 1
    current_lines: list[str] = []

    for idx, line in enumerate(lines, start=1):
        if line.startswith('#'):
            if current_lines:
                content = '\n'.join(current_lines).strip()
                if content:
                    sections.append({
                        'title': current_title,
                        'start_line': current_start,
                        'end_line': idx - 1,
                        'content': content,
                    })
            # New heading
            current_title = line.lstrip('#').strip() or current_title
            current_start = idx
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        content = '\n'.join(current_lines).strip()
        if content:
            sections.append({
                'title': current_title,
                'start_line': current_start,
                'end_line': len(lines),
                'content': content,
            })

    return sections


class KnowledgeRetriever:
    """Read-only retriever over approved local documentation."""

    def __init__(self, docs_root: str | Path | None = None):
        if docs_root is None:
            env_root = os.getenv('DOCS_ROOT')
            if env_root:
                self.root = Path(env_root).resolve()
            else:
                self.root = (Path(__file__).resolve().parent.parent.parent / 'docs').resolve()
        else:
            self.root = Path(docs_root).resolve()

    def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        """Search only approved documentation sections and return structured results."""
        if not self.root.is_dir():
            return []

        q_tokens = _extract_tokens(query)
        if not q_tokens:
            return []

        candidates: list[dict[str, Any]] = []

        # Find all .md files in approved subdirectories only
        for path in self.root.rglob('*.md'):
            # Path safety check
            try:
                rel = path.relative_to(self.root)
            except ValueError:
                continue

            parts = rel.parts
            if not parts:
                continue
            first_dir = parts[0]

            # Only accept files inside approved knowledge subdirectories or top-level README if in approved subdirs
            if first_dir not in APPROVED_SUBDIRS:
                continue

            # Normalized repo-relative path (e.g. docs/SOP/...)
            repo_rel_path = f'docs/{rel.as_posix()}'

            try:
                text = path.read_text(encoding='utf-8', errors='ignore')
            except OSError:
                continue

            sections = _parse_sections(text, rel.as_posix())
            path_tokens = _extract_tokens(rel.as_posix())
            for sec in sections:
                sec_tokens = _extract_tokens(sec['content'])
                title_tokens = _extract_tokens(sec['title']) | path_tokens
                overlap = (q_tokens & sec_tokens) | (q_tokens & title_tokens)
                if overlap:
                    score = len(q_tokens & sec_tokens) + 3 * len(q_tokens & title_tokens)
                    excerpt = sec['content'][:450].strip()
                    candidates.append({
                        'source_path': repo_rel_path,
                        'section_title': sec['title'],
                        'locator': f"L{sec['start_line']}-L{sec['end_line']}",
                        'excerpt': excerpt,
                        'score': score,
                    })

        candidates.sort(key=lambda x: (-x['score'], x['source_path'], x['locator']))
        # Deduplicate / limit
        results: list[dict[str, Any]] = []
        seen = set()
        for item in candidates:
            key = (item['source_path'], item['locator'])
            if key not in seen:
                seen.add(key)
                results.append({
                    'source_path': item['source_path'],
                    'section_title': item['section_title'],
                    'locator': item['locator'],
                    'excerpt': item['excerpt'],
                })
            if len(results) >= limit:
                break

        return results
