#!/usr/bin/env python3
"""Fail-closed evaluator for completed RESIDUAL R4.1 canary evidence.

This program is read-only with respect to its evidence directory and has no
deployment, promotion, rollback, network, or credential-management capability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_HEAD = "8701367db6d3202f24b3eb9f4696b0cadf657985"
EXPECTED_TREE = "79bfe6ed1743907065ed44aeb9c460c47527e0c6"
SCHEMA = "residual.r4.1.canary-evidence/v1"
DISPOSITIONS = {
    "PROMOTION_ELIGIBLE", "CANARY_FAILED", "EVIDENCE_INCOMPLETE", "ROLLBACK_REQUIRED"
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EVENT_ORDER = [
    "outbox_durable", "network_send", "receiver_effect", "receipt_durable",
    "crash", "restart", "receipt_lookup", "outbox_ack",
]
ARTIFACT_FIELDS = [
    ("authorization", "receipt_artifact"), ("outbox", "journal_artifact"),
    ("crash_restart", "trace_artifact"), ("protected_services", "artifact"),
    ("production_mutations", "artifact"), ("credential_mutations", "artifact"),
    ("rollback", "artifact"),
]


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp must be UTC and end in Z")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.tzinfo != timezone.utc:
        raise ValueError("timestamp must be UTC")
    return parsed


def nested(data: Any, *keys: str) -> Any:
    for key in keys:
        if not isinstance(data, dict) or key not in data:
            raise KeyError(".".join(keys))
        data = data[key]
    return data


class Evaluation:
    def __init__(self) -> None:
        self.checks: dict[str, str] = {}
        self.reasons: list[str] = []
        self.rollback_triggers: list[str] = []

    def mark(self, name: str, status: str, reason: str | None = None) -> None:
        previous = self.checks.get(name)
        rank = {"PASS": 0, "FAIL": 1, "INCOMPLETE": 2, "ROLLBACK": 3}
        if previous is None or rank[status] > rank[previous]:
            self.checks[name] = status
        if reason and reason not in self.reasons:
            self.reasons.append(reason)
        if status == "ROLLBACK" and reason and reason not in self.rollback_triggers:
            self.rollback_triggers.append(reason)

    def disposition(self) -> str:
        values = set(self.checks.values())
        if "ROLLBACK" in values:
            return "ROLLBACK_REQUIRED"
        if "INCOMPLETE" in values:
            return "EVIDENCE_INCOMPLETE"
        if "FAIL" in values:
            return "CANARY_FAILED"
        return "PROMOTION_ELIGIBLE"


def safe_artifact(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("artifact path must be a non-empty POSIX relative path")
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts or relative != raw.as_posix():
        raise ValueError(f"unsafe or non-normal artifact path: {relative!r}")
    candidate = root / raw
    resolved = candidate.resolve(strict=True)
    resolved.relative_to(root.resolve())
    if not resolved.is_file() or candidate.is_symlink():
        raise ValueError(f"artifact is not a regular non-symlink file: {relative}")
    return resolved


def check_shape(bundle: Any, ev: Evaluation) -> bool:
    required = {
        "schema", "run_id", "candidate", "authorization", "bounds", "prestate",
        "poststate", "events", "receiver", "outbox", "crash_restart",
        "protected_services", "production_mutations", "credential_mutations",
        "rollback", "operator_interventions", "artifacts",
    }
    if not isinstance(bundle, dict):
        ev.mark("schema", "INCOMPLETE", "evidence root is not a JSON object")
        return False
    missing = sorted(required - set(bundle))
    extra = sorted(set(bundle) - required)
    if missing or extra or bundle.get("schema") != SCHEMA:
        ev.mark("schema", "INCOMPLETE", f"schema mismatch; missing={missing}, unexpected={extra}")
        return False
    object_keys = {
        "candidate": {"head", "tree"},
        "authorization": {"receipt_artifact", "run_id", "candidate_head", "candidate_tree", "environment", "not_before", "not_after", "authorized_by", "canary_only", "promotion_authorized"},
        "bounds": {"started_at", "finished_at", "max_duration_seconds", "max_network_attempts", "observed_network_attempts", "timed_out"},
        "prestate": {"captured_at", "candidate_head", "candidate_tree", "environment_digest", "protected_services_digest", "credentials_digest", "production_state_digest"},
        "poststate": {"captured_at", "candidate_head", "candidate_tree", "environment_digest", "protected_services_digest", "credentials_digest", "production_state_digest"},
        "receiver": {"operation_id", "side_effect_count", "side_effect_ids"},
        "outbox": {"operation_id", "pre_state", "post_state", "durable_before_send", "durable_terminal", "journal_artifact"},
        "crash_restart": {"injected", "operation_id_before", "operation_id_after", "receipt_checked_before_retry", "retry_suppressed_by_receipt", "receiver_side_effect_count_after_restart", "trace_artifact"},
        "protected_services": {"stable", "before_digest", "after_digest", "artifact"},
        "production_mutations": {"count", "authorized_count", "artifact"},
        "credential_mutations": {"count", "authorized_count", "artifact"},
        "rollback": {"rehearsed", "succeeded", "restored_state_digest", "expected_state_digest", "within_seconds", "max_seconds", "artifact"},
    }
    malformed = sorted(name for name, keys in object_keys.items() if not isinstance(bundle.get(name), dict) or set(bundle[name]) != keys)
    if malformed or not isinstance(bundle.get("events"), list) or not isinstance(bundle.get("operator_interventions"), list):
        ev.mark("schema", "INCOMPLETE", f"malformed object shape: {malformed}")
        return False
    ev.mark("schema", "PASS")
    return True


def verify_artifacts(root: Path, bundle: dict[str, Any], auth_digest: str, ev: Evaluation) -> dict[str, Path]:
    found: dict[str, Path] = {}
    artifacts = bundle.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        ev.mark("evidence_hashes", "INCOMPLETE", "artifact manifest is absent or empty")
        return found
    seen: set[str] = set()
    for index, item in enumerate(artifacts):
        try:
            if set(item) != {"path", "sha256", "bytes", "media_type", "producer"}:
                raise ValueError("manifest entry has missing or unexpected keys")
            rel = item["path"]
            if rel in seen:
                raise ValueError(f"duplicate artifact path: {rel}")
            seen.add(rel)
            if not SHA256_RE.fullmatch(item["sha256"]):
                raise ValueError(f"invalid sha256 for {rel}")
            if not isinstance(item["bytes"], int) or item["bytes"] < 0:
                raise ValueError(f"invalid byte count for {rel}")
            path = safe_artifact(root, rel)
            if path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
                raise ValueError(f"size or digest mismatch for {rel}")
            found[rel] = path
        except (KeyError, TypeError, ValueError, OSError) as exc:
            ev.mark("evidence_hashes", "INCOMPLETE", f"artifact[{index}] unverifiable: {exc}")
    referenced: list[Any] = []
    for parent, key in ARTIFACT_FIELDS:
        try:
            referenced.append(nested(bundle, parent, key))
        except KeyError:
            pass
    for event in bundle.get("events", []) if isinstance(bundle.get("events"), list) else []:
        if isinstance(event, dict):
            referenced.append(event.get("artifact"))
    missing_refs = sorted({str(x) for x in referenced if x not in found})
    if missing_refs:
        ev.mark("evidence_hashes", "INCOMPLETE", f"referenced artifacts absent from verified manifest: {missing_refs}")
    if ev.checks.get("evidence_hashes") != "INCOMPLETE":
        ev.mark("evidence_hashes", "PASS")
    try:
        receipt = nested(bundle, "authorization", "receipt_artifact")
        actual = sha256_file(found[receipt])
        if actual != auth_digest:
            ev.mark("canary_authorization", "INCOMPLETE", "authorization receipt does not match external trust-anchor digest")
        else:
            receipt_value = json.loads(found[receipt].read_text(encoding="utf-8"))
            expected = {k: v for k, v in bundle["authorization"].items() if k != "receipt_artifact"}
            if receipt_value != expected:
                ev.mark("canary_authorization", "INCOMPLETE", "authorization receipt content contradicts the evidence envelope")
            else:
                ev.mark("canary_authorization", "PASS")
    except (KeyError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        ev.mark("canary_authorization", "INCOMPLETE", "authorization receipt is unavailable")
    return found


def evaluate(bundle: dict[str, Any], root: Path, auth_digest: str) -> Evaluation:
    ev = Evaluation()
    if not check_shape(bundle, ev):
        return ev
    verify_artifacts(root, bundle, auth_digest, ev)

    try:
        candidate = bundle["candidate"]
        states = [bundle["prestate"], bundle["poststate"]]
        exact = candidate == {"head": EXPECTED_HEAD, "tree": EXPECTED_TREE}
        exact = exact and all(s["candidate_head"] == EXPECTED_HEAD and s["candidate_tree"] == EXPECTED_TREE for s in states)
        ev.mark("candidate_identity", "PASS" if exact else "INCOMPLETE", None if exact else "candidate HEAD/tree binding is absent or contradictory")
    except (KeyError, TypeError):
        ev.mark("candidate_identity", "INCOMPLETE", "candidate HEAD/tree evidence is malformed")

    try:
        pre, post = bundle["prestate"], bundle["poststate"]
        for name, state in (("prestate", pre), ("poststate", post)):
            required = {"captured_at", "candidate_head", "candidate_tree", "environment_digest", "protected_services_digest", "credentials_digest", "production_state_digest"}
            valid = set(state) == required and all(SHA256_RE.fullmatch(state[x]) for x in required if x.endswith("digest"))
            parse_time(state["captured_at"])
            ev.mark(name, "PASS" if valid else "INCOMPLETE", None if valid else f"{name} is malformed")
    except (KeyError, TypeError, ValueError):
        ev.mark("prestate_poststate", "INCOMPLETE", "prestate or poststate is malformed")

    operation_ids: list[str] = []
    try:
        events = bundle["events"]
        if not isinstance(events, list) or [x["seq"] for x in events] != list(range(len(events))):
            raise ValueError("event sequence is not contiguous from zero")
        kinds = [x["kind"] for x in events]
        operation_ids.extend(x["operation_id"] for x in events)
        positions = [kinds.index(kind) for kind in EVENT_ORDER]
        ordered = positions == sorted(positions)
        ev.mark("network_action_ordering", "PASS" if ordered else "FAIL", None if ordered else "required network/restart events are out of order")
        if not (positions[0] < positions[1] and positions[3] < positions[4] < positions[5] < positions[6] < positions[7]):
            ev.mark("receipt_first_restart", "FAIL", "receipt-first restart ordering was not demonstrated")
        else:
            ev.mark("receipt_first_restart", "PASS")
    except (KeyError, TypeError, ValueError) as exc:
        ev.mark("network_action_ordering", "INCOMPLETE", f"event trace is incomplete: {exc}")
        ev.mark("receipt_first_restart", "INCOMPLETE", "restart reconciliation cannot be verified")

    try:
        operation_ids += [
            bundle["receiver"]["operation_id"], bundle["outbox"]["operation_id"],
            bundle["crash_restart"]["operation_id_before"], bundle["crash_restart"]["operation_id_after"],
        ]
        stable = bool(operation_ids) and len(set(operation_ids)) == 1 and bool(operation_ids[0])
        ev.mark("stable_operation_id", "PASS" if stable else "FAIL", None if stable else "operation_id changed or is empty")
    except (KeyError, TypeError):
        ev.mark("stable_operation_id", "INCOMPLETE", "operation_id evidence is malformed")

    try:
        receiver = bundle["receiver"]
        side_effect_ok = receiver["side_effect_count"] == 1 and len(receiver["side_effect_ids"]) == 1
        after_restart = bundle["crash_restart"]["receiver_side_effect_count_after_restart"]
        status = "PASS" if side_effect_ok and after_restart == 1 else "ROLLBACK"
        ev.mark("exactly_one_receiver_effect", status, None if status == "PASS" else "receiver-side effect count is not exactly one")
    except (KeyError, TypeError):
        ev.mark("exactly_one_receiver_effect", "INCOMPLETE", "receiver-side effect evidence is malformed")

    try:
        outbox = bundle["outbox"]
        ok = outbox["pre_state"] == "pending" and outbox["post_state"] == "acknowledged" and outbox["durable_before_send"] is True and outbox["durable_terminal"] is True
        ev.mark("durable_outbox_transition", "PASS" if ok else "FAIL", None if ok else "durable pending-to-acknowledged transition failed")
    except (KeyError, TypeError):
        ev.mark("durable_outbox_transition", "INCOMPLETE", "outbox evidence is malformed")

    try:
        restart = bundle["crash_restart"]
        ok = restart["injected"] is True and restart["receipt_checked_before_retry"] is True and restart["retry_suppressed_by_receipt"] is True
        ev.mark("crash_restart_behavior", "PASS" if ok else "FAIL", None if ok else "crash/restart receipt-first reconciliation failed")
    except (KeyError, TypeError):
        ev.mark("crash_restart_behavior", "INCOMPLETE", "crash/restart evidence is malformed")

    try:
        services = bundle["protected_services"]
        stable = services["stable"] is True and services["before_digest"] == services["after_digest"] and services["before_digest"] == bundle["prestate"]["protected_services_digest"] and services["after_digest"] == bundle["poststate"]["protected_services_digest"]
        ev.mark("protected_service_stability", "PASS" if stable else "ROLLBACK", None if stable else "protected service instability detected")
    except (KeyError, TypeError):
        ev.mark("protected_service_stability", "INCOMPLETE", "protected service evidence is malformed")

    for key, check_name, reason in (
        ("production_mutations", "no_unauthorized_production_mutation", "unauthorized production mutation detected"),
        ("credential_mutations", "no_credential_mutation", "credential mutation detected"),
    ):
        try:
            check = bundle[key]
            digest_key = "production_state_digest" if key == "production_mutations" else "credentials_digest"
            clean = check["count"] == 0 and check["authorized_count"] == 0 and bundle["prestate"][digest_key] == bundle["poststate"][digest_key]
            ev.mark(check_name, "PASS" if clean else "ROLLBACK", None if clean else reason)
        except (KeyError, TypeError):
            ev.mark(check_name, "INCOMPLETE", f"{key} evidence is malformed")

    try:
        bounds = bundle["bounds"]
        start, finish = parse_time(bounds["started_at"]), parse_time(bounds["finished_at"])
        duration = (finish - start).total_seconds()
        complete = isinstance(bounds["max_duration_seconds"], int) and isinstance(bounds["max_network_attempts"], int) and isinstance(bounds["observed_network_attempts"], int)
        exceeded = duration < 0 or duration > bounds["max_duration_seconds"] or bounds["observed_network_attempts"] > bounds["max_network_attempts"] or bounds["timed_out"] is True
        ev.mark("bounded_execution", "ROLLBACK" if complete and exceeded else ("PASS" if complete else "INCOMPLETE"), "canary execution exceeded an authorized bound" if complete and exceeded else None)
    except (KeyError, TypeError, ValueError):
        ev.mark("bounded_execution", "INCOMPLETE", "execution-bound evidence is malformed")

    try:
        auth = bundle["authorization"]
        start, finish = parse_time(bundle["bounds"]["started_at"]), parse_time(bundle["bounds"]["finished_at"])
        authorized = (
            auth["run_id"] == bundle["run_id"] and auth["candidate_head"] == EXPECTED_HEAD and auth["candidate_tree"] == EXPECTED_TREE
            and auth["canary_only"] is True and auth["promotion_authorized"] is False
            and parse_time(auth["not_before"]) <= start <= finish <= parse_time(auth["not_after"])
            and isinstance(auth["environment"], str) and bool(auth["environment"])
            and isinstance(auth["authorized_by"], str) and bool(auth["authorized_by"])
        )
        ev.mark("authorization_scope", "PASS" if authorized else "INCOMPLETE", None if authorized else "authorization scope does not bind the completed canary")
    except (KeyError, TypeError, ValueError):
        ev.mark("authorization_scope", "INCOMPLETE", "authorization scope is malformed")

    try:
        rollback = bundle["rollback"]
        ok = rollback["rehearsed"] is True and rollback["succeeded"] is True and rollback["restored_state_digest"] == rollback["expected_state_digest"] and rollback["within_seconds"] <= rollback["max_seconds"]
        ev.mark("rollback_capability", "PASS" if ok else "FAIL", None if ok else "rollback capability rehearsal did not succeed within bounds")
    except (KeyError, TypeError):
        ev.mark("rollback_capability", "INCOMPLETE", "rollback capability evidence is malformed")

    try:
        interventions = bundle["operator_interventions"]
        if not isinstance(interventions, list):
            raise TypeError
        valid = all(set(x) == {"at", "actor", "action", "reason", "authorized"} and parse_time(x["at"]) and x["authorized"] is True and all(isinstance(x[k], str) and x[k] for k in ("actor", "action", "reason")) for x in interventions)
        ev.mark("operator_intervention_log", "PASS" if valid else "INCOMPLETE", None if valid else "operator intervention log is malformed or contains an unauthorized intervention")
    except (KeyError, TypeError, ValueError):
        ev.mark("operator_intervention_log", "INCOMPLETE", "operator intervention log is malformed")
    return ev


def render_report(template: str, decision: dict[str, Any], rollback: dict[str, Any]) -> str:
    checks = "\n".join(f"- `{name}`: **{status}**" for name, status in sorted(decision["checks"].items()))
    reasons = "\n".join(f"- {reason}" for reason in decision["reasons"]) or "- None."
    triggers = "\n".join(f"- {reason}" for reason in rollback["triggers"]) or "- None."
    values = {
        "DISPOSITION": decision["disposition"], "CANDIDATE_HEAD": decision["candidate_head"] or "UNVERIFIED",
        "CANDIDATE_TREE": decision["candidate_tree"] or "UNVERIFIED", "RUN_ID": decision["run_id"] or "UNVERIFIED",
        "EVIDENCE_SHA256": decision["evaluated_evidence_sha256"], "AUTHORIZATION_SHA256": decision["authorization_receipt_sha256"],
        "CHECKS": checks, "REASONS": reasons, "ROLLBACK_REQUIRED": str(rollback["required"]).lower(),
        "ROLLBACK_TRIGGERS": triggers,
    }
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--authorization-sha256", required=True)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--rollback-decision", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    if not SHA256_RE.fullmatch(args.authorization_sha256):
        parser.error("--authorization-sha256 must be 64 lowercase hexadecimal characters")
    raw = b""
    bundle: Any = {}
    parse_reason: str | None = None
    try:
        root = args.evidence.resolve(strict=True)
        evidence_file = root / "canary-evidence.json"
        if evidence_file.is_symlink() or not evidence_file.is_file():
            raise ValueError("canary-evidence.json must be a regular non-symlink file")
        raw = evidence_file.read_bytes()
        bundle = json.loads(raw)
    except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        parse_reason = f"canary-evidence.json is malformed: {exc}"
        root = args.evidence.absolute()
    ev = evaluate(bundle, root, args.authorization_sha256)
    if parse_reason:
        ev.mark("schema", "INCOMPLETE", parse_reason)
    disposition = ev.disposition()
    assert disposition in DISPOSITIONS
    decision = {
        "schema": "residual.r4.1.promotion-decision/v1", "disposition": disposition,
        "run_id": bundle.get("run_id") if isinstance(bundle, dict) and isinstance(bundle.get("run_id"), str) else None,
        "candidate_head": bundle.get("candidate", {}).get("head") if isinstance(bundle, dict) and isinstance(bundle.get("candidate"), dict) and isinstance(bundle["candidate"].get("head"), str) else None,
        "candidate_tree": bundle.get("candidate", {}).get("tree") if isinstance(bundle, dict) and isinstance(bundle.get("candidate"), dict) and isinstance(bundle["candidate"].get("tree"), str) else None,
        "evaluated_evidence_sha256": sha256_bytes(raw), "authorization_receipt_sha256": args.authorization_sha256,
        "checks": dict(sorted(ev.checks.items())), "reasons": ev.reasons,
        "promotion_performed": False, "human_promotion_required": True,
    }
    rollback = {
        "schema": "residual.r4.1.rollback-decision/v1", "required": disposition == "ROLLBACK_REQUIRED",
        "triggers": ev.rollback_triggers, "rollback_executed": False, "execution_authorized": False,
    }
    template = (Path(__file__).with_name("PROMOTION_REPORT.md.tmpl")).read_text(encoding="utf-8")
    write_new(args.decision, canonical_bytes(decision))
    write_new(args.rollback_decision, canonical_bytes(rollback))
    write_new(args.report, render_report(template, decision, rollback).encode())
    print(disposition)
    return 0 if disposition == "PROMOTION_ELIGIBLE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
