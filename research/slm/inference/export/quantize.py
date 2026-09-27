"""Quantization and dtype-conversion paths for export.

Supported today (proven on randomly-initialized tiny configs):
  * fp32  - reference round-trip dtype
  * fp16  - IEEE half precision
  * bf16  - bfloat16
  * int8-dynamic - torch dynamic quantization of nn.Linear weights

Lower-bit candidate path (documented, not implemented): GGUF-style
block-quantized formats via llama.cpp (q8_0 first candidate, then
q6_k / q4_k_m). These require a NanoLM->GGUF converter and a pinned
llama-cpp runtime; they are the intended deployment format for
Residual-Nano on ordinary CPU hosts once trained weights exist.
"""

from __future__ import annotations

import torch
from torch import nn

SUPPORTED_DTYPES = ("fp32", "fp16", "bf16", "int8-dynamic")

#: Documented candidates for the lower-bit export path. Order reflects
#: evaluation priority after the SLM-00 freeze lifts.
LOWER_BIT_CANDIDATES: tuple[dict[str, str], ...] = (
    {
        "format": "gguf-q8_0",
        "runtime": "llama.cpp",
        "note": "8-bit block quantization; expected near-lossless vs fp16, "
        "~1 byte/param. First candidate for Residual-Nano CPU deployment.",
    },
    {
        "format": "gguf-q6_k",
        "runtime": "llama.cpp",
        "note": "6-bit k-quant; ~0.75 byte/param, small quality loss.",
    },
    {
        "format": "gguf-q4_k_m",
        "runtime": "llama.cpp",
        "note": "4-bit k-quant; ~0.5 byte/param, needs quality eval on "
        "benchmark before adoption. Blocked on SLM-00 unfreeze.",
    },
)


def convert_dtype(model: nn.Module, dtype: str) -> nn.Module:
    """Return the model cast to fp16 or bf16 (fp32 is a no-op)."""
    if dtype == "fp32":
        return model
    if dtype == "fp16":
        return model.to(torch.float16)
    if dtype == "bf16":
        return model.to(torch.bfloat16)
    raise ValueError(f"convert_dtype does not handle {dtype!r}")


def quantize_dynamic_int8(model: nn.Module) -> nn.Module:
    """Apply torch dynamic INT8 quantization to all Linear layers.

    Weights are stored as qint8; activations stay float and are quantized
    per-batch at runtime. Note: when embeddings are tied, the quantized
    lm_head holds a dequantized copy of the shared weight - acceptable
    for test artifacts, to be revisited for production exports.
    """
    model = model.to(torch.float32)
    return torch.ao.quantization.quantize_dynamic(
        model, {nn.Linear}, dtype=torch.qint8
    )
