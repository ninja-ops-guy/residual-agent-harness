"""Trainer loop: cosine LR with warmup, gradient clipping, checkpointing,
and full seed control. Machinery only — no training runs before the
SLM-00 benchmark freeze (see research/slm/SECURITY-BOUNDARY.md).
"""

import json
import math
import os
import random

import numpy as np
import torch

from .config import Config
from .data import PackedBinDataset, resolve_split_bins, validate_split_paths
from .model import NanoLM


def set_seed(seed: int) -> None:
    """Seed python, numpy and torch (incl. CUDA) for determinism."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def cosine_lr(step: int, cfg: Config) -> float:
    """Linear warmup then cosine decay to min_lr."""
    t = cfg.train
    if step < t.warmup_steps:
        return t.lr * (step + 1) / t.warmup_steps
    progress = (step - t.warmup_steps) / max(1, t.max_steps - t.warmup_steps)
    progress = min(1.0, progress)
    cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
    return t.min_lr + (t.lr - t.min_lr) * cosine


class Trainer:
    """Single-device training loop with checkpointing."""

    def __init__(self, cfg: Config, device: torch.device | str | None = None) -> None:
        self.cfg = cfg
        set_seed(cfg.train.seed)
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)
        self.model = NanoLM(cfg.model).to(self.device)
        self.opt = torch.optim.AdamW(
            self.model.parameters(),
            lr=cfg.train.lr,
            weight_decay=cfg.train.weight_decay,
        )
        # MATERIAL-5: the validation bin must come from an explicit split
        # mapping (train/val/holdout distinct). No implicit defaults;
        # holdout can never be aliased as val.
        train_bin, val_bin = self._resolve_bins(cfg)
        self.train_data = PackedBinDataset(
            train_bin, cfg.model, seed=cfg.train.seed
        )
        self.val_data = PackedBinDataset(
            val_bin, cfg.model, seed=cfg.train.seed + 1
        )
        os.makedirs(cfg.train.out_dir, exist_ok=True)

    @staticmethod
    def _resolve_bins(cfg: Config) -> tuple[str, str]:
        t = cfg.train
        if t.split_manifest:
            bins = resolve_split_bins(t.split_manifest)
            return bins["train"], bins["val"]
        if not t.train_bin or not t.val_bin:
            raise ValueError(
                "no split mapping configured: set train.split_manifest "
                "(JSON {train,val,holdout} -> distinct bin paths) or "
                "explicit train.train_bin/train.val_bin; the scaffold "
                "never defaults a validation set")
        validate_split_paths(t.train_bin, t.val_bin)
        return t.train_bin, t.val_bin

    @torch.no_grad()
    def evaluate(self) -> float:
        """Mean validation loss over cfg.train.eval_steps batches."""
        self.model.eval()
        losses = []
        for _ in range(self.cfg.train.eval_steps):
            x, y = self.val_data.sample_batch(self.cfg.train.batch_size, self.device)
            _, loss = self.model(x, y)
            losses.append(loss.item())
        self.model.train()
        return float(np.mean(losses))

    def save_checkpoint(self, step: int, name: str | None = None) -> str:
        """Write model/optimizer/step checkpoint to out_dir."""
        name = name or f"ckpt_step{step:07d}.pt"
        path = os.path.join(self.cfg.train.out_dir, name)
        torch.save(
            {
                "step": step,
                "model_state": self.model.state_dict(),
                "opt_state": self.opt.state_dict(),
                "config": {
                    "model": vars(self.cfg.model),
                    "train": vars(self.cfg.train),
                },
            },
            path,
        )
        return path

    def load_checkpoint(self, path: str) -> int:
        """Restore model/optimizer state; returns the saved step."""
        ckpt = torch.load(path, map_location=self.device)
        self.model.load_state_dict(ckpt["model_state"])
        self.opt.load_state_dict(ckpt["opt_state"])
        return int(ckpt["step"])

    def train(self, start_step: int = 0) -> None:
        """Run the optimization loop to cfg.train.max_steps."""
        t = self.cfg.train
        self.model.train()
        log_path = os.path.join(t.out_dir, "train_log.jsonl")
        with open(log_path, "a", encoding="utf-8") as log:
            for step in range(start_step, t.max_steps):
                lr = cosine_lr(step, self.cfg)
                for group in self.opt.param_groups:
                    group["lr"] = lr

                total = 0.0
                for _ in range(t.grad_accum):
                    x, y = self.train_data.sample_batch(t.batch_size, self.device)
                    _, loss = self.model(x, y)
                    (loss / t.grad_accum).backward()
                    total += loss.item() / t.grad_accum
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), t.grad_clip)
                self.opt.step()
                self.opt.zero_grad(set_to_none=True)

                if (step + 1) % t.ckpt_interval == 0 or step + 1 == t.max_steps:
                    self.save_checkpoint(step + 1)
                if (step + 1) % t.eval_interval == 0:
                    val = self.evaluate()
                    record = {
                        "step": step + 1,
                        "train_loss": total,
                        "val_loss": val,
                        "lr": lr,
                    }
                    log.write(json.dumps(record) + "\n")
                    log.flush()
