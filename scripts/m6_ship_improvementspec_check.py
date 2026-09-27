from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

# Force imports from the candidate repository, never the outer editable install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from residual.improvement.spec import ImprovementSpec


def fail(message: str) -> None:
    raise AssertionError(message)


kw = dict(
    improvement_id="RI-ROADMAP-001",
    observation="repair attempts consume measurable resources",
    hypothesis="bounded repair context can reduce repeated implementation failures",
    target_metrics=("task_success_rate", "repair_attempts"),
    preserve_metrics=("verification_integrity",),
    protected_invariants=("M4", "evidence_integrity", "promotion_authority"),
    acceptance={"success_rate_min": 0.9, "max_regression": 0.0},
)

spec = ImprovementSpec(**kw)
value = spec.to_dict()
if value["target_metrics"] != ["task_success_rate", "repair_attempts"]:
    fail("target_metrics must serialize as an ordered list")
if value["preserve_metrics"] != ["verification_integrity"]:
    fail("preserve_metrics must serialize as an ordered list")
if value["protected_invariants"] != ["M4", "evidence_integrity", "promotion_authority"]:
    fail("protected_invariants must serialize as an ordered list")
if value["human_approval_required"] is not True:
    fail("human_approval_required must default to True")

value["acceptance"]["success_rate_min"] = 0
if spec.to_dict()["acceptance"]["success_rate_min"] != 0.9:
    fail("to_dict() must defensively copy acceptance")

canonical_value = spec.canonical_json()
expected = json.dumps(spec.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
if not isinstance(canonical_value, str):
    fail(f"canonical_json() must return str, got {type(canonical_value).__name__}")
if canonical_value != expected:
    fail(f"canonical_json() mismatch: expected {expected!r}, got {canonical_value!r}")

expected_hash = hashlib.sha256(canonical_value.encode("utf-8")).hexdigest()
if spec.sha256() != expected_hash:
    fail(f"sha256() mismatch: expected {expected_hash}, got {spec.sha256()!r}")
if spec.sha256() != ImprovementSpec(**kw).sha256():
    fail("identical contracts must have stable sha256 identity")

try:
    spec.improvement_id = "changed"
except FrozenInstanceError:
    pass
else:
    fail("ImprovementSpec must be frozen")

invalid = [
    ("blank improvement_id", {**kw, "improvement_id": " "}),
    ("blank observation", {**kw, "observation": "\t"}),
    ("blank hypothesis", {**kw, "hypothesis": ""}),
    ("empty target_metrics", {**kw, "target_metrics": ()}),
    ("empty preserve_metrics", {**kw, "preserve_metrics": ()}),
    ("empty protected_invariants", {**kw, "protected_invariants": ()}),
    ("blank target metric", {**kw, "target_metrics": ("ok", " ")}),
    ("blank preserve metric", {**kw, "preserve_metrics": (" ",)}),
    ("blank protected invariant", {**kw, "protected_invariants": ("M4", "")}),
    ("empty acceptance", {**kw, "acceptance": {}}),
    ("human approval disabled", {**kw, "human_approval_required": False}),
]
for label, case in invalid:
    try:
        ImprovementSpec(**case)
    except ValueError:
        continue
    fail(f"invalid ImprovementSpec accepted: {label}")
