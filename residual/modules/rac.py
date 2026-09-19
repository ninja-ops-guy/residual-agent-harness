"""RAC research-improvement StationModule.

RESIDUAL verifies a JSON-compatible RAC candidate envelope without importing
RAC or executing its scientific machinery. RAC remains authoritative for
measurement, held-out boundaries, evidence classification, physical execution,
and human promotion.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

from ..brakes import BrakeAction, BrakeTrip
from ..extensions import VerifierDescriptor, VerifierRevision
from ..goalspec import CheckType
from ..quarantine import ProposedAction
from ..verifier import CheckResult


CANDIDATE_CONTRACT = "rac-residual-candidate/1.0"
IMPROVEMENT_SCHEMA = "rac-residual-improvement/1.0"
EVIDENCE_SCHEMA = "rac-residual-evidence/1.0"
DECISION_SCHEMA = "rac-residual-decision/1.0"
REQUIRED_FORBIDDEN_CAPABILITIES = frozenset(
    {
        "held_out_candidate_selection",
        "physical_experiment_execution",
        "automatic_scientific_promotion",
    }
)
ALLOWED_RAC_CAPABILITIES = frozenset(
    {
        "read_public_artifact",
        "write_bounded_candidate",
        "digital_experiment_execution",
        "evidence_collection",
        "advisory_decision",
    }
)
FORBIDDEN_ACTION_NAMES = frozenset(
    {"rac.held_out_select", "rac.physical_execute", "rac.promote"}
)
VALID_OUTCOMES = frozenset({"PASS", "FAIL", "INCONCLUSIVE"})
VALID_DECISIONS = frozenset({"PROMOTABLE", "REJECTED", "INCONCLUSIVE"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REVISION_RE = re.compile(r"^[0-9a-f]{40,64}$")
_SPEC_ID_RE = re.compile(r"^RAC-I-[0-9]{6}$")
_HYPOTHESIS_ID_RE = re.compile(r"^RAC-H-[0-9]{6}$")
_EVIDENCE_ID_RE = re.compile(r"^RAC-EV-[0-9]{6}$")
_DECISION_ID_RE = re.compile(r"^RAC-D-[0-9]{6}$")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.fullmatch(value))


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _authority_violation(value: Mapping[str, Any]) -> str | None:
    authority = _as_mapping(value.get("authority"))
    if authority is None:
        return "missing authority block"
    if authority.get("advisory_only") is not True:
        return "RAC decisions must remain advisory-only"
    if authority.get("human_gate_required") is not True:
        return "RAC promotion requires a human gate"
    if authority.get("automatic_promotion_forbidden") is not True:
        return "automatic RAC promotion must remain forbidden"

    decision = _as_mapping(value.get("decision"))
    if decision is None:
        return "missing decision block"
    if decision.get("human_gate_required") is not True:
        return "decision removed the human promotion gate"
    if decision.get("automation_may_promote") is not False:
        return "decision granted automated promotion authority"

    spec = _as_mapping(value.get("improvement_spec"))
    if spec is None:
        return "missing ImprovementSpec"
    forbidden = spec.get("forbidden_capabilities")
    if not isinstance(forbidden, (list, tuple)):
        return "ImprovementSpec missing forbidden capabilities"
    missing = REQUIRED_FORBIDDEN_CAPABILITIES - set(forbidden)
    if missing:
        return f"ImprovementSpec removed mandatory prohibitions: {sorted(missing)}"
    return None


class RACModule:
    """First-class RESIDUAL module for RAC improvement envelopes."""

    name = "rac"
    version = "0.1.0"

    def quarantine_policies(self) -> tuple:
        return (self._forbidden_capability_policy,)

    def verifiers(self) -> dict[str, VerifierDescriptor]:
        revision = VerifierRevision.from_artifact(
            __file__,
            configuration={"candidate_contract": CANDIDATE_CONTRACT},
            policy={
                "rac_scientific_authority": "external",
                "negative_results_retained": True,
                "automatic_promotion": False,
            },
        )
        return {
            "contract_integrity": VerifierDescriptor(
                CheckType.MECHANICAL, self._contract_integrity, revision
            ),
            "replication_independence": VerifierDescriptor(
                CheckType.STRUCTURAL, self._replication_independence, revision
            ),
            "authority_boundary": VerifierDescriptor(
                CheckType.STRUCTURAL, self._authority_boundary, revision
            ),
        }

    def brakes(self) -> tuple:
        return (RACAuthorityBrake(),)

    def on_run_opened(self, spec) -> None:
        return None

    def on_run_closed(self, result) -> None:
        return None

    def _forbidden_capability_policy(self, action: ProposedAction) -> str | None:
        capability = action.arguments.get("rac_capability")
        if action.name in FORBIDDEN_ACTION_NAMES:
            return f"RAC action {action.name!r} is outside RESIDUAL authority"
        if action.name.startswith("rac.") and not isinstance(capability, str):
            return "RAC actions must declare a rac_capability"
        if capability in REQUIRED_FORBIDDEN_CAPABILITIES:
            return f"RAC capability {capability!r} is outside RESIDUAL authority"
        if capability is not None and capability not in ALLOWED_RAC_CAPABILITIES:
            return f"unknown RAC capability {capability!r} is denied fail-closed"
        return None

    def _contract_integrity(
        self, candidate: Any, parameters: dict
    ) -> tuple[CheckResult, str]:
        if not isinstance(candidate, Mapping):
            return CheckResult.FAIL, "RAC candidate must be a mapping"
        if candidate.get("contract") != CANDIDATE_CONTRACT:
            return CheckResult.FAIL, "unsupported RAC candidate contract"

        spec = _as_mapping(candidate.get("improvement_spec"))
        decision = _as_mapping(candidate.get("decision"))
        evidence = candidate.get("evidence")
        if spec is None or decision is None or not isinstance(evidence, (list, tuple)):
            return CheckResult.FAIL, "candidate is missing spec/evidence/decision blocks"

        if spec.get("schema_version") != IMPROVEMENT_SCHEMA:
            return CheckResult.FAIL, "unsupported RAC ImprovementSpec schema"
        if not _SPEC_ID_RE.fullmatch(str(spec.get("spec_id", ""))):
            return CheckResult.FAIL, "invalid RAC ImprovementSpec id"
        if not _HYPOTHESIS_ID_RE.fullmatch(str(spec.get("hypothesis_id", ""))):
            return CheckResult.FAIL, "invalid RAC hypothesis id"
        baseline_revision = spec.get("baseline_revision")
        if not isinstance(baseline_revision, str) or not _REVISION_RE.fullmatch(
            baseline_revision
        ):
            return CheckResult.FAIL, "invalid RAC baseline revision"
        if decision.get("schema_version") != DECISION_SCHEMA:
            return CheckResult.FAIL, "unsupported RAC decision schema"
        if not _DECISION_ID_RE.fullmatch(str(decision.get("decision_id", ""))):
            return CheckResult.FAIL, "invalid RAC decision id"

        try:
            spec_hash = _sha256(spec)
        except (TypeError, ValueError):
            return CheckResult.FAIL, "ImprovementSpec is not canonical finite JSON"

        if decision.get("spec_sha256") != spec_hash:
            return CheckResult.FAIL, "decision references a different ImprovementSpec"

        evaluation_version = spec.get("evaluation_version")
        if not isinstance(evaluation_version, str) or not evaluation_version:
            return CheckResult.FAIL, "ImprovementSpec evaluation_version is missing"

        evidence_hashes: list[str] = []
        for index, bundle in enumerate(evidence):
            bundle = _as_mapping(bundle)
            if bundle is None:
                return CheckResult.FAIL, f"evidence[{index}] is not a mapping"
            if bundle.get("schema_version") != EVIDENCE_SCHEMA:
                return CheckResult.FAIL, f"evidence[{index}] schema is unsupported"
            if not _EVIDENCE_ID_RE.fullmatch(str(bundle.get("evidence_id", ""))):
                return CheckResult.FAIL, f"evidence[{index}] id is invalid"
            source_revision = bundle.get("source_revision")
            if not isinstance(source_revision, str) or not _REVISION_RE.fullmatch(
                source_revision
            ):
                return CheckResult.FAIL, f"evidence[{index}] source revision is invalid"
            if bundle.get("spec_sha256") != spec_hash:
                return CheckResult.FAIL, f"evidence[{index}] references another spec"
            if bundle.get("evaluation_version") != evaluation_version:
                return CheckResult.FAIL, f"evidence[{index}] evaluation version drift"

            for field in (
                "spec_sha256",
                "experiment_manifest_sha256",
                "firewall_attestation_sha256",
            ):
                if not _is_sha256(bundle.get(field)):
                    return CheckResult.FAIL, f"evidence[{index}].{field} is invalid"

            artifacts = bundle.get("artifact_sha256s")
            if (
                not isinstance(artifacts, (list, tuple))
                or not artifacts
                or any(not _is_sha256(item) for item in artifacts)
            ):
                return CheckResult.FAIL, f"evidence[{index}] artifact hashes are invalid"

            if bundle.get("outcome") not in VALID_OUTCOMES:
                return CheckResult.FAIL, f"evidence[{index}] outcome is invalid"
            producer = bundle.get("producer_id")
            verifier = bundle.get("independent_verifier_id")
            producer_identity = bundle.get("producer_identity_sha256")
            verifier_identity = bundle.get("independent_verifier_identity_sha256")
            verifier_receipt = bundle.get("independent_verifier_receipt_sha256")
            replication_receipt = bundle.get("replication_receipt_sha256")
            if not isinstance(producer, str) or not producer:
                return CheckResult.FAIL, f"evidence[{index}] producer identity missing"
            if not _is_sha256(producer_identity):
                return CheckResult.FAIL, f"evidence[{index}] producer identity hash invalid"
            if not isinstance(verifier, str) or not verifier:
                return CheckResult.FAIL, f"evidence[{index}] verifier identity missing"
            if not _is_sha256(verifier_identity):
                return CheckResult.FAIL, f"evidence[{index}] verifier identity hash invalid"
            if not _is_sha256(verifier_receipt):
                return CheckResult.FAIL, f"evidence[{index}] verifier receipt hash invalid"
            if producer == verifier or producer_identity == verifier_identity:
                return CheckResult.FAIL, f"evidence[{index}] is self-verified"
            if not isinstance(bundle.get("replication_id"), str) or not bundle.get(
                "replication_id"
            ):
                return CheckResult.FAIL, f"evidence[{index}] replication identity missing"
            if not _is_sha256(replication_receipt):
                return CheckResult.FAIL, f"evidence[{index}] replication receipt hash invalid"

            try:
                evidence_hashes.append(_sha256(bundle))
            except (TypeError, ValueError):
                return CheckResult.FAIL, f"evidence[{index}] is not canonical finite JSON"

        decision_refs = decision.get("evidence_sha256s")
        if not isinstance(decision_refs, (list, tuple)):
            return CheckResult.FAIL, "decision evidence references are missing"
        if list(decision_refs) != evidence_hashes:
            return CheckResult.FAIL, "decision evidence hashes do not match supplied evidence"

        if decision.get("status") not in VALID_DECISIONS:
            return CheckResult.FAIL, "decision status is invalid"

        return CheckResult.PASS, "RAC envelope hashes and frozen evaluation binding verified"

    def _replication_independence(
        self, candidate: Any, parameters: dict
    ) -> tuple[CheckResult, str]:
        if not isinstance(candidate, Mapping):
            return CheckResult.FAIL, "RAC candidate must be a mapping"
        evidence = candidate.get("evidence")
        decision = _as_mapping(candidate.get("decision"))
        if not isinstance(evidence, (list, tuple)) or decision is None:
            return CheckResult.FAIL, "candidate is missing evidence/decision"

        bundles = [bundle for bundle in evidence if isinstance(bundle, Mapping)]
        if len(bundles) != len(evidence):
            return CheckResult.FAIL, "evidence bundle shape invalid"

        outcomes = [bundle.get("outcome") for bundle in bundles]
        if any(outcome == "FAIL" for outcome in outcomes):
            expected = "REJECTED"
        elif any(outcome == "INCONCLUSIVE" for outcome in outcomes):
            expected = "INCONCLUSIVE"
        elif (
            len({bundle.get("replication_id") for bundle in bundles}) < 2
            or len({bundle.get("replication_receipt_sha256") for bundle in bundles}) < 2
        ):
            expected = "INCONCLUSIVE"
        elif (
            len({bundle.get("independent_verifier_id") for bundle in bundles}) < 2
            or len(
                {
                    bundle.get("independent_verifier_identity_sha256")
                    for bundle in bundles
                }
            ) < 2
            or len(
                {
                    bundle.get("independent_verifier_receipt_sha256")
                    for bundle in bundles
                }
            ) < 2
        ):
            expected = "INCONCLUSIVE"
        elif bundles and all(outcome == "PASS" for outcome in outcomes):
            expected = "PROMOTABLE"
        else:
            expected = "INCONCLUSIVE"

        observed = decision.get("status")
        if observed != expected:
            return (
                CheckResult.FAIL,
                f"RAC decision coherence failure: expected {expected}, got {observed}",
            )
        if expected == "PROMOTABLE":
            return (
                CheckResult.PASS,
                "replicated PASS evidence has hash-distinct replication and verifier receipts",
            )
        return CheckResult.PASS, f"non-promotable evidence coherently remains {expected}"

    def _authority_boundary(
        self, candidate: Any, parameters: dict
    ) -> tuple[CheckResult, str]:
        if not isinstance(candidate, Mapping):
            return CheckResult.FAIL, "RAC candidate must be a mapping"
        violation = _authority_violation(candidate)
        if violation:
            return CheckResult.FAIL, violation
        return CheckResult.PASS, "RAC scientific authority remains external and human-gated"


class RACAuthorityBrake:
    """Abort when observations claim a capability RESIDUAL must never receive."""

    name = "rac_authority_boundary"

    def reset(self) -> None:
        return None

    def update(self, event: dict) -> BrakeTrip | None:
        capability = event.get("rac_capability")
        payload = event.get("payload")
        if isinstance(payload, Mapping):
            capability = payload.get("rac_capability", capability)
        if capability in REQUIRED_FORBIDDEN_CAPABILITIES:
            return BrakeTrip(
                self.name,
                f"forbidden RAC capability observed: {capability}",
                "",
                BrakeAction.ABORT,
            )
        if capability is not None and capability not in ALLOWED_RAC_CAPABILITIES:
            return BrakeTrip(
                self.name,
                f"unknown RAC capability observed: {capability}",
                "",
                BrakeAction.ABORT,
            )

        candidate = None
        if isinstance(payload, Mapping):
            candidate = payload.get("candidate")
        if isinstance(candidate, Mapping):
            violation = _authority_violation(candidate)
            if violation:
                return BrakeTrip(
                    self.name,
                    violation,
                    "",
                    BrakeAction.ABORT,
                )
        return None
