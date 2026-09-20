"""Dataset packing hooks.

Token streams are stored as raw uint16 .bin files (vocab_size <= 65535),
memory-mapped and sampled as contiguous windows — the standard packing
scheme for from-scratch pretraining. Corpus/benchmark data is owned by
SLM-00; this module only defines the interface.
"""

import numpy as np
import torch

from .config import ModelConfig


class PackedBinDataset:
    """Memory-mapped packed token stream with random-window sampling."""

    def __init__(self, bin_path: str, cfg: ModelConfig, seed: int = 1337) -> None:
        self.tokens = np.memmap(bin_path, dtype=np.uint16, mode="r")
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
