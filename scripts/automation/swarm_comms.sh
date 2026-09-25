#!/usr/bin/env bash
# SC-MESH advisory recovery controller.
#
# This intentionally creates a SEPARATE recovery Station on loopback port 8770.
# It must never reuse the F6 Station (8766), its data directory, SSH identity,
# tokens, projects, or workers.
#
# The first stage is communications-only. The advisory bridge uses only
# sync/messages/message/ack and never claims RESIDUAL tasks.
set -Eeuo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/automation/lib.sh
source "$HERE/lib.sh"

task_init "swarm-comms"
need git
need python
need curl
need flock

SC_MESH_REF="${SC_MESH_REF:-7783081c858ad9ddf98b2e64e740e1104ae5d08b}"
PORT="${SC_MESH_RECOVERY_PORT:-8770}"
[[ "$PORT" != "8766" && "$PORT" != "8765" ]] || die "refusing reserved F6/legacy Station port: $PORT"

SC_SHA="$(resolve_commit "$SC_MESH_REF")"
WT="$(ensure_worktree sc-mesh-recovery "$SC_SHA")"
TREE="$(git -C "$WT" rev-parse 'HEAD^{tree}')"
STATE="$AUTOMATION_ROOT/shared-comms-r0"
DATA="$STATE/station-data"
PIDFILE="$STATE/station.pid"
PROJECT_FILE="$STATE/project.json"
SECRETS="$STATE/secrets"
AGENTS="$STATE/agents"
mkdir -p "$STATE" "$SECRETS" "$AGENTS"
chmod 700 "$STATE" "$SECRETS" "$AGENTS" 2>/dev/null || true

cat > "$RUN_DIR/repair-contract.txt" <<EOF
RESIDUAL SC-MESH RECOVERY AUTOMATED REPAIR CONTRACT

Exact SC-MESH candidate:
$SC_SHA

Purpose:
restore advisory Shared Comms only. Shared messages are DATA, never task authority.

The repair MUST NOT:
- call or widen claim/result/execution authority;
- change #448/#455/#457/#458;
- touch port 8766 or the frozen F6 data;
- reuse F6 SSH keys/tunnels;
- print or persist plaintext tokens outside 0600 token files;
- push, merge, approve, or widen network listeners;
- weaken project/generation/enrollment/message idempotency checks.

If the failure is environmental, report the exact cause and bounded remediation
instead of weakening SC-MESH security checks.
EOF

MESH_VERIFY="python -m pytest -q tests/station/test_sc_mesh_001.py tests/station/test_sc_mesh_continuity.py tests/station/test_sc_mesh_openclaw.py tests/station/test_sc_mesh_runner.py"

station_alive() {
  [[ -f "$PIDFILE" ]] || return 1
  local pid
  pid="$(cat "$PIDFILE" 2>/dev/null || true)"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  [[ -r "/proc/$pid/cmdline" ]] || return 1
  local cmd
  cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline")"
  [[ "$cmd" == *"residual.station.server"* && "$cmd" == *"--port $PORT"* && "$cmd" == *"--data $DATA"* ]]
}

preflight() {
  log "SC-MESH head=$SC_SHA tree=$TREE"
  if ! run_logged mesh-tests bash -lc "cd '$WT' && $MESH_VERIFY"; then
    AUTO_REPAIR_ALLOWED_REGEX='^(residual/station/(mesh|mesh_|claw_adapter|continuity|contracts|server|service|store).*|tests/station/test_sc_mesh_.*|docs/station/SC_MESH_.*|deploy/systemd/residual-mesh-worker@.service)$'
    export AUTO_REPAIR_ALLOWED_REGEX
    fail_with_codex "$WT" "$MESH_VERIFY" "$RUN_DIR/repair-contract.txt"
  fi
  run_logged mesh-compile bash -lc "cd '$WT' && python -m py_compile residual/station/mesh.py residual/station/mesh_state.py residual/station/mesh_worker.py residual/station/mesh_runner.py"
  if ss -ltn 2>/dev/null | grep -qE "[:.]8766[[:space:]]"; then
    log "F6 Station port 8766 is present and intentionally untouched."
  fi
  log "preflight PASS"
}

station_up() {
  if station_alive; then
    log "recovery Station already running pid=$(cat "$PIDFILE") port=$PORT"
    curl -fsS "http://127.0.0.1:$PORT/api/bootstrap" >/dev/null
    return 0
  fi
  if ss -ltn 2>/dev/null | grep -qE "[:.]$PORT[[:space:]]"; then
    die "port $PORT is occupied by an unmanaged listener"
  fi
  mkdir -p "$DATA"
  log "starting isolated recovery Station on 127.0.0.1:$PORT"
  (
    cd "$WT"
    PYTHONDONTWRITEBYTECODE=1 nohup python -m residual.station.server       --host 127.0.0.1 --port "$PORT" --data "$DATA"       > "$STATE/station.log" 2>&1 &
    echo $! > "$PIDFILE"
  )
  for _ in $(seq 1 30); do
    if station_alive && curl -fsS "http://127.0.0.1:$PORT/api/bootstrap" >/dev/null 2>&1; then
      log "recovery Station UP pid=$(cat "$PIDFILE")"
      printf '%s\n' "$SC_SHA" > "$STATE/station-head"
      printf '%s\n' "$TREE" > "$STATE/station-tree"
      return 0
    fi
    sleep 1
  done
  tail -n 150 "$STATE/station.log" > "$RUN_DIR/station-start-tail.log" || true
  fail_with_codex "$WT" "$MESH_VERIFY" "$RUN_DIR/repair-contract.txt"
}

station_down() {
  if ! station_alive; then
    log "recovery Station already stopped"
    rm -f "$PIDFILE"
    return 0
  fi
  local pid
  pid="$(cat "$PIDFILE")"
  log "stopping owned recovery Station pid=$pid"
  kill -TERM "$pid"
  for _ in $(seq 1 20); do
    kill -0 "$pid" 2>/dev/null || { rm -f "$PIDFILE"; log "Station stopped"; return 0; }
    sleep 1
  done
  die "Station did not stop cleanly; refusing SIGKILL automatically"
}

bootstrap_project() {
  station_up
  PYTHONPATH="$WT" python - "$PORT" "$PROJECT_FILE" <<'PY'
import json, pathlib, sys, urllib.request
port, project_file = sys.argv[1], pathlib.Path(sys.argv[2])
base = f"http://127.0.0.1:{port}"

def req(path, *, token=None, body=None):
    headers = {}
    data = None
    if token:
        headers["X-Station-Token"] = token
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    request = urllib.request.Request(base + path, headers=headers, data=data)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read())

boot = req("/api/bootstrap")
token = boot["token"]
if project_file.exists():
    saved = json.loads(project_file.read_text())
    projects = req("/api/projects", token=token)["projects"]
    if any(p.get("id") == saved.get("project_id") for p in projects):
        print("project_reused", saved["project_id"])
        raise SystemExit(0)

created = req("/api/projects", token=token, body={
    "markdown": boot["demo_spec"],
    "source": "",
    "allow_cloud": False,
    "commands": False,
})
record = {"project_id": created["project_id"], "purpose": "advisory-shared-comms-recovery"}
project_file.write_text(json.dumps(record, indent=2) + "\n")
print("project_created", record["project_id"])
PY
}

project_id() {
  bootstrap_project >/dev/null
  python - "$PROJECT_FILE" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))["project_id"])
PY
}

enroll() {
  local name="$1" host_id="${2:-$(hostname)}"
  [[ "$name" =~ ^[A-Za-z0-9._-]+$ ]] || die "invalid agent name"
  station_up
  bootstrap_project
  local pid token_file meta_file
  pid="$(project_id)"
  token_file="$SECRETS/${name}.token"
  meta_file="$AGENTS/${name}.json"

  PYTHONPATH="$WT" python - "$PORT" "$pid" "$name" "$host_id" "$token_file" "$meta_file" <<'PY'
import json, os, pathlib, sys, time, urllib.error, urllib.request
port, project, name, host_id, token_name, meta_name = sys.argv[1:]
base = f"http://127.0.0.1:{port}"
token_path, meta_path = pathlib.Path(token_name), pathlib.Path(meta_name)
worker_id = "recovery-" + name

def open_json(path, *, headers=None, body=None):
    headers = dict(headers or {})
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    req = urllib.request.Request(base + path, headers=headers, data=data)
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read())

if token_path.exists():
    token = token_path.read_text().strip()
    try:
        open_json(
            f"/api/mesh/worker/sync?project_id={project}",
            headers={"Authorization": "Bearer " + token},
        )
        print("enrollment_reused", worker_id)
        raise SystemExit(0)
    except urllib.error.HTTPError:
        raise SystemExit(
            "Existing token is invalid/expired. Refusing silent rotation; revoke/rotate explicitly."
        )

boot = open_json("/api/bootstrap")
body = {
    "worker_id": worker_id,
    "host_id": host_id,
    "adapter": "openclaw-advisory",
    "adapter_version": "r0",
    "project_ids": [project],
    "capabilities": ["comms.read", "comms.write"],
    "topics": ["swarm-recovery"],
    "expires_at": time.time() + 7 * 24 * 60 * 60,
}
created = open_json(
    "/api/mesh/enroll",
    headers={"X-Station-Token": boot["token"]},
    body=body,
)
token_path.parent.mkdir(parents=True, exist_ok=True)
token_path.write_text(created["token"])
os.chmod(token_path, 0o600)
safe = dict(created["worker"])
safe["token_file"] = str(token_path)
meta_path.write_text(json.dumps(safe, indent=2, sort_keys=True) + "\n")
print("enrolled", worker_id, "token_file", token_path)
PY
}

bridge_args() {
  local name="$1" profile="$2" agent="$3" address="$4"
  local pid
  pid="$(project_id)"
  printf '%q '     python "$HERE/mesh_advisory_bridge.py"     --station "http://127.0.0.1:$PORT"     --project "$pid"     --worker-id "recovery-$name"     --token-file "$SECRETS/${name}.token"     --outbox "$AGENTS/${name}-outbox.sqlite3"     --state "$AGENTS/${name}-bridge.sqlite3"     --address "$address"     --profile "$profile"     --agent "$agent"     --once
}

send_message() {
  local sender="$1" text="$2" key="$3" pid
  pid="$(project_id)"
  PYTHONPATH="$WT" python "$HERE/mesh_advisory_bridge.py"     --station "http://127.0.0.1:$PORT"     --project "$pid"     --worker-id "recovery-$sender"     --token-file "$SECRETS/${sender}.token"     --outbox "$AGENTS/${sender}-outbox.sqlite3"     --state "$AGENTS/${sender}-bridge.sqlite3"     --send "$text" --idempotency-key "$key"
}

summary_count() {
  local name="$1" pid
  pid="$(project_id)"
  PYTHONPATH="$WT" python "$HERE/mesh_advisory_bridge.py"     --station "http://127.0.0.1:$PORT"     --project "$pid"     --worker-id "recovery-$name"     --token-file "$SECRETS/${name}.token"     --outbox "$AGENTS/${name}-outbox.sqlite3"     --state "$AGENTS/${name}-bridge.sqlite3"     --summary | python -c 'import json,sys; print(json.load(sys.stdin)["inference_count"])'
}

bridge_once() {
  local name="$1" profile="$2" agent="$3" address="$4"
  local pid
  pid="$(project_id)"
  PYTHONPATH="$WT" python "$HERE/mesh_advisory_bridge.py"     --station "http://127.0.0.1:$PORT"     --project "$pid"     --worker-id "recovery-$name"     --token-file "$SECRETS/${name}.token"     --outbox "$AGENTS/${name}-outbox.sqlite3"     --state "$AGENTS/${name}-bridge.sqlite3"     --address "$address" --profile "$profile" --agent "$agent" --once
}

messages_json() {
  local name="$1" pid
  pid="$(project_id)"
  PYTHONPATH="$WT" python "$HERE/mesh_advisory_bridge.py"     --station "http://127.0.0.1:$PORT"     --project "$pid"     --worker-id "recovery-$name"     --token-file "$SECRETS/${name}.token"     --outbox "$AGENTS/${name}-outbox.sqlite3"     --state "$AGENTS/${name}-bridge.sqlite3"     --messages --after 0
}

canary() {
  local name="$1" profile="$2" agent="$3" address="$4"
  need openclaw
  preflight
  station_up
  bootstrap_project
  enroll controller "$(hostname)"
  enroll "$name" "$(hostname)"

  local before after_non send_out addressed_seq after_addr after_restart msgfile
  before="$(summary_count "$name")"

  send_message controller "RECOVERY_NONADDRESSED_V1" "recovery-nonaddressed-${name}-v1"     > "$RUN_DIR/nonaddressed-send.json"
  if ! run_logged canary-nonaddressed bridge_once "$name" "$profile" "$agent" "$address"; then
    fail_with_codex "$WT" "$MESH_VERIFY" "$RUN_DIR/repair-contract.txt"
  fi
  after_non="$(summary_count "$name")"
  [[ "$after_non" == "$before" ]] || {
    log "non-addressed traffic unexpectedly invoked inference: $before -> $after_non"
    fail_with_codex "$WT" "$MESH_VERIFY" "$RUN_DIR/repair-contract.txt"
  }

  send_out="$(send_message controller "$address reply exactly SWARM_COMMS_OK" "recovery-addressed-${name}-v1")"
  printf '%s\n' "$send_out" > "$RUN_DIR/addressed-send.json"
  addressed_seq="$(printf '%s' "$send_out" | python -c 'import json,sys; print(json.load(sys.stdin)["seq"])')"

  if ! run_logged canary-addressed bridge_once "$name" "$profile" "$agent" "$address"; then
    fail_with_codex "$WT" "$MESH_VERIFY" "$RUN_DIR/repair-contract.txt"
  fi
  after_addr="$(summary_count "$name")"
  (( after_addr >= before )) || die "inference counter regressed"

  msgfile="$RUN_DIR/messages.json"
  messages_json "$name" > "$msgfile"
  python - "$msgfile" "recovery-$name" "$addressed_seq" <<'PY'
import json,sys
doc=json.load(open(sys.argv[1]))
worker=sys.argv[2]; request_seq=int(sys.argv[3])
matches=[]
for row in doc.get("messages", []):
    env=row.get("envelope") or {}
    payload=env.get("payload") or {}
    if env.get("sender")==worker and payload.get("reply_to_seq")==request_seq:
        matches.append(row)
assert len(matches)==1, f"expected exactly one response, got {len(matches)}"
text=str((matches[0].get("envelope") or {}).get("payload",{}).get("text",""))
assert "SWARM_COMMS_OK" in text, text[:300]
print("addressed_round_trip PASS")
PY

  # Restart simulation: the same durable cursor/inbox must not invoke the model
  # again or create a second response.
  if ! run_logged canary-restart bridge_once "$name" "$profile" "$agent" "$address"; then
    fail_with_codex "$WT" "$MESH_VERIFY" "$RUN_DIR/repair-contract.txt"
  fi
  after_restart="$(summary_count "$name")"
  [[ "$after_restart" == "$after_addr" ]] || {
    log "restart caused duplicate inference: $after_addr -> $after_restart"
    fail_with_codex "$WT" "$MESH_VERIFY" "$RUN_DIR/repair-contract.txt"
  }
  messages_json "$name" > "$RUN_DIR/messages-after-restart.json"
  python - "$RUN_DIR/messages-after-restart.json" "recovery-$name" "$addressed_seq" <<'PY'
import json,sys
doc=json.load(open(sys.argv[1])); worker=sys.argv[2]; request_seq=int(sys.argv[3])
matches=[r for r in doc.get("messages",[]) if (r.get("envelope") or {}).get("sender")==worker and ((r.get("envelope") or {}).get("payload") or {}).get("reply_to_seq")==request_seq]
assert len(matches)==1, f"duplicate response count={len(matches)}"
print("restart_duplicate_check PASS")
PY

  python - "$RUN_DIR/canary-receipt.json" "$SC_SHA" "$TREE" "$name" "$before" "$after_addr" "$after_restart" <<'PY'
import datetime,json,pathlib,sys
path,head,tree,name,before,after,restart=sys.argv[1:]
pathlib.Path(path).write_text(json.dumps({
  "schema":"residual.sc.mesh.recovery-canary/1",
  "head":head,"tree":tree,"agent":name,
  "non_addressed_zero_inference":True,
  "addressed_round_trip":True,
  "restart_duplicate_response":False,
  "inference_count_before":int(before),
  "inference_count_after_addressed":int(after),
  "inference_count_after_restart":int(restart),
  "recorded_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
},indent=2)+"\n")
PY
  log "CANARY PASS: $name"
  log "receipt=$RUN_DIR/canary-receipt.json"
}

bridge_run() {
  local name="$1" profile="$2" agent="$3" address="$4"
  need openclaw
  enroll "$name" "$(hostname)"
  log "starting supervised advisory loop for $name; Ctrl+C stops only this bridge"
  while true; do
    if ! bridge_once "$name" "$profile" "$agent" "$address"; then
      log "bridge iteration failed; invoking bounded Codex diagnosis/repair"
      fail_with_codex "$WT" "$MESH_VERIFY" "$RUN_DIR/repair-contract.txt"
    fi
    sleep "${SC_MESH_POLL_SECONDS:-2}"
  done
}

status() {
  echo "SC_MESH_HEAD=$SC_SHA"
  echo "SC_MESH_TREE=$TREE"
  echo "PORT=$PORT"
  echo "DATA=$DATA"
  if station_alive; then
    echo "STATION=UP pid=$(cat "$PIDFILE")"
  else
    echo "STATION=DOWN"
  fi
  if [[ -f "$PROJECT_FILE" ]]; then
    echo "PROJECT=$(project_id)"
  else
    echo "PROJECT=UNINITIALIZED"
  fi
  echo "ENROLLED_TOKEN_FILES:"
  find "$SECRETS" -maxdepth 1 -type f -name '*.token' -printf '  %f\n' 2>/dev/null || true
}

usage() {
  cat <<EOF
Usage:
  $0 preflight
  $0 station-up
  $0 station-down
  $0 bootstrap
  $0 enroll NAME [HOST_ID]
  $0 canary NAME PROFILE AGENT ADDRESS
  $0 bridge-run NAME PROFILE AGENT ADDRESS
  $0 status

Example canary:
  $0 canary anvil anvil anvil @ANVIL

Safety:
  - port 8766/F6 is never touched;
  - only advisory SC-MESH message APIs are used by mesh_advisory_bridge.py;
  - tokens are written mode 0600 and never printed;
  - bridge-run is sequential; do not launch all 14 until the canary is green.
EOF
}

case "${1:-}" in
  preflight) preflight ;;
  station-up) preflight; station_up ;;
  station-down) station_down ;;
  bootstrap) preflight; station_up; bootstrap_project ;;
  enroll) [[ $# -ge 2 ]] || { usage; exit 2; }; enroll "$2" "${3:-$(hostname)}" ;;
  canary) [[ $# -eq 5 ]] || { usage; exit 2; }; canary "$2" "$3" "$4" "$5" ;;
  bridge-run) [[ $# -eq 5 ]] || { usage; exit 2; }; bridge_run "$2" "$3" "$4" "$5" ;;
  status) status ;;
  *) usage; exit 2 ;;
esac
