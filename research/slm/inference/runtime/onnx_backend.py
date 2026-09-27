"""ONNX Runtime backend (documented stub).

Intended target: `onnxruntime` running an exported NanoLM graph. This is
a deliberate placeholder for the same reasons as the GGUF stub: no
trained weights exist, and the ONNX export op-set/static-shape contract
for the scaffold (learned positional embeddings, tied head) still needs
to be frozen.

Planned wiring:
  * artifact: `artifacts.model` -> path to a `.onnx` file
  * quantization: "fp32", "fp16", or "int8-dynamic" (ORT dynamic
    quantization of MatMul-heavy graphs)
  * load(): `onnxruntime.InferenceSession(path, providers=["CPUExecutionProvider"])`
  * generate(): run the session per step over a rolling token window and
    sample with the shared `runtime.backend.sample_next_token` so
    decoding semantics match the PyTorch backend exactly
  * metadata(): context length from the graph's sequence input bound,
    device "cpu"

The class raises NotImplementedError on load so manifests cannot
silently select an unimplemented backend.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .backend import BackendCapabilities, DecodingConfig


class OnnxBackend:
    """Stub for an ONNX Runtime backend. Not yet implemented."""

    def load(self, manifest: dict[str, Any]) -> None:
        """Reject loads until the ONNX export path is defined."""
        raise NotImplementedError(
            "OnnxBackend is a stub: the NanoLM ONNX export op-set contract "
            "and a pinned onnxruntime dependency are required first. See "
            "module docstring."
        )

    def generate(
        self, tokens: Sequence[int], decoding: DecodingConfig
    ) -> list[int]:
        raise NotImplementedError("OnnxBackend is a stub")

    def metadata(self) -> BackendCapabilities:
        raise NotImplementedError("OnnxBackend is a stub")
