"""evidence_sufficiency verifier (slm00.verifier.evidence_sufficiency).

Category contract
-----------------
input_state:
  evidence_requirements: [{requirement_id, kind}]   explicit requirements
  artifacts: [{artifact_id, kind, digest, provenance}]  available evidence
  required_verifier_outputs: [str]   verifier refs that MUST appear in the
                                     claim's verifier_outputs

expected_output:
  sufficient: bool
  missing_requirements: [requirement_id]   exact set, empty iff sufficient

Candidate output:
  {"sufficient": bool, "missing_requirements": [requirement_id],
   "verifier_outputs": [str]}

Determinism rule: sufficiency is decided ONLY by mechanical checks —
requirement coverage by kind-matching artifacts, provenance integrity
(provenance non-empty object with source_class), digest/reference validity
(sha256 format), and required verifier outputs present. No judgment of
whether evidence "looks sufficient" is performed; any requirement that
cannot be reduced to these mechanical checks MUST NOT be encoded here (see
AMBIGUITY.md).

Derived truth: a requirement is satisfied iff at least one artifact with a
matching kind exists that has a valid digest and valid provenance. The
derived sufficiency is compared with expected_output; mismatch is a
BENCHMARK_DEFECT.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from .base import (
    BaseVerifier,
    VerifierResult,
    _defect,
    _fail,
    _pass,
    is_valid_digest,
)

_VALID_SOURCE_CLASSES = {"ax21", "synthetic", "benchmark", "replay", "other"}


class EvidenceSufficiencyVerifier(BaseVerifier):
    VERIFIER_ID = "slm00.verifier.evidence_sufficiency"
    CATEGORY = "evidence_sufficiency"

    @staticmethod
    def _artifact_ok(artifact: Mapping[str, Any]) -> bool:
        """Artifact is usable evidence: valid digest + provenance integrity."""
        if not isinstance(artifact, Mapping):
            return False
        if not is_valid_digest(artifact.get("digest")):
            return False
        provenance = artifact.get("provenance")
        if not isinstance(provenance, Mapping):
            return False
        if provenance.get("source_class") not in _VALID_SOURCE_CLASSES:
            return False
        return True

    @classmethod
    def derive_missing(cls, input_state: Mapping[str, Any]) -> frozenset:
        """Exact set of unsatisfied requirement ids, derived mechanically."""
        requirements = input_state.get("evidence_requirements") or []
        artifacts = input_state.get("artifacts") or []
        usable = [a for a in artifacts if cls._artifact_ok(a)]
        missing = set()
        for req in requirements:
            kind = req.get("kind")
            if not any(a.get("kind") == kind for a in usable):
                missing.add(req.get("requirement_id"))
        return frozenset(missing)

    def _check_item(self, item: Mapping[str, Any]) -> Optional[VerifierResult]:
        defect = super()._check_item(item)
        if defect is not None:
            return defect
        state = item["input_state"]
        reqs = state.get("evidence_requirements")
        if not isinstance(reqs, list) or not reqs:
            return _defect(
                "DEFECT_MISSING_REQUIREMENTS",
                "evidence_requirements must be a non-empty list",
            )
        ids = [r.get("requirement_id") for r in reqs if isinstance(r, Mapping)]
        if len(ids) != len(reqs) or None in ids:
            return _defect("DEFECT_BAD_REQUIREMENT", "requirement missing id")
        if len(set(ids)) != len(ids):
            return _defect("DEFECT_DUPLICATE_REQUIREMENT_ID")
        for req in reqs:
            if not isinstance(req.get("kind"), str) or not req["kind"]:
                return _defect("DEFECT_REQUIREMENT_MISSING_KIND")
        artifacts = state.get("artifacts")
        if not isinstance(artifacts, list):
            return _defect("DEFECT_MISSING_ARTIFACTS", "artifacts must be a list")
        rvo = state.get("required_verifier_outputs")
        if rvo is not None and not (
            isinstance(rvo, list) and all(isinstance(v, str) for v in rvo)
        ):
            return _defect("DEFECT_BAD_REQUIRED_VERIFIER_OUTPUTS")
        return None

    def _derive_expected(
        self, item: Mapping[str, Any]
    ) -> tuple[Any, Optional[VerifierResult]]:
        return self.derive_missing(item["input_state"]), None

    def _expected_matches(
        self, expected: Mapping[str, Any], derived: frozenset
    ) -> Optional[VerifierResult]:
        sufficient = expected.get("sufficient")
        if not isinstance(sufficient, bool):
            return _defect("DEFECT_MISSING_SUFFICIENCY", "expected sufficient: bool")
        declared = expected.get("missing_requirements")
        if not isinstance(declared, list):
            return _defect("DEFECT_MISSING_MISSING_SET")
        if frozenset(declared) != derived:
            return _defect(
                "EXPECTED_SET_MISMATCH",
                f"expected missing {sorted(declared)} != derived {sorted(derived)}",
            )
        if sufficient != (not derived):
            return _defect(
                "DEFECT_SUFFICIENCY_INCONSISTENT",
                "expected sufficient flag inconsistent with missing set",
            )
        return None

    def _evaluate(
        self, item: Mapping[str, Any], candidate_output: Mapping[str, Any]
    ) -> VerifierResult:
        state = item["input_state"]
        expected = item["expected_output"]
        derived = self.derive_missing(state)

        claimed_missing = candidate_output.get("missing_requirements")
        if not isinstance(claimed_missing, list):
            return _fail("MISSING_FIELD", "missing_requirements must be a list")
        unknown = set(claimed_missing) - {
            r["requirement_id"] for r in state["evidence_requirements"]
        }
        if unknown:
            return _fail(
                "UNKNOWN_REQUIREMENT_ID",
                f"candidate cites unknown requirement ids {sorted(unknown)}",
            )
        if frozenset(claimed_missing) != derived:
            return _fail(
                "WRONG_MISSING_SET",
                f"candidate missing {sorted(claimed_missing)} != "
                f"actual {sorted(derived)}",
            )
        sufficient = candidate_output.get("sufficient")
        if not isinstance(sufficient, bool):
            return _fail("MISSING_FIELD", "sufficient must be a bool")
        if sufficient != expected["sufficient"]:
            return _fail(
                "WRONG_SUFFICIENCY",
                f"candidate sufficient={sufficient} != expected "
                f"{expected['sufficient']}",
            )
        required_outputs = state.get("required_verifier_outputs") or []
        if required_outputs:
            outputs = candidate_output.get("verifier_outputs")
            if not isinstance(outputs, list):
                return _fail(
                    "MISSING_VERIFIER_OUTPUTS",
                    "verifier_outputs list required for this item",
                )
            absent = sorted(set(required_outputs) - set(outputs))
            if absent:
                return _fail(
                    "MISSING_VERIFIER_OUTPUTS",
                    f"required verifier outputs absent: {absent}",
                )
        return _pass()
