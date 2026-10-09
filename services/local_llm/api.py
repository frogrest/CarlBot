"""Shared HTTP surface for choosing and downloading a local model.

Both the helpdesk and agent services mount the same router so the two runtimes
behave identically and stay consistent. Endpoints only ever act on the curated
catalog: the caller passes a catalog `id`, never a URL or filesystem path.

Threat model: this is the same unauthenticated, loopback-only lab API as the
rest of the project. It cannot execute commands or write outside the models
directory; it can select among allow-listed models and start/cancel a download.
The deterministic policy engine remains the only authority for simulated
actions.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Callable, Optional

from fastapi import APIRouter, HTTPException

from .catalog import CATALOG, get_model
from .downloader import DownloadError, ModelDownloader
from .runtime import LocalLlmRuntime
from .store import ModelStore


def apply_selected_model(runtime: LocalLlmRuntime, store: ModelStore) -> None:
    """Point the runtime at the store's selected model when one is installed."""
    selected = store.selected_model_path()
    if selected and runtime.config.model_path != selected:
        runtime.config = dataclasses.replace(runtime.config, model_path=selected)


def model_snapshot(
    store: ModelStore,
    downloader: ModelDownloader,
    runtime: LocalLlmRuntime,
) -> dict[str, Any]:
    """Full truthful snapshot: catalog, install/selection state, downloads, runtime."""
    selected = store.selected_id()
    active_path = store.selected_model_path() or runtime.config.model_path
    models: list[dict[str, Any]] = []
    for option in CATALOG:
        entry = option.as_dict()
        entry['installed'] = store.is_installed(option.id)
        entry['installed_size_bytes'] = store.installed_size(option.id)
        entry['is_selected'] = option.id == selected
        models.append(entry)
    return {
        'models': models,
        'selected_id': selected,
        'active_model_path': active_path,
        'models_dir': str(store.root),
        'download': downloader.snapshot(),
        'runtime': runtime.status().as_dict(),
    }


def build_llm_router(
    store: ModelStore,
    downloader: ModelDownloader,
    runtime: LocalLlmRuntime,
    *,
    on_select: Optional[Callable[[], None]] = None,
) -> APIRouter:
    """Create the `/api/llm` router bound to this service's runtime objects."""
    router = APIRouter()

    @router.get('/api/llm/models')
    def list_models() -> dict[str, Any]:
        return model_snapshot(store, downloader, runtime)

    @router.post('/api/llm/models/{model_id}/download')
    def start_download(model_id: str) -> dict[str, Any]:
        if get_model(model_id) is None:
            raise HTTPException(404, f'Unknown model id: {model_id}')
        try:
            downloader.start(model_id)
        except DownloadError as exc:
            raise HTTPException(409, str(exc)) from exc
        return model_snapshot(store, downloader, runtime)

    @router.post('/api/llm/models/{model_id}/download/cancel')
    def cancel_download(model_id: str) -> dict[str, Any]:
        if get_model(model_id) is None:
            raise HTTPException(404, f'Unknown model id: {model_id}')
        downloader.cancel(model_id)
        return model_snapshot(store, downloader, runtime)

    @router.post('/api/llm/models/{model_id}/select')
    def select_model(model_id: str) -> dict[str, Any]:
        if get_model(model_id) is None:
            raise HTTPException(404, f'Unknown model id: {model_id}')
        try:
            store.select(model_id)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        apply_selected_model(runtime, store)
        if on_select is not None:
            on_select()
        runtime.ensure_started()
        return model_snapshot(store, downloader, runtime)

    @router.delete('/api/llm/models/{model_id}')
    def remove_model(model_id: str) -> dict[str, Any]:
        if get_model(model_id) is None:
            raise HTTPException(404, f'Unknown model id: {model_id}')
        if downloader.active_model_id() == model_id:
            raise HTTPException(409, 'cannot remove a model while it is downloading')
        store.remove(model_id)
        apply_selected_model(runtime, store)
        return model_snapshot(store, downloader, runtime)

    return router
