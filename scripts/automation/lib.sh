#!/usr/bin/env bash
# Shared automation primitives for RESIDUAL hardening/recovery runners.
#
# Design goals:
# - idempotent: reruns reuse exact worktrees/state instead of silently rotating;
# - evidence-first: every command is logged with a machine-readable receipt;
# - fail-closed: an exact candidate never becomes "green" because Codex repaired
#   a different worktree;
# - autonomous-but-bounded: on failure Codex may repair only an isolated local
#   branch/worktree. It never pushes, merges, approves, or touches credentials.
set -Eeuo pipefail

AUTOMATION_ROOT="${RESIDUAL_AUTOMATION_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/residual-automation}"
mkdir -p "$AUTOMATION_ROOT"/{runs,worktrees,repairs,locks}

log() {
  # Diagnostics belong on stderr so helper functions can safely return machine
  # values on stdout and be used inside command substitution.
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2
}

die() {
  log "ERROR: $*"
  return 1
}

need() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

repo_root() {
  git rev-parse --show-toplevel
}

task_init() {
  TASK_NAME="$1"
  RUN_ID="${TASK_NAME}-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  RUN_DIR="$AUTOMATION_ROOT/runs/$RUN_ID"
  mkdir -p "$RUN_DIR"
  exec > >(tee -a "$RUN_DIR/console.log") 2>&1

  # One active runner of a given task at a time. A second invocation waits
  # rather than racing the same worktree/state.
  exec 9>"$AUTOMATION_ROOT/locks/${TASK_NAME}.lock"
  flock 9
  log "task=$TASK_NAME run_id=$RUN_ID evidence=$RUN_DIR"
  capture_diagnostics
}

capture_diagnostics() {
  {
    echo "captured_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "hostname=$(hostname 2>/dev/null || true)"
    echo "uname=$(uname -a 2>/dev/null || true)"
    echo "uid=$(id -u 2>/dev/null || true)"
    echo "cwd=$(pwd)"
    echo "git=$(git --version 2>/dev/null || true)"
    echo "python=$(python --version 2>&1 || true)"
    echo "codex=$(codex --version 2>&1 || true)"
    echo "disk:"
    df -h . 2>/dev/null || true
    echo "memory:"
    free -h 2>/dev/null || true
    echo "listeners:"
    ss -ltn 2>/dev/null || true
    if command -v nvidia-smi >/dev/null 2>&1; then
      echo "gpu:"
      nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version --format=csv,noheader 2>/dev/null || true
    fi
  } > "$RUN_DIR/diagnostics.txt"
}

resolve_commit() {
  local root ref
  root="$(repo_root)"
  ref="$1"
  if ! git -C "$root" cat-file -e "$ref^{commit}" 2>/dev/null; then
    log "fetching ref $ref"
    git -C "$root" fetch --no-tags origin "$ref" >/dev/null 2>&1 || true
  fi
  git -C "$root" rev-parse "$ref^{commit}"
}

ensure_worktree() {
  local task sha root dir
  task="$1"
  sha="$2"
  root="$(repo_root)"
  dir="$AUTOMATION_ROOT/worktrees/${task}-${sha:0:12}"

  if [[ -e "$dir/.git" ]]; then
    local observed
    observed="$(git -C "$dir" rev-parse HEAD)"
    [[ "$observed" == "$sha" ]] || die "managed worktree $dir is $observed, expected $sha"
    [[ -z "$(git -C "$dir" status --porcelain=v1)" ]] || die "managed worktree is dirty: $dir"
  else
    mkdir -p "$(dirname "$dir")"
    git -C "$root" worktree add --detach "$dir" "$sha" >/dev/null
  fi
  printf '%s\n' "$dir"
}

run_logged() {
  local label
  label="$1"
  shift
  local logfile="$RUN_DIR/${label}.log"
  local cmdfile="$RUN_DIR/${label}.command"
  printf '%q ' "$@" > "$cmdfile"
  printf '\n' >> "$cmdfile"
  log "START $label: $(cat "$cmdfile")"
  set +e
  "$@" > >(tee "$logfile") 2>&1
  local rc=$?
  set -e
  printf '%s\n' "$rc" > "$RUN_DIR/${label}.exit"
  log "END $label rc=$rc"
  return "$rc"
}

expect_failure() {
  local label
  label="$1"
  shift
  if run_logged "$label" "$@"; then
    log "EXPECTED FAILURE DID NOT OCCUR: $label"
    return 1
  fi
  log "expected negative control failed as required: $label"
  return 0
}

write_receipt() {
  local status="$1" head="$2" tree="$3"
  python - "$RUN_DIR/receipt.json" "$TASK_NAME" "$status" "$head" "$tree" <<'PY'
import json, pathlib, sys, datetime
path, task, status, head, tree = sys.argv[1:]
pathlib.Path(path).write_text(json.dumps({
    "schema": "residual.automation.receipt/1",
    "task": task,
    "status": status,
    "head": head,
    "tree": tree,
    "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
}, indent=2) + "\n")
PY
}

repair_worktree() {
  local task="$1" base_sha="$2" root branch dir
  root="$(repo_root)"
  branch="auto-repair/${task}-${base_sha:0:12}"
  dir="$AUTOMATION_ROOT/repairs/${task}-${base_sha:0:12}"

  if [[ -e "$dir/.git" ]]; then
    printf '%s\n' "$dir"
    return 0
  fi
  if git -C "$root" show-ref --verify --quiet "refs/heads/$branch"; then
    git -C "$root" worktree add "$dir" "$branch" >/dev/null
  else
    git -C "$root" worktree add -b "$branch" "$dir" "$base_sha" >/dev/null
  fi
  printf '%s\n' "$dir"
}

codex_repair() {
  local task="$1" candidate_dir="$2" verify_cmd="$3" contract_file="$4"
  local base_sha repair prompt final session rc
  base_sha="$(git -C "$candidate_dir" rev-parse HEAD)"
  repair="$(repair_worktree "$task" "$base_sha")"
  prompt="$RUN_DIR/codex-repair-prompt.txt"
  final="$RUN_DIR/codex-final.txt"
  session="$RUN_DIR/codex-session.jsonl"

  {
    cat "$contract_file"
    cat <<EOF

AUTOMATION FAILURE CONTEXT

Exact failing candidate: $base_sha
Repair worktree: $repair
Evidence directory: $RUN_DIR

The exact candidate remains failed even if you repair this isolated worktree.
You may edit only the repair worktree.
Do not push, merge, approve PRs, alter credentials, or modify external host state.
Do not print environment variables or secrets.
Diagnose from the logs below, make the smallest repair, and run the verifier.

Verifier:
$verify_cmd

Recent diagnostics/log tails:
EOF
    for file in "$RUN_DIR"/*.log; do
      [[ -f "$file" ]] || continue
      echo
      echo "===== $(basename "$file") ====="
      tail -n 180 "$file"
    done
  } > "$prompt"

  if [[ "${AUTO_CODEX_ON_FAILURE:-1}" != "1" ]]; then
    log "Codex auto-repair disabled (AUTO_CODEX_ON_FAILURE!=1)"
    return 2
  fi
  if ! command -v codex >/dev/null 2>&1; then
    log "Codex not installed; failure evidence retained at $RUN_DIR"
    return 127
  fi

  local -a cmd
  cmd=(codex)
  if [[ -n "${AUTO_CODEX_PROFILE:-}" ]]; then
    cmd+=(--profile "$AUTO_CODEX_PROFILE")
  fi
  cmd+=(exec -C "$repair" --sandbox workspace-write --json --output-last-message "$final" -)

  log "invoking Codex in isolated repair worktree: $repair"
  set +e
  timeout --signal=INT "${AUTO_CODEX_TIMEOUT:-1200}" "${cmd[@]}" < "$prompt" > "$session" 2> "$RUN_DIR/codex-stderr.txt"
  rc=$?
  set -e
  log "Codex exited rc=$rc"

  git -C "$repair" diff --binary "$base_sha" > "$RUN_DIR/repair.patch" || true
  git -C "$repair" diff --stat "$base_sha" > "$RUN_DIR/repair.stat" || true
  git -C "$repair" diff --name-only "$base_sha" > "$RUN_DIR/repair.files" || true

  if [[ -n "${AUTO_REPAIR_ALLOWED_REGEX:-}" && -s "$RUN_DIR/repair.files" ]]; then
    if grep -Ev "$AUTO_REPAIR_ALLOWED_REGEX" "$RUN_DIR/repair.files" > "$RUN_DIR/repair.disallowed"; then
      log "Codex changed disallowed paths:"
      cat "$RUN_DIR/repair.disallowed"
      return 3
    fi
  fi

  log "rerunning verifier in repair worktree"
  if (cd "$repair" && bash -lc "$verify_cmd") > "$RUN_DIR/post-repair-verify.log" 2>&1; then
    log "repair worktree verifier PASS; exact candidate remains failed"
    if [[ "${AUTO_CODEX_COMMIT:-0}" == "1" && -n "$(git -C "$repair" status --porcelain=v1)" ]]; then
      git -C "$repair" add -A
      git -C "$repair" commit -m "auto($task): remediate failed diagnostic runner"
      log "local repair commit created; nothing was pushed"
    fi
    return 0
  fi
  log "repair verifier still failing"
  return 4
}

fail_with_codex() {
  local candidate_dir="$1" verify_cmd="$2" contract_file="$3"
  local head tree
  head="$(git -C "$candidate_dir" rev-parse HEAD)"
  tree="$(git -C "$candidate_dir" rev-parse 'HEAD^{tree}')"
  write_receipt "CANDIDATE_FAIL" "$head" "$tree"
  if codex_repair "$TASK_NAME" "$candidate_dir" "$verify_cmd" "$contract_file"; then
    log "AUTO_REPAIR_READY: review $RUN_DIR/repair.patch and isolated repair worktree"
    # Non-zero by design: the exact candidate that was requested still failed.
    exit 10
  fi
  log "AUTO_REPAIR_FAILED_OR_BLOCKED"
  exit 20
}
