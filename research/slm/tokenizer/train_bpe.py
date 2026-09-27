#!/usr/bin/env python3
"""Train a custom residual-bpe tokenizer on a provided corpus file.

Byte-level BPE trained on UTF-8 text from a plain-text or JSONL corpus.
Exports a tiktoken-compatible `.tiktoken` file (base64 token + rank per
line), loadable via research/slm/dataset/compile.py --tokenizer or
research/slm/tokenizer/measure.py.

Tooling only: this script trains a tokenizer on an explicitly provided
corpus file. It performs no model training and touches no benchmark.

Usage:
    python train_bpe.py --corpus corpus.jsonl --vocab-size 8192 \
        --output residual_bpe.tiktoken
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Iterator

# GPT-4-style pre-tokenization pattern (same family as cl100k/o200k).
PAT_STR = (
    r"'(?i:[sdmt]|ll|ve|re)|[^\r\n\p{L}\p{N}]?+\p{L}++"
    r"|\p{N}{1,3}+| ?[^\s\p{L}\p{N}]++[\r\n]*+|\s++$|\s*[\r\n]"
    r"|\s+(?!\S)|\s+"
)
BASE_VOCAB = 256  # one entry per byte


def fail(msg: str) -> "SystemExit":
    print(f"error: {msg}", file=sys.stderr)
    return SystemExit(2)


def get_regex():
    try:
        import regex
    except ImportError:
        raise fail("regex is required: pip install regex==2024.11.6")
    return regex.compile(PAT_STR)


def iter_texts(corpus: Path) -> Iterator[str]:
    """Yield text chunks from a .jsonl (canonical JSON per line) or text."""
    with corpus.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.rstrip("\n")
            if not line.strip():
                continue
            if corpus.suffix == ".jsonl":
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise fail(f"{corpus}:{lineno}: invalid JSONL: {exc}")
                yield json.dumps(obj, sort_keys=True, ensure_ascii=False)
            else:
                yield line


def train_bpe(corpus: Path, vocab_size: int) -> dict[bytes, int]:
    """Return mergeable_ranks: bytes -> rank (bytes 0..255 first)."""
    if vocab_size <= BASE_VOCAB:
        raise fail(f"--vocab-size must be > {BASE_VOCAB}")
    rx = get_regex()
    # word (tuple of single-byte tokens) -> count
    words: Counter[tuple[bytes, ...]] = Counter()
    for text in iter_texts(corpus):
        for match in rx.findall(text):
            words[tuple(bytes([b]) for b in match.encode("utf-8"))] += 1
    if not words:
        raise fail(f"corpus {corpus} produced no tokens")

    ranks: dict[bytes, int] = {bytes([b]): b for b in range(BASE_VOCAB)}
    next_rank = BASE_VOCAB
    target_merges = vocab_size - BASE_VOCAB
    for merge_i in range(target_merges):
        pair_counts: Counter[tuple[bytes, bytes]] = Counter()
        for word, count in words.items():
            for a, b in zip(word, word[1:]):
                pair_counts[(a, b)] += count
        if not pair_counts:
            print(f"warning: no more pairs after {merge_i} merges; "
                  f"stopping early", file=sys.stderr)
            break
        (a, b), _ = max(pair_counts.items(), key=lambda kv: (kv[1], kv[0]))
        merged = a + b
        ranks[merged] = next_rank
        next_rank += 1
        new_words: Counter[tuple[bytes, ...]] = Counter()
        for word, count in words.items():
            out: list[bytes] = []
            i = 0
            while i < len(word):
                if i + 1 < len(word) and word[i] == a and word[i + 1] == b:
                    out.append(merged)
                    i += 2
                else:
                    out.append(word[i])
                    i += 1
            new_words[tuple(out)] += count
        words = new_words
        if merge_i % 500 == 0:
            print(f"merge {merge_i}/{target_merges}", file=sys.stderr)
    return ranks


def export_tiktoken(ranks: dict[bytes, int], output: Path) -> None:
    lines = []
    for token, rank in sorted(ranks.items(), key=lambda kv: kv[1]):
        lines.append(f"{base64.b64encode(token).decode('ascii')} {rank}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--corpus", required=True,
                   help="Training corpus: .jsonl (one JSON record/line) or "
                        "plain UTF-8 text.")
    p.add_argument("--vocab-size", type=int, default=8192,
                   help="Total vocab size incl. 256 byte tokens "
                        "(default: 8192).")
    p.add_argument("--output", required=True,
                   help="Output .tiktoken file path.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    corpus = Path(args.corpus)
    if not corpus.exists():
        raise fail(f"corpus not found: {corpus}")
    started = time.monotonic()
    ranks = train_bpe(corpus, args.vocab_size)
    output = Path(args.output)
    export_tiktoken(ranks, output)
    print(json.dumps({
        "vocab_size": len(ranks),
        "output": str(output),
        "elapsed_seconds": round(time.monotonic() - started, 2),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
