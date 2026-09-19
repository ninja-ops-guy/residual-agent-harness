from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ALLOWED_INVARIANTS = {
    "M4",
    "evidence_integrity",
    "verification_integrity",
    "promotion_authority",
}
OPS = {"<=", ">=", "==", "<", ">"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


snapshot = json.loads(Path("evidence/m6-discovery-snapshot.json").read_text())
proposal = json.loads(Path("proposal.json").read_text())

claimed_hash = snapshot.pop("snapshot_hash")
actual_hash = hashlib.sha256(canonical(snapshot).encode("utf-8")).hexdigest()
if claimed_hash != actual_hash:
    raise AssertionError("EvidenceSnapshot hash mismatch")
if proposal.get("evidence_snapshot_hash") != claimed_hash:
    raise AssertionError("proposal must bind exact EvidenceSnapshot hash")
if proposal.get("human_approval_required") is not True:
    raise AssertionError("proposal must retain human approval")

kind = proposal.get("type")
metrics = snapshot["metrics"]
metric_catalog = set(snapshot["metric_catalog"])

if kind == "improvement_spec":
    observation = proposal.get("observation")
    if not isinstance(observation, dict):
        raise AssertionError("ImprovementSpec observation must be structured")
    metric = observation.get("metric")
    if metric not in metrics:
        raise AssertionError("observation metric is not measured")
    if observation.get("value") != metrics[metric]:
        raise AssertionError("observation baseline value was invented or changed")
    if "comparison_metric" in observation:
        comparison = observation["comparison_metric"]
        if comparison not in metrics:
            raise AssertionError("comparison metric is not measured")
        if observation.get("comparison_value") != metrics[comparison]:
            raise AssertionError("comparison baseline value was invented or changed")

    hypothesis = proposal.get("hypothesis")
    if not isinstance(hypothesis, str) or len(hypothesis.strip()) < 30:
        raise AssertionError("hypothesis must be substantive and falsifiable")

    targets = proposal.get("target_metrics")
    preserves = proposal.get("preserve_metrics")
    if not isinstance(targets, list) or not targets or any(x not in metric_catalog for x in targets):
        raise AssertionError("target_metrics must be nonempty measured metric IDs")
    if not isinstance(preserves, list) or not preserves or any(x not in metric_catalog for x in preserves):
        raise AssertionError("preserve_metrics must be nonempty measured metric IDs")
    if set(targets) & set(preserves):
        raise AssertionError("target and preserve metrics must be distinct")

    invariants = proposal.get("protected_invariants")
    if not isinstance(invariants, list) or not invariants or any(x not in ALLOWED_INVARIANTS for x in invariants):
        raise AssertionError("protected_invariants must use registered invariant IDs")

    acceptance = proposal.get("acceptance")
    if not isinstance(acceptance, list) or not acceptance:
        raise AssertionError("acceptance must be a structured criterion list")
    covered = set()
    for criterion in acceptance:
        if not isinstance(criterion, dict) or set(criterion) != {"metric", "operator", "threshold"}:
            raise AssertionError("each acceptance criterion must contain metric/operator/threshold only")
        m = criterion["metric"]
        if m not in set(targets) | set(preserves):
            raise AssertionError("acceptance criterion references undeclared metric")
        if criterion["operator"] not in OPS:
            raise AssertionError("acceptance operator is unsupported")
        value = criterion["threshold"]
        if type(value) not in (int, float) or isinstance(value, bool) or not math.isfinite(value):
            raise AssertionError("acceptance threshold must be finite numeric")
        covered.add(m)
    if not set(targets).issubset(covered):
        raise AssertionError("every target metric requires an acceptance criterion")
    if not set(preserves).issubset(covered):
        raise AssertionError("every preserve metric requires an acceptance criterion")

elif kind == "measurement_gap":
    required = {
        "type", "question", "missing_metric", "why_needed",
        "proposed_measurement", "preserve_invariants",
        "evidence_snapshot_hash", "human_approval_required",
    }
    if set(proposal) != required:
        raise AssertionError("MeasurementGap fields must match the closed contract")
    missing = proposal["missing_metric"]
    if not isinstance(missing, str) or not missing.strip() or missing in metrics:
        raise AssertionError("MeasurementGap metric must actually be absent")
    for field in ("question", "why_needed", "proposed_measurement"):
        if not isinstance(proposal[field], str) or len(proposal[field].strip()) < 20:
            raise AssertionError(f"{field} must be substantive")
    invariants = proposal["preserve_invariants"]
    if not isinstance(invariants, list) or not invariants or any(x not in ALLOWED_INVARIANTS for x in invariants):
        raise AssertionError("MeasurementGap preserve_invariants must use registered invariant IDs")
else:
    raise AssertionError("proposal type must be improvement_spec or measurement_gap")
