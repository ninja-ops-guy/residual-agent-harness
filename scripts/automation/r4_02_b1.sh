#!/usr/bin/env bash
# R4-02 B1 promotion-invariant qualification runner.
#
# This runner proves three different things instead of collapsing them:
# 1. the frozen predecessor still reproduces the promotion-sensitive link bug;
# 2. the exact successor rejects the same construction for TAR and TAR.ZST;
# 3. safe confined relative links still work after promotion.
#
# Any unexpected candidate failure invokes Codex in an isolated repair branch.
# The exact candidate is NEVER relabeled green because that repair succeeds.
set -Eeuo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/automation/lib.sh
source "$HERE/lib.sh"

task_init "r4-02-b1"
need git
need flock

select_r4_python() {
  local candidate
  local -a candidates=()
  if [[ -n "${R4_02_PYTHON:-}" ]]; then
    candidates+=("$R4_02_PYTHON")
  fi
  # Prefer known local qualification environments when present, then fall back
  # to PATH. Every candidate is capability-checked; merely existing is not
  # sufficient.
  candidates+=(
    "/tmp/residual-r4-02-native-venv/bin/python"
    "/tmp/residual-r4-venv/bin/python"
    "python3"
    "python"
  )
  for candidate in "${candidates[@]}"; do
    if [[ "$candidate" == */* ]]; then
      [[ -x "$candidate" ]] || continue
    else
      command -v "$candidate" >/dev/null 2>&1 || continue
      candidate="$(command -v "$candidate")"
    fi
    if "$candidate" - <<'PY' >/dev/null 2>&1
import sys, tarfile
version = sys.version_info[:3]
minimum = {(3, 11): (3, 11, 13), (3, 12): (3, 12, 11), (3, 13): (3, 13, 4)}
ok = version >= minimum.get(version[:2], (3, 14, 0))
ok = ok and callable(getattr(tarfile, "data_filter", None))
raise SystemExit(0 if ok else 1)
PY
    then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

PYTHON_BIN="$(select_r4_python)" || {
  log "No local Python satisfies the R4-02 runtime floor and tarfile.data_filter capability."
  log "Set R4_02_PYTHON=/path/to/a/supported/python and rerun."
  exit 30
}
run_logged python-preflight "$PYTHON_BIN" - <<'PY'
import json, sys, tarfile
print(json.dumps({
    "executable": sys.executable,
    "version": sys.version,
    "data_filter": callable(getattr(tarfile, "data_filter", None)),
}, sort_keys=True))
PY

BASE_REF="${R4_02_B1_BASE_REF:-2b75b42cd8cf1a7f13eac64a77d86ddfb619d169}"
TARGET_REF="${R4_02_B1_TARGET_REF:-e8894c443936710b86efc85e9cbcc29a5f70840e}"

BASE_SHA="$(resolve_commit "$BASE_REF")"
TARGET_SHA="$(resolve_commit "$TARGET_REF")"
BASE_WT="$(ensure_worktree r4-02-b1-base "$BASE_SHA")"
TARGET_WT="$(ensure_worktree r4-02-b1-target "$TARGET_SHA")"
TREE="$(git -C "$TARGET_WT" rev-parse 'HEAD^{tree}')"

cat > "$RUN_DIR/repair-contract.txt" <<EOF
RESIDUAL R4-02 B1 AUTOMATED REPAIR CONTRACT

Security defect:
TAR/TAR.ZST link safety must be invariant under staging-directory relocation.
A relative link that leaves the logical runtime root and later re-enters a
known staging basename must be rejected before promotion.

Required invariants:
- link validation is defined in the logical archive/runtime namespace;
- root underflow is rejected even if the physical staging path re-enters;
- TAR and TAR.ZST have equivalent authority semantics;
- confined relative links such as lib/link -> ../bin/ollama remain supported;
- staging cleanup, Python data_filter, post-tree validation, ZIP validation,
  and runtime security floors must not be weakened;
- no product changes outside R4-02 archive authority scope.

Do not edit GitHub state. Do not push or merge.
EOF

VERIFY_CMD="'$PYTHON_BIN' -m pytest -q -p no:cacheprovider tests/security/test_r4_02_archive_authority.py"

log "base=$BASE_SHA target=$TARGET_SHA tree=$TREE"

if ! run_logged candidate-compile bash -lc "cd '$TARGET_WT' && '$PYTHON_BIN' -m py_compile residual/station/archive.py tests/security/test_r4_02_archive_authority.py"; then
  AUTO_REPAIR_ALLOWED_REGEX='^(residual/station/archive.py|tests/security/test_r4_02_archive_authority.py|scripts/security/r4_02_.*|docs/security/SNYK_R4_02.md)$'
  export AUTO_REPAIR_ALLOWED_REGEX
  fail_with_codex "$TARGET_WT" "$VERIFY_CMD" "$RUN_DIR/repair-contract.txt"
fi

# The predecessor must remain sensitive to the B1 oracle for the *right reason*.
# A generic nonzero pytest exit is not enough: an unsupported Python runtime,
# import error, or fixture failure must never be mistaken for B1 reproduction.
NEGATIVE_XML="$RUN_DIR/predecessor-reproduction.xml"
NEGATIVE_CMD="cd '$TARGET_WT' && R4_02_ARCHIVE_SOURCE='$BASE_WT/residual/station/archive.py' '$PYTHON_BIN' -m pytest -q -p no:cacheprovider tests/security/test_r4_02_archive_authority.py -k 'link_confinement_survives_staging_promotion and fixed123' --junitxml='$NEGATIVE_XML'"
set +e
run_logged predecessor-reproduction bash -lc "$NEGATIVE_CMD"
NEGATIVE_RC=$?
set -e
if [[ "$NEGATIVE_RC" -ne 1 ]] || ! "$PYTHON_BIN" - "$NEGATIVE_XML" <<'PY'
import pathlib, sys, xml.etree.ElementTree as ET
path = pathlib.Path(sys.argv[1])
if not path.is_file():
    raise SystemExit(1)
root = ET.parse(path).getroot()
cases = list(root.iter("testcase"))
failures = [case.find("failure") for case in cases if case.find("failure") is not None]
errors = [case.find("error") for case in cases if case.find("error") is not None]
skips = [case.find("skipped") for case in cases if case.find("skipped") is not None]
texts = "\n".join((item.get("message") or "") + "\n" + (item.text or "") for item in failures)
ok = (
    len(cases) == 2
    and len(failures) == 2
    and not errors
    and not skips
    and "DID NOT RAISE" in texts
)
raise SystemExit(0 if ok else 1)
PY
then
  log "The predecessor negative control did not reproduce B1 with the expected two DID-NOT-RAISE failures."
  fail_with_codex "$TARGET_WT" "$VERIFY_CMD" "$RUN_DIR/repair-contract.txt"
fi
log "predecessor B1 reproduction confirmed: 2/2 matched-basename cases failed for DID NOT RAISE"

# Fast focused pass first so diagnostics point directly at B1 if it regresses.
FOCUSED="'$PYTHON_BIN' -m pytest -q -p no:cacheprovider tests/security/test_r4_02_archive_authority.py -k 'link_confinement_survives_staging_promotion or confined_parent_relative_symlink_survives_promotion or logical_link_target_rejects_root_underflow'"
if ! run_logged candidate-focused bash -lc "cd '$TARGET_WT' && $FOCUSED"; then
  AUTO_REPAIR_ALLOWED_REGEX='^(residual/station/archive.py|tests/security/test_r4_02_archive_authority.py|scripts/security/r4_02_.*|docs/security/SNYK_R4_02.md)$'
  export AUTO_REPAIR_ALLOWED_REGEX
  fail_with_codex "$TARGET_WT" "$VERIFY_CMD" "$RUN_DIR/repair-contract.txt"
fi

if ! run_logged candidate-full bash -lc "cd '$TARGET_WT' && $VERIFY_CMD"; then
  AUTO_REPAIR_ALLOWED_REGEX='^(residual/station/archive.py|tests/security/test_r4_02_archive_authority.py|scripts/security/r4_02_.*|docs/security/SNYK_R4_02.md)$'
  export AUTO_REPAIR_ALLOWED_REGEX
  fail_with_codex "$TARGET_WT" "$VERIFY_CMD" "$RUN_DIR/repair-contract.txt"
fi

run_logged diff-check bash -lc "cd '$TARGET_WT' && git diff --check"

write_receipt "PASS" "$TARGET_SHA" "$TREE"
log "PASS: exact R4-02 B1 successor satisfied predecessor sensitivity + focused + full archive tests"
log "receipt=$RUN_DIR/receipt.json"
