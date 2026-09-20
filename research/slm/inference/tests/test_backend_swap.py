"""Backend-swap transparency: callers see only the Backend interface."""

import json
import os
from collections.abc import Sequence
from typing import Any

import pytest

from research.slm.inference.export.export import (
    build_model_from_config,
    export_model,
)
from research.slm.inference.runtime.backend import (
    Backend,
    BackendCapabilities,
    DecodingConfig,
    load_backend,
)
from research.slm.inference.runtime.gguf_backend import GgufBackend
from research.slm.inference.runtime.onnx_backend import OnnxBackend

TINY_CONFIG = os.path.join(os.path.dirname(__file__), "tiny-config.yaml")


class EchoBackend:
    """Trivial stand-in backend implementing the same interface."""

    def load(self, manifest: dict[str, Any]) -> None:
        self._caps = BackendCapabilities(
            backend="echo",
            context_length=manifest["artifacts"]["context_length"],
            quantization="none",
            device="cpu",
        )

    def generate(
        self, tokens: Sequence[int], decoding: DecodingConfig
    ) -> list[int]:
        return list(tokens)[: decoding.max_new_tokens]

    def metadata(self) -> BackendCapabilities:
        return self._caps


def caller_roundtrip(backend: Backend, tokens: list[int]) -> list[int]:
    """Canonical caller: identical code regardless of backend."""
    caps = backend.metadata()
    assert isinstance(caps, BackendCapabilities)
    decoding = DecodingConfig(max_new_tokens=4, temperature=0.0, seed=7)
    return backend.generate(tokens[-caps.context_length :], decoding)


def test_backend_swap_transparent_to_caller(tmp_path):
    """The same caller code works against the PyTorch backend and a stub."""
    model, raw = build_model_from_config(TINY_CONFIG, seed=99)
    manifest_path = export_model(
        model=model,
        source_config=raw.get("model") or raw,
        training_config=None,
        dtype="fp32",
        output_dir=str(tmp_path),
        code_commit="test-commit",
        seed=99,
    )
    pytorch_backend = load_backend(manifest_path)
    assert isinstance(pytorch_backend, Backend)  # runtime-checkable protocol

    tokens = [3, 1, 4, 1, 5]
    for backend in (pytorch_backend, _make_echo()):
        out = caller_roundtrip(backend, tokens)
        assert isinstance(out, list)
        assert 0 < len(out) <= 4
        assert all(isinstance(t, int) for t in out)


def _make_echo() -> EchoBackend:
    backend = EchoBackend()
    backend.load({"artifacts": {"context_length": 32}})
    return backend


def test_stub_backends_fail_loudly():
    """Documented GGUF/ONNX stubs must not silently pretend to work."""
    for cls in (GgufBackend, OnnxBackend):
        with pytest.raises(NotImplementedError):
            cls().load({"backend": cls.__name__, "artifacts": {}})


def test_manifest_rejects_unknown_backend(tmp_path):
    model, raw = build_model_from_config(TINY_CONFIG, seed=99)
    manifest_path = export_model(
        model=model,
        source_config=raw.get("model") or raw,
        training_config=None,
        dtype="fp32",
        output_dir=str(tmp_path),
        code_commit="test-commit",
        seed=99,
    )
    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    manifest["backend"] = "nonsense"
    with pytest.raises(ValueError, match="unknown backend"):
        load_backend(manifest)
