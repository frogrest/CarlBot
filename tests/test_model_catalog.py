"""Deterministic tests for the curated model catalog and download manager.

No network and no multi-gigabyte download: `httpx.MockTransport` serves a fake
GGUF byte stream, and every store points at a `tmp_path`.
"""
from __future__ import annotations

import threading

import httpx
import pytest

from services.local_llm import (
    CATALOG,
    DownloadError,
    DownloadState,
    LocalLlmConfig,
    ModelDownloader,
    ModelStore,
    apply_selected_model,
    get_model,
    model_snapshot,
)
from services.local_llm import LocalLlmRuntime


# -- catalog ---------------------------------------------------------------
def test_catalog_entries_are_unique_and_well_formed():
    ids = [option.id for option in CATALOG]
    assert len(ids) == len(set(ids))
    assert len(CATALOG) >= 4
    for option in CATALOG:
        assert option.download_url.startswith('https://huggingface.co/')
        assert option.filename.endswith('.gguf')
        assert option.size_bytes > 0
        assert option.context_window > 0
        assert option.min_ram_gb > 0
    assert any(option.recommended for option in CATALOG)


def test_get_model_returns_none_for_unknown():
    assert get_model('does-not-exist') is None
    assert get_model(CATALOG[0].id) is CATALOG[0]


# -- store -----------------------------------------------------------------
def _store(tmp_path) -> ModelStore:
    return ModelStore(tmp_path / 'models')


def test_store_records_install_and_defaults_selection(tmp_path):
    store = _store(tmp_path)
    option = CATALOG[0]
    store.ensure_dir()
    store.target_path(option.id).write_bytes(b'GGUF')

    store.record_installed(option.id, option)

    assert store.is_installed(option.id)
    assert store.selected_id() == option.id
    assert store.selected_model_path().endswith(option.filename)


def test_store_select_requires_install(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        store.select(CATALOG[0].id)


def test_store_remove_deletes_file_and_clears_selection(tmp_path):
    store = _store(tmp_path)
    option = CATALOG[0]
    store.ensure_dir()
    store.target_path(option.id).write_bytes(b'GGUF')
    store.record_installed(option.id, option)

    removed = store.remove(option.id)

    assert removed is True
    assert not store.is_installed(option.id)
    assert store.selected_id() is None
    assert store.selected_model_path() == ''


def test_store_survives_corrupt_registry(tmp_path):
    store = _store(tmp_path)
    store.ensure_dir()
    store.registry_path.write_text('{not json', encoding='utf-8')
    assert store.selected_id() is None  # no crash


# -- downloader ------------------------------------------------------------
def _gguf_client(payload: bytes, *, content_length: bool = True):
    headers = {'content-length': str(len(payload))} if content_length else {}

    def handler(_request):
        return httpx.Response(200, headers=headers, content=payload)

    return lambda: httpx.Client(transport=httpx.MockTransport(handler))


def test_downloader_completes_and_verifies_gguf(tmp_path):
    store = _store(tmp_path)
    option = CATALOG[0]
    payload = b'GGUF' + b'\x00' * 5000
    downloader = ModelDownloader(store, client_factory=_gguf_client(payload), chunk_size=1024)

    downloader.start(option.id)
    downloader.join(timeout=10)

    progress = downloader.progress_for(option.id)
    assert progress.state is DownloadState.COMPLETED
    assert progress.bytes_downloaded == len(payload)
    target = store.target_path(option.id)
    assert target.read_bytes().startswith(b'GGUF')
    assert store.is_installed(option.id)
    assert not (target.with_name(target.name + '.part')).exists()


def test_downloader_rejects_non_gguf_content(tmp_path):
    store = _store(tmp_path)
    option = CATALOG[0]
    downloader = ModelDownloader(store, client_factory=_gguf_client(b'NOPE not a model'))

    downloader.start(option.id)
    downloader.join(timeout=10)

    progress = downloader.progress_for(option.id)
    assert progress.state is DownloadState.ERROR
    assert 'GGUF' in progress.error
    assert not store.is_installed(option.id)


def test_downloader_rejects_unknown_model(tmp_path):
    downloader = ModelDownloader(_store(tmp_path))
    with pytest.raises(DownloadError):
        downloader.start('nope')


def test_downloader_serializes_concurrent_downloads(tmp_path):
    store = _store(tmp_path)
    gate = threading.Event()

    def handler(_request):
        gate.wait(timeout=5)
        return httpx.Response(200, headers={'content-length': '8'}, content=b'GGUFxxxx')

    blocked = ModelDownloader(
        store, client_factory=lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    blocked.start(CATALOG[0].id)
    try:
        with pytest.raises(DownloadError):
            blocked.start(CATALOG[1].id)
    finally:
        gate.set()
        blocked.join(timeout=10)


def test_downloader_cancel_cleans_up(tmp_path):
    store = _store(tmp_path)
    gate = threading.Event()

    def handler(_request):
        gate.wait(timeout=5)
        return httpx.Response(200, headers={'content-length': '8'}, content=b'GGUFxxxx')

    downloader = ModelDownloader(
        store, client_factory=lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    downloader.start(CATALOG[0].id)
    assert downloader.active_model_id() == CATALOG[0].id

    downloader.cancel(CATALOG[0].id)
    gate.set()
    downloader.join(timeout=10)

    assert downloader.progress_for(CATALOG[0].id).state is DownloadState.CANCELLED
    assert not store.is_installed(CATALOG[0].id)


# -- runtime wiring --------------------------------------------------------
def test_apply_selected_model_points_runtime_at_selection(tmp_path):
    store = _store(tmp_path)
    option = CATALOG[0]
    store.ensure_dir()
    store.target_path(option.id).write_bytes(b'GGUF')
    store.record_installed(option.id, option)

    runtime = LocalLlmRuntime(LocalLlmConfig(enabled=True, model_path=''))
    apply_selected_model(runtime, store)

    assert runtime.config.model_path.endswith(option.filename)


def test_runtime_from_env_uses_store_selection(tmp_path, monkeypatch):
    monkeypatch.delenv('LOCAL_LLM_MODEL_PATH', raising=False)
    store = _store(tmp_path)
    option = CATALOG[0]
    store.ensure_dir()
    store.target_path(option.id).write_bytes(b'GGUF')
    store.record_installed(option.id, option)

    runtime = LocalLlmRuntime.from_env(store=store)

    assert runtime.config.model_path.endswith(option.filename)


def test_model_snapshot_reports_catalog_and_runtime(tmp_path):
    store = _store(tmp_path)
    runtime = LocalLlmRuntime(LocalLlmConfig(enabled=False))
    downloader = ModelDownloader(store)
    snapshot = model_snapshot(store, downloader, runtime)
    assert {m['id'] for m in snapshot['models']} == {o.id for o in CATALOG}
    assert snapshot['selected_id'] is None
    assert snapshot['runtime']['state'] == 'disabled'


# -- helpdesk endpoints ----------------------------------------------------
def test_helpdesk_lists_models(helpdesk):
    response = helpdesk.get('/api/llm/models')
    assert response.status_code == 200
    body = response.json()
    assert len(body['models']) == len(CATALOG)
    assert body['runtime']['state'] == 'disabled'


def test_helpdesk_download_endpoint_persists_and_selects(helpdesk, monkeypatch, tmp_path):
    import services.helpdesk.app as helpdesk_module

    store = helpdesk_module.local_llm_store
    monkeypatch.setattr(store, 'root', tmp_path / 'models')
    monkeypatch.setattr(store, 'registry_path', tmp_path / 'models' / 'models.json')
    downloader = helpdesk_module.local_llm_downloader
    monkeypatch.setattr(
        downloader, '_client_factory',
        _gguf_client(b'GGUF' + b'\x00' * 2000),
    )

    option = CATALOG[0]
    started = helpdesk.post(f'/api/llm/models/{option.id}/download')
    assert started.status_code == 200
    downloader.join(timeout=10)

    listing = helpdesk.get('/api/llm/models').json()
    entry = next(m for m in listing['models'] if m['id'] == option.id)
    assert entry['installed'] is True
    assert listing['selected_id'] == option.id


def test_helpdesk_download_unknown_model_is_404(helpdesk):
    assert helpdesk.post('/api/llm/models/nope/download').status_code == 404


def test_helpdesk_select_uninstalled_model_is_409(helpdesk, monkeypatch, tmp_path):
    import services.helpdesk.app as helpdesk_module

    store = helpdesk_module.local_llm_store
    monkeypatch.setattr(store, 'root', tmp_path / 'models')
    monkeypatch.setattr(store, 'registry_path', tmp_path / 'models' / 'models.json')

    response = helpdesk.post(f'/api/llm/models/{CATALOG[0].id}/select')
    assert response.status_code == 409
