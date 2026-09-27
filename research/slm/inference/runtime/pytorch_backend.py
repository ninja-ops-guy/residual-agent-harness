"""PyTorch backend: loads scaffold (NanoLM) export artifacts.

Supports artifacts produced by `research.slm.inference.export` in any
of its dtypes: fp32, fp16, bf16, or int8-dynamic. CPU-first; a CUDA
device is used only if explicitly requested via the `SLM_DEVICE`
environment variable.
"""

from __future__ import annotations

import os
import random
from collections.abc import Sequence
from typing import Any

import torch

from .backend import BackendCapabilities, DecodingConfig, sample_next_token
from .scaffold_import import ModelConfig, NanoLM

_QUANTIZED_DTYPES = {"int8-dynamic"}


class PyTorchBackend:
    """Backend implementation running the scaffold NanoLM under PyTorch."""

    def __init__(self) -> None:
        self.model: torch.nn.Module | None = None
        self._capabilities: BackendCapabilities | None = None
        self._device = torch.device(os.environ.get("SLM_DEVICE", "cpu"))

    # ------------------------------------------------------------------
    def load(self, manifest: dict[str, Any]) -> None:
        """Load the model artifact referenced by the manifest."""
        artifact_path = manifest["artifacts"]["model"]
        quantization = manifest["artifacts"].get("quantization", "fp32")
        artifact = torch.load(artifact_path, map_location="cpu", weights_only=False)
        cfg = ModelConfig(**artifact["model_config"])
        model = NanoLM(cfg)
        if quantization in _QUANTIZED_DTYPES:
            model = torch.ao.quantization.quantize_dynamic(
                model, {torch.nn.Linear}, dtype=torch.qint8
            )
        else:
            dtype = {
                "fp32": torch.float32,
                "fp16": torch.float16,
                "bf16": torch.bfloat16,
            }.get(quantization)
            if dtype is None:
                raise ValueError(f"unsupported quantization {quantization!r}")
            model = model.to(dtype)
        model.load_state_dict(artifact["state_dict"])
        model.to(self._device)
        model.eval()
        self.model = model
        self._capabilities = BackendCapabilities(
            backend="pytorch",
            context_length=cfg.max_seq,
            quantization=quantization,
            device=str(self._device),
            vocab_size=cfg.vocab_size,
            parameter_count=sum(p.numel() for p in model.parameters()),
            supports_streaming=False,
            extra={
                "d_model": cfg.d_model,
                "n_layers": cfg.n_layers,
                "n_heads": cfg.n_heads,
                "tie_embeddings": cfg.tie_embeddings,
            },
        )

    # ------------------------------------------------------------------
    @torch.no_grad()
    def generate(
        self, tokens: Sequence[int], decoding: DecodingConfig
    ) -> list[int]:
        """Greedy/sampled autoregressive generation on token ids."""
        if self.model is None or self._capabilities is None:
            raise RuntimeError("backend not loaded; call load() first")
        rng = random.Random(decoding.seed)
        ctx = self._capabilities.context_length
        prompt = [int(t) for t in tokens][-ctx:]
        out: list[int] = []
        for _ in range(decoding.max_new_tokens):
            window = (prompt + out)[-ctx:]
            idx = torch.tensor([window], dtype=torch.long, device=self._device)
            logits, _ = self.model(idx)
            next_token = sample_next_token(
                logits[0, -1].float().cpu().tolist(), decoding, rng
            )
            out.append(next_token)
            if next_token in decoding.stop_tokens:
                break
        return out

    # ------------------------------------------------------------------
    def metadata(self) -> BackendCapabilities:
        """Capabilities of the loaded model."""
        if self._capabilities is None:
            raise RuntimeError("backend not loaded; call load() first")
        return self._capabilities
