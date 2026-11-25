"""Read-only, source-bound shared memory derived from the Station event ledger.

The retained events/artifacts remain the primary store. This projection has no
write, claim, dispatch, approval or integration operation. A digest checks bytes,
not the truth of a statement or the authority to act on it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
import sqlite3
import time
from pathlib import Path

from residual.core import ContractError, canonical, strict_json
from .contracts import ID, event_validate, sha

SCHEMA = "residual.station.evidence-context/1"
MAX_EVENTS = 20_000
MAX_EVENT_BYTES = 8_000_000
MAX_ARTIFACT_BYTES = 256_000
MAX_ARTIFACT_SCAN_BYTES = 8_000_000
MAX_RESPONSE_BYTES = 32_000
MAX_ITEMS = 100
ARTIFACT_KINDS = {"checks.completed": "checks", "review.completed": "review",
                  "integration.completed": "integration"}
NOTE_KINDS = {"task.finding", "worker.expired", "task.transition"}
COMMIT = re.compile(r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")


def _integer(value, name, lower, upper):
    if type(value) is not int or not lower <= value <= upper:
        raise ContractError(f"{name} must be an integer from {lower} through {upper}")
    return value


def _fail():
    # Do not echo corrupt log/artifact content into an error or provider packet.
    raise ContractError("Shared memory source integrity or binding check failed")


def _snapshot(root, pid):
    path = Path(root).resolve() / "station.sqlite3"
    if not path.is_file():
        raise ContractError("An existing Station database is required")
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=15)
    db.row_factory = sqlite3.Row
    try:
        db.execute("BEGIN")  # project, tasks, log and artifact metadata share a snapshot
        row = db.execute("SELECT value FROM projects WHERE id=?", (pid,)).fetchone()
        if row is None:
            raise ContractError("Project was not found")
        project = strict_json(row[0])
        tasks = {r["id"]: strict_json(r["value"]) for r in db.execute(
            "SELECT id,value FROM tasks WHERE project=?", (pid,))}
        rows, read_bytes = [], 0
        cursor = db.execute("SELECT seq,event_id,prev_hash,hash,"
                            "CASE WHEN length(value)<=24000 THEN value ELSE NULL END AS value "
                            "FROM events WHERE project=? ORDER BY seq LIMIT ?", (pid, MAX_EVENTS + 1))
        for row in cursor:
            if row["value"] is None:
                _fail()
            read_bytes += len(row["value"].encode("utf-8"))
            if len(rows) == MAX_EVENTS or read_bytes > MAX_EVENT_BYTES:
                raise ContractError("Shared memory scan bound exceeded; retain the ledger and narrow the project")
            rows.append(row)
        artifacts = {r["id"]: dict(r) for r in db.execute(
            "SELECT * FROM artifacts WHERE project=?", (pid,))}
    finally:
        db.close()
    previous, events = "0" * 64, []
    for row in rows:
        try:
            event = strict_json(row["value"])
            event_validate(event)
            if (event["event_id"] != row["event_id"] or event["project_id"] != pid
                    or row["prev_hash"] != previous
                    or row["hash"] != sha({"previous": previous, "event": event})):
                _fail()
        except (KeyError, TypeError, ValueError):
            _fail()
        previous = row["hash"]
        events.append({**event, "seq": row["seq"], "hash": row["hash"]})
    return project, tasks, events, artifacts, previous


def _scope(tasks, tid):
    if tid not in tasks:
        raise ContractError("Task was not found")
    found, visiting = set(), set()

    def visit(current):
        if current in visiting or current not in tasks:
            raise ContractError("Shared memory dependency graph is invalid")
        if current in found:
            return
        visiting.add(current)
        for parent in tasks[current]["depends_on"]:
            visit(parent)
        visiting.remove(current)
        found.add(current)
    visit(tid)
    return found


def _artifact(root, pid, aid, kind, artifacts, cache, budget):
    if (not isinstance(aid, str) or not aid.startswith(pid + ":")
            or not re.fullmatch(r"[a-f0-9]{64}", aid[len(pid) + 1:])):
        _fail()
    meta = artifacts.get(aid)
    if not meta or meta["project"] != pid or meta["kind"] != kind:
        _fail()
    if (aid, kind) in cache:
        return cache[(aid, kind)]
    if type(meta["size"]) is not int or not 0 <= meta["size"] <= MAX_ARTIFACT_BYTES:
        raise ContractError("Shared memory artifact exceeds its bounded read contract")
    budget["bytes"] += meta["size"]
    if budget["bytes"] > MAX_ARTIFACT_SCAN_BYTES:
        raise ContractError("Shared memory artifact scan bound exceeded; retain the original evidence")
    try:
        with (Path(root).resolve() / "artifacts" / pid / aid.split(":")[1]).open("rb") as stream:
            data = stream.read(MAX_ARTIFACT_BYTES + 1)
        if len(data) != meta["size"] or hashlib.sha256(data).hexdigest() != aid.split(":")[1]:
            _fail()
        value = strict_json(data.decode("utf-8"))
        if not isinstance(value, dict):
            _fail()
        cache[(aid, kind)] = value
        return value
    except (OSError, UnicodeError, ValueError):
        _fail()


def _checks(value):
    checks = value.get("checks")
    if (not isinstance(checks, list) or not checks or len(checks) > 2000
            or any(not isinstance(c, dict) or type(c.get("passed")) is not bool
                   or not isinstance(c.get("id"), str) for c in checks)):
        _fail()
    return {"passed": sum(c["passed"] for c in checks), "total": len(checks),
            "failures": [{"check_id": c["id"][:100], "detail": str(c.get("detail", ""))[:400]}
                         for c in checks if not c["passed"]][:5]}


def _record(root, pid, event, artifacts, cache, budget):
    kind, data = event["event_type"], event["data"]
    source = {"event_id": event["event_id"], "event_hash": event["hash"],
              "seq": event["seq"], "actor": event["actor"], "timestamp": event["timestamp"],
              "host_id": None, "host_provenance": "not_recorded_by_source"}
    record = {"task_id": event["task_id"], "kind": kind, "attempt": event["attempt"],
              "spec_hash": event["spec_hash"], "base_commit": None, "head_commit": None,
              "source": source, "duplicate_events": 0,
              "authority": "context_only", "truth_status": "not_established_by_memory"}
    if kind in ARTIFACT_KINDS:
        aid = data.get("evidence")
        value = _artifact(root, pid, aid, ARTIFACT_KINDS[kind], artifacts, cache, budget)
        if (not isinstance(value.get("head_commit"), str) or not COMMIT.fullmatch(value["head_commit"])
                or value["head_commit"] != data.get("head_commit")
                or not isinstance(value.get("base_commit"), str) or not COMMIT.fullmatch(value["base_commit"])
                or (kind != "integration.completed" and value.get("spec_hash") != event["spec_hash"])):
            _fail()
        record.update(base_commit=value["base_commit"], head_commit=value["head_commit"])
        source.update(artifact_id=aid, artifact_sha256=aid.split(":")[1])
        if kind == "review.completed":
            if type(value.get("approved")) is not bool or value["approved"] != data.get("approved"):
                _fail()
            findings = value.get("findings")
            if not isinstance(findings, list) or len(findings) > 8:
                _fail()
            for finding in findings:
                if (not isinstance(finding, dict) or finding.get("severity") not in {"note", "warning", "blocking"}
                        or not isinstance(finding.get("message"), str)):
                    _fail()
            blocking = sum(f["severity"] == "blocking" for f in findings)
            if (type(data.get("blocking_findings")) is not int
                    or blocking != data.get("blocking_findings") or (value["approved"] and blocking)
                    or (not value["approved"] and not blocking)):
                _fail()
            facts = {"approved": value["approved"], "findings": [
                {"severity": f["severity"], "message": f["message"][:400]} for f in findings]}
            record["outcome_digest"] = sha({"approved": value["approved"]})
            record["negative"] = not value["approved"]
        else:
            facts = _checks(value)
            record["outcome_digest"] = sha([(c["id"], c["passed"]) for c in value["checks"]])
            if kind == "checks.completed" and (type(data.get("passed")) is not int
                    or type(data.get("total")) is not int
                    or facts["passed"] != data.get("passed") or facts["total"] != data.get("total")):
                _fail()
            record["negative"] = facts["passed"] != facts["total"]
        record["facts"] = facts
        # Source bytes define repeated evidence; transport copies never corroborate.
        identity = {"task": record["task_id"], "kind": kind, "artifact": aid,
                    "spec_hash": record["spec_hash"]}
    else:
        if kind == "task.transition":
            if data.get("to") not in {"blocked", "repair_required"}:
                return None
            if not isinstance(data.get("findings", []), list) or any(
                    not isinstance(x, str) for x in data.get("findings", [])):
                _fail()
            facts = {"from": data.get("from"), "to": data["to"],
                     "findings": [x[:400] for x in data.get("findings", [])[:5]]}
        elif kind == "worker.expired":
            facts = {"from": data.get("from"), "message": "Worker authority expired; retained evidence is context only"}
        else:
            if not isinstance(data.get("message", ""), str):
                _fail()
            facts = {"message": data.get("message", "")[:1600]}
            if "patch_sha256" in data:
                if not isinstance(data["patch_sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", data["patch_sha256"]):
                    _fail()
                facts["patch_sha256"] = data["patch_sha256"]
        record.update(facts=facts, negative=kind != "task.finding")
        identity = {"task": record["task_id"], "kind": kind, "attempt": event["attempt"],
                    "spec_hash": record["spec_hash"], "data_digest": sha(data)}
    record["id"] = sha(identity)
    return record


def _evidence_context(root, pid, tid, *, revision=None, after=0, limit=20,
                      max_age_seconds=None, now=None, snapshot_root=None):
    """Rebuild a bounded context packet from original durable sources.

    ``after`` is an item offset; pass returned snapshot_root on later pages to
    reject a changed ledger. Expiry affects applicability, never source retention.
    ``now`` exists for deterministic local qualification, not HTTP clients.
    """
    if not isinstance(pid, str) or not re.fullmatch(r"p-[a-f0-9]{12}", pid):
        raise ContractError("Invalid project ID")
    if not isinstance(tid, str) or not ID.fullmatch(tid):
        raise ContractError("Invalid task ID")
    if revision is not None and (not isinstance(revision, str) or not COMMIT.fullmatch(revision)):
        raise ContractError("Revision must be a full commit hash")
    _integer(after, "after", 0, MAX_EVENTS)
    _integer(limit, "limit", 1, MAX_ITEMS)
    if snapshot_root is not None and (not isinstance(snapshot_root, str)
            or not re.fullmatch(r"[a-f0-9]{64}", snapshot_root)):
        raise ContractError("Invalid shared memory snapshot root")
    if after and snapshot_root is None:
        raise ContractError("Further shared memory pages require the returned snapshot_root")
    if max_age_seconds is not None:
        _integer(max_age_seconds, "max_age_seconds", 1, 365 * 24 * 60 * 60)
    current = time.time() if now is None else now
    if type(current) not in {float, int} or not math.isfinite(current):
        raise ContractError("Invalid observation time")
    try:
        project, tasks, events, artifacts, journal_root = _snapshot(root, pid)
        scope = _scope(tasks, tid)
    except ContractError:
        raise
    except (sqlite3.Error, KeyError, TypeError, ValueError, RecursionError):
        _fail()
    selected = tasks[tid]
    revision = revision or selected.get("head_commit") or selected.get("base_commit")
    if revision is not None and (not isinstance(revision, str) or not COMMIT.fullmatch(revision)):
        _fail()
    scope_tasks = [{"id": name, "state": tasks[name]["state"], "attempt": tasks[name]["attempt"],
                    "head_commit": tasks[name].get("head_commit"),
                    "base_commit": tasks[name].get("base_commit"),
                    "depends_on": tasks[name]["depends_on"]} for name in sorted(scope)]
    binding = sha({"journal_root": journal_root, "spec_hash": project["spec_hash"],
                   "tasks": scope_tasks, "task": tid, "revision": revision,
                   "max_age_seconds": max_age_seconds})
    if snapshot_root is not None and snapshot_root != binding:
        raise ContractError("Shared memory snapshot changed; restart discovery from the first page")
    records = {}
    cache, budget = {}, {"bytes": 0}
    workers = {(event["task_id"], event["attempt"]): event["actor"] for event in events
               if event["event_type"] == "task.claimed"}
    for event in events:
        if event["task_id"] not in scope or event["event_type"] not in ARTIFACT_KINDS.keys() | NOTE_KINDS:
            continue
        record = _record(root, pid, event, artifacts, cache, budget)
        if record is None:
            continue
        record["source"]["worker_id"] = workers.get((event["task_id"], event["attempt"]))
        if record["id"] in records:
            records[record["id"]]["duplicate_events"] += 1
            continue
        records[record["id"]] = record
    groups = {}
    latest = {}
    for record in records.values():
        key = (record["task_id"], record["kind"])
        latest[key] = max(latest.get(key, record), record, key=lambda r: r["source"]["seq"])
        if record["head_commit"]:
            group = key + (record["spec_hash"], record["head_commit"])
            groups.setdefault(group, {}).setdefault(record["outcome_digest"], []).append(record["id"])
    group_counts = {key: sum(map(len, outcomes.values())) for key, outcomes in groups.items()}
    for record in records.values():
        key = (record["task_id"], record["kind"])
        head, source = record["head_commit"], record["source"]
        recorded = dt.datetime.fromisoformat(source["timestamp"]).timestamp()
        record["age_seconds"] = round(max(0.0, current - recorded), 3)
        reasons = []
        if recorded > current:
            reasons.append("future_timestamp")
        if record["spec_hash"] != project["spec_hash"]:
            reasons.append("spec_changed")
        if head is None:
            reasons.append("revision_unbound")
        elif head != revision:
            reasons.append("different_revision")
        if max_age_seconds is not None and current - recorded > max_age_seconds:
            reasons.append("expired_for_query")
        if record["attempt"] != tasks[record["task_id"]]["attempt"]:
            reasons.append("earlier_attempt")
        record["applicability"] = "current_revision" if not reasons else "historical_context"
        record["limitations"] = reasons
        newer = latest[key]
        record["superseded_for_current_work_by"] = newer["id"] if newer["source"]["seq"] > source["seq"] else None
        group_key = key + (record["spec_hash"], head)
        peers = groups.get(group_key, {})
        own_outcome = record.get("outcome_digest")
        record["conflict_count"] = group_counts.get(group_key, 0) - len(peers.get(own_outcome, []))
        conflicts = []
        for outcome, peer_ids in peers.items():
            if outcome != own_outcome:
                conflicts.extend(peer_ids[:10 - len(conflicts)])
                if len(conflicts) == 10:
                    break
        record["conflicts"] = sorted(conflicts)
        if record["conflict_count"]:
            record["applicability"] = "conflicted"
        record["independent_corroboration"] = 0
    # Deterministic relevance: conflicts, target failures, target evidence, deps.
    # History remains addressable; no source or failed attempt is deleted.
    ordered = sorted(records.values(), key=lambda r: (
        0 if r["conflicts"] else 1 if r["task_id"] == tid and r["negative"]
        else 2 if r["task_id"] == tid else 3, -r["source"]["seq"], r["id"]))
    result = {"schema": SCHEMA, "project_id": pid, "task_id": tid, "spec_hash": project["spec_hash"],
              "revision": revision, "scope": sorted(scope), "authority": "context_only",
              "task_state": next(t for t in scope_tasks if t["id"] == tid),
              "dependency_states": {t["id"]: t["state"] for t in scope_tasks if t["id"] != tid},
              "requires_current_verification": True, "journal_root": journal_root,
              "through_seq": events[-1]["seq"] if events else 0, "snapshot_root": binding,
              "observed_at": dt.datetime.fromtimestamp(current, dt.timezone.utc).isoformat(),
              "source_integrity": "hash_links_and_referenced_bytes_checked",
              "source_authentication": "local_station_ledger_not_independent_attestation",
              "total": len(ordered), "offset": after, "items": [], "next_offset": None}
    for record in ordered[after:after + limit]:
        result["items"].append(record)
        if len(canonical(result).encode("utf-8")) > MAX_RESPONSE_BYTES - 128:
            result["items"].pop()
            break
    next_offset = after + len(result["items"])
    if next_offset < len(ordered):
        if not result["items"]:
            raise ContractError("Shared memory item exceeds response bound")
        result["next_offset"] = next_offset
    return result


def evidence_context(root, pid, tid, *, revision=None, after=0, limit=20,
                     max_age_seconds=None, now=None, snapshot_root=None):
    """Return the source projection, normalizing malformed retained state."""
    try:
        return _evidence_context(root, pid, tid, revision=revision, after=after, limit=limit,
                                 max_age_seconds=max_age_seconds, now=now, snapshot_root=snapshot_root)
    except ContractError:
        raise
    except (sqlite3.Error, OSError, KeyError, TypeError, ValueError, AttributeError,
            OverflowError, RecursionError):
        _fail()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read source-bound Station memory without starting workers")
    parser.add_argument("--root", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--revision")
    parser.add_argument("--after", type=int, default=0)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--max-age-seconds", type=int)
    parser.add_argument("--snapshot-root")
    args = parser.parse_args(argv)
    try:
        result = evidence_context(args.root, args.project, args.task, revision=args.revision,
                                  after=args.after, limit=args.limit,
                                  max_age_seconds=args.max_age_seconds, snapshot_root=args.snapshot_root)
    except ContractError as exc:
        parser.exit(2, str(exc) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
