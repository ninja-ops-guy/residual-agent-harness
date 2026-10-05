from __future__ import annotations

import hashlib
import json

from residual import (
    AmendmentRule,
    CheckType,
    GoalSpec,
    LoopController,
    RunOutcome,
    StationExtensionRegistry,
    SuccessCriterion,
    Verifier,
)
from residual.brakes import BrakeAction, BrakeTrip
from residual.modules.rac import RACAuthorityBrake, RACModule
from residual.quarantine import PolicyDecision, ProposedAction, QuarantineStore


SHA = "a" * 64
REV = "b" * 40


def _hash(value) -> str:
    blob = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _spec_payload() -> dict:
    return {
        "schema_version": "rac-residual-improvement/1.0",
        "spec_id": "RAC-I-000001",
        "hypothesis_id": "RAC-H-000001",
        "baseline_revision": REV,
        "target_component": "ruthless_pipeline.pattern_genome",
        "proposed_change": "Test one bounded infrastructure change.",
        "evaluation_version": "RAC-EVAL-004",
        "acceptance": {"runtime": {"max_regression": 0.0}},
        "falsification": {"runtime": {"min_regression": 0.01}},
        "created_utc": "2026-09-18T00:00:00Z",
        "forbidden_capabilities": [
            "held_out_candidate_selection",
            "physical_experiment_execution",
            "automatic_scientific_promotion",
        ],
    }


def _evidence(
    spec_hash: str,
    index: int,
    *,
    outcome: str = "PASS",
    replication_id: str = "replication-a",
    verifier_id: str = "verifier-a",
    producer_id: str = "worker-a",
    verifier_identity_sha256: str | None = None,
    verifier_receipt_sha256: str | None = None,
    replication_receipt_sha256: str | None = None,
) -> dict:
    verifier_identity_sha256 = verifier_identity_sha256 or (("c" if index % 2 else "d") * 64)
    verifier_receipt_sha256 = verifier_receipt_sha256 or (("e" if index % 2 else "f") * 64)
    replication_receipt_sha256 = replication_receipt_sha256 or (("1" if index % 2 else "2") * 64)
    return {
        "schema_version": "rac-residual-evidence/1.0",
        "evidence_id": f"RAC-EV-{index:06d}",
        "spec_sha256": spec_hash,
        "source_revision": REV,
        "evaluation_version": "RAC-EVAL-004",
        "experiment_manifest_sha256": SHA,
        "firewall_attestation_sha256": SHA,
        "artifact_sha256s": [SHA],
        "outcome": outcome,
        "producer_id": producer_id,
        "producer_identity_sha256": "b" * 64,
        "independent_verifier_id": verifier_id,
        "independent_verifier_identity_sha256": verifier_identity_sha256,
        "independent_verifier_receipt_sha256": verifier_receipt_sha256,
        "replication_id": replication_id,
        "replication_receipt_sha256": replication_receipt_sha256,
        "notes": "",
    }


def _candidate(
    *,
    outcomes=("PASS", "PASS"),
    replication_ids=("replication-a", "replication-b"),
    verifier_ids=("verifier-a", "verifier-b"),
    status="PROMOTABLE",
) -> dict:
    spec = _spec_payload()
    spec_hash = _hash(spec)
    bundles = [
        _evidence(
            spec_hash,
            index + 1,
            outcome=outcome,
            replication_id=replication_ids[index],
            verifier_id=verifier_ids[index],
        )
        for index, outcome in enumerate(outcomes)
    ]
    decision = {
        "schema_version": "rac-residual-decision/1.0",
        "decision_id": "RAC-D-000001",
        "spec_sha256": spec_hash,
        "evidence_sha256s": [_hash(bundle) for bundle in bundles],
        "status": status,
        "reason": "bounded test fixture",
        "human_gate_required": True,
        "automation_may_promote": False,
    }
    return {
        "contract": "rac-residual-candidate/1.0",
        "improvement_spec": spec,
        "evidence": bundles,
        "decision": decision,
        "authority": {
            "advisory_only": True,
            "human_gate_required": True,
            "automatic_promotion_forbidden": True,
        },
    }


def _goal() -> GoalSpec:
    return GoalSpec(
        "rac_improvement",
        "Verify one externally-produced RAC improvement evidence envelope.",
        (
            SuccessCriterion(
                "contract",
                CheckType.MECHANICAL,
                "Verify RAC hashes and frozen evaluation binding.",
                "rac:contract_integrity",
            ),
            SuccessCriterion(
                "replication",
                CheckType.STRUCTURAL,
                "Verify outcome, replication, and independent-verifier coherence.",
                "rac:replication_independence",
            ),
            SuccessCriterion(
                "authority",
                CheckType.STRUCTURAL,
                "Verify RESIDUAL cannot promote RAC scientific claims.",
                "rac:authority_boundary",
            ),
        ),
        1,
        1000,
        60,
        AmendmentRule(("operator",)),
    )


class Pass:
    def __init__(self, candidate):
        self.candidate = candidate

    def run_pass(self, spec, pass_number):
        return {"candidate": self.candidate, "tokens_used": 0, "observations": []}


def _run(candidate) -> RunOutcome:
    registry = StationExtensionRegistry().register_module(RACModule())
    controller = LoopController(
        _goal(), Verifier({}), Pass(candidate), extensions=registry
    )
    return controller.run().outcome


def test_valid_replicated_advisory_candidate_passes_station() -> None:
    assert _run(_candidate()) == RunOutcome.SUCCESS


def test_correctly_retained_negative_result_is_verified_not_rewritten() -> None:
    candidate = _candidate(
        outcomes=("FAIL",),
        replication_ids=("replication-a",),
        verifier_ids=("verifier-a",),
        status="REJECTED",
    )
    assert _run(candidate) == RunOutcome.SUCCESS
    assert candidate["evidence"][0]["outcome"] == "FAIL"
    assert candidate["decision"]["status"] == "REJECTED"


def test_false_promotable_without_replication_fails() -> None:
    candidate = _candidate(
        outcomes=("PASS",),
        replication_ids=("replication-a",),
        verifier_ids=("verifier-a",),
        status="PROMOTABLE",
    )
    assert _run(candidate) != RunOutcome.SUCCESS


def test_same_verifier_identity_cannot_satisfy_promotable() -> None:
    candidate = _candidate(
        verifier_ids=("verifier-a", "verifier-a"),
        status="PROMOTABLE",
    )
    assert _run(candidate) != RunOutcome.SUCCESS



def test_distinct_labels_cannot_fake_hash_bound_independence() -> None:
    candidate = _candidate()
    first, second = candidate["evidence"]
    second["independent_verifier_identity_sha256"] = first[
        "independent_verifier_identity_sha256"
    ]
    candidate["decision"]["evidence_sha256s"] = [_hash(bundle) for bundle in candidate["evidence"]]
    assert _run(candidate) != RunOutcome.SUCCESS

    candidate = _candidate()
    first, second = candidate["evidence"]
    second["replication_receipt_sha256"] = first["replication_receipt_sha256"]
    candidate["decision"]["evidence_sha256s"] = [_hash(bundle) for bundle in candidate["evidence"]]
    assert _run(candidate) != RunOutcome.SUCCESS

def test_self_verification_fails_contract_integrity() -> None:
    candidate = _candidate()
    bundle = candidate["evidence"][0]
    bundle["independent_verifier_id"] = bundle["producer_id"]
    candidate["decision"]["evidence_sha256s"][0] = _hash(bundle)
    assert _run(candidate) != RunOutcome.SUCCESS


def test_spec_tamper_after_evidence_binding_fails() -> None:
    candidate = _candidate()
    candidate["improvement_spec"]["evaluation_version"] = "RAC-EVAL-005"
    assert _run(candidate) != RunOutcome.SUCCESS


def test_authority_escalation_fails_and_is_quarantined() -> None:
    candidate = _candidate()
    candidate["authority"]["automatic_promotion_forbidden"] = False
    assert _run(candidate) != RunOutcome.SUCCESS

    gate = QuarantineStore()
    held = gate.hold(
        ProposedAction(
            "tool_call",
            "rac.promote",
            {"rac_capability": "automatic_scientific_promotion"},
            "worker",
        )
    )
    decision = gate.evaluate(held, RACModule().quarantine_policies())
    assert decision == PolicyDecision.DENY


def test_authority_brake_aborts_forbidden_capability_observation() -> None:
    brake = RACAuthorityBrake()
    trip = brake.update(
        {
            "kind": "custom",
            "payload": {"rac_capability": "physical_experiment_execution"},
        }
    )
    assert isinstance(trip, BrakeTrip)
    assert trip.recommended_action == BrakeAction.ABORT


def test_non_rac_action_is_not_blocked_by_rac_policy() -> None:
    action = ProposedAction(
        "tool_call", "read_file", {"rac_capability": "read_public_artifact"}, "worker"
    )
    assert RACModule().quarantine_policies()[0](action) is None


def test_unknown_schema_and_capability_fail_closed() -> None:
    candidate = _candidate()
    candidate["decision"]["schema_version"] = "rac-residual-decision/99.0"
    assert _run(candidate) != RunOutcome.SUCCESS

    module = RACModule()
    undeclared = ProposedAction("tool_call", "rac.read", {}, "worker")
    assert module.quarantine_policies()[0](undeclared) is not None

    unknown = ProposedAction(
        "tool_call", "rac.experimental", {"rac_capability": "future_unknown"}, "worker"
    )
    assert module.quarantine_policies()[0](unknown) is not None

    trip = RACAuthorityBrake().update(
        {"kind": "custom", "payload": {"rac_capability": "future_unknown"}}
    )
    assert isinstance(trip, BrakeTrip)
    assert trip.recommended_action == BrakeAction.ABORT
