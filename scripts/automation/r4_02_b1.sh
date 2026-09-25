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
need python
need flock

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

VERIFY_CMD="python -m pytest -q -p no:cacheprovider tests/security/test_r4_02_archive_authority.py"

log "base=$BASE_SHA target=$TARGET_SHA tree=$TREE"

if ! run_logged candidate-compile bash -lc "cd '$TARGET_WT' && python -m py_compile residual/station/archive.py tests/security/test_r4_02_archive_authority.py"; then
  AUTO_REPAIR_ALLOWED_REGEX='^(residual/station/archive.py|tests/security/test_r4_02_archive_authority.py|scripts/security/r4_02_.*|docs/security/SNYK_R4_02.md)$'
  export AUTO_REPAIR_ALLOWED_REGEX
  fail_with_codex "$TARGET_WT" "$VERIFY_CMD" "$RUN_DIR/repair-contract.txt"
fi

# The predecessor must remain sensitive to the new oracle. We run the successor
# test file while injecting only the predecessor archive-security source.
NEGATIVE_CMD="cd '$TARGET_WT' && R4_02_ARCHIVE_SOURCE='$BASE_WT/residual/station/archive.py' python -m pytest -q -p no:cacheprovider tests/security/test_r4_02_archive_authority.py -k 'link_confinement_survives_staging_promotion'"
if ! expect_failure predecessor-reproduction bash -lc "$NEGATIVE_CMD"; then
  log "The B1 negative control no longer distinguishes predecessor from successor."
  fail_with_codex "$TARGET_WT" "$VERIFY_CMD" "$RUN_DIR/repair-contract.txt"
fi

# Fast focused pass first so diagnostics point directly at B1 if it regresses.
FOCUSED="python -m pytest -q -p no:cacheprovider tests/security/test_r4_02_archive_authority.py -k 'link_confinement_survives_staging_promotion or confined_parent_relative_symlink_survives_promotion or logical_link_target_rejects_root_underflow'"
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
