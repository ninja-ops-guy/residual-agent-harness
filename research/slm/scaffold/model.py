"""Decoder-only transformer model (PyTorch), from scratch.

Self-contained: multi-head causal self-attention, MLP, pre-norm blocks,
learned positional embeddings, optional tied input/output embeddings.
"""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import ModelConfig


class CausalSelfAttention(nn.Module):
    """Multi-head causal self-attention."""

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        if cfg.d_model % cfg.n_heads != 0:
            raise ValueError("d_model must be divisible by n_heads")
        self.n_heads = cfg.n_heads
        self.head_dim = cfg.d_model // cfg.n_heads
        self.qkv = nn.Linear(cfg.d_model, 3 * cfg.d_model, bias=False)
        self.proj = nn.Linear(cfg.d_model, cfg.d_model, bias=False)
        self.dropout = cfg.dropout
        mask = torch.tril(torch.ones(cfg.max_seq, cfg.max_seq))
        self.register_buffer("mask", mask.view(1, 1, cfg.max_seq, cfg.max_seq))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        bsz, seq, dim = x.shape
        q, k, v = self.qkv(x).split(dim, dim=2)

        def split_heads(t: torch.Tensor) -> torch.Tensor:
            return t.view(bsz, seq, self.n_heads, self.head_dim).transpose(1, 2)

        q, k, v = split_heads(q), split_heads(k), split_heads(v)
        if hasattr(F, "scaled_dot_product_attention"):
            # is_causal=True replaces the explicit mask for full blocks.
            out = F.scaled_dot_product_attention(
                q,
                k,
                v,
                is_causal=True,
                dropout_p=self.dropout if self.training else 0.0,
            )
        else:  # pragma: no cover - fallback for older torch
            scores = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_dim)
            scores = scores.masked_fill(self.mask[:, :, :seq, :seq] == 0, -1e9)
            out = F.softmax(scores, dim=-1) @ v
        out = out.transpose(1, 2).contiguous().view(bsz, seq, dim)
        return self.proj(out)


class MLP(nn.Module):
    """Position-wise feed-forward network (GELU)."""

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        hidden = cfg.ffn_mult * cfg.d_model
        self.up = nn.Linear(cfg.d_model, hidden, bias=False)
        self.down = nn.Linear(hidden, cfg.d_model, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.down(F.gelu(self.up(x)))


class Block(nn.Module):
    """Pre-norm transformer block."""

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.ln1 = nn.LayerNorm(cfg.d_model)
        self.attn = CausalSelfAttention(cfg)
        self.ln2 = nn.LayerNorm(cfg.d_model)
        self.mlp = MLP(cfg)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln1(x))
        return x + self.mlp(self.ln2(x))


class NanoLM(nn.Module):
    """Decoder-only language model with learned positional embeddings."""

    def __init__(self, cfg: ModelConfig) -> None:
        super().__init__()
        self.cfg = cfg
        self.tok_emb = nn.Embedding(cfg.vocab_size, cfg.d_model)
        self.pos_emb = nn.Embedding(cfg.max_seq, cfg.d_model)
        self.drop = nn.Dropout(cfg.dropout)
        self.blocks = nn.ModuleList(Block(cfg) for _ in range(cfg.n_layers))
        self.ln_f = nn.LayerNorm(cfg.d_model)
        self.lm_head = nn.Linear(cfg.d_model, cfg.vocab_size, bias=False)
        if cfg.tie_embeddings:
            self.lm_head.weight = self.tok_emb.weight
        self.apply(self._init_weights)

    @staticmethod
    def _init_weights(module: nn.Module) -> None:
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(
        self, idx: torch.Tensor, targets: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        seq = idx.shape[1]
        if seq > self.cfg.max_seq:
            raise ValueError(f"sequence length {seq} > max_seq {self.cfg.max_seq}")
        pos = torch.arange(seq, device=idx.device)
        x = self.drop(self.tok_emb(idx) + self.pos_emb(pos))
        for block in self.blocks:
            x = block(x)
        logits = self.lm_head(self.ln_f(x))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)), targets.view(-1)
            )
        return logits, loss

    def count_parameters(self) -> int:
        """Number of trainable parameters (tied embeddings counted once)."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
