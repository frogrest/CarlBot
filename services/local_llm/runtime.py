"""Managed local inference runtime (a `llama-server` child process).

The runtime owns the lifecycle of a loopback-only, OpenAI-compatible server so
the existing chat/agent clients keep working unchanged. It never builds a shell
command: arguments are a validated list, only one instance can exist per
process, and the child is reaped on shutdown.

The deterministic policy engine remains the security boundary; this module only
manages the model server and bounded generation.
"""

from __future__ import annotations

import dataclasses
import logging
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional, Sequence

import httpx

from .config import LocalLlmConfig, LocalLlmConfigError

logger = logging.getLogger(__name__)

_MISSING_MODEL_INSTRUCTIONS = (
    'Obtain a compatible GGUF instruct model from the provider '
    '(Qwen 7B-8B class, 4-bit quantized recommended).',
    'Set LOCAL_LLM_MODEL_PATH to the .gguf file path (see LOCAL_LLM_SETUP.md).',
    'Restart CarlBot or POST /api/llm/start to retry loading.',
)
_MISSING_RUNTIME_INSTRUCTIONS = (
    'Install the llama.cpp server binary (llama-server) and put it on PATH, '
    'or set LOCAL_LLM_SERVER_BIN to its path.',
    'Confirm the binary matches your platform; see LOCAL_LLM_SETUP.md.',
)


class LocalLlmState(str, Enum):
    DISABLED = 'disabled'
    RUNTIME_MISSING = 'runtime_missing'
    MODEL_NOT_CONFIGURED = 'model_not_configured'
    LOADING = 'loading'
    READY = 'ready'
    BUSY = 'busy'
    ERROR = 'error'


class LocalLlmError(RuntimeError):
    """Base error for the local runtime."""


class RuntimeBusyError(LocalLlmError):
    """Raised when a generation is already in flight."""


@dataclass(frozen=True)
class RuntimeStatus:
    """Truthful snapshot of the runtime/model state."""

    state: LocalLlmState
    ready: bool
    detail: str
    model_path: str = ''
    base_url: str = ''
    pid: Optional[int] = None
    instructions: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            'state': self.state.value,
            'ready': self.ready,
            'detail': self.detail,
            'model_path': self.model_path,
            'base_url': self.base_url,
            'pid': self.pid,
            'instructions': list(self.instructions),
        }


class LocalLlmRuntime:
    """Single-instance manager for a local `llama-server` process."""

    def __init__(
        self,
        config: LocalLlmConfig,
        *,
        popen: Optional[Callable[..., Any]] = None,
        client: Optional[httpx.Client] = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        poll_interval: float = 0.5,
        config_error: Optional[str] = None,
    ) -> None:
        self.config = config
        self._popen = popen or subprocess.Popen
        self._client = client
        self._owns_client = client is None
        self._sleep = sleep
        self._monotonic = monotonic
        self._poll_interval = poll_interval
        self._config_error = config_error
        self._lock = threading.RLock()
        self._generate_lock = threading.Lock()
        self._process: Any = None
        self._log_lines: deque[str] = deque(maxlen=40)
        self._state = self._initial_state()
        self._detail = config_error or ''

    # -- construction ----------------------------------------------------
    @classmethod
    def from_env(cls, store: Any = None, **kwargs: Any) -> 'LocalLlmRuntime':
        """Build from the environment without crashing on invalid values.

        When a `ModelStore` is supplied and it has a selected, installed model,
        that selection is used for the model path. The selection is the primary
        control (set from the UI); `LOCAL_LLM_MODEL_PATH` is the fallback for a
        fresh install with nothing selected yet.
        """
        try:
            config = LocalLlmConfig.from_env()
        except LocalLlmConfigError as exc:
            return cls(LocalLlmConfig(), config_error=str(exc), **kwargs)
        if store is not None:
            selected = store.selected_model_path()
            if selected:
                config = dataclasses.replace(config, model_path=selected)
        return cls(config, **kwargs)

    def _initial_state(self) -> LocalLlmState:
        if self._config_error:
            return LocalLlmState.ERROR
        if not self.config.enabled:
            return LocalLlmState.DISABLED
        if not self.config.model_available():
            return LocalLlmState.MODEL_NOT_CONFIGURED
        if self.config.resolve_server_binary() is None:
            return LocalLlmState.RUNTIME_MISSING
        return LocalLlmState.LOADING

    # -- introspection ---------------------------------------------------
    @property
    def is_ready(self) -> bool:
        return self.status().ready

    def status(self) -> RuntimeStatus:
        with self._lock:
            state = self._state
            if self._process is not None and state not in {LocalLlmState.DISABLED, LocalLlmState.ERROR}:
                code = self._process.poll()
                if code is not None:
                    state = LocalLlmState.ERROR
                    self._detail = self._crash_detail(code)
                    self._state = state
                    self._process = None
            return self._snapshot(state)

    def _snapshot(self, state: LocalLlmState) -> RuntimeStatus:
        detail = ''
        instructions: tuple[str, ...] = ()
        if state == LocalLlmState.DISABLED:
            detail = 'local inference is disabled (LOCAL_LLM_ENABLED=0)'
        elif state == LocalLlmState.MODEL_NOT_CONFIGURED:
            detail = 'no readable local model file is configured (LOCAL_LLM_MODEL_PATH)'
            instructions = _MISSING_MODEL_INSTRUCTIONS
        elif state == LocalLlmState.RUNTIME_MISSING:
            detail = 'the llama-server runtime binary could not be found'
            instructions = _MISSING_RUNTIME_INSTRUCTIONS
        elif state == LocalLlmState.LOADING:
            detail = 'local model is loading'
        elif state == LocalLlmState.READY:
            detail = 'local model loaded and ready'
        elif state == LocalLlmState.BUSY:
            detail = 'local model is busy generating'
        else:  # ERROR
            detail = self._detail or 'local runtime is in an error state'
        return RuntimeStatus(
            state=state,
            ready=state in {LocalLlmState.READY, LocalLlmState.BUSY},
            detail=detail,
            model_path=self.config.model_path,
            base_url=self.config.base_url if self.config.enabled else '',
            pid=self._process.pid if self._process is not None else None,
            instructions=instructions,
        )

    # -- lifecycle -------------------------------------------------------
    def ensure_started(self) -> RuntimeStatus:
        """Start the runtime once; safe and idempotent to call repeatedly."""
        with self._lock:
            if self._config_error:
                self._state = LocalLlmState.ERROR
                return self._snapshot(self._state)
            if not self.config.enabled:
                self._state = LocalLlmState.DISABLED
                return self._snapshot(self._state)
            if self._process is not None:
                code = self._process.poll()
                if code is None:
                    self._state = (
                        LocalLlmState.READY if self._health_check()
                        else LocalLlmState.LOADING
                    )
                    return self._snapshot(self._state)
                self._detail = self._crash_detail(code)
                self._process = None
                self._state = LocalLlmState.ERROR
                return self._snapshot(self._state)
            if not self.config.model_available():
                self._state = LocalLlmState.MODEL_NOT_CONFIGURED
                return self._snapshot(self._state)
            binary = self.config.resolve_server_binary()
            if binary is None:
                self._state = LocalLlmState.RUNTIME_MISSING
                return self._snapshot(self._state)
            self._spawn(binary)
            return self._await_ready()

    def _build_argv(self, binary: str) -> list[str]:
        cfg = self.config
        argv = [
            binary,
            '-m', cfg.model_path,
            '--host', cfg.host,
            '--port', str(cfg.port),
            '-c', str(cfg.n_ctx),
            '-ngl', '0',
            '--jinja',
        ]
        if cfg.n_threads:
            argv += ['-t', str(cfg.n_threads)]
        return argv

    def _spawn(self, binary: str) -> None:
        argv = self._build_argv(binary)
        self._state = LocalLlmState.LOADING
        self._detail = ''
        self._log_lines.clear()
        try:
            self._process = self._popen(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                shell=False,
            )
        except OSError as exc:
            self._process = None
            self._state = LocalLlmState.ERROR
            self._detail = f'failed to start the local runtime: {exc}'
            return
        self._start_drain()

    def _start_drain(self) -> None:
        stream = getattr(self._process, 'stdout', None)
        if stream is None:
            return

        def drain() -> None:
            try:
                for line in stream:
                    self._log_lines.append(str(line).rstrip('\n'))
            except (ValueError, OSError):
                pass

        thread = threading.Thread(target=drain, daemon=True, name='local-llm-log')
        thread.start()

    def _await_ready(self) -> RuntimeStatus:
        deadline = self._monotonic() + self.config.startup_timeout
        while True:
            if self._process is None:
                return self._snapshot(self._state)
            code = self._process.poll()
            if code is not None:
                self._detail = self._crash_detail(code)
                self._process = None
                self._state = LocalLlmState.ERROR
                return self._snapshot(self._state)
            if self._health_check():
                self._state = LocalLlmState.READY
                return self._snapshot(self._state)
            if self._monotonic() >= deadline:
                self._detail = 'local runtime did not become ready before the startup timeout'
                self._terminate_process()
                self._state = LocalLlmState.ERROR
                return self._snapshot(self._state)
            self._sleep(self._poll_interval)

    def _crash_detail(self, code: Any) -> str:
        tail = ' | '.join(list(self._log_lines)[-3:])
        detail = f'local runtime exited with code {code}'
        return f'{detail} (last output: {tail})' if tail else detail

    def _terminate_process(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        try:
            if process.poll() is not None:
                return
            process.terminate()
            try:
                process.wait(timeout=5)
            except Exception:
                process.kill()
                try:
                    process.wait(timeout=5)
                except Exception:
                    pass
        except OSError:
            pass

    # -- health / generation --------------------------------------------
    def _http_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=5.0)
            self._owns_client = True
        return self._client

    def _health_check(self) -> bool:
        try:
            response = self._http_client().get(self.config.health_url, timeout=2.0)
        except (httpx.HTTPError, OSError):
            return False
        if response.status_code != 200:
            return False
        try:
            payload = response.json()
        except ValueError:
            return False
        return isinstance(payload, dict) and payload.get('status') == 'ok'

    def health_check(self) -> bool:
        """Public readiness probe against the configured server."""
        with self._lock:
            return self._health_check()

    def generate(
        self,
        messages: Sequence[dict[str, str]],
        *,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """Run one bounded generation; only one may be in flight at a time."""
        with self._lock:
            status = self.ensure_started()
            if status.state not in {LocalLlmState.READY, LocalLlmState.BUSY}:
                raise LocalLlmError(
                    f'local runtime is not ready: {status.state.value} ({status.detail})'
                )
            if not self._generate_lock.acquire(blocking=False):
                self._state = LocalLlmState.BUSY
                raise RuntimeBusyError('a local generation is already in progress')
            self._state = LocalLlmState.BUSY
        try:
            limit = self.config.max_output_tokens
            if max_tokens is not None:
                limit = min(int(max_tokens), limit)
            payload = {
                'model': 'local',
                'messages': list(messages),
                'max_tokens': limit,
                'temperature': 0,
            }
            try:
                response = self._http_client().post(
                    f'{self.config.base_url}/chat/completions',
                    json=payload,
                    timeout=timeout or self.config.generation_timeout,
                )
                response.raise_for_status()
                body = response.json()
            except (httpx.HTTPError, ValueError, OSError) as exc:
                raise LocalLlmError('local generation request failed') from exc
        finally:
            with self._lock:
                self._state = LocalLlmState.READY
            self._generate_lock.release()
        try:
            return body['choices'][0]['message']['content']
        except (KeyError, IndexError, TypeError) as exc:
            raise LocalLlmError('local model returned malformed output') from exc

    def stop(self) -> None:
        """Terminate the child process and release the HTTP client."""
        with self._lock:
            self._terminate_process()
            if self._owns_client and self._client is not None:
                try:
                    self._client.close()
                except Exception:
                    pass
                self._client = None
            self._state = self._initial_state()
            self._detail = self._config_error or ''

    def close(self) -> None:
        self.stop()
