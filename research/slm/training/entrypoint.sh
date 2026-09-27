#!/usr/bin/env bash
# Container entrypoint: dispatch train / eval subcommands.
set -euo pipefail

cmd="${1:---help}"; shift || true

case "$cmd" in
  train)
    exec python -m scaffold.train "$@"
    ;;
  eval)
    exec python -m scaffold.evaluate "$@"
    ;;
  --help|-h|help)
    echo "usage: entrypoint.sh [train|eval] [args...]"
    echo "  train --config configs/nano-30m.yaml"
    echo "  eval  --config configs/nano-30m.yaml --checkpoint runs/x/ckpt.pt"
    ;;
  *)
    echo "unknown command: $cmd" >&2
    exit 2
    ;;
esac
