#!/usr/bin/env python3
"""Strict AUD-1 F6 physical-evidence front end for PR #403.

Uses the existing read-only collector primitives, but adds release-critical guards:
raw git identity (so 40-char SHAs are not redacted), live Station process provenance,
required phase/remote artifacts, semantic validation of runner-side evidence, timing
and ownership validation, explicit stale-result HTTP 403 proof bound to the original
task/lease, and closed-world manifest verification.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("f6_collect_base", HERE / "f6_collect.py")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)

TARGET_SHA = base.TARGET_SHA
SCHEMA = "residual.aud1.f6.physical.v2"
REMOTE_SCHEMA = "residual.aud1.f6.remote.v2"
STALE_SCHEMA = "residual.aud1.f6.stale-probe.v2"
GRACE = 180.0
SURRENDER_TEXT = "Runner authority was surrendered after persistent heartbeat loss"
STALE_REJECTION_TEXT = "Task authority belongs to another runner"

LABELS = {
    "F6-A-inside-window": [
        "00-preflight",
        "01-owned-before-interrupt",
        "02-transport-down",
        "03-reconnected-inside-window",
        "04-terminal",
    ],
    "F6-B-outside-window": [
        "00-preflight",
        "01-owned-before-interrupt",
        "02-transport-down",
        "03-after-worker-authority-grace",
        "04-reassigned",
        "05-old-runner-returned",
        "06-stale-result-boundary",
    ],
}
ATTACH = {
    "F6-A-inside-window": [
        "remote-01-owned-before.json",
        "remote-02-transport-down.json",
        "remote-03-reconnected.json",
        "remote-04-terminal.json",
    ],
    "F6-B-outside-window": [
        "remote-01-owned-before.json",
        "remote-02-transport-down.json",
        "remote-03-after-grace.json",
        "remote-04-reassigned.json",
        "remote-05-old-returned.json",
        "stale-result-rejection.json",
    ],
}
OLD_RUNNER_ATTACH = {
    "F6-A-inside-window": [
        "remote-01-owned-before.json",
        "remote-02-transport-down.json",
        "remote-03-reconnected.json",
        "remote-04-terminal.json",
    ],
    "F6-B-outside-window": [
        "remote-01-owned-before.json",
        "remote-02-transport-down.json",
        "remote-03-after-grace.json",
        "remote-05-old-returned.json",
    ],
}


def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_utc(value):
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def git(repo, *args):
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def raw_identity(repo):
    repo = pathlib.Path(repo).resolve()
    rh, head, eh = git(repo, "rev-parse", "HEAD")
    rs, status, es = git(repo, "status", "--porcelain=v1")
    rt, tree, et = git(repo, "rev-parse", "HEAD^{tree}")
    return {
        "path": str(repo),
        "expected_sha": TARGET_SHA,
        "head_sha": head,
        "tree_sha": tree,
        "tracked_or_untracked_changes": status.splitlines() if status else [],
        "exact_head": rh == 0 and head == TARGET_SHA,
        "clean_worktree": rs == 0 and not status,
        "git_errors": [item for item in (eh, es, et) if item],
    }


def alive(pid):
    try:
        pid = int(pid)
    except Exception:
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def within(child, parent):
    child_path = pathlib.Path(child).resolve()
    parent_path = pathlib.Path(parent).resolve()
    return child_path == parent_path or parent_path in child_path.parents


def station_record(path, repo, db, url):
    path = pathlib.Path(path).resolve()
    sidecar = pathlib.Path(str(path) + ".sha256")
    errors = []
    if not path.is_file():
        return None, ["station launch record missing"]
    if not sidecar.is_file():
        return None, ["station launch record digest missing"]
    try:
        expected = sidecar.read_text(encoding="utf-8").split()[0]
        actual = base.sha256_file(path)
        record = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [f"station launch record unreadable: {exc}"]

    if expected != actual:
        errors.append("station launch record digest mismatch")

    repo_path = pathlib.Path(repo).resolve()
    db_path = pathlib.Path(db).resolve()
    module_path = pathlib.Path(record.get("server_module", ".")).resolve()
    tree_rc, observed_tree, tree_err = git(repo_path, "rev-parse", "HEAD^{tree}")

    if record.get("schema") != "residual.aud1.f6.station-launch.v1":
        errors.append("station launch schema mismatch")
    if record.get("candidate_head") != TARGET_SHA:
        errors.append("station process not bound to target candidate")
    if tree_rc != 0:
        errors.append("station candidate tree could not be resolved" + (f": {tree_err}" if tree_err else ""))
    elif record.get("candidate_tree") != observed_tree:
        errors.append("station process candidate tree mismatch")
    if pathlib.Path(record.get("candidate_repo", ".")).resolve() != repo_path:
        errors.append("station process candidate repo mismatch")
    if not within(module_path, repo_path) or not module_path.is_file():
        errors.append("station module not inside exact candidate checkout")
    elif record.get("server_module_sha256") != base.sha256_file(module_path):
        errors.append("station module bytes changed since launch")
    if pathlib.Path(record.get("station_data", ".")).resolve() != db_path.parent:
        errors.append("station data/DB mismatch")
    if record.get("station_url", "").rstrip("/") != url.rstrip("/"):
        errors.append("station URL mismatch")
    if not alive(record.get("pid")):
        errors.append("station launch PID is not alive")

    safe = base.redact(record)
    # Cryptographic identity material is public evidence, not credential material.
    # The generic opaque-value redactor intentionally fails closed for arbitrary
    # high-entropy strings, so restore only the fields already verified above.
    for key in ("candidate_head", "candidate_tree", "server_module_sha256"):
        if key in record:
            safe[key] = record[key]
    safe["record_sha256"] = actual
    safe["process_alive"] = alive(record.get("pid"))
    return safe, errors


def outdir(root, case):
    return pathlib.Path(root).resolve() / case


def capture(args):
    out = outdir(args.output, args.case)
    out.mkdir(parents=True, exist_ok=True)

    identity = raw_identity(args.candidate_repo)
    if not identity["exact_head"]:
        raise SystemExit(
            f"REFUSE: candidate is {identity['head_sha']!r}, expected {TARGET_SHA}"
        )
    if not identity["clean_worktree"]:
        raise SystemExit("REFUSE: candidate checkout is dirty")

    process, errors = station_record(
        args.station_record,
        args.candidate_repo,
        args.db,
        args.station_url,
    )
    if errors:
        raise SystemExit("REFUSE: " + "; ".join(errors))

    probe = base.public_probe(args.station_url)
    if probe.get("status") != 200 or probe.get("authority_key_names_present"):
        raise SystemExit("REFUSE: public bootstrap metadata-only proof failed")

    seq = len(list(out.glob("snapshot-*.json"))) + 1
    payload = {
        "schema": SCHEMA,
        "case": args.case,
        "label": args.label,
        "candidate": identity,
        "station_process": process,
        "environment": base.environment_snapshot(),
        "station": base.station_snapshot(args.db, args.project, args.task),
        "public_probe": probe,
    }
    path = out / f"snapshot-{seq:03d}-{args.label}.json"
    base.atomic_json(path, payload)
    print(path)
    return 0


def delegate(name, args):
    return getattr(base, name)(args)


def readshots(out):
    snapshots = {}
    for path in sorted(out.glob("snapshot-*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            snapshots[value.get("label")] = value
        except Exception:
            pass
    return snapshots


def ledger(out):
    path = out / "operator-ledger.jsonl"
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            rows.append({"_invalid": line})
    return rows


def ltime(rows, kind, last=False):
    values = []
    for row in rows:
        if row.get("kind") == kind and row.get("timestamp"):
            try:
                values.append(parse_utc(row["timestamp"]))
            except Exception:
                pass
    return values[-1 if last else 0] if values else None


def task(snapshot):
    tasks = snapshot.get("station", {}).get("tasks", [])
    return tasks[0].get("value", {}) if tasks else {}


def task_id(snapshot):
    tasks = snapshot.get("station", {}).get("tasks", [])
    return tasks[0].get("id") if tasks else None


def event_rows(snapshot):
    return snapshot.get("station", {}).get("events", [])


def event_value(row):
    value = row.get("value") if isinstance(row, dict) else None
    return value if isinstance(value, dict) else {}


def validate_event_chain(snapshot, label):
    errors = []
    previous = "0" * 64
    last_seq = 0
    for row in event_rows(snapshot):
        if not isinstance(row, dict):
            errors.append(f"snapshot {label} contains non-object event")
            continue
        seq = row.get("seq")
        if type(seq) is not int or seq <= last_seq:
            errors.append(f"snapshot {label} event sequence is not strictly increasing")
            continue
        value = event_value(row)
        if not value:
            errors.append(f"snapshot {label} event {seq} lacks structured value")
            continue
        if row.get("prev_hash") != previous:
            errors.append(f"snapshot {label} event {seq} prev_hash mismatch")
        expected = base.sha256_bytes(
            base.canonical({"previous": previous, "event": value}).encode("utf-8")
        )
        if row.get("hash") != expected:
            errors.append(f"snapshot {label} event {seq} hash mismatch")
        previous = row.get("hash") or previous
        last_seq = seq
    return errors


def validate_snapshot_sequence(shots, case):
    errors = []
    previous_events = []
    previous_monotonic = None
    for label in LABELS[case]:
        snapshot = shots.get(label)
        if not snapshot:
            continue
        station = snapshot.get("station", {})
        captured = station.get("captured_at")
        try:
            parse_utc(captured)
        except Exception:
            errors.append(f"snapshot {label} has invalid capture timestamp")

        current_monotonic = station.get("captured_monotonic_ns")
        if type(current_monotonic) is not int or current_monotonic <= 0:
            errors.append(f"snapshot {label} lacks monotonic capture time")
        elif previous_monotonic is not None and current_monotonic <= previous_monotonic:
            errors.append(f"snapshot {label} monotonic capture order regressed")
        else:
            previous_monotonic = current_monotonic

        current_events = event_rows(snapshot)
        if len(current_events) < len(previous_events):
            errors.append(f"snapshot {label} event history regressed")
        else:
            for old, new in zip(previous_events, current_events):
                if old.get("seq") != new.get("seq") or old.get("hash") != new.get("hash"):
                    errors.append(f"snapshot {label} event history is not a prefix extension")
                    break
        previous_events = current_events
    return errors


def find_event(snapshot, event_type, tid, *, attempt=None, actor=None, after_seq=0):
    matches = []
    for row in event_rows(snapshot):
        value = event_value(row)
        if row.get("seq", 0) <= after_seq:
            continue
        if value.get("event_type") != event_type or value.get("task_id") != tid:
            continue
        if attempt is not None and value.get("attempt") != attempt:
            continue
        if actor is not None and value.get("actor") != actor:
            continue
        matches.append((row, value))
    return matches


def validate_f6_b_authority_order(shots):
    errors = []
    before_snapshot = shots.get("01-owned-before-interrupt", {})
    down_snapshot = shots.get("02-transport-down", {})
    reassigned_snapshot = shots.get("04-reassigned", {})
    before = task(before_snapshot)
    down_task = task(down_snapshot)
    reassigned = task(reassigned_snapshot)
    tid = task_id(before_snapshot)

    old_owner = before.get("owner")
    old_lease = before.get("lease")
    old_attempt = before.get("attempt")
    if not old_owner or not old_lease or type(old_attempt) is not int:
        return ["pre-interrupt authority tuple is incomplete"]

    if down_task.get("owner") != old_owner or down_task.get("lease") != old_lease:
        errors.append("transport-down snapshot does not retain the original authority tuple")
    if down_task.get("attempt") != old_attempt:
        errors.append("transport-down attempt differs from pre-interrupt attempt")

    new_owner = reassigned.get("owner")
    new_attempt = reassigned.get("attempt")
    if not new_owner or new_owner == old_owner:
        errors.append("reassignment to different owner not proven")
    if type(new_attempt) is not int or new_attempt != old_attempt + 1:
        errors.append("reassignment attempt is not the next task attempt")

    down_events = event_rows(down_snapshot)
    down_seq = max((row.get("seq", 0) for row in down_events if isinstance(row, dict)), default=0)
    expired = find_event(
        reassigned_snapshot, "worker.expired", tid, attempt=old_attempt, after_seq=down_seq
    )
    if not expired:
        errors.append("natural worker expiry/recovery event not proven after transport down")
        return errors
    expired_row, expired_value = expired[-1]
    if expired_value.get("data", {}).get("from") != "running":
        errors.append("worker expiry event is not recovery from running authority")

    lease_until = down_task.get("lease_until")
    try:
        lease_until = float(lease_until)
        expired_at = parse_utc(expired_value.get("timestamp")).timestamp()
        if expired_at + 1e-6 < lease_until:
            errors.append("worker expiry event predates the authoritative lease deadline")
    except Exception:
        errors.append("natural lease-expiry timing is not machine-verifiable")

    claims = find_event(
        reassigned_snapshot,
        "task.claimed",
        tid,
        attempt=new_attempt if type(new_attempt) is int else None,
        actor=new_owner,
        after_seq=expired_row.get("seq", 0),
    )
    if not claims:
        errors.append("replacement claim is not proven after natural recovery")
    return errors


def attached(out, name):
    path = out / "attachments" / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def runner_identity(record):
    process = record.get("runner_process")
    if not isinstance(process, dict):
        return None
    pid = process.get("ProcessId")
    created = process.get("CreationDate")
    if not pid or not created:
        return None
    return (record.get("hostname"), int(pid), str(created))


def tcp_reachable(record):
    probe = record.get("tcp_probe")
    return isinstance(probe, dict) and probe.get("TcpTestSucceeded") is True


def residual_worker_running(record):
    process = record.get("runner_process")
    return (
        record.get("runner_process_found") is True
        and isinstance(process, dict)
        and process.get("IsResidualWorker") is True
        and process.get("ProcessId") == record.get("runner_pid_requested")
    )


def validate_remote_evidence(out, case):
    """Validate runner-side phase evidence, not merely attachment existence."""
    errors = []
    names = [name for name in ATTACH[case] if name.startswith("remote-")]
    records = {}

    for name in names:
        record = attached(out, name)
        if not record:
            errors.append(f"remote evidence missing/invalid: {name}")
            continue
        records[name] = record
        if record.get("schema") != REMOTE_SCHEMA:
            errors.append(f"remote evidence schema mismatch: {name}")
        requested_pid = record.get("runner_pid_requested")
        if type(requested_pid) is not int or requested_pid <= 0:
            errors.append(f"remote evidence lacks valid runner PID: {name}")

    before = records.get("remote-01-owned-before.json")
    down = records.get("remote-02-transport-down.json")
    old_pid = before.get("runner_pid_requested") if before else None
    old_host = before.get("hostname") if before else None
    old_identity = runner_identity(before) if before else None

    if before:
        if old_identity is None:
            errors.append("pre-interrupt runner process identity is incomplete")
        if not residual_worker_running(before):
            errors.append("pre-interrupt evidence is not bound to a live RESIDUAL worker")
        if before.get("runner_has_station_connection") is not True:
            errors.append("pre-interrupt runner lacks Station TCP connection")
        if not tcp_reachable(before):
            errors.append("pre-interrupt Station TCP probe is not reachable")

    if down:
        if down.get("runner_pid_requested") != old_pid or down.get("hostname") != old_host:
            errors.append("transport-down evidence is not from the same old runner")
        if not residual_worker_running(down):
            errors.append("transport-down evidence lost the original live RESIDUAL worker")
        if old_identity and runner_identity(down) != old_identity:
            errors.append("transport-down process identity differs from pre-interrupt runner")
        if down.get("runner_has_station_connection") is not False:
            errors.append("transport-down runner still owns a Station TCP connection")
        if tcp_reachable(down):
            errors.append("transport-down Station TCP probe still succeeds")

    if case == "F6-A-inside-window":
        reconnect = records.get("remote-03-reconnected.json")
        terminal = records.get("remote-04-terminal.json")

        if reconnect:
            if reconnect.get("runner_pid_requested") != old_pid or reconnect.get("hostname") != old_host:
                errors.append("inside-window reconnect evidence is not from the same old runner")
            if not residual_worker_running(reconnect):
                errors.append("inside-window reconnect did not retain the original RESIDUAL worker")
            if old_identity and runner_identity(reconnect) != old_identity:
                errors.append("inside-window reconnect process identity changed")
            if reconnect.get("runner_has_station_connection") is not True:
                errors.append("inside-window reconnect did not restore runner Station connection")
            if not tcp_reachable(reconnect):
                errors.append("inside-window reconnect Station TCP probe did not recover")

        if terminal:
            if terminal.get("runner_pid_requested") != old_pid or terminal.get("hostname") != old_host:
                errors.append("terminal evidence is not from the same old runner")
            # A --once runner may exit naturally after submission, so terminal evidence may
            # legitimately show no process. If it is still alive, it must still be the same one.
            if terminal.get("runner_process_found") is True:
                if not residual_worker_running(terminal):
                    errors.append("terminal live process is not the expected RESIDUAL worker")
                elif old_identity and runner_identity(terminal) != old_identity:
                    errors.append("terminal runner process identity changed")
    else:
        after_grace = records.get("remote-03-after-grace.json")
        reassigned = records.get("remote-04-reassigned.json")
        old_returned = records.get("remote-05-old-returned.json")

        if after_grace:
            if after_grace.get("runner_pid_requested") != old_pid or after_grace.get("hostname") != old_host:
                errors.append("after-grace evidence is not from the same old runner")
            runner_log = after_grace.get("runner_log")
            tail = runner_log.get("Tail", []) if isinstance(runner_log, dict) else []
            joined = "\n".join(str(item) for item in tail)
            if SURRENDER_TEXT not in joined:
                errors.append("after-grace evidence lacks WorkerAuthorityLost surrender proof")
            if after_grace.get("runner_process_found") is not False:
                errors.append("old runner process did not exit after authority surrender")
            if after_grace.get("runner_has_station_connection") is not False:
                errors.append("after-grace old runner still owns a Station TCP connection")
            if tcp_reachable(after_grace):
                errors.append("after-grace Station TCP probe unexpectedly succeeds")

        if reassigned:
            if not residual_worker_running(reassigned):
                errors.append("reassigned evidence is not bound to a live RESIDUAL worker")
            new_identity = runner_identity(reassigned)
            if not new_identity:
                errors.append("reassigned-runner process identity is incomplete")
            elif old_identity and new_identity == old_identity:
                errors.append("reassignment remote evidence is still the old runner process")
            if (
                reassigned.get("hostname") == old_host
                and reassigned.get("runner_pid_requested") == old_pid
            ):
                errors.append("reassignment reused the old runner PID on the same host")
            if reassigned.get("runner_has_station_connection") is not True:
                errors.append("new reassigned runner lacks Station TCP connection")
            if not tcp_reachable(reassigned):
                errors.append("new reassigned runner cannot reach Station")

        if old_returned:
            if old_returned.get("runner_pid_requested") != old_pid or old_returned.get("hostname") != old_host:
                errors.append("old-return evidence is not from the original runner host/PID")
            if old_returned.get("runner_process_found") is not False:
                errors.append("surrendered old runner process unexpectedly exists after reconnect")
            if old_returned.get("runner_has_station_connection") is not False:
                errors.append("old runner reacquired a Station TCP connection after surrender")
            if not tcp_reachable(old_returned):
                # The host must again reach Station while the surrendered process remains gone;
                # otherwise a 403/no-connection observation could be explained by the tunnel
                # still being broken rather than by surrendered authority.
                errors.append("old-runner return did not restore host-level Station reachability")

    return errors


def validate_stale_probe(stale, before_snapshot):
    errors = []
    if not stale:
        return ["stale-result rejection artifact missing/invalid"]

    if stale.get("schema") != STALE_SCHEMA:
        errors.append("stale probe schema mismatch")
    if stale.get("observed_status") != 403 or stale.get("rejected") is not True:
        errors.append("stale result not explicitly rejected with HTTP 403")
    if stale.get("accepted") is not False:
        errors.append("stale result accepted flag is not exactly false")
    if stale.get("credential_value_retained") is not False:
        errors.append("stale probe retained credential material")

    expected_project = before_snapshot.get("station", {}).get("project_id")
    expected_task = task_id(before_snapshot)
    expected_authority = task(before_snapshot)
    expected_lease = expected_authority.get("lease")
    expected_lease_fingerprint = (
        "sha256:" + base.sha256_bytes(str(expected_lease).encode("utf-8"))
        if expected_lease else None
    )
    if stale.get("project_id") != expected_project:
        errors.append("stale probe project does not match pre-interrupt project")
    if stale.get("task_id") != expected_task:
        errors.append("stale probe task does not match pre-interrupt task")
    if stale.get("lease_fingerprint") != expected_lease_fingerprint:
        errors.append("stale probe lease does not match pre-interrupt lease")
    if stale.get("attempt") != expected_authority.get("attempt"):
        errors.append("stale probe attempt does not match pre-interrupt attempt")
    if stale.get("owner") != expected_authority.get("owner"):
        errors.append("stale probe owner does not match pre-interrupt owner")

    response_excerpt = stale.get("response_excerpt", "")
    if STALE_REJECTION_TEXT not in response_excerpt:
        errors.append(
            "stale probe 403 is not bound to the expected reassigned-authority denial"
        )
    return errors


def validate(out, case):
    errors = []
    shots = readshots(out)
    rows = ledger(out)

    for label in LABELS[case]:
        snapshot = shots.get(label)
        if not snapshot:
            errors.append(f"missing required snapshot: {label}")
            continue
        if not snapshot.get("candidate", {}).get("exact_head"):
            errors.append(f"snapshot {label} not target-bound")
        if not snapshot.get("candidate", {}).get("clean_worktree"):
            errors.append(f"snapshot {label} dirty")
        if snapshot.get("station_process", {}).get("candidate_head") != TARGET_SHA:
            errors.append(f"snapshot {label} lacks Station process binding")
        if not snapshot.get("station_process", {}).get("record_sha256"):
            errors.append(f"snapshot {label} lacks Station witness digest")
        probe = snapshot.get("public_probe") or {}
        if probe.get("status") != 200 or probe.get("authority_key_names_present"):
            errors.append(f"snapshot {label} bootstrap proof failed")
        if snapshot.get("station", {}).get("sqlite_integrity") != "ok":
            errors.append(f"snapshot {label} SQLite integrity failed")
        errors.extend(validate_event_chain(snapshot, label))

    errors.extend(validate_snapshot_sequence(shots, case))

    for name in ATTACH[case]:
        if not (out / "attachments" / name).is_file():
            errors.append(f"missing required attachment: {name}")
        if not (out / "attachments" / (name + ".meta.json")).is_file():
            errors.append(f"missing attachment metadata: {name}")

    errors.extend(validate_remote_evidence(out, case))

    down = ltime(rows, "TUNNEL_DOWN")
    up = ltime(rows, "TUNNEL_UP", True)
    if not down:
        errors.append("operator ledger lacks TUNNEL_DOWN")
    if not any(row.get("kind") == "HITL" for row in rows):
        errors.append("operator ledger lacks ownership confirmation")
    if any(row.get("_invalid") for row in rows):
        errors.append("operator ledger contains invalid JSON")

    if case == "F6-A-inside-window":
        if not up:
            errors.append("operator ledger lacks TUNNEL_UP")
        elif down:
            seconds = (up - down).total_seconds()
            if not 0 <= seconds < GRACE:
                errors.append(f"inside-window reconnect timing invalid: {seconds:.3f}s")

        before = task(shots.get("01-owned-before-interrupt", {}))
        reconnect = task(shots.get("03-reconnected-inside-window", {}))
        if not before.get("owner") or before.get("owner") != reconnect.get("owner"):
            errors.append("inside-window same owner not proven")
        if not before.get("lease") or before.get("lease") != reconnect.get("lease"):
            errors.append("inside-window same lease not proven")
    else:
        down_time = (
            shots.get("02-transport-down", {})
            .get("station", {})
            .get("captured_at")
        )
        grace_time = (
            shots.get("03-after-worker-authority-grace", {})
            .get("station", {})
            .get("captured_at")
        )
        if not down_time or not grace_time:
            errors.append("outside-window timing snapshots incomplete")
        elif (parse_utc(grace_time) - parse_utc(down_time)).total_seconds() < GRACE:
            errors.append("outside-window worker grace not exceeded")

        before_snapshot = shots.get("01-owned-before-interrupt", {})
        before = task(before_snapshot)
        reassigned = task(shots.get("04-reassigned", {}))
        old_return = task(shots.get("05-old-runner-returned", {}))

        if not before.get("owner"):
            errors.append("pre-interrupt owner missing")
        if not reassigned.get("owner") or reassigned.get("owner") == before.get("owner"):
            errors.append("reassignment to different owner not proven")
        if old_return.get("owner") != reassigned.get("owner"):
            errors.append("old runner return changed ownership")

        errors.extend(validate_f6_b_authority_order(shots))

        stale = attached(out, "stale-result-rejection.json")
        errors.extend(validate_stale_probe(stale, before_snapshot))

        if not any(row.get("kind") == "REASSIGNMENT" for row in rows):
            errors.append("reassignment ledger entry missing")
        if not any(row.get("kind") == "STALE_RESULT" for row in rows):
            errors.append("stale-result rejection ledger entry missing")

    return {
        "ok": not errors,
        "validated_at": utcnow(),
        "case": case,
        "errors": errors,
        "required_labels": LABELS[case],
        "required_attachments": ATTACH[case],
    }


def freeze(args):
    out = outdir(args.output, args.case)
    if not out.is_dir():
        raise SystemExit(f"Case directory not found: {out}")

    validation = validate(out, args.case)
    files = []
    for path in sorted(
        item
        for item in out.rglob("*")
        if item.is_file() and item.name not in {"manifest.json", "manifest.sha256"}
    ):
        files.append(
            {
                "path": path.relative_to(out).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": base.sha256_file(path),
            }
        )

    manifest = {
        "schema": SCHEMA,
        "case": args.case,
        "frozen_at": utcnow(),
        "target_sha": TARGET_SHA,
        "validation": validation,
        "files": files,
    }
    raw = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    (out / "manifest.json").write_bytes(raw)
    digest = base.sha256_bytes(raw)
    (out / "manifest.sha256").write_text(
        f"{digest}  manifest.json\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"manifest_sha256": digest, "validation": validation},
            indent=2,
        )
    )
    return 0 if validation["ok"] else 2


def verify(args):
    out = outdir(args.output, args.case)
    manifest_path = out / "manifest.json"
    digest_path = out / "manifest.sha256"
    errors = []

    if not manifest_path.is_file() or not digest_path.is_file():
        print(json.dumps({"ok": False, "errors": ["manifest files missing"]}, indent=2))
        return 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {item["path"] for item in manifest.get("files", [])}
    actual = {
        path.relative_to(out).as_posix()
        for path in out.rglob("*")
        if path.is_file() and path.name not in {"manifest.json", "manifest.sha256"}
    }
    errors += [f"missing: {item}" for item in sorted(expected - actual)]
    errors += [f"unexpected after freeze: {item}" for item in sorted(actual - expected)]

    for item in manifest.get("files", []):
        path = out / item["path"]
        if path.is_file() and base.sha256_file(path) != item["sha256"]:
            errors.append(f"hash mismatch: {item['path']}")

    if digest_path.read_text(encoding="utf-8").split()[0] != base.sha256_file(
        manifest_path
    ):
        errors.append("manifest hash mismatch")
    if not manifest.get("validation", {}).get("ok"):
        errors.append("manifest records failed physical-evidence validation")

    print(
        json.dumps(
            {
                "verified_at": utcnow(),
                "case": args.case,
                "ok": not errors,
                "errors": errors,
                "manifest_sha256": base.sha256_file(manifest_path),
            },
            indent=2,
        )
    )
    return 0 if not errors else 2


def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="AUD1-F6-EVIDENCE")
    sub = parser.add_subparsers(dest="cmd", required=True)

    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("--case", required=True, choices=list(LABELS))
    capture_parser.add_argument("--label", required=True)
    capture_parser.add_argument("--candidate-repo", required=True)
    capture_parser.add_argument("--station-record", required=True)
    capture_parser.add_argument("--db", required=True)
    capture_parser.add_argument("--project", required=True)
    capture_parser.add_argument("--task")
    capture_parser.add_argument("--station-url", required=True)
    capture_parser.set_defaults(func=capture)

    note_parser = sub.add_parser("note")
    note_parser.add_argument("--case", required=True, choices=list(LABELS))
    note_parser.add_argument(
        "--kind",
        required=True,
        choices=[
            "HITL",
            "TUNNEL_DOWN",
            "TUNNEL_UP",
            "OBSERVATION",
            "REASSIGNMENT",
            "STALE_RESULT",
            "ERROR",
        ],
    )
    note_parser.add_argument("--message", required=True)
    note_parser.set_defaults(func=lambda args: delegate("note", args))

    attach_parser = sub.add_parser("attach")
    attach_parser.add_argument("--case", required=True, choices=list(LABELS))
    attach_parser.add_argument("--file", required=True)
    attach_parser.add_argument("--name", default="")
    attach_parser.set_defaults(func=lambda args: delegate("attach", args))

    freeze_parser = sub.add_parser("freeze")
    freeze_parser.add_argument("--case", required=True, choices=list(LABELS))
    freeze_parser.set_defaults(func=freeze)

    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--case", required=True, choices=list(LABELS))
    verify_parser.set_defaults(func=verify)

    return parser


def main(argv=None):
    args = parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
