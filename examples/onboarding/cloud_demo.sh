#!/usr/bin/env bash
set -euo pipefail

OUT="${1:-runs/cloud-demo}"
MODEL="${RESIDUAL_DEMO_MODEL:-gpt-5.6-luna}"
CFG="$(mktemp)"
trap 'rm -f "$CFG"' EXIT

cat >"$CFG" <<EOF
plugins = ["residual.browser_bridge:register"]

[local]
kind = "browser_bridge"
model = "$MODEL"
placement = "remote"
timeout_seconds = 90

[limits]
local_rounds = 1
max_output_tokens = 256

[cache]
enabled = false
EOF

printf 'RESIDUAL browser-cloud demo\n  transport: browser bridge / Puter.js host\n  model:     %s\n  output:    %s\n\n' "$MODEL" "$OUT"
printf 'If prompted above the VM, enable cloud access with Puter and then return here.\n\n'
python3 -m residual run examples/onboarding/sample_project/task.json --config "$CFG" --output "$OUT"
python3 -m residual verify-trace "$OUT/trace.jsonl" --result "$OUT/result.json"
printf '\nCloud demo complete. Inspect %s/trace.jsonl and %s/result.json\n' "$OUT" "$OUT"
