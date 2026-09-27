"""Entrypoint: evaluate a checkpoint's validation loss.

Usage: python -m scaffold.evaluate --config cfg.yaml --checkpoint ckpt.pt
"""

import argparse

from .config import load_config
from .trainer import Trainer


def main() -> None:
    """Load a checkpoint and report validation loss."""
    parser = argparse.ArgumentParser(description="Evaluate a NanoLM checkpoint.")
    parser.add_argument("--config", required=True, help="YAML config path")
    parser.add_argument("--checkpoint", required=True, help="checkpoint path")
    args = parser.parse_args()

    cfg = load_config(args.config)
    trainer = Trainer(cfg)
    step = trainer.load_checkpoint(args.checkpoint)
    val_loss = trainer.evaluate()
    print(f"checkpoint step={step} val_loss={val_loss:.4f}")


if __name__ == "__main__":
    main()
