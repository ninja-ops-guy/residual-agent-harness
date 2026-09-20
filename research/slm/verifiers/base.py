"""Shared verifier interface for the SLM-00 Control Bench v0 verifier suite.

Lane D (category-specific verifiers). Lane C's benchmark items reference
verifiers by the IDs declared here and in MANIFEST.json.

Contract
--------
Every verifier is a pure, deterministic function:

    verify(item, candidate_output) -> VerifierResult

where the verdict is one of PASS | FAIL | BENCHMARK_DEFECT with a
machine-readable reason code. Verifiers:

* perform no network or model calls;
* never silently repair defects in benchmark items — they report them as
  BENCHMARK_DEFECT;
* never silently repair malformed candidate output — malformed output is a
  FAIL (per CONTROL-BENCH-V0: "Invalid output is a failure, not silently
  repaired");
* treat any check requiring subjective semantic judgment as out of scope for
  the deterministic subset (see AMBIGUITY.md).
"""
from __future__ import annotations

import enum
import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence


class Verdict(str, enum.Enum):
    """Terminal verdict of a verifier invocation."""

    PASS = "PASS"
    FAIL = "FAIL"
    BENCHMARK_DEFECT = "BENCHMARK_DEFECT"


@dataclass(frozen=True)
class VerifierResult:
    """Result of a verifier invocation.

    reason_code is a stable, SCREAMING_SNAKE_CASE machine code. Tests and
    downstream analysis may key on (verdict, reason_code) but not on detail.
    """

    verdict: Verdict
    reason_code: str
    detail: str = ""

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return f"{self.verdict.value}:{self.reason_code}:{self.detail}"


class MalformedOutput:
    """Sentinel wrapper for syntactically invalid candidate output.

    Harnesses that parse model output should pass MalformedOutput(raw) when
    parsing fails, rather than passing raw strings. Verifiers MUST fail any
    candidate wrapped in this sentinel without inspecting raw content.
    """

    def __init__(self, raw: Any = None) -> None:
        self.raw = raw

    def __repr__(self) -> str:  # pragma: no cover - convenience only
        return f"MalformedOutput({self.raw!r})"


# Item contract fields (CONTROL-BENCH-V0 "Item contract"). Lane C items MUST
# carry at least these fields.
REQUIRED_ITEM_FIELDS: Sequence[str] = (
    "item_id",
    "category",
    "input_state",
    "expected_output",
    "verifier_ref",
)

_SHA256_RE = re.compile(r"^(sha256:)?[0-9a-f]{64}$")


def _pass(reason_code: str = "OK", detail: str = "") -> VerifierResult:
    return VerifierResult(Verdict.PASS, reason_code, detail)


def _fail(reason_code: str, detail: str = "") -> VerifierResult:
    return VerifierResult(Verdict.FAIL, reason_code, detail)


def _defect(reason_code: str, detail: str = "") -> VerifierResult:
    return VerifierResult(Verdict.BENCHMARK_DEFECT, reason_code, detail)


def canonicalize(value: Any) -> Any:
    """Canonical form for semantic JSON equivalence.

    Dict key order is normalized recursively; lists keep order (order is
    semantic unless a verifier states otherwise); numbers 1 and 1.0 are
    equivalent. Two candidate/expected values are semantically equal iff
    their canonical forms are equal. Byte-exact serialization is NOT
    required.
    """
    if isinstance(value, Mapping):
        return {k: canonicalize(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [canonicalize(v) for v in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value)
    return value


def semantically_equal(a: Any, b: Any) -> bool:
    """Semantic (not byte-exact) JSON equality."""
    return canonicalize(a) == canonicalize(b)


def canonical_dumps(value: Any) -> str:
    return json.dumps(canonicalize(value), sort_keys=True, separators=(",", ":"))


def is_valid_digest(value: Any) -> bool:
    """True iff value is a well-formed sha256 digest reference."""
    return isinstance(value, str) and bool(_SHA256_RE.match(value))


def get_path(obj: Any, path: str) -> Any:
    """Dotted-path lookup into nested mappings/lists.

    Returns _MISSING when any segment is absent, so callers can distinguish
    "absent" from None.
    """
    current = obj
    for segment in path.split("."):
        if isinstance(current, Mapping) and segment in current:
            current = current[segment]
        elif isinstance(current, (list, tuple)) and segment.isdigit():
            idx = int(segment)
            if 0 <= idx < len(current):
                current = current[idx]
            else:
                return MISSING
        else:
            return MISSING
    return current


class _Missing:
    _instance: Optional["_Missing"] = None

    def __new__(cls) -> "_Missing":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:  # pragma: no cover - convenience only
        return "MISSING"

    def __bool__(self) -> bool:
        return False


MISSING = _Missing()

NO_DERIVATION = object()  # sentinel: verifier does not independently derive


class BaseVerifier:
    """Abstract base for category-specific deterministic verifiers.

    Subclasses set VERIFIER_ID / CATEGORY and implement _derive_expected()
    (independent recomputation of the expected answer from input_state, used
    adversarially against Lane C's frozen expected_output) and _evaluate()
    (grading of the candidate against the item).
    """

    VERIFIER_ID: str = "base"
    CATEGORY: str = "base"
    VERSION: str = "1.0.0"

    def verify(self, item: Mapping[str, Any], candidate_output: Any) -> VerifierResult:
        defect = self._check_item(item)
        if defect is not None:
            return defect
        if isinstance(candidate_output, MalformedOutput) or not isinstance(
            candidate_output, Mapping
        ):
            return _fail(
                "MALFORMED_OUTPUT",
                "candidate output is not a parseable JSON object",
            )
        derived, defect = self._derive_expected(item)
        if defect is not None:
            return defect
        expected = item["expected_output"]
        if derived is not NO_DERIVATION:
            match = self._expected_matches(expected, derived)
            if match is not None:
                return match
        return self._evaluate(item, candidate_output)

    # -- hooks -----------------------------------------------------------

    def _check_item(self, item: Mapping[str, Any]) -> Optional[VerifierResult]:
        if not isinstance(item, Mapping):
            return _defect("ITEM_NOT_OBJECT", "benchmark item is not an object")
        for field_name in REQUIRED_ITEM_FIELDS:
            if field_name not in item:
                return _defect(
                    "ITEM_MISSING_FIELD", f"item missing required field {field_name!r}"
                )
        if item.get("category") != self.CATEGORY:
            return _defect(
                "CATEGORY_MISMATCH",
                f"item category {item.get('category')!r} != verifier category "
                f"{self.CATEGORY!r}",
            )
        verifier_ref = item.get("verifier_ref")
        if isinstance(verifier_ref, str) and verifier_ref != self.VERIFIER_ID:
            return _defect(
                "VERIFIER_REF_MISMATCH",
                f"item verifier_ref {verifier_ref!r} != {self.VERIFIER_ID!r}",
            )
        if not isinstance(item["input_state"], Mapping):
            return _defect("INPUT_STATE_NOT_OBJECT")
        if not isinstance(item["expected_output"], Mapping):
            return _defect("EXPECTED_OUTPUT_NOT_OBJECT")
        return None

    def _derive_expected(
        self, item: Mapping[str, Any]
    ) -> tuple[Any, Optional[VerifierResult]]:
        """Independently derive the expected answer from input_state.

        Returns (derived, defect). derived is NO_DERIVATION when the category
        does not support independent derivation (None is a legitimate derived
        value and MUST NOT be used as the sentinel); defect non-null means the
        item is internally inconsistent / unverifiable -> BENCHMARK_DEFECT.
        """
        return NO_DERIVATION, None

    def _expected_matches(
        self, expected: Mapping[str, Any], derived: Any
    ) -> Optional[VerifierResult]:
        """Compare frozen expected_output with derived answer.

        Returns a BENCHMARK_DEFECT result on mismatch, else None. Subclasses
        that derive the full expected answer override this.
        """
        return None

    def _evaluate(
        self, item: Mapping[str, Any], candidate_output: Mapping[str, Any]
    ) -> VerifierResult:
        raise NotImplementedError

    # -- shared helpers --------------------------------------------------

    @staticmethod
    def _require(condition: bool, reason_code: str, detail: str) -> Optional[VerifierResult]:
        if condition:
            return _defect(reason_code, detail)
        return None


def ensure_unique_ids(values: Iterable[Any], key: str) -> bool:
    seen = set()
    for value in values:
        ident = value.get(key) if isinstance(value, Mapping) else None
        if ident in seen:
            return False
        seen.add(ident)
    return True
