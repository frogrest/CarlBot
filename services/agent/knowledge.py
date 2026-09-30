"""Simple keyword-based knowledge retrieval layer.

Searches Markdown and TXT files under data/knowledge/ for keyword overlap.
This implementation is intentionally minimal and deterministic so it works
without any external service. It is designed to be replaced by an embedding /
vector-search backend later while keeping the same interface.
"""
from __future__ import annotations

from services.common.config import KNOWLEDGE


def search(query: str, limit: int = 5) -> list[dict[str, object]]:
    """Return the top knowledge documents matching *query* by keyword overlap.

    Each result contains:
      - source: relative path within the knowledge directory
      - score: number of query terms found in the document
      - snippet: first 600 characters of the document
    """
    terms = set(query.lower().split())
    results: list[dict[str, object]] = []

    files = list(KNOWLEDGE.rglob("*.md")) + list(KNOWLEDGE.rglob("*.txt"))
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        text_lower = text.lower()
        score = sum(1 for term in terms if term in text_lower)
        if score > 0:
            results.append({
                "source": str(path.relative_to(KNOWLEDGE)),
                "score": score,
                "snippet": text[:600],
            })

    results.sort(key=lambda r: r["score"], reverse=True)  # type: ignore[arg-type]
    return results[:limit]


def list_documents() -> list[str]:
    """Return the relative paths of all knowledge documents."""
    files = list(KNOWLEDGE.rglob("*.md")) + list(KNOWLEDGE.rglob("*.txt"))
    return [str(p.relative_to(KNOWLEDGE)) for p in files]


def get_document(doc_path: str) -> dict[str, object] | None:
    """Return the content and metadata of a specific knowledge document."""
    target = (KNOWLEDGE / doc_path).resolve()
    # Prevent directory traversal
    if not target.is_relative_to(KNOWLEDGE.resolve()) or not target.exists() or not target.is_file():
        return None
    try:
        content = target.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    # Derive title from first heading if present
    title = doc_path
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# "):
            title = line[2:].strip()
            break

    return {
        "source": doc_path,
        "title": title,
        "size": len(content),
        "lines": len(content.splitlines()),
        "content": content,
    }


def list_document_summaries() -> list[dict[str, object]]:
    """Return summaries for all knowledge documents."""
    docs = []
    for rel_path in list_documents():
        doc = get_document(rel_path)
        if doc:
            docs.append({
                "source": doc["source"],
                "title": doc["title"],
                "size": doc["size"],
                "lines": doc["lines"],
                "snippet": doc["content"][:300],
            })
    return docs

