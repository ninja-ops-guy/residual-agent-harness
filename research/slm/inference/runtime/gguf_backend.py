"""GGUF backend (documented stub).

Intended target: llama.cpp-style runtimes loading a GGUF artifact via
`llama-cpp-python`. This backend is a deliberate placeholder: the export
path for GGUF requires a converter for the scaffold architecture
(NanoLM: learned positional embeddings, tied output head) that does not
yet exist, and no trained weights exist to validate against.

Planned wiring once the converter lands (see export/quantize.py,
`LOWER_BIT_CANDIDATES`):
  * artifact: `artifacts.model` -> path to a `.gguf` file
  * quantization: one of "q8_0", "q6_k", "q4_k_m"
  * load(): `llama_cpp.Llama(model_path=..., n_ctx=..., n_threads=...)`
  * generate(): prompt token ids -> `Llama.generate(...)` with the
    shared sampling semantics in `runtime.backend.sample_next_token`
    mirrored via llama.cpp sampling params (temp/top_k/top_p/seed)
  * metadata(): context length from `n_ctx()`, quantization from the
    manifest, device "cpu" (GGUF path is CPU-first by design)

The class raises NotImplementedError on load so manifests cannot
silently select an unimplemented backend.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .backend import BackendCapabilities, DecodingConfig


class GgufBackend:
    """Stub for a llama.cpp-style GGUF runtime. Not yet implemented."""

    def load(self, manifest: dict[str, Any]) -> None:
        """Reject loads until the GGUF export converter exists."""
        raise NotImplementedError(
            "GgufBackend is a stub: the NanoLM->GGUF converter and a pinned "
            "llama-cpp-python dependency are required first. See module "
            "docstring and export/quantize.py LOWER_BIT_CANDIDATES."
        )

    def generate(
        self, tokens: Sequence[int], decoding: DecodingConfig
    ) -> list[int]:
        raise NotImplementedError("GgufBackend is a stub")

    def metadata(self) -> BackendCapabilities:
        raise NotImplementedError("GgufBackend is a stub")
