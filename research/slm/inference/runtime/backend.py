"""Backend abstraction for SLM inference.

Any runtime (PyTorch, llama.cpp-style GGUF, ONNX Runtime) sits behind the
same `Backend` protocol so callers (e.g. the StationLMProvider decision
model) never see backend-specific details.

A backend is selected from an export manifest via `load_backend(manifest)`.
The manifest is the JSON document produced by `research.slm.inference.export`;
its `backend` field selects the implementation.
"""

from __future__ import annotations

import json
import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

MANIFEST_SCHEMA_VERSION = "1.0"


@dataclass
class DecodingConfig:
    """Sampling parameters for text generation."""

    max_new_tokens: int = 32
    temperature: float = 1.0
    top_k: int = 0  # 0 disables top-k filtering
    top_p: float = 1.0  # 1.0 disables nucleus filtering
    seed: int | None = None  # per-request seed; None = nondeterministic
    stop_tokens: list[int] = field(default_factory=list)


@dataclass
class BackendCapabilities:
    """Self-reported capabilities of a loaded backend."""

    backend: str  # e.g. "pytorch", "gguf", "onnx"
    context_length: int
    quantization: str  # e.g. "fp32", "fp16", "bf16", "int8-dynamic"
    device: str  # e.g. "cpu", "cuda:0"
    vocab_size: int = 0
    parameter_count: int = 0
    supports_streaming: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Backend(Protocol):
    """Minimal inference backend contract.

    Implementations must be loadable from an export manifest, generate
    token continuations, and report their capabilities. Tokenizers are
    deliberately out of scope: callers pass and receive token id lists.
    """

    def load(self, manifest: dict[str, Any]) -> None:
        """Load model artifacts referenced by the export manifest."""
        ...

    def generate(
        self, tokens: Sequence[int], decoding: DecodingConfig
    ) -> list[int]:
        """Return newly generated token ids (prompt tokens not included)."""
        ...

    def metadata(self) -> BackendCapabilities:
        """Report capabilities of the currently loaded model."""
        ...


def load_manifest(path: str) -> dict[str, Any]:
    """Read and minimally validate an export manifest JSON file."""
    with open(path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported manifest schema_version "
            f"{manifest.get('schema_version')!r}; expected {MANIFEST_SCHEMA_VERSION!r}"
        )
    if "backend" not in manifest or "artifacts" not in manifest:
        raise ValueError("manifest missing required 'backend' or 'artifacts' fields")
    return manifest


def load_backend(manifest: dict[str, Any] | str) -> Backend:
    """Instantiate and load the backend named by the manifest.

    Accepts either a manifest dict or a path to a manifest JSON file.
    This is the single entry point callers use; swapping backends is a
    manifest change only.
    """
    if isinstance(manifest, str):
        manifest = load_manifest(manifest)
    name = manifest["backend"]
    if name == "pytorch":
        from .pytorch_backend import PyTorchBackend

        backend: Backend = PyTorchBackend()
    elif name == "gguf":
        from .gguf_backend import GgufBackend

        backend = GgufBackend()
    elif name == "onnx":
        from .onnx_backend import OnnxBackend

        backend = OnnxBackend()
    else:
        raise ValueError(f"unknown backend {name!r} in manifest")
    backend.load(manifest)
    return backend


def sample_next_token(
    logits: Sequence[float], decoding: DecodingConfig, rng: random.Random
) -> int:
    """Sample one token from logits given temperature/top-k/top-p.

    Pure-Python so every backend shares identical sampling semantics.
    """
    import math

    temperature = max(decoding.temperature, 1e-6)
    scaled = [v / temperature for v in logits]
    ranked = sorted(enumerate(scaled), key=lambda kv: kv[1], reverse=True)
    if decoding.top_k and decoding.top_k > 0:
        ranked = ranked[: decoding.top_k]
    if decoding.top_p < 1.0:
        keep: list[tuple[int, float]] = []
        running = 0.0
        total = sum(math.exp(v - ranked[0][1]) for _, v in ranked)
        for idx, v in ranked:
            running += math.exp(v - ranked[0][1]) / total
            keep.append((idx, v))
            if running >= decoding.top_p:
                break
        ranked = keep
    peak = ranked[0][1]
    weights = [math.exp(v - peak) for _, v in ranked]
    total_w = sum(weights)
    pick = rng.random() * total_w
    acc = 0.0
    for (idx, _), w in zip(ranked, weights):
        acc += w
        if pick <= acc:
            return idx
    return ranked[-1][0]
