"""Managed local inference runtime (llama.cpp `llama-server`).

CarlBot starts and owns its own local OpenAI-compatible server so the existing
chat/agent clients keep working unchanged and no paid API key is required.

Nothing here contacts a real customer system: the runtime is a local process on
loopback, and the deterministic policy layer remains the security boundary.

`catalog` / `store` / `downloader` / `api` add a curated, allow-listed way to
choose and download a compatible GGUF model from the UI — no arbitrary URLs or
paths, and no shell.
"""

from .api import apply_selected_model, build_llm_router, model_snapshot
from .catalog import CATALOG, ModelOption, catalog_dicts, get_model
from .client import DEFAULT_LOCAL_MODEL_NAME, resolve_endpoint
from .config import LocalLlmConfig, LocalLlmConfigError
from .downloader import DownloadError, DownloadProgress, DownloadState, ModelDownloader
from .runtime import (
    LocalLlmError,
    LocalLlmRuntime,
    LocalLlmState,
    RuntimeBusyError,
    RuntimeStatus,
)
from .store import ModelStore

__all__ = [
    'CATALOG',
    'DEFAULT_LOCAL_MODEL_NAME',
    'DownloadError',
    'DownloadProgress',
    'DownloadState',
    'LocalLlmConfig',
    'LocalLlmConfigError',
    'LocalLlmError',
    'LocalLlmRuntime',
    'LocalLlmState',
    'ModelDownloader',
    'ModelOption',
    'ModelStore',
    'RuntimeBusyError',
    'RuntimeStatus',
    'apply_selected_model',
    'build_llm_router',
    'catalog_dicts',
    'get_model',
    'model_snapshot',
    'resolve_endpoint',
]
