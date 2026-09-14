#!/usr/bin/env bash
set -euo pipefail

MODEL="${1:-${RESIDUAL_FACTORY_MODEL:-}}"
BASE_URL="${RESIDUAL_OLLAMA_URL:-http://localhost:11434}"

if ! command -v python >/dev/null 2>&1; then
  echo "python is required" >&2
  exit 2
fi
if ! command -v git >/dev/null 2>&1; then
  echo "git is required" >&2
  exit 2
fi

python -m pip install -e '.[factory]'

if [[ -n "$MODEL" ]]; then
  if ! command -v ollama >/dev/null 2>&1; then
    echo "Ollama is required when a model is supplied. Install/start Ollama, then rerun." >&2
    exit 2
  fi
  if ! ollama list | awk 'NR>1 {print $1}' | grep -Fxq "$MODEL"; then
    echo "Model $MODEL is not installed. Run: ollama pull $MODEL" >&2
    exit 2
  fi
  python -m residual doctor --model "$MODEL" --base-url "$BASE_URL" --canary --calibrate-concurrency \
    --json runs/factory-host-profile.json
  echo
  echo "Factory bootstrap complete. Dry-run the corpus with:"
  echo "  python benchmarks/factory/corpus/run_corpus.py --model '$MODEL' --base-url '$BASE_URL' --dry-run --output runs/factory-corpus-dry-run"
else
  python -m residual doctor --json runs/factory-host-profile.json
  echo
  echo "Base Factory prerequisites passed."
  echo "To validate local inference, rerun with a model: scripts/setup_factory.sh qwen2.5-coder:7b"
fi
