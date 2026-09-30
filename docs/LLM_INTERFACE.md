# Future LLM Interface

## Contract

The LLM reasoning component receives a structured `ReasoningRequest` and returns a structured `ReasoningResponse`. Both are defined in `services/agent/reasoning.py`.

## Input (ReasoningRequest)

```json
{
  "asset_id": "CAM-001",
  "asset_kind": "camera",
  "observations": [
    {"check": {"ping": true, "rtsp": false, "rtsp_auth": true, "rtsp_path": true}}
  ],
  "historical_evidence": [
    {"id": "HIST-001", "root_cause": "rtsp_down", "resolution": "Reconnected stream"}
  ],
  "knowledge": [
    {"source": "troubleshooting.md", "score": 3, "snippet": "RTSP down with healthy ping..."}
  ],
  "active_faults": []
}
```

## Output (ReasoningResponse)

```json
{
  "hypotheses": [
    {"fault": "rtsp_down", "confidence": 0.95, "reasoning": "Ping OK but RTSP failed"}
  ],
  "tool_intents": [
    {"name": "reconnect_stream", "arguments": {"asset_id": "CAM-001"}}
  ],
  "recommended_action": "Reconnect the RTSP stream",
  "confidence": 0.95,
  "safety_class": "SAFE_REVERSIBLE"
}
```

## Rules

1. The runtime validates the output schema.
2. Each `tool_intent` is checked against `policy.py` before execution.
3. The model is **never** the authority for safety — the policy engine is.
4. The simulator/tool layer remains deterministic and testable without a model.
5. Direct model-generated HTTP calls are **prohibited**.

## System Prompt

The system prompt is defined in `services/agent/reasoning.py` as `SYSTEM_PROMPT`. It instructs the model to:
- Use only supplied data
- Separate facts from hypotheses
- Never fabricate results
- Request human action for consequential changes

## Implementation Guide

```python
from services.agent.reasoning import ReasoningProvider, ReasoningRequest, ReasoningResponse

class MyLLMProvider(ReasoningProvider):
    def reason(self, request: ReasoningRequest) -> ReasoningResponse:
        # 1. Format request into model input (system prompt + observations)
        # 2. Call your model (OpenAI, local, etc.)
        # 3. Parse structured JSON response
        # 4. Return ReasoningResponse
        ...
```

Register your provider in the agent's configuration. The agent will:
1. Call `provider.reason(request)` with current observations
2. Check each `tool_intent` against `policy.py`
3. Execute only allowed intents via the portal API
4. Verify results
5. Document everything in the ticket
