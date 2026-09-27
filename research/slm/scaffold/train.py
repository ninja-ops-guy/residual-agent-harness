"""Entrypoint: train a model from a YAML config.

NOTE: gated by the SLM-00 benchmark freeze. This script must not be run
against real corpora until SLM-00 is complete (SECURITY-BOUNDARY.md).

Usage: python -m scaffold.train --config path/to/config.yaml [--resume ckpt.pt]
"""

import argparse

from .config import load_config
from .trainer import Trainer


def main() -> None:
    """Parse args and run the trainer."""
    parser = argparse.ArgumentParser(description="Train a NanoLM model.")
    parser.add_argument("--config", required=True, help="YAML config path")
    parser.add_argument("--resume", default=None, help="checkpoint to resume from")
    args = parser.parse_args()

    cfg = load_config(args.config)
    trainer = Trainer(cfg)
    start = 0
    if args.resume:
        start = trainer.load_checkpoint(args.resume)
    print(f"parameters: {trainer.model.count_parameters():,}")
    trainer.train(start_step=start)


if __name__ == "__main__":
    main()
