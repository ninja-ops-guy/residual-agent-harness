"""Dataset packing hooks.

Token streams are stored as raw uint32-le .bin files (little-endian
unsigned 32-bit token ids), memory-mapped and sampled as contiguous
windows — the standard packing scheme for from-scratch pretraining.
uint32-le is the single agreed dtype end-to-end (SLM-INFRA-QUAL
MATERIAL-4): dataset/compile.py packs ``array.array("I")`` and declares
``"dtype": "uint32-le"`` in the dataset manifest; this module reads the
same dtype so vocab growth beyond 65535 never silently corrupts the
stream (a uint16 reader would misread every token 2:1).

Split mapping (SLM-INFRA-QUAL MATERIAL-5): the scaffold REQUIRES an
explicit split->bin mapping (``resolve_split_bins``) with three distinct
paths for train / val / holdout. Holdout bins may never be used as the
validation set (SECURITY-BOUNDARY rule 2); see ``validate_split_paths``.

Corpus/benchmark data is owned by SLM-00; this module only defines the
interface.
"""

import json
import os

import numpy as np
import torch

from .config import ModelConfig

# Single agreed packed dtype (little-endian uint32). Matches
# dataset/compile.py's "dtype": "uint32-le" manifest declaration.
PACKED_DTYPE = np.dtype("<u4")
PACKED_DTYPE_NAME = "uint32-le"

REQUIRED_SPLITS = ("train", "val", "holdout")


class PackedBinDataset:
    """Memory-mapped packed uint32-le token stream with random-window
    sampling."""

    def __init__(self, bin_path: str, cfg: ModelConfig, seed: int = 1337) -> None:
        self.tokens = np.memmap(bin_path, dtype=PACKED_DTYPE, mode="r")
        if cfg.vocab_size > np.iinfo(np.uint32).max:
            raise ValueError(
                f"vocab_size {cfg.vocab_size} exceeds uint32 token range")
        self.seq_len = cfg.max_seq
        self.rng = np.random.default_rng(seed)

    def __len__(self) -> int:
        return max(0, len(self.tokens) - self.seq_len - 1)

    def sample_batch(
        self, batch_size: int, device: torch.device | str
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Draw (inputs, targets) of shape (batch_size, seq_len).

        targets are inputs shifted left by one token.
        """
        if len(self) <= 0:
            raise ValueError("token stream too short for seq_len")
        starts = self.rng.integers(0, len(self), size=batch_size)
        x = np.stack(
            [self.tokens[s : s + self.seq_len] for s in starts]
        ).astype(np.int64)
        y = np.stack(
            [self.tokens[s + 1 : s + self.seq_len + 1] for s in starts]
        ).astype(np.int64)
        return (
            torch.from_numpy(x).to(device),
            torch.from_numpy(y).to(device),
        )


def resolve_split_bins(manifest_path: str) -> dict[str, str]:
    """Load an explicit split->bin mapping (JSON object).

    The mapping MUST contain distinct paths for "train", "val", and
    "holdout". There is no default: the scaffold never guesses which bin
    is the validation set (MATERIAL-5). Raises ValueError on any
    violation.
    """
    with open(manifest_path, "r", encoding="utf-8") as fh:
        mapping = json.load(fh)
    if not isinstance(mapping, dict):
        raise ValueError(
            f"split manifest {manifest_path} must be a JSON object "
            f"{{split: bin_path}}")
    missing = [s for s in REQUIRED_SPLITS if not mapping.get(s)]
    if missing:
        raise ValueError(
            f"split manifest {manifest_path} missing required split(s) "
            f"{missing}; train/val/holdout bins must all be mapped "
            f"explicitly")
    validate_split_paths(mapping["train"], mapping["val"],
                         mapping["holdout"])
    return {s: str(mapping[s]) for s in REQUIRED_SPLITS}


def validate_split_paths(train_bin: str, val_bin: str,
                         holdout_bin: str | None = None) -> None:
    """Refuse split assignments that alias holdout data as validation.

    Rules (SECURITY-BOUNDARY rule 2, MATERIAL-5):
      * train, val, and holdout paths must all be distinct
      * the validation bin may never BE, or be named like, the holdout
        bin (a path whose stem is "holdout")
    Raises ValueError on violation.
    """
    paths = {"train": train_bin, "val": val_bin}
    if holdout_bin is not None:
        paths["holdout"] = holdout_bin
    norm = {k: os.path.normpath(v) for k, v in paths.items()}
    if len(set(norm.values())) != len(norm):
        raise ValueError(
            f"split bins must be distinct paths, got {paths}; "
            f"holdout data may never serve as train/val")
    val_stem = os.path.splitext(os.path.basename(norm["val"]))[0].lower()
    if val_stem == "holdout":
        raise ValueError(
            f"validation bin {val_bin!r} is the holdout bin by name; "
            f"using holdout as val violates SECURITY-BOUNDARY rule 2 "
            f"(no holdout access during training)")
