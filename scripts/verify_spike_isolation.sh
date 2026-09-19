#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-origin/main}"
changed="$(git diff --name-only "$BASE"...HEAD)"
if printf '%s\n' "$changed" | grep -Eq '^(residual/factory/|residual/m4/|\.github/protected-blobs\.json)'; then
  echo "SPIKE ISOLATION FAIL: protected path modified" >&2; exit 1
fi
if grep -R -nE '(^|[[:space:]])(from|import)[[:space:]]+residual\.(factory|m4)' spikes/a2a --include='*.py'; then
  echo "SPIKE ISOLATION FAIL: prohibited internal import" >&2; exit 1
fi
echo "SPIKE ISOLATION PASS"
