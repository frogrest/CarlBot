"""Deterministic tests for the managed local LLM runtime.

The runtime is exercised with an injected fake process, a fake clock, and an
`httpx.MockTransport` client, so no model is downloaded, no server is started,
and no real system is contacted.
"""
from __future__ import annotations

import threading

import httpx
import pytest

from services.local_llm import (
    LocalLlmConfig,
    LocalLlmConfigError,
    LocalLlmError,
    LocalLlmRuntime,
    LocalLlmState,
    RuntimeBusyError,
    resolve_endpoint,
)
from services.local_llm.client import DEFAULT_LOCAL_MODEL_NAME


class FakeProcess:
    def __init__(self, exit_code=None, pid=4321):
        self._exit_code = exit_code
        self.pid = pid
        self.stdout = None
        self.terminated = False
        self.killed = False
        self.argv = []

    def poll(self):
        return self._exit_code

    def terminate(self):
        self.terminated = True
        if self._exit_code is None:
            self._exit_code = 0

    def kill(self):
        self.killed = True
        self._exit_code = -9

    def wait(self, timeout=None):
        return self._exit_code


class FakeClock:
    """Monotonic clock whose `sleep` advances time, so startup can time out fast."""

    def __init__(self, start=0.0, step=0.5):
        self._now = start
        self._step = step

    def monotonic(self):
        return self._now

    def sleep(self, seconds):
        self._now += max(seconds, self._step)


def _health_ok(_request):
    return httpx.Response(200, json={'status': 'ok'})


def _ready_runtime(tmp_path, handler=None, *, exit_code=None, clock=None, **overrides):
    """Build a runtime whose fake binary/model exist and whose server is faked."""
    model = tmp_path / 'model.gguf'
    model.write_bytes(b'GGUF')
    binary = tmp_path / 'llama-server'
    binary.write_bytes(b'bin')

    config = LocalLlmConfig(
        enabled=True,
        model_path=str(model),
        server_bin=str(binary),
        port=overrides.pop('port', 8123),
        startup_timeout=overrides.pop('startup_timeout', 2.0),
        max_output_tokens=overrides.pop('max_output_tokens', 128),
        **overrides,
    )
    clock = clock or FakeClock()
    processes: list[FakeProcess] = []

    def popen(argv, **_kwargs):
        process = FakeProcess(exit_code=exit_code)
        process.argv = argv
        processes.append(process)
        return process

    transport = httpx.MockTransport(handler or _health_ok)
    runtime = LocalLlmRuntime(
        config,
        popen=popen,
        client=httpx.Client(transport=transport),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )
    return runtime, processes


# -- configuration ---------------------------------------------------------
def test_disabled_runtime_reports_disabled():
    runtime = LocalLlmRuntime(LocalLlmConfig(enabled=False))
    status = runtime.status()
    assert status.state is LocalLlmState.DISABLED
    assert status.ready is False


def test_missing_model_reports_actionable_instructions(tmp_path):
    runtime = LocalLlmRuntime(
        LocalLlmConfig(enabled=True, model_path='', server_bin=''),
        client=httpx.Client(transport=httpx.MockTransport(_health_ok)),
    )
    status = runtime.ensure_started()
    assert status.state is LocalLlmState.MODEL_NOT_CONFIGURED
    assert status.instructions
    assert any('LOCAL_LLM_MODEL_PATH' in line for line in status.instructions)


def test_missing_runtime_reports_instructions(tmp_path):
    model = tmp_path / 'model.gguf'
    model.write_bytes(b'GGUF')
    runtime = LocalLlmRuntime(
        LocalLlmConfig(enabled=True, model_path=str(model),
                       server_bin='carlbot-no-such-binary-xyz'),
        client=httpx.Client(transport=httpx.MockTransport(_health_ok)),
    )
    status = runtime.ensure_started()
    assert status.state is LocalLlmState.RUNTIME_MISSING
    assert any('llama-server' in line for line in status.instructions)


@pytest.mark.parametrize('env', [
    {'LOCAL_LLM_PORT': 'not-a-port'},
    {'LOCAL_LLM_PORT': '70000'},
    {'LOCAL_LLM_MAX_OUTPUT_TOKENS': '0'},
    {'LOCAL_LLM_ENABLED': 'maybe'},
    {'LOCAL_LLM_STARTUP_TIMEOUT': '-5'},
])
def test_invalid_env_values_are_rejected(env):
    with pytest.raises(LocalLlmConfigError):
        LocalLlmConfig.from_env(env)


def test_invalid_env_does_not_crash_from_env(monkeypatch):
    monkeypatch.setenv('LOCAL_LLM_PORT', '99999')
    runtime = LocalLlmRuntime.from_env()
    status = runtime.status()
    assert status.state is LocalLlmState.ERROR
    assert 'LOCAL_LLM_PORT' in status.detail


# -- startup lifecycle -----------------------------------------------------
def test_ensure_started_becomes_ready_and_starts_once(tmp_path):
    runtime, processes = _ready_runtime(tmp_path)

    first = runtime.ensure_started()
    second = runtime.ensure_started()

    assert first.state is LocalLlmState.READY and first.ready is True
    assert second.state is LocalLlmState.READY
    assert len(processes) == 1
    argv = processes[0].argv
    assert argv[0].endswith('llama-server')
    assert argv[1:3] == ['-m', runtime.config.model_path]
    assert '--host' in argv and '127.0.0.1' in argv
    assert '-ngl' in argv and '0' in argv


def test_startup_timeout_reports_error_and_terminates(tmp_path):
    def handler(_request):
        return httpx.Response(503, json={'status': 'loading'})

    clock = FakeClock(step=0.5)
    runtime, processes = _ready_runtime(
        tmp_path, handler=handler, clock=clock, startup_timeout=1.0)

    status = runtime.ensure_started()

    assert status.state is LocalLlmState.ERROR
    assert 'timeout' in status.detail
    assert runtime.status().ready is False
    assert processes[0].terminated is True


def test_runtime_crash_is_reported(tmp_path):
    runtime, _processes = _ready_runtime(tmp_path, exit_code=1)
    status = runtime.ensure_started()
    assert status.state is LocalLlmState.ERROR
    assert 'exited with code 1' in status.detail


def test_stop_terminates_process_and_clears_ready(tmp_path):
    runtime, processes = _ready_runtime(tmp_path)
    assert runtime.ensure_started().ready is True

    runtime.stop()

    assert processes[0].terminated is True
    assert runtime.status().ready is False


# -- generation ------------------------------------------------------------
def _capturing_handler(requests, *, content='hello', status=200, body=None):
    def handler(request):
        requests.append(request)
        if request.url.path.endswith('/health'):
            return httpx.Response(200, json={'status': 'ok'})
        if body is not None:
            return httpx.Response(status, json=body)
        return httpx.Response(status, json={
            'choices': [{'message': {'content': content}}],
        })
    return handler


def test_generate_bounds_output_tokens(tmp_path):
    import json

    requests = []
    runtime, _ = _ready_runtime(tmp_path, handler=_capturing_handler(requests))
    runtime.ensure_started()

    runtime.generate([{'role': 'user', 'content': 'hi'}], max_tokens=99999)
    payload = json.loads(requests[-1].content)
    assert payload['max_tokens'] == runtime.config.max_output_tokens

    runtime.generate([{'role': 'user', 'content': 'hi'}], max_tokens=10)
    payload = json.loads(requests[-1].content)
    assert payload['max_tokens'] == 10


def test_generate_rejected_when_not_ready(tmp_path):
    runtime = LocalLlmRuntime(
        LocalLlmConfig(enabled=True, model_path='', server_bin=''),
        client=httpx.Client(transport=httpx.MockTransport(_health_ok)),
    )
    with pytest.raises(LocalLlmError):
        runtime.generate([{'role': 'user', 'content': 'hi'}])


def test_generate_returns_model_text(tmp_path):
    runtime, _ = _ready_runtime(tmp_path, handler=_capturing_handler([], content='answer'))
    runtime.ensure_started()
    assert runtime.generate([{'role': 'user', 'content': 'hi'}]) == 'answer'


def test_malformed_generation_output_is_rejected(tmp_path):
    runtime, _ = _ready_runtime(
        tmp_path, handler=_capturing_handler([], body={'unexpected': True}))
    runtime.ensure_started()
    with pytest.raises(LocalLlmError):
        runtime.generate([{'role': 'user', 'content': 'hi'}])


def test_concurrent_generation_is_rejected(tmp_path):
    started = threading.Event()
    release = threading.Event()

    def handler(request):
        if request.url.path.endswith('/health'):
            return httpx.Response(200, json={'status': 'ok'})
        started.set()
        release.wait(timeout=5)
        return httpx.Response(200, json={
            'choices': [{'message': {'content': 'ok'}}],
        })

    runtime, _ = _ready_runtime(tmp_path, handler=handler)
    runtime.ensure_started()

    failures: list[Exception] = []

    def run():
        try:
            runtime.generate([{'role': 'user', 'content': 'one'}])
        except Exception as exc:  # pragma: no cover - defensive
            failures.append(exc)

    thread = threading.Thread(target=run)
    thread.start()
    assert started.wait(timeout=5)

    with pytest.raises(RuntimeBusyError):
        runtime.generate([{'role': 'user', 'content': 'two'}])

    release.set()
    thread.join(timeout=5)
    assert failures == []


# -- endpoint resolution ---------------------------------------------------
def test_resolve_endpoint_prefers_ready_runtime(tmp_path):
    runtime, _ = _ready_runtime(tmp_path)
    runtime.ensure_started()

    base_url, model = resolve_endpoint(runtime=runtime, env={'LLM_BASE_URL': 'https://external/v1'})

    assert base_url == runtime.config.base_url
    assert model == DEFAULT_LOCAL_MODEL_NAME


def test_resolve_endpoint_falls_back_to_external_when_not_ready(tmp_path):
    runtime = LocalLlmRuntime(
        LocalLlmConfig(enabled=True, model_path='', server_bin=''),
        client=httpx.Client(transport=httpx.MockTransport(_health_ok)),
    )
    base_url, model = resolve_endpoint(
        runtime=runtime,
        env={'LLM_BASE_URL': 'https://external/v1', 'LLM_MODEL': 'external-model'},
    )
    assert base_url == 'https://external/v1'
    assert model == 'external-model'


def test_resolve_endpoint_empty_without_any_configuration():
    assert resolve_endpoint(env={}) == ('', '')


# -- helpdesk wiring -------------------------------------------------------
def test_helpdesk_llm_status_endpoint(helpdesk):
    response = helpdesk.get('/api/llm/status')
    assert response.status_code == 200
    body = response.json()
    assert body['state'] == 'disabled'
    assert body['ready'] is False
    assert set(body) >= {'state', 'ready', 'detail', 'model_path', 'instructions'}


def test_helpdesk_llm_start_is_idempotent(helpdesk):
    first = helpdesk.post('/api/llm/start')
    second = helpdesk.post('/api/llm/start')
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()['state'] == 'disabled'


def test_chat_still_works_without_a_model(helpdesk):
    response = helpdesk.post('/api/chat/query', json={'message': 'hello'})
    assert response.status_code == 200
    body = response.json()
    assert body['reasoning_mode'] == 'deterministic'


def test_agent_llm_status_and_start_are_bounded(agent_main):
    status = agent_main.llm_status()
    assert status['state'] == 'disabled'
    assert status['ready'] is False
    assert agent_main.llm_start()['state'] == 'disabled'
