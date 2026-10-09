"""Configuration for the managed local (llama.cpp) inference runtime.

Every value comes from an environment variable with a safe default. No API key
is required and no value ever becomes a shell string: the runtime turns these
fields into a validated argument list for a loopback-only server.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import Mapping, Optional

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 8080
DEFAULT_N_CTX = 4096
DEFAULT_MAX_OUTPUT_TOKENS = 512
DEFAULT_STARTUP_TIMEOUT = 180.0
DEFAULT_GENERATION_TIMEOUT = 120.0
DEFAULT_MODELS_DIR = '/app/data/models'
SERVER_BINARY_NAME = 'llama-server'

_TRUE_VALUES = {'1', 'true', 'yes', 'on'}
_FALSE_VALUES = {'0', 'false', 'no', 'off'}


class LocalLlmConfigError(ValueError):
    """Raised when an environment value is present but invalid."""


def _parse_bool(value: Optional[str], default: bool) -> bool:
    if value is None or not str(value).strip():
        return default
    normalized = str(value).strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise LocalLlmConfigError(f'invalid boolean value: {value!r}')


def _parse_int(value: Optional[str], default: int, *, name: str,
               minimum: int = 1, maximum: Optional[int] = None) -> int:
    if value is None or not str(value).strip():
        return default
    try:
        parsed = int(str(value).strip())
    except ValueError as exc:
        raise LocalLlmConfigError(f'{name} must be an integer, got {value!r}') from exc
    if parsed < minimum or (maximum is not None and parsed > maximum):
        bounds = f'{minimum}..{maximum}' if maximum is not None else f'>= {minimum}'
        raise LocalLlmConfigError(f'{name} must be in range {bounds}, got {parsed}')
    return parsed


def _parse_float(value: Optional[str], default: float, *, name: str,
                 minimum: float = 1.0) -> float:
    if value is None or not str(value).strip():
        return default
    try:
        parsed = float(str(value).strip())
    except ValueError as exc:
        raise LocalLlmConfigError(f'{name} must be a number, got {value!r}') from exc
    if parsed < minimum:
        raise LocalLlmConfigError(f'{name} must be >= {minimum}, got {parsed}')
    return parsed


@dataclass(frozen=True)
class LocalLlmConfig:
    """Validated runtime settings; immutable so it can be shared safely."""

    enabled: bool = True
    model_path: str = ''
    server_bin: str = ''
    models_dir: str = DEFAULT_MODELS_DIR
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    n_ctx: int = DEFAULT_N_CTX
    n_threads: int = 0
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    startup_timeout: float = DEFAULT_STARTUP_TIMEOUT
    generation_timeout: float = DEFAULT_GENERATION_TIMEOUT

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> 'LocalLlmConfig':
        source = os.environ if env is None else env

        def raw(key: str) -> Optional[str]:
            return source.get(key)

        return cls(
            enabled=_parse_bool(raw('LOCAL_LLM_ENABLED'), True),
            model_path=(raw('LOCAL_LLM_MODEL_PATH') or '').strip(),
            server_bin=(raw('LOCAL_LLM_SERVER_BIN') or '').strip(),
            models_dir=(raw('LOCAL_LLM_MODELS_DIR') or '').strip() or DEFAULT_MODELS_DIR,
            host=(raw('LOCAL_LLM_HOST') or '').strip() or DEFAULT_HOST,
            port=_parse_int(raw('LOCAL_LLM_PORT'), DEFAULT_PORT,
                            name='LOCAL_LLM_PORT', minimum=1, maximum=65535),
            n_ctx=_parse_int(raw('LOCAL_LLM_N_CTX'), DEFAULT_N_CTX,
                             name='LOCAL_LLM_N_CTX', minimum=256),
            n_threads=_parse_int(raw('LOCAL_LLM_N_THREADS'), 0,
                                 name='LOCAL_LLM_N_THREADS', minimum=0, maximum=1024),
            max_output_tokens=_parse_int(
                raw('LOCAL_LLM_MAX_OUTPUT_TOKENS'), DEFAULT_MAX_OUTPUT_TOKENS,
                name='LOCAL_LLM_MAX_OUTPUT_TOKENS', minimum=1, maximum=8192),
            startup_timeout=_parse_float(
                raw('LOCAL_LLM_STARTUP_TIMEOUT'), DEFAULT_STARTUP_TIMEOUT,
                name='LOCAL_LLM_STARTUP_TIMEOUT'),
            generation_timeout=_parse_float(
                raw('LOCAL_LLM_GENERATION_TIMEOUT'), DEFAULT_GENERATION_TIMEOUT,
                name='LOCAL_LLM_GENERATION_TIMEOUT'),
        )

    @property
    def base_url(self) -> str:
        """OpenAI-compatible base URL (the `/v1` prefix the clients expect)."""
        return f'http://{self.host}:{self.port}/v1'

    @property
    def health_url(self) -> str:
        """llama-server exposes readiness at the server root, not under /v1."""
        return f'http://{self.host}:{self.port}/health'

    def model_available(self) -> bool:
        return bool(self.model_path) and os.path.isfile(self.model_path)

    def resolve_server_binary(self) -> Optional[str]:
        """Return the runtime binary path, or None when it cannot be found."""
        if self.server_bin:
            if os.path.isfile(self.server_bin):
                return self.server_bin
            return shutil.which(self.server_bin)
        return shutil.which(SERVER_BINARY_NAME)
