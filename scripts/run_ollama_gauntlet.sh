#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-}"
OUTPUT="${2:-runs/ollama-gauntlet-$(date +%Y%m%d-%H%M%S)}"
REPEATS="${RESIDUAL_GAUNTLET_REPEATS:-3}"

if [[ -z "$MODEL" ]]; then
  echo "usage: $0 <ollama-model> [output-dir]" >&2
  exit 2
fi
if ! command -v ollama >/dev/null 2>&1; then
  echo "ollama is not installed or not on PATH" >&2
  exit 3
fi
if ! command -v residual-gauntlet >/dev/null 2>&1; then
  echo "residual-gauntlet is not installed; run: python -m pip install -e '.[factory]'" >&2
  exit 4
fi

if ! ollama list >/tmp/residual-ollama-models.txt 2>/dev/null; then
  echo "ollama is not reachable; start the Ollama service first" >&2
  exit 5
fi
if ! awk 'NR>1 {print $1}' /tmp/residual-ollama-models.txt | grep -Fxq "$MODEL"; then
  echo "model '$MODEL' is not installed; pull it explicitly with: ollama pull $MODEL" >&2
  exit 6
fi

exec residual-gauntlet   --provider ollama   --model "$MODEL"   --repeats "$REPEATS"   --output "$OUTPUT"
