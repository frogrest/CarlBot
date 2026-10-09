"""Curated catalog of compatible local GGUF instruct models.

CarlBot only ever downloads a model from this fixed, allow-listed list. There is
no arbitrary-URL input anywhere: the UI picks an `id`, and the backend resolves
the filename and download location from the entry below. That keeps the managed
runtime from becoming a general-purpose downloader.

Every `download_url` here was verified to resolve (HTTP 200) and the
`size_bytes` value matches the served `Content-Length` at the time of writing.
Sizes are approximate snapshots of a specific quantization, not a guarantee —
the runtime always trusts the actual file on disk. The operators remain
responsible for each model's license and terms of use.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional

GIB = 1024 ** 3


@dataclass(frozen=True)
class ModelOption:
    """One downloadable GGUF instruct model."""

    id: str
    display_name: str
    family: str
    parameters: str
    quantization: str
    filename: str
    size_bytes: int
    license: str
    repo: str
    download_url: str
    context_window: int
    min_ram_gb: int
    summary: str
    recommended: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# 4-bit Q4_K_M quantization is the CPU-inference baseline recommended in
# LOCAL_LLM_SETUP.md. Ordering: smallest first so the UI reads naturally.
CATALOG: tuple[ModelOption, ...] = (
    ModelOption(
        id='qwen2.5-3b-instruct-q4',
        display_name='Qwen2.5 3B Instruct',
        family='Qwen2.5',
        parameters='3B',
        quantization='Q4_K_M',
        filename='Qwen2.5-3B-Instruct-Q4_K_M.gguf',
        size_bytes=1929903264,
        license='Apache-2.0',
        repo='bartowski/Qwen2.5-3B-Instruct-GGUF',
        download_url=(
            'https://huggingface.co/bartowski/Qwen2.5-3B-Instruct-GGUF/'
            'resolve/main/Qwen2.5-3B-Instruct-Q4_K_M.gguf'
        ),
        context_window=32768,
        min_ram_gb=4,
        summary=(
            'Lightweight general-purpose instruct model. The safest choice for '
            '8 GB machines or when you want fast CPU responses.'
        ),
    ),
    ModelOption(
        id='gemma-2-2b-it-q4',
        display_name='Gemma 2 2B IT',
        family='Gemma 2',
        parameters='2B',
        quantization='Q4_K_M',
        filename='gemma-2-2b-it-Q4_K_M.gguf',
        size_bytes=1708582752,
        license='Gemma Terms of Use',
        repo='bartowski/gemma-2-2b-it-GGUF',
        download_url=(
            'https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/'
            'resolve/main/gemma-2-2b-it-Q4_K_M.gguf'
        ),
        context_window=8192,
        min_ram_gb=4,
        summary=(
            'Very small instruction-tuned model. Good for quick offline replies '
            'when RAM is tight; shorter context than the Qwen options.'
        ),
    ),
    ModelOption(
        id='llama-3.2-3b-instruct-q4',
        display_name='Llama 3.2 3B Instruct',
        family='Llama 3.2',
        parameters='3B',
        quantization='Q4_K_M',
        filename='Llama-3.2-3B-Instruct-Q4_K_M.gguf',
        size_bytes=2019377696,
        license='Llama 3.2 Community License',
        repo='bartowski/Llama-3.2-3B-Instruct-GGUF',
        download_url=(
            'https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/'
            'resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf'
        ),
        context_window=131072,
        min_ram_gb=4,
        summary=(
            'Meta instruction-tuned model with a long context window and solid '
            'instruction following for its size.'
        ),
    ),
    ModelOption(
        id='phi-3.5-mini-instruct-q4',
        display_name='Phi-3.5 Mini Instruct',
        family='Phi-3.5',
        parameters='3.8B',
        quantization='Q4_K_M',
        filename='Phi-3.5-mini-instruct-Q4_K_M.gguf',
        size_bytes=2393232672,
        license='MIT',
        repo='bartowski/Phi-3.5-mini-instruct-GGUF',
        download_url=(
            'https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/'
            'resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf'
        ),
        context_window=131072,
        min_ram_gb=5,
        summary=(
            'Compact reasoning-focused model under a permissive MIT license. '
            'Strong at short technical explanations.'
        ),
    ),
    ModelOption(
        id='qwen2.5-7b-instruct-q4',
        display_name='Qwen2.5 7B Instruct',
        family='Qwen2.5',
        parameters='7B',
        quantization='Q4_K_M',
        filename='Qwen2.5-7B-Instruct-Q4_K_M.gguf',
        size_bytes=4683074240,
        license='Apache-2.0',
        repo='bartowski/Qwen2.5-7B-Instruct-GGUF',
        download_url=(
            'https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/'
            'resolve/main/Qwen2.5-7B-Instruct-Q4_K_M.gguf'
        ),
        context_window=32768,
        min_ram_gb=8,
        summary=(
            'The recommended baseline for this lab: the best quality/speed '
            'balance for 16-32 GB machines running CPU inference.'
        ),
        recommended=True,
    ),
    ModelOption(
        id='llama-3.1-8b-instruct-q4',
        display_name='Llama 3.1 8B Instruct',
        family='Llama 3.1',
        parameters='8B',
        quantization='Q4_K_M',
        filename='Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf',
        size_bytes=4920739232,
        license='Llama 3.1 Community License',
        repo='bartowski/Meta-Llama-3.1-8B-Instruct-GGUF',
        download_url=(
            'https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/'
            'resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf'
        ),
        context_window=131072,
        min_ram_gb=8,
        summary=(
            'Largest option here. Best quality, slowest on CPU, and needs the '
            'most RAM — pick it only if you have headroom to spare.'
        ),
    ),
)

_BY_ID = {option.id: option for option in CATALOG}


def get_model(model_id: str) -> Optional[ModelOption]:
    """Return the catalog entry for `model_id`, or None when it is unknown."""
    return _BY_ID.get(model_id)


def catalog_dicts() -> list[dict[str, Any]]:
    return [option.as_dict() for option in CATALOG]
