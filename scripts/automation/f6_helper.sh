#!/usr/bin/env bash
# AUD-1/F6 helper qualification runner.
#
# This script NEVER executes physical F6. It only qualifies the evidence helper
# and its surrounding security tests against an exact helper commit. A failure
# may be repaired by Codex only in an isolated local repair worktree; the frozen
# product candidate is outside the allowed repair scope.
set -Eeuo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/automation/lib.sh
source "$HERE/lib.sh"

task_init "aud1-f6-helper"
need git
need python
need flock

HELPER_REF="${F6_HELPER_REF:-a2567103c7e634310d696e421692fa1f86624e3b}"
FROZEN_CANDIDATE="${F6_CANDIDATE_SHA:-943c77a28ada1bc3931408c5f9b40d40c25eb2dc}"

HELPER_SHA="$(resolve_commit "$HELPER_REF")"
WT="$(ensure_worktree aud1-f6-helper "$HELPER_SHA")"
TREE="$(git -C "$WT" rev-parse 'HEAD^{tree}')"

cat > "$RUN_DIR/repair-contract.txt" <<EOF
RESIDUAL AUD-1 / F6 HELPER AUTOMATED REPAIR CONTRACT

Frozen product candidate:
$FROZEN_CANDIDATE

The product candidate must not be changed.

This lane may repair only helper/evidence tooling and helper tests. It MUST NOT:
- execute F6-A or F6-B;
- interrupt tunnels or workers;
- change the frozen candidate;
- weaken exact 403 / rejected=true / accepted=false requirements;
- retain raw worker credentials or raw leases in evidence;
- weaken candidate SHA/tree/module binding;
- weaken expiry -> recovery -> reassignment ordering;
- weaken project/task/attempt/owner binding;
- weaken event-chain or monotonic snapshot checks;
- push, merge, approve, or authorize physical execution.

Fix the smallest helper defect exposed by the captured tests and rerun the
specified verifier.
EOF

FOCUSED="python -m pytest tests/tools/test_aud1_f6_collect.py tests/tools/test_aud1_f6_guard.py tests/tools/test_aud1_f6_stale_probe.py -q"
BROAD="python -m pytest tests/station/test_aud1_security.py tests/station/test_aud1_authority_separation.py tests/tools/test_aud1_f6_collect.py tests/tools/test_aud1_f6_guard.py tests/tools/test_aud1_f6_stale_probe.py -q"
VERIFY_CMD="$BROAD"

log "helper_head=$HELPER_SHA helper_tree=$TREE frozen_candidate=$FROZEN_CANDIDATE"

# Verify the helper is still hard-bound to the frozen release candidate.
if ! run_logged target-binding bash -lc "cd '$WT' && python - <<'PY'
import importlib.util, pathlib
root = pathlib.Path('.')
spec = importlib.util.spec_from_file_location('f6_collect', root/'tools/aud1/f6_collect.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
expected = '$FROZEN_CANDIDATE'
assert m.TARGET_SHA == expected, (m.TARGET_SHA, expected)
print('TARGET_SHA', m.TARGET_SHA)
PY"; then
  AUTO_REPAIR_ALLOWED_REGEX='^(tools/aud1/|tests/tools/test_aud1_f6_|tests/station/test_aud1_)'
  export AUTO_REPAIR_ALLOWED_REGEX
  fail_with_codex "$WT" "$VERIFY_CMD" "$RUN_DIR/repair-contract.txt"
fi

if ! run_logged helper-compile bash -lc "cd '$WT' && python -m py_compile tools/aud1/f6_collect.py tools/aud1/f6_case_guard.py tools/aud1/f6_stale_result_probe.py"; then
  AUTO_REPAIR_ALLOWED_REGEX='^(tools/aud1/|tests/tools/test_aud1_f6_|tests/station/test_aud1_)'
  export AUTO_REPAIR_ALLOWED_REGEX
  fail_with_codex "$WT" "$VERIFY_CMD" "$RUN_DIR/repair-contract.txt"
fi

if ! run_logged focused bash -lc "cd '$WT' && $FOCUSED"; then
  AUTO_REPAIR_ALLOWED_REGEX='^(tools/aud1/|tests/tools/test_aud1_f6_|tests/station/test_aud1_)'
  export AUTO_REPAIR_ALLOWED_REGEX
  fail_with_codex "$WT" "$VERIFY_CMD" "$RUN_DIR/repair-contract.txt"
fi

if ! run_logged broad bash -lc "cd '$WT' && $BROAD"; then
  AUTO_REPAIR_ALLOWED_REGEX='^(tools/aud1/|tests/tools/test_aud1_f6_|tests/station/test_aud1_)'
  export AUTO_REPAIR_ALLOWED_REGEX
  fail_with_codex "$WT" "$VERIFY_CMD" "$RUN_DIR/repair-contract.txt"
fi

# This is diagnostic only. GitHub governance/advisory failures do not rewrite
# the local helper verdict and do not trigger physical F6.
if command -v gh >/dev/null 2>&1; then
  run_logged github-checks bash -lc "cd '$WT' && gh pr checks 455 || true" || true
fi

run_logged diff-check bash -lc "cd '$WT' && git diff --check"
write_receipt "PASS_HELPER_ONLY" "$HELPER_SHA" "$TREE"
log "PASS: helper qualification only. PHYSICAL F6 REMAINS UNEXECUTED/UNAUTHORIZED BY THIS SCRIPT."
log "receipt=$RUN_DIR/receipt.json"
