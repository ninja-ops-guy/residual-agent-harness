#!/bin/sh
# Verifier v1 for enterprise spec implementation. Run from repo root.
set -u
cd "$(dirname "$0")/../.."
fail=0

echo "== 1. Requirement coverage =="
grep -oE 'ENT[0-9]-R[0-9]+' docs/enterprise/ENTERPRISE_SPECS.md | sort -u > /tmp/reqs.txt
missing=0
while read -r r; do
  if ! grep -rq "$r" residual/ docs/enterprise/ --include='*.py' --include='*.md' \
      --exclude=ENTERPRISE_SPECS.md; then
    echo "MISSING: $r"; missing=1
  fi
done < /tmp/reqs.txt
[ "$missing" = 1 ] && fail=1 || echo "all $(wc -l < /tmp/reqs.txt) requirements referenced"

echo "== 2. Traceability doc =="
if [ ! -f docs/enterprise/TRACEABILITY.md ]; then echo "MISSING traceability"; fail=1; else
  bad=0
  grep -oE '`[^`]+\.(py|md|json|yaml|yml)`' docs/enterprise/TRACEABILITY.md | tr -d '`' | sort -u | while read -r p; do
    [ -f "$p" ] || { echo "BROKEN REF: $p"; bad=1; }
  done
  echo "traceability refs checked"
fi

echo "== 3. Imports =="
python3 - <<'PY' || fail=1
import importlib
for m in ["residual.iam","residual.compliance","residual.tenancy","residual.hadr",
          "residual.supplychain","residual.integrations","residual.licensing"]:
    importlib.import_module(m)
    print("ok", m)
PY

echo "== 4. Tests =="
python3 -m pytest tests/ -q --tb=no > /tmp/verifier_tests.txt 2>&1 || fail=1; tail -2 /tmp/verifier_tests.txt

echo "VERIFIER EXIT: $fail"
exit $fail
