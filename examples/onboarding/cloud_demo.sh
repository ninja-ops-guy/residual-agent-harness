#!/usr/bin/env bash
set -euo pipefail

: "${LLM_BASE_URL:?cloud demo session is not active}"
: "${LLM_API_KEY:?cloud demo session is not active}"

OUT="${1:-runs/cloud-demo}"
MODEL="${RESIDUAL_DEMO_MODEL:-auto:fast}"
CFG="$(mktemp)"
trap 'rm -f "$CFG"' EXIT

cat >"$CFG" <<EOF
[local]
kind = "openai_compatible"
model = "$MODEL"
base_url = "$LLM_BASE_URL"
placement = "remote"
api_key_env = "LLM_API_KEY"
json_mode = true
output_token_field = "max_tokens"
timeout_seconds = 45

[limits]
local_rounds = 1
max_output_tokens = 256

[cache]
enabled = false
EOF

printf 'RESIDUAL cloud demo\n  endpoint: %s\n  model:    %s\n  output:   %s\n\n' "$LLM_BASE_URL" "$MODEL" "$OUT"
python3 -m residual run examples/onboarding/sample_project/task.json --config "$CFG" --output "$OUT"
python3 -m residual verify-trace "$OUT/trace.jsonl" --result "$OUT/result.json"
printf '\nCloud demo complete. Inspect %s/trace.jsonl and %s/result.json\n' "$OUT" "$OUT"
