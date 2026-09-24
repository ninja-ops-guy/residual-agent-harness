"""Configuration loading for the SLM scaffold.

Architecture configs live in research/slm/configs/*.yaml and describe
model shape only (no training has been run with them; see
research/slm/SECURITY-BOUNDARY.md).
"""

from dataclasses import dataclass, field

import yaml


@dataclass
class ModelConfig:
    """Architecture hyperparameters for a decoder-only transformer."""

    d_model: int
    n_layers: int
    n_heads: int
    vocab_size: int
    max_seq: int
    ffn_mult: int = 4
    dropout: float = 0.0
    tie_embeddings: bool = True


@dataclass
class TrainConfig:
    """Optimization hyperparameters.

    Data mapping: prefer ``split_manifest`` — a JSON file mapping
    {"train": ..., "val": ..., "holdout": ...} to three DISTINCT bin
    paths (see scaffold/data.resolve_split_bins; SLM-INFRA-QUAL
    MATERIAL-5). The ``train_bin``/``val_bin`` fields are an explicit
    fallback only and are validated to never alias the holdout.
    """

    batch_size: int = 32
    grad_accum: int = 1
    max_steps: int = 10000
    warmup_steps: int = 500
    lr: float = 3e-4
    min_lr: float = 3e-5
    weight_decay: float = 0.1
    grad_clip: float = 1.0
    seed: int = 1337
    eval_interval: int = 500
    eval_steps: int = 50
    ckpt_interval: int = 1000
    out_dir: str = "runs/default"
    split_manifest: str = ""
    train_bin: str = ""
    val_bin: str = ""


@dataclass
class Config:
    """Top-level config combining model and training sections."""

    model: ModelConfig
    train: TrainConfig = field(default_factory=TrainConfig)


def load_config(path: str) -> Config:
    """Load a YAML config file into a Config.

    The YAML may contain a `model:` mapping and/or a `train:` mapping.
    Pure architecture configs (configs/*.yaml) only define `model:`.
    """
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    model = ModelConfig(**(raw.get("model") or {}))
    train = TrainConfig(**(raw.get("train") or {}))
    return Config(model=model, train=train)
