#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = ROOT / "docs/v1/CLAIM_REGISTRY.json"
DOCS = ROOT / "docs/v1/DOCUMENT_AUTHORITY.json"

ADMISSION = {"NOT_ADMITTED", "ADMITTED_D3"}
QUALIFICATION = {"NOT_QUALIFIED", "EXPERIMENTAL_EVIDENCE", "D3_QUALIFIED", "RC_QUALIFIED"}
RELEASE = {"NOT_RELEASED", "RELEASE_CANDIDATE", "RELEASED"}
SUPPORT = {"NOT_SUPPORTED", "SUPPORTED"}
DOC_AUTHORITY = {"CURRENT_NORMATIVE", "CURRENT_DESCRIPTIVE", "HISTORICAL_EVIDENCE", "PROPOSAL", "REFERENCE_TEMPLATE", "ROADMAP"}
EVIDENCE_RESULT = {"PASS", "FAIL", "UNKNOWN", "BLOCKED"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ClaimControlError(ValueError):
    pass


def _load(path: Path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ClaimControlError(f"{path} root must be an object")
    return value


def _nonempty_list(value, name):
    if not isinstance(value, list) or not value:
        raise ClaimControlError(f"{name} must be a non-empty list")
    return value


def _hex(value, name, pattern):
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ClaimControlError(f"{name} has invalid identity/digest form")
    return value


def _evidence_binding(value, cid, index):
    if not isinstance(value, dict):
        raise ClaimControlError(f"{cid}: qualification_evidence[{index}] must be an object")
    evidence_id = value.get("evidence_id")
    source = value.get("source")
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        raise ClaimControlError(f"{cid}: qualification_evidence[{index}].evidence_id missing")
    if not isinstance(source, str) or not source.strip():
        raise ClaimControlError(f"{cid}: qualification_evidence[{index}].source missing")
    head = _hex(value.get("subject_head"), f"{cid}: qualification_evidence[{index}].subject_head", HEX40)
    tree = _hex(value.get("subject_tree"), f"{cid}: qualification_evidence[{index}].subject_tree", HEX40)
    result = value.get("result")
    if result not in EVIDENCE_RESULT:
        raise ClaimControlError(f"{cid}: qualification_evidence[{index}].result invalid")
    digest = value.get("evidence_sha256")
    _hex(digest, f"{cid}: qualification_evidence[{index}].evidence_sha256", HEX64)
    artifact = value.get("artifact_sha256")
    if artifact is not None:
        _hex(artifact, f"{cid}: qualification_evidence[{index}].artifact_sha256", HEX64)
    return head, tree, result


def _validate_release_authorization(value, cid, qualified_head, qualified_tree):
    if not isinstance(value, dict):
        raise ClaimControlError(f"{cid}: RELEASED requires release_authorization evidence")
    if value.get("release") != "v1.0.0":
        raise ClaimControlError(f"{cid}: release_authorization.release must be v1.0.0")
    if not isinstance(value.get("identity"), str) or not value["identity"].strip():
        raise ClaimControlError(f"{cid}: release_authorization.identity missing")
    head = _hex(value.get("source_head"), f"{cid}: release_authorization.source_head", HEX40)
    tree = _hex(value.get("source_tree"), f"{cid}: release_authorization.source_tree", HEX40)
    _hex(value.get("artifact_set_sha256"), f"{cid}: release_authorization.artifact_set_sha256", HEX64)
    _hex(value.get("evidence_sha256"), f"{cid}: release_authorization.evidence_sha256", HEX64)
    if head != qualified_head or tree != qualified_tree:
        raise ClaimControlError(f"{cid}: release authorization must bind the RC-qualified subject")


def validate_claim_registry(doc):
    if doc.get("schema_version") != "residual.v1-claim-registry.v1":
        raise ClaimControlError("unsupported claim registry schema")
    claims = _nonempty_list(doc.get("claims"), "claims")
    seen = set()

    for claim in claims:
        if not isinstance(claim, dict):
            raise ClaimControlError("each claim must be an object")
        cid = claim.get("claim_id")
        if not isinstance(cid, str) or not cid or cid in seen:
            raise ClaimControlError("claim_id must be unique and non-empty")
        seen.add(cid)

        if claim.get("admission_state") not in ADMISSION:
            raise ClaimControlError(f"{cid}: invalid admission_state")
        if claim.get("qualification_state") not in QUALIFICATION:
            raise ClaimControlError(f"{cid}: invalid qualification_state")
        if claim.get("release_state") not in RELEASE:
            raise ClaimControlError(f"{cid}: invalid release_state")
        if claim.get("support_state") not in SUPPORT:
            raise ClaimControlError(f"{cid}: invalid support_state")

        qstate = claim["qualification_state"]
        evidence = claim.get("qualification_evidence")
        qualified_head = claim.get("qualified_subject_head")
        qualified_tree = claim.get("qualified_subject_tree")

        if qstate == "NOT_QUALIFIED":
            if evidence not in (None, []):
                raise ClaimControlError(f"{cid}: NOT_QUALIFIED cannot carry authoritative qualification_evidence")
            if qualified_head is not None or qualified_tree is not None:
                raise ClaimControlError(f"{cid}: NOT_QUALIFIED cannot carry qualified subject identity")
        else:
            entries = _nonempty_list(evidence, f"{cid}: qualification_evidence")
            bindings = [_evidence_binding(item, cid, i) for i, item in enumerate(entries)]

            if qstate in {"D3_QUALIFIED", "RC_QUALIFIED"}:
                if claim["admission_state"] != "ADMITTED_D3":
                    raise ClaimControlError(f"{cid}: D3/RC qualification cannot confer admission")
                qualified_head = _hex(qualified_head, f"{cid}: qualified_subject_head", HEX40)
                qualified_tree = _hex(qualified_tree, f"{cid}: qualified_subject_tree", HEX40)
                if any(result != "PASS" for _, _, result in bindings):
                    raise ClaimControlError(f"{cid}: qualified state requires only PASS qualification evidence")
                if any(head != qualified_head or tree != qualified_tree for head, tree, _ in bindings):
                    raise ClaimControlError(f"{cid}: qualification evidence must bind the qualified subject")
            elif qualified_head is not None or qualified_tree is not None:
                raise ClaimControlError(f"{cid}: experimental evidence cannot declare a qualified subject")

        if claim["release_state"] == "RELEASED":
            if claim["admission_state"] != "ADMITTED_D3" or qstate != "RC_QUALIFIED":
                raise ClaimControlError(f"{cid}: release requires admitted RC-qualified state")
            _validate_release_authorization(
                claim.get("release_authorization"), cid, qualified_head, qualified_tree
            )
            if claim["support_state"] != "SUPPORTED":
                raise ClaimControlError(f"{cid}: released capability must be supported")
        elif claim.get("release_authorization") is not None:
            raise ClaimControlError(f"{cid}: release_authorization is valid only for RELEASED state")

        if claim["support_state"] == "SUPPORTED" and claim["release_state"] != "RELEASED":
            raise ClaimControlError(f"{cid}: support does not exist before authorized release")

    return seen


def validate_document_authority(doc):
    if doc.get("schema_version") != "residual.v1-document-authority.v1":
        raise ClaimControlError("unsupported document authority schema")
    documents = _nonempty_list(doc.get("documents"), "documents")
    seen = set()
    for entry in documents:
        if not isinstance(entry, dict):
            raise ClaimControlError("each document entry must be an object")
        path = entry.get("path")
        if not isinstance(path, str) or not path or path in seen:
            raise ClaimControlError("document paths must be unique and non-empty")
        seen.add(path)
        authority = entry.get("authority_class")
        if authority not in DOC_AUTHORITY:
            raise ClaimControlError(f"{path}: invalid authority_class")
        if entry.get("release_evidence_eligible") and authority != "CURRENT_NORMATIVE":
            raise ClaimControlError(f"{path}: only CURRENT_NORMATIVE may satisfy current release evidence")
    return seen


def main():
    claims = _load(CLAIMS)
    docs = _load(DOCS)
    validate_claim_registry(claims)
    validate_document_authority(docs)
    print("PASS: v1 claim/document authority registries satisfy evidence-bound state invariants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
