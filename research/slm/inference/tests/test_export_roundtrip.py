"""Export -> reload round-trip tests on tiny randomly-initialized configs."""

import os

import torch

from research.slm.inference.export.export import (
    build_model_from_config,
    export_model,
)
from research.slm.inference.runtime.backend import load_backend
from research.slm.inference.runtime.scaffold_import import NanoLM

TINY_CONFIG = os.path.join(os.path.dirname(__file__), "tiny-config.yaml")
SEED = 1234


def _logits(model: NanoLM, tokens: list[int]) -> torch.Tensor:
    idx = torch.tensor([tokens], dtype=torch.long)
    with torch.no_grad():
        logits, _ = model.eval()(idx)
    return logits


def test_fp32_roundtrip_identical_logits(tmp_path):
    """FP32 export -> reload must reproduce logits exactly."""
    model, raw = build_model_from_config(TINY_CONFIG, seed=SEED)
    tokens = [1, 5, 9, 13, 17]
    before = _logits(model, tokens)

    manifest_path = export_model(
        model=model,
        source_config=raw.get("model") or raw,
        training_config=None,
        dtype="fp32",
        output_dir=str(tmp_path),
        code_commit="test-commit",
        seed=SEED,
    )
    backend = load_backend(manifest_path)
    after = _logits(backend.model, tokens)  # type: ignore[attr-defined]
    assert torch.equal(before, after)


def test_int8_export_runs(tmp_path):
    """INT8 dynamic export must load and generate through the backend."""
    model, raw = build_model_from_config(TINY_CONFIG, seed=SEED)
    manifest_path = export_model(
        model=model,
        source_config=raw.get("model") or raw,
        training_config=None,
        dtype="int8-dynamic",
        output_dir=str(tmp_path),
        code_commit="test-commit",
        seed=SEED,
    )
    backend = load_backend(manifest_path)
    caps = backend.metadata()
    assert caps.backend == "pytorch"
    assert caps.quantization == "int8-dynamic"
    assert caps.device == "cpu"
    assert caps.context_length == 32


def test_half_precision_exports_load(tmp_path):
    """FP16 and BF16 exports must load and report their dtype."""
    model, raw = build_model_from_config(TINY_CONFIG, seed=SEED)
    for dtype in ("fp16", "bf16"):
        out = tmp_path / dtype
        manifest_path = export_model(
            model=model,
            source_config=raw.get("model") or raw,
            training_config=None,
            dtype=dtype,
            output_dir=str(out),
            code_commit="test-commit",
            seed=SEED,
        )
        backend = load_backend(manifest_path)
        assert backend.metadata().quantization == dtype
