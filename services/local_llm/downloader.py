"""Background downloader for allow-listed catalog models.

Only `catalog.py` entries can be downloaded — there is no arbitrary-URL or
arbitrary-path input. A single download runs at a time, streams to a `.part`
file with live progress, verifies the GGUF magic bytes, and only then atomically
renames the file into place. Cancellation and failures clean up the partial
file. No shell is ever involved.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

import httpx

from .catalog import ModelOption, get_model
from .store import ModelStore

logger = logging.getLogger(__name__)

GGUF_MAGIC = b'GGUF'
DEFAULT_CHUNK_SIZE = 1024 * 256
# Allow a little slack over the recorded size (CDN/header drift), but never an
# unbounded stream: a runaway response is treated as an error.
MAX_EXTRA_BYTES = 64 * 1024 * 1024
DEFAULT_HTTP_TIMEOUT = 30.0


class DownloadState(str, Enum):
    IDLE = 'idle'
    DOWNLOADING = 'downloading'
    VERIFYING = 'verifying'
    COMPLETED = 'completed'
    ERROR = 'error'
    CANCELLED = 'cancelled'


class DownloadError(RuntimeError):
    """Raised when a download request is rejected before it starts."""


@dataclass
class DownloadProgress:
    model_id: str
    state: DownloadState
    bytes_downloaded: int = 0
    total_bytes: int = 0
    error: str = ''

    def as_dict(self) -> dict[str, Any]:
        return {
            'model_id': self.model_id,
            'state': self.state.value,
            'bytes_downloaded': self.bytes_downloaded,
            'total_bytes': self.total_bytes,
            'percent': (
                round(self.bytes_downloaded * 100 / self.total_bytes)
                if self.total_bytes > 0
                else None
            ),
            'error': self.error,
        }


class ModelDownloader:
    """Serial background downloader for the curated model catalog."""

    def __init__(
        self,
        store: ModelStore,
        *,
        client_factory: Optional[Callable[[], httpx.Client]] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> None:
        self.store = store
        self._client_factory = client_factory or self._default_client
        self._chunk_size = chunk_size
        self._lock = threading.RLock()
        self._progress: dict[str, DownloadProgress] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._thread: Optional[threading.Thread] = None
        self._active_id: Optional[str] = None

    @staticmethod
    def _default_client() -> httpx.Client:
        return httpx.Client(follow_redirects=True, timeout=DEFAULT_HTTP_TIMEOUT)

    # -- queries ---------------------------------------------------------
    def active_model_id(self) -> Optional[str]:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return self._active_id
            return None

    def progress_for(self, model_id: str) -> DownloadProgress:
        with self._lock:
            existing = self._progress.get(model_id)
            if existing is not None:
                return existing
            installed = self.store.is_installed(model_id)
            return DownloadProgress(
                model_id=model_id,
                state=DownloadState.COMPLETED if installed else DownloadState.IDLE,
                bytes_downloaded=self.store.installed_size(model_id) or 0,
                total_bytes=self.store.installed_size(model_id) or 0,
            )

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {
                model_id: progress.as_dict()
                for model_id, progress in self._progress.items()
            }

    # -- control ---------------------------------------------------------
    def start(self, model_id: str) -> DownloadProgress:
        """Begin a download. Rejects unknown ids and concurrent downloads."""
        option = get_model(model_id)
        if option is None:
            raise DownloadError(f'unknown model id: {model_id}')
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise DownloadError(
                    f'a download is already in progress ({self._active_id}); '
                    'wait for it to finish or cancel it first'
                )
            if self.store.is_installed(model_id):
                progress = DownloadProgress(
                    model_id=model_id,
                    state=DownloadState.COMPLETED,
                    bytes_downloaded=self.store.installed_size(model_id) or 0,
                    total_bytes=self.store.installed_size(model_id) or 0,
                )
                self._progress[model_id] = progress
                return progress
            cancel_event = threading.Event()
            self._cancel_events[model_id] = cancel_event
            self._progress[model_id] = DownloadProgress(
                model_id=model_id,
                state=DownloadState.DOWNLOADING,
                total_bytes=option.size_bytes,
            )
            self._active_id = model_id
            thread = threading.Thread(
                target=self._run,
                args=(option, cancel_event),
                daemon=True,
                name=f'model-download-{model_id}',
            )
            self._thread = thread
            thread.start()
            return self._progress[model_id]

    def cancel(self, model_id: str) -> DownloadProgress:
        with self._lock:
            event = self._cancel_events.get(model_id)
            if event is None or (self._thread is not None and not self._thread.is_alive()):
                return self.progress_for(model_id)
            event.set()
            return self._progress.get(
                model_id, self.progress_for(model_id)
            )

    def join(self, timeout: Optional[float] = None) -> None:
        """Wait for the active download thread (used by tests/shutdown)."""
        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout)

    # -- worker ----------------------------------------------------------
    def _set(self, model_id: str, **changes: Any) -> DownloadProgress:
        with self._lock:
            progress = self._progress.get(model_id) or DownloadProgress(
                model_id=model_id, state=DownloadState.IDLE)
            for key, value in changes.items():
                setattr(progress, key, value)
            self._progress[model_id] = progress
            return progress

    def _run(self, option: ModelOption, cancel_event: threading.Event) -> None:
        model_id = option.id
        target = self.store.target_path(model_id)
        if target is None:  # pragma: no cover - guarded by start()
            self._set(model_id, state=DownloadState.ERROR, error='unknown model id')
            return
        part = target.with_name(target.name + '.part')
        self.store.ensure_dir()
        try:
            self._download(option, target, part, cancel_event)
        except _Cancelled:
            self._safe_unlink(part)
            self._set(model_id, state=DownloadState.CANCELLED, error='')
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            self._safe_unlink(part)
            logger.warning('model download failed for %s: %s', model_id, exc)
            self._set(model_id, state=DownloadState.ERROR, error=str(exc) or 'download failed')
        finally:
            with self._lock:
                if self._active_id == model_id:
                    self._active_id = None

    def _download(
        self,
        option: ModelOption,
        target: Path,
        part: Path,
        cancel_event: threading.Event,
    ) -> None:
        model_id = option.id
        self._safe_unlink(part)
        downloaded = 0
        total = option.size_bytes
        cap = option.size_bytes + MAX_EXTRA_BYTES
        client = self._client_factory()
        try:
            with client.stream('GET', option.download_url) as response:
                response.raise_for_status()
                header_length = response.headers.get('content-length')
                if header_length and header_length.isdigit():
                    total = int(header_length)
                with open(part, 'wb') as handle:
                    first_chunk = True
                    for chunk in response.iter_bytes(self._chunk_size):
                        if cancel_event.is_set():
                            raise _Cancelled()
                        if not chunk:
                            continue
                        if first_chunk:
                            if not chunk.startswith(GGUF_MAGIC):
                                raise DownloadError(
                                    'downloaded file is not a GGUF model '
                                    '(missing GGUF header)'
                                )
                            first_chunk = False
                        downloaded += len(chunk)
                        if downloaded > cap:
                            raise DownloadError(
                                'download exceeded the expected size limit'
                            )
                        handle.write(chunk)
                        self._set(
                            model_id,
                            state=DownloadState.DOWNLOADING,
                            bytes_downloaded=downloaded,
                            total_bytes=total,
                        )
        finally:
            try:
                client.close()
            except Exception:
                pass

        if cancel_event.is_set():
            raise _Cancelled()
        if downloaded == 0:
            raise DownloadError('download returned no data')

        self._set(
            model_id,
            state=DownloadState.VERIFYING,
            bytes_downloaded=downloaded,
            total_bytes=total,
        )
        part.replace(target)
        self.store.record_installed(model_id, option)
        self._set(
            model_id,
            state=DownloadState.COMPLETED,
            bytes_downloaded=downloaded,
            total_bytes=total,
            error='',
        )

    @staticmethod
    def _safe_unlink(path: Path) -> None:
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass


class _Cancelled(Exception):
    """Internal signal: the caller cancelled the download."""
