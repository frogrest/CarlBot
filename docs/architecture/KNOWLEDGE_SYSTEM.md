# Knowledge and Historical-Ticket System

## Sources of truth

The assistant should reason from three main evidence classes:

1. Live operational evidence.
2. Historical helpdesk incidents.
3. Internal technical documentation.

## Historical ticket search

The search layer should support fields such as:

- title
- description
- root cause
- resolution
- technician notes
- site/property
- asset
- vendor
- symptom keywords
- date

The system should return enough metadata for the assistant to explain why a historical ticket was relevant.

## Documentation

Recommended tree:

```text
docs/
  SOP/
  RTSP/
  Networking/
  Cameras/
  NVR/
  AI-Box/
  Alarm-EG/
  AI-Cloud/
  Vendor/
  Escalation/
  Known-Issues/
```

## Retrieval result

Use a structured result such as:

```json
{
  "source_type": "ticket",
  "source_id": "T-123",
  "title": "Camera offline after switch replacement",
  "relevance": 0.87,
  "evidence": ["..."],
  "source_location": "historical/helpdesk"
}
```

## RAG upgrade path

Start with deterministic local search.

Later add:

```text
Document
 ↓
chunking
 ↓
metadata
 ↓
embedding
 ↓
vector index
 ↓
retrieval
 ↓
reranking
 ↓
evidence bundle
```

The deterministic keyword search should remain available for tests.

## Citation behavior

The chatbot should be able to say:

> Historical ticket T-123 reported the same symptom and was resolved after correcting the RTSP stream path.

That is much more useful than saying:

> I think the RTSP path is wrong.

## Conflict handling

When documents disagree:

1. Prefer the newer approved internal procedure.
2. Surface the conflict rather than hiding it.
3. Escalate when the conflict affects safety or consequential changes.

## Source hierarchy

```text
Current approved SOP
      ↓
Current site/device configuration
      ↓
Recent historical ticket
      ↓
Older historical ticket
      ↓
Generic technical knowledge
```

Generic model memory should not silently override internal procedures.
