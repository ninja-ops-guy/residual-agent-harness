#!/usr/bin/env bash
# One-command onboarding demo (Track O).
# Runs a bounded task against the sample project with scripted providers
# (no model calls, no network), then verifies the resulting evidence trace.
# Exit 0 on success; non-zero with a diagnostic on failure.
set -euo pipefail

cd "$(dirname "$0")/../.."
OUT="${1:-runs/onboarding}"

echo "==> residual run examples/onboarding/sample_project (scripted demo providers)"
python3 -m residual run examples/onboarding/sample_project/task.json \
  --config examples/onboarding/config.toml --output "$OUT"

echo "==> verifying evidence trace"
ROOT="$(python3 -m residual verify-trace "$OUT/trace.jsonl" | python3 -c 'import sys, json; print(json.load(sys.stdin)["root"])')"
python3 -m residual verify-trace "$OUT/trace.jsonl" --expected-root "$ROOT"
python3 -m residual verify-trace "$OUT/trace.jsonl" --expected-root "$ROOT" --result "$OUT/result.json"

echo "==> onboarding demo OK — evidence in $OUT"
