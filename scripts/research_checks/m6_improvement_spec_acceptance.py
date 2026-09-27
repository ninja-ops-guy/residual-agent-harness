from __future__ import annotations

import hashlib
import json
import os
import sys

sys.path.insert(0, os.getcwd())

from residual.improvement import ImprovementSpec


def expect_invalid(**case):
    try:
        ImprovementSpec(**case)
    except (ValueError, TypeError):
        return
    raise AssertionError("invalid ImprovementSpec accepted: " + repr(case))


acceptance = {
    "token_reduction_pct": 10,
    "nested": {"max_regression": 1},
    "modes": ["strict", "bounded"],
}
base = dict(
    improvement_id="RI-0001",
    observation="retry cost is high",
    hypothesis="bounded retry reduces cost",
    target_metrics=("token_cost",),
    preserve_metrics=("task_success",),
    protected_invariants=("M4", "evidence_integrity"),
)
s = ImprovementSpec(**base, acceptance=acceptance)
original_hash = s.sha256()
expected = {
    "token_reduction_pct": 10,
    "nested": {"max_regression": 1},
    "modes": ["strict", "bounded"],
}
assert s.to_dict()["acceptance"] == expected

# Input aliases must not mutate the spec.
acceptance["token_reduction_pct"] = 999
acceptance["nested"]["max_regression"] = 999
acceptance["modes"].append("evil")
assert s.to_dict()["acceptance"] == expected
assert s.sha256() == original_hash

# Public acceptance data must be deeply immutable.
try:
    s.acceptance["token_reduction_pct"] = 999
except (TypeError, AttributeError):
    pass
else:
    raise AssertionError("acceptance mapping is mutable")

try:
    s.acceptance["nested"]["max_regression"] = 999
except (TypeError, AttributeError):
    pass
else:
    raise AssertionError("nested acceptance mapping is mutable")

try:
    s.acceptance["modes"].append("evil")
except (TypeError, AttributeError):
    pass
else:
    raise AssertionError("nested acceptance sequence is mutable")

assert s.sha256() == original_hash

# to_dict must recursively thaw into detached mutable JSON data.
d = s.to_dict()
d["acceptance"]["nested"]["max_regression"] = 999
d["acceptance"]["modes"].append("changed")
assert s.to_dict()["acceptance"] == expected
assert s.sha256() == original_hash

c = s.canonical_json()
assert c == json.dumps(
    s.to_dict(),
    sort_keys=True,
    separators=(",", ":"),
    ensure_ascii=False,
    allow_nan=False,
)
assert s.sha256() == hashlib.sha256(c.encode("utf-8")).hexdigest()
assert s.sha256() == ImprovementSpec(**base, acceptance=expected).sha256()

for case in (
    {**base, "acceptance": expected, "improvement_id": " "},
    {**base, "acceptance": expected, "observation": "\t"},
    {**base, "acceptance": expected, "hypothesis": ""},
    {**base, "acceptance": expected, "target_metrics": ()},
    {**base, "acceptance": expected, "preserve_metrics": ()},
    {**base, "acceptance": expected, "protected_invariants": ()},
    {**base, "acceptance": expected, "target_metrics": ("ok", " ")},
    {**base, "acceptance": {}},
    {**base, "acceptance": expected, "human_approval_required": False},
    {**base, "acceptance": {"bad": float("nan")}},
    {**base, "acceptance": {"bad": float("inf")}},
    {**base, "acceptance": {1: "non-string-key"}},
    {**base, "acceptance": {"bad": object()}},
):
    expect_invalid(**case)

print("M6 ImprovementSpec immutable acceptance: PASS")
