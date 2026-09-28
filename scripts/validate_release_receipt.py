#!/usr/bin/env python3
"""Fail-closed cross-field validation for the RESIDUAL v1 release receipt.

R4.1 identity is canary provenance only. The post-convergence RC source/tree,
qualified artifact set, and final tag are distinct authority roles.

This validator checks structural/cross-field release binding. It does not itself
perform Git signature verification, artifact hashing from external files, or
human authorization. For V1_CLOSED it requires trusted expected RC source/tree
and the complete expected artifact-name -> SHA-256 mapping from the caller so
internally consistent self-reported identities cannot substitute for the
selected release identity or silently add/drop release artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

CANARY_COMMIT = "8701367db6d3202f24b3eb9f4696b0cadf657985"
CANARY_TREE = "79bfe6ed1743907065ed44aeb9c460c47527e0c6"
CANARY_PARENT = "eada7577cf6f2de875b508c6a82f47870e3aa673"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
RC_TAG = re.compile(r"^v1\.0\.0-rc\.[1-9][0-9]*$")
FINAL_TAG = "v1.0.0"
CLOSURE_STATES = {"PRE_CLOSURE", "V1_CLOSED", "ROLLED_BACK"}
REQUIRED_GATES = {f"V1-G{i:02d}" for i in range(1, 11)}


class ReceiptBindingError(ValueError):
    pass


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReceiptBindingError(f"{name} must be an object")
    return value


def _hex(value: Any, name: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ReceiptBindingError(f"{name} has invalid digest/commit form")
    return value


def _artifact_set_digest(mapping: dict[str, str]) -> str:
    canonical = json.dumps(sorted(mapping.items()), ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _artifact_map(doc: dict[str, Any]) -> dict[str, str]:
    artifacts = doc.get("artifact")
    if not isinstance(artifacts, list) or not artifacts:
        raise ReceiptBindingError("artifact must contain at least one release artifact")
    result: dict[str, str] = {}
    for index, artifact in enumerate(artifacts):
        entry = _mapping(artifact, f"artifact[{index}]")
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise ReceiptBindingError(f"artifact[{index}].name missing")
        if name in result:
            raise ReceiptBindingError(f"duplicate release artifact name: {name}")
        result[name] = _hex(entry.get("sha256"), f"artifact[{index}].sha256", HEX64)
    return result


def _validate_artifact_binding(doc: dict[str, Any], artifact_map: dict[str, str]) -> dict[str, str]:
    binding = _mapping(doc.get("artifact_binding"), "artifact_binding")
    declared_set = _hex(binding.get("artifact_set_sha256"), "artifact_binding.artifact_set_sha256", HEX64)
    entries = binding.get("artifacts")
    if not isinstance(entries, list) or not entries:
        raise ReceiptBindingError("artifact_binding.artifacts must be a non-empty list")

    bound: dict[str, str] = {}
    for index, raw in enumerate(entries):
        entry = _mapping(raw, f"artifact_binding.artifacts[{index}]")
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise ReceiptBindingError(f"artifact_binding.artifacts[{index}].name missing")
        if name in bound:
            raise ReceiptBindingError(f"duplicate artifact binding name: {name}")
        rc_digest = _hex(
            entry.get("rc_artifact_sha256"),
            f"artifact_binding.artifacts[{index}].rc_artifact_sha256",
            HEX64,
        )
        qualified_digest = _hex(
            entry.get("qualified_artifact_sha256"),
            f"artifact_binding.artifacts[{index}].qualified_artifact_sha256",
            HEX64,
        )
        if entry.get("artifact_equal") is not True:
            raise ReceiptBindingError(f"artifact binding {name} must declare artifact_equal=true")
        if rc_digest != qualified_digest:
            raise ReceiptBindingError(f"qualified artifact digest does not equal RC artifact digest for {name}")
        bound[name] = rc_digest

    if set(bound) != set(artifact_map):
        missing = sorted(set(artifact_map) - set(bound))
        extra = sorted(set(bound) - set(artifact_map))
        raise ReceiptBindingError(f"artifact binding must cover exact release artifact set; missing={missing} extra={extra}")

    for name, digest in artifact_map.items():
        if bound[name] != digest:
            raise ReceiptBindingError(f"artifact binding digest does not match release artifact {name}")

    observed_set = _artifact_set_digest(bound)
    if declared_set != observed_set:
        raise ReceiptBindingError("artifact_binding.artifact_set_sha256 does not match bound artifact set")
    return bound


def _closed_prerequisites(doc: dict[str, Any]) -> None:
    decisions = doc.get("decisions")
    if not isinstance(decisions, list):
        raise ReceiptBindingError("V1_CLOSED requires the full gate decision inventory")
    seen: dict[str, str] = {}
    for entry in decisions:
        gate = _mapping(entry, "decision").get("gate_id")
        state = entry.get("state")
        if gate in seen:
            raise ReceiptBindingError(f"duplicate release gate decision: {gate}")
        if not isinstance(gate, str):
            raise ReceiptBindingError("release gate decision missing gate_id")
        seen[gate] = state
    if set(seen) != REQUIRED_GATES:
        missing = sorted(REQUIRED_GATES - set(seen))
        extra = sorted(set(seen) - REQUIRED_GATES)
        raise ReceiptBindingError(f"V1_CLOSED requires exactly V1-G01..V1-G10; missing={missing} extra={extra}")
    not_go = sorted(g for g, state in seen.items() if state != "GO")
    if not_go:
        raise ReceiptBindingError(f"V1_CLOSED requires GO for every release gate; non_go={not_go}")

    verification = _mapping(doc.get("verification"), "verification")
    if verification.get("result") != "GO":
        raise ReceiptBindingError("V1_CLOSED requires verification.result=GO")
    for field in ("health", "readiness", "critical_journeys", "observability"):
        if verification.get(field) is not True:
            raise ReceiptBindingError(f"V1_CLOSED requires verification.{field}=true")

    deployment = _mapping(doc.get("deployment"), "deployment")
    if deployment.get("result") != "DEPLOYED":
        raise ReceiptBindingError("V1_CLOSED requires deployment.result=DEPLOYED")

    rollback = _mapping(doc.get("rollback_window"), "rollback_window")
    if rollback.get("outcome") != "PASSED":
        raise ReceiptBindingError("V1_CLOSED requires rollback_window.outcome=PASSED")


def validate_binding(
    doc: dict[str, Any],
    *,
    expected_rc_source: str | None = None,
    expected_rc_tree: str | None = None,
    expected_artifacts: dict[str, str] | None = None,
) -> None:
    if doc.get("schema_version") != "residual.release-receipt.v1":
        raise ReceiptBindingError("unsupported schema_version")
    if doc.get("release") != "v1.0.0":
        raise ReceiptBindingError("release must be v1.0.0")

    canary = _mapping(_mapping(doc.get("canary_provenance"), "canary_provenance").get("candidate"), "canary_provenance.candidate")
    if canary.get("commit") != CANARY_COMMIT or canary.get("tree") != CANARY_TREE or canary.get("parent") != CANARY_PARENT:
        raise ReceiptBindingError("canary provenance does not bind the frozen R4.1 candidate")
    _hex(doc["canary_provenance"].get("post_canary_report_sha256"), "canary_provenance.post_canary_report_sha256", HEX64)

    candidate = _mapping(doc.get("candidate"), "candidate")
    rc_source_commit = _hex(candidate.get("commit"), "candidate.commit", HEX40)
    rc_source_tree = _hex(candidate.get("tree"), "candidate.tree", HEX40)
    _hex(candidate.get("parent"), "candidate.parent", HEX40)
    if rc_source_commit == CANARY_COMMIT:
        raise ReceiptBindingError("R4 canary provenance cannot populate RC source identity")

    rc_tag = _mapping(doc.get("rc_tag"), "rc_tag")
    if not isinstance(rc_tag.get("name"), str) or not RC_TAG.fullmatch(rc_tag["name"]):
        raise ReceiptBindingError("rc_tag.name must be v1.0.0-rc.N")
    rc_commit = _hex(rc_tag.get("commit"), "rc_tag.commit", HEX40)
    if rc_tag.get("signature_verified") is not True:
        raise ReceiptBindingError("rc_tag signature is not verified")
    if rc_commit != rc_source_commit:
        raise ReceiptBindingError("rc_tag.commit does not equal RC source commit")

    artifacts = _artifact_map(doc)
    bound_artifacts = _validate_artifact_binding(doc, artifacts)

    binding = _mapping(doc.get("binding_verification"), "binding_verification")
    if binding.get("candidate_rc_equal") is not True:
        raise ReceiptBindingError("binding_verification.candidate_rc_equal must be true")
    if not isinstance(binding.get("validator"), str) or not binding["validator"]:
        raise ReceiptBindingError("binding_verification.validator missing")
    _hex(binding.get("report_sha256"), "binding_verification.report_sha256", HEX64)

    closure = _mapping(doc.get("closure"), "closure")
    closure_state = closure.get("state")
    if closure_state not in CLOSURE_STATES:
        raise ReceiptBindingError("closure.state is invalid")

    final_tag = doc.get("final_tag")
    if final_tag is None:
        if closure_state == "V1_CLOSED":
            raise ReceiptBindingError("V1_CLOSED requires an exact signed final tag")
        if binding.get("candidate_final_equal") is not None:
            raise ReceiptBindingError("candidate_final_equal must be null before final tag exists")
        return

    if closure_state == "PRE_CLOSURE":
        raise ReceiptBindingError("final tag is not valid in PRE_CLOSURE state")

    final_tag = _mapping(final_tag, "final_tag")
    if final_tag.get("name") != FINAL_TAG:
        raise ReceiptBindingError("final_tag.name must be v1.0.0")
    final_commit = _hex(final_tag.get("commit"), "final_tag.commit", HEX40)
    if final_tag.get("signature_verified") is not True:
        raise ReceiptBindingError("final_tag signature is not verified")
    if final_commit != rc_source_commit:
        raise ReceiptBindingError("final_tag.commit does not equal RC source commit")
    if binding.get("candidate_final_equal") is not True:
        raise ReceiptBindingError("binding_verification.candidate_final_equal must be true after final tag exists")

    if closure_state == "V1_CLOSED":
        _closed_prerequisites(doc)
        if expected_rc_source is None or expected_rc_tree is None or expected_artifacts is None:
            raise ReceiptBindingError("V1_CLOSED requires trusted expected RC source/tree/artifact-set inputs")
        expected_rc_source = _hex(expected_rc_source, "expected_rc_source", HEX40)
        expected_rc_tree = _hex(expected_rc_tree, "expected_rc_tree", HEX40)
        if rc_source_commit != expected_rc_source:
            raise ReceiptBindingError("receipt RC source does not equal externally selected RC source")
        if rc_source_tree != expected_rc_tree:
            raise ReceiptBindingError("receipt RC tree does not equal externally selected RC tree")

        normalized_expected: dict[str, str] = {}
        for name, digest in expected_artifacts.items():
            if not isinstance(name, str) or not name:
                raise ReceiptBindingError("expected artifact name must be non-empty")
            if name in normalized_expected:
                raise ReceiptBindingError(f"duplicate expected artifact name: {name}")
            normalized_expected[name] = _hex(digest, f"expected artifact {name}", HEX64)

        if bound_artifacts != normalized_expected:
            raise ReceiptBindingError("receipt artifact set does not equal externally selected qualified artifact set")


def _parse_expected_artifacts(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in values:
        if "=" not in raw:
            raise ReceiptBindingError("--expected-artifact must use NAME=SHA256")
        name, digest = raw.split("=", 1)
        if not name or name in result:
            raise ReceiptBindingError("expected artifact names must be unique and non-empty")
        result[name] = _hex(digest, f"expected artifact {name}", HEX64)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--expected-rc-source")
    parser.add_argument("--expected-rc-tree")
    parser.add_argument("--expected-artifact", action="append", default=[], metavar="NAME=SHA256")
    args = parser.parse_args()
    try:
        doc = json.loads(args.receipt.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise ReceiptBindingError("receipt root must be an object")
        expected_artifacts = _parse_expected_artifacts(args.expected_artifact) if args.expected_artifact else None
        validate_binding(
            doc,
            expected_rc_source=args.expected_rc_source,
            expected_rc_tree=args.expected_rc_tree,
            expected_artifacts=expected_artifacts,
        )
    except (OSError, json.JSONDecodeError, ReceiptBindingError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS: release receipt RC/artifact-set/final-tag binding verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
