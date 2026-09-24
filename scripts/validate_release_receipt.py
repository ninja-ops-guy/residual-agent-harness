#!/usr/bin/env python3
"""Fail-closed cross-field validation for the RESIDUAL v1 release receipt.

JSON Schema validates shape, but draft-2020-12 does not provide portable field-to-field
equality. This validator binds the selected release candidate to the RC/final tag
commits while preserving the frozen R4.1 candidate only as canary provenance.
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
    candidate_commit = _hex(candidate.get("commit"), "candidate.commit", HEX40)
    _hex(candidate.get("tree"), "candidate.tree", HEX40)
    _hex(candidate.get("parent"), "candidate.parent", HEX40)

    rc_tag = _mapping(doc.get("rc_tag"), "rc_tag")
    if not isinstance(rc_tag.get("name"), str) or not RC_TAG.fullmatch(rc_tag["name"]):
        raise ReceiptBindingError("rc_tag.name must be v1.0.0-rc.N")
    rc_commit = _hex(rc_tag.get("commit"), "rc_tag.commit", HEX40)
    if rc_tag.get("signature_verified") is not True:
        raise ReceiptBindingError("rc_tag signature is not verified")
    if rc_commit != candidate_commit:
        raise ReceiptBindingError("rc_tag.commit does not equal candidate.commit")

    binding = _mapping(doc.get("binding_verification"), "binding_verification")
    if binding.get("candidate_rc_equal") is not True:
        raise ReceiptBindingError("binding_verification.candidate_rc_equal must be true")
    if not isinstance(binding.get("validator"), str) or not binding["validator"]:
        raise ReceiptBindingError("binding_verification.validator missing")
    _hex(binding.get("report_sha256"), "binding_verification.report_sha256", HEX64)

    final_tag = doc.get("final_tag")
    if final_tag is None:
        if binding.get("candidate_final_equal") is not None:
            raise ReceiptBindingError("candidate_final_equal must be null before final tag exists")
        return

    final_tag = _mapping(final_tag, "final_tag")
    if final_tag.get("name") != FINAL_TAG:
        raise ReceiptBindingError("final_tag.name must be v1.0.0")
    final_commit = _hex(final_tag.get("commit"), "final_tag.commit", HEX40)
    if final_tag.get("signature_verified") is not True:
        raise ReceiptBindingError("final_tag signature is not verified")
    if final_commit != candidate_commit:
        raise ReceiptBindingError("final_tag.commit does not equal candidate.commit")
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
    print("PASS: release receipt candidate/tag binding verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
