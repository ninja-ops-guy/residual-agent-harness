"""failure_classification verifier (slm00.verifier.failure_classification).

Category contract
-----------------
input_state:
  taxonomy: [label]                 exact frozen taxonomy
  aliases: {alias: label}           preregistered alias map (may be {})
  observation: {...}                free-form evidence of the failure

expected_output:
  label: str                        the single correct taxonomy label

Candidate output: {"label": str}

Deterministic mapping rules:
  1. candidate label exactly in taxonomy            -> that label
  2. candidate label in preregistered aliases       -> aliases[label]
  3. otherwise                                      -> FAIL UNKNOWN_LABEL
Grading: mapped label must equal expected label exactly. No partial credit,
no semantic similarity. Expected labels outside the frozen taxonomy, or
aliases that collide with taxonomy labels or map to non-taxonomy targets,
are BENCHMARK_DEFECTs.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from .base import BaseVerifier, VerifierResult, _defect, _fail, _pass


class FailureClassificationVerifier(BaseVerifier):
    VERIFIER_ID = "slm00.verifier.failure_classification"
    CATEGORY = "failure_classification"

    def _check_item(self, item: Mapping[str, Any]) -> Optional[VerifierResult]:
        defect = super()._check_item(item)
        if defect is not None:
            return defect
        state = item["input_state"]
        taxonomy = state.get("taxonomy")
        if not isinstance(taxonomy, list) or not taxonomy or not all(
            isinstance(t, str) for t in taxonomy
        ):
            return _defect("DEFECT_BAD_TAXONOMY", "taxonomy must be non-empty [str]")
        if len(set(taxonomy)) != len(taxonomy):
            return _defect("DEFECT_DUPLICATE_TAXONOMY_LABEL")
        aliases = state.get("aliases")
        if aliases is None:
            aliases = {}
        if not isinstance(aliases, Mapping):
            return _defect("DEFECT_BAD_ALIASES")
        for alias, target in aliases.items():
            if alias in taxonomy:
                return _defect(
                    "DEFECT_ALIAS_COLLIDES_WITH_TAXONOMY",
                    f"alias {alias!r} shadows a taxonomy label",
                )
            if target not in taxonomy:
                return _defect(
                    "DEFECT_ALIAS_TARGET_UNKNOWN",
                    f"alias {alias!r} maps to non-taxonomy label {target!r}",
                )
        if not isinstance(state.get("observation"), Mapping):
            return _defect("DEFECT_MISSING_OBSERVATION")
        expected_label = item["expected_output"].get("label")
        if expected_label not in taxonomy:
            return _defect(
                "DEFECT_EXPECTED_LABEL_NOT_IN_TAXONOMY",
                f"expected label {expected_label!r} outside frozen taxonomy",
            )
        return None

    def _evaluate(
        self, item: Mapping[str, Any], candidate_output: Mapping[str, Any]
    ) -> VerifierResult:
        state = item["input_state"]
        taxonomy = state["taxonomy"]
        aliases = state.get("aliases") or {}
        raw = candidate_output.get("label")
        if not isinstance(raw, str) or not raw:
            return _fail("MISSING_LABEL", "candidate label must be a non-empty string")
        if raw in taxonomy:
            mapped = raw
        elif raw in aliases:
            mapped = aliases[raw]
        else:
            return _fail(
                "UNKNOWN_LABEL",
                f"label {raw!r} is neither a taxonomy label nor a "
                f"preregistered alias",
            )
        if mapped != item["expected_output"]["label"]:
            return _fail(
                "WRONG_LABEL",
                f"mapped label {mapped!r} != expected "
                f"{item['expected_output']['label']!r}",
            )
        return _pass()
