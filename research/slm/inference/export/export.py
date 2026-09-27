"""Export CLI: checkpoint/config -> quantized artifact + manifest.

Runs end-to-end on randomly-initialized tiny configs (no training, no
benchmarks, no real weights - pre-SLM-00-freeze machinery only).
All outputs are labeled `qualification: non-production-test-artifact`.

Examples:
  python -m inference.export.export --config configs/nano-30m.yaml \
      --dtype int8-dynamic --output-dir out/nano30m-int8

  python -m inference.export.export --checkpoint runs/x/ckpt.pt \
      --dtype fp32 --output-dir out/x-fp32 --code-commit $(git rev-parse HEAD)
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import torch

from ..runtime.scaffold_import import ModelConfig, NanoLM
from .manifest import (
    QUALIFICATION_TEST_ARTIFACT,
    ExportManifest,
    ModelCard,
    QualificationReceipt,
    sha256_file,
)
from .quantize import SUPPORTED_DTYPES, convert_dtype, quantize_dynamic_int8

DEFAULT_SEED = 1337


def build_model_from_config(config_path: str, seed: int) -> tuple[NanoLM, dict]:
    """Instantiate a randomly-initialized NanoLM from a YAML config."""
    import yaml

    with open(config_path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    model_cfg = raw.get("model") or {}
    torch.manual_seed(seed)
    model = NanoLM(ModelConfig(**model_cfg))
    return model, raw


def build_model_from_checkpoint(
    checkpoint_path: str,
) -> tuple[NanoLM, dict, dict | None]:
    """Rebuild a NanoLM from a scaffold training checkpoint."""
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    cfg_dict = ckpt["config"]["model"]
    model = NanoLM(ModelConfig(**cfg_dict))
    model.load_state_dict(ckpt["model_state"])
    return model, cfg_dict, ckpt["config"].get("train")


def export_model(
    model: NanoLM,
    source_config: dict,
    training_config: dict | None,
    dtype: str,
    output_dir: str,
    code_commit: str,
    seed: int,
    tokenizer_file: str | None = None,
    model_card_name: str = "unnamed",
) -> str:
    """Quantize/convert, save the artifact, and write the manifest.

    Returns the manifest path. Artifacts are test-grade only and always
    carry the non-production-test-artifact qualification label.
    """
    if dtype not in SUPPORTED_DTYPES:
        raise ValueError(f"dtype must be one of {SUPPORTED_DTYPES}, got {dtype!r}")
    os.makedirs(output_dir, exist_ok=True)
    model.eval()

    if dtype == "int8-dynamic":
        export_nn = quantize_dynamic_int8(model)
    else:
        export_nn = convert_dtype(model, dtype)

    artifact_path = os.path.join(output_dir, "model.bin")
    torch.save(
        {
            "state_dict": export_nn.state_dict(),
            "model_config": dict(model.cfg.__dict__)
            if not isinstance(model.cfg, dict)
            else model.cfg,
            "quantization": dtype,
        },
        artifact_path,
    )

    manifest = ExportManifest(
        backend="pytorch",
        artifacts={
            "model": artifact_path,
            "format": "torch-state-dict",
            "quantization": dtype,
            "parameter_count": model.count_parameters(),
        },
        model_hash=sha256_file(artifact_path),
        tokenizer_hash=sha256_file(tokenizer_file) if tokenizer_file else None,
        dataset_manifest_hash=None,  # no datasets exist pre-freeze
        source_config=source_config,
        training_config=training_config,
        code_commit=code_commit,
        seed=seed,
        qualification_receipt=QualificationReceipt(
            qualification=QUALIFICATION_TEST_ARTIFACT
        ),
        model_card=ModelCard(name=model_card_name),
    )
    manifest_path = os.path.join(output_dir, "manifest.json")
    manifest.write(manifest_path)
    return manifest_path


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description=(
            "Export a scaffold NanoLM to a quantized inference artifact "
            "plus a provenance manifest. Test artifacts only "
            f"({QUALIFICATION_TEST_ARTIFACT})."
        )
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--config", help="YAML architecture config (random init)")
    src.add_argument("--checkpoint", help="scaffold training checkpoint (.pt)")
    parser.add_argument(
        "--dtype",
        required=True,
        choices=SUPPORTED_DTYPES,
        help="export dtype/quantization",
    )
    parser.add_argument("--output-dir", required=True, help="artifact directory")
    parser.add_argument(
        "--code-commit",
        default=os.environ.get("SLM_CODE_COMMIT", "unknown"),
        help="git commit of the exporting code (or set SLM_CODE_COMMIT)",
    )
    parser.add_argument(
        "--seed", type=int, default=DEFAULT_SEED, help="random-init seed"
    )
    parser.add_argument(
        "--tokenizer-file",
        default=None,
        help="tokenizer artifact to hash into the manifest (optional)",
    )
    parser.add_argument(
        "--model-card-name",
        default=None,
        help="name field for the manifest model card",
    )
    args = parser.parse_args(argv)

    if args.checkpoint:
        model, model_cfg, train_cfg = build_model_from_checkpoint(args.checkpoint)
        source_config = {"model": model_cfg}
        seed = (train_cfg or {}).get("seed", args.seed)
    else:
        model, raw = build_model_from_config(args.config, args.seed)
        source_config = raw.get("model") or raw
        train_cfg = None
        seed = args.seed

    manifest_path = export_model(
        model=model,
        source_config=source_config,
        training_config=train_cfg,
        dtype=args.dtype,
        output_dir=args.output_dir,
        code_commit=args.code_commit,
        seed=seed,
        tokenizer_file=args.tokenizer_file,
        model_card_name=args.model_card_name
        or os.path.basename(args.output_dir.rstrip("/")),
    )
    with open(manifest_path, "r", encoding="utf-8") as fh:
        print(json.dumps(json.load(fh), indent=2, sort_keys=True))
    print(f"manifest written to {manifest_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
