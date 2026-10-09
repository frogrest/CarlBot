"""Resolve the OpenAI-compatible endpoint used by the existing LLM clients.

Precedence:
1. the managed local runtime, when it is enabled and ready;
2. an external `LLM_BASE_URL` + `LLM_MODEL` pair;
3. nothing, which keeps the deterministic (no-model) behaviour.
"""

from __future__ import annotations

import os
from typing import Mapping, Optional, Tuple

from .runtime import LocalLlmRuntime

DEFAULT_LOCAL_MODEL_NAME = 'local-gguf'


def resolve_endpoint(
    *,
    runtime: Optional[LocalLlmRuntime] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Tuple[str, str]:
    """Return `(base_url, model)`; both empty when no model is available."""
    source = os.environ if env is None else env
    if runtime is not None and runtime.config.enabled and runtime.status().ready:
        model = (source.get('LLM_MODEL') or '').strip() or DEFAULT_LOCAL_MODEL_NAME
        return runtime.config.base_url, model
    base_url = (source.get('LLM_BASE_URL') or '').strip().rstrip('/')
    model = (source.get('LLM_MODEL') or '').strip()
    return base_url, model
