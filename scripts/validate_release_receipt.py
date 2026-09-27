#!/usr/bin/env python3
"""Fail-closed cross-field validation for the RESIDUAL v1 release receipt.

R4.1 identity is canary provenance only. The post-convergence RC source/tree,
qualified artifact, and final tag are distinct authority roles.
"""

from __future__ import annotations

import argparse
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


def validate_binding(doc: dict[str, Any]) -> None:
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
    _hex(candidate.get("tree"), "candidate.tree", HEX40)
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

    artifacts = doc.get("artifact")
    if not isinstance(artifacts, list) or not artifacts:
        raise ReceiptBindingError("artifact must contain at least one release artifact")
    artifact_digests=set()
    for index, artifact in enumerate(artifacts):
        entry=_mapping(artifact, f"artifact[{index}]")
        artifact_digests.add(_hex(entry.get("sha256"), f"artifact[{index}].sha256", HEX64))

    artifact_binding=_mapping(doc.get("artifact_binding"), "artifact_binding")
    rc_artifact=_hex(artifact_binding.get("rc_artifact_sha256"), "artifact_binding.rc_artifact_sha256", HEX64)
    qualified_artifact=_hex(artifact_binding.get("qualified_artifact_sha256"), "artifact_binding.qualified_artifact_sha256", HEX64)
    if artifact_binding.get("artifact_equal") is not True:
        raise ReceiptBindingError("artifact_binding.artifact_equal must be true")
    if rc_artifact != qualified_artifact:
        raise ReceiptBindingError("qualified artifact digest does not equal RC artifact digest")
    if rc_artifact not in artifact_digests:
        raise ReceiptBindingError("RC artifact digest is not present in release artifacts")

    binding = _mapping(doc.get("binding_verification"), "binding_verification")
    if binding.get("candidate_rc_equal") is not True:
        raise ReceiptBindingError("binding_verification.candidate_rc_equal must be true")
    if not isinstance(binding.get("validator"), str) or not binding["validator"]:
        raise ReceiptBindingError("binding_verification.validator missing")
    _hex(binding.get("report_sha256"), "binding_verification.report_sha256", HEX64)

    closure=_mapping(doc.get("closure"), "closure")
    closure_state=closure.get("state")
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    try:
        doc = json.loads(args.receipt.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            raise ReceiptBindingError("receipt root must be an object")
        validate_binding(doc)
    except (OSError, json.JSONDecodeError, ReceiptBindingError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS: release receipt RC/artifact/final-tag binding verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
