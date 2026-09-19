#!/usr/bin/env python3
"""RRI-001: deterministic RAC/RESIDUAL contract smoke mission.

No model calls, RAC imports, held-out data, or physical execution.
"""
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
from residual.modules.rac import RACModule


SHA = "a" * 64
REV = "b" * 40


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def candidate() -> dict:
    spec = {
        "schema_version": "rac-residual-improvement/1.0",
        "spec_id": "RAC-I-000001",
        "hypothesis_id": "RAC-H-000001",
        "baseline_revision": REV,
        "target_component": "ruthless_pipeline.pattern_genome",
        "proposed_change": "RRI-001 deterministic integration smoke.",
        "evaluation_version": "RAC-EVAL-004",
        "acceptance": {"contract_conformance": True},
        "falsification": {"contract_conformance": False},
        "created_utc": "2026-09-18T00:00:00Z",
        "forbidden_capabilities": [
            "held_out_candidate_selection",
            "physical_experiment_execution",
            "automatic_scientific_promotion",
        ],
    }
    spec_hash = digest(spec)

    evidence = []
    for number, replication, verifier in (
        (1, "rri-001-a", "verifier-a"),
        (2, "rri-001-b", "verifier-b"),
    ):
        evidence.append(
            {
                "schema_version": "rac-residual-evidence/1.0",
                "evidence_id": f"RAC-EV-{number:06d}",
                "spec_sha256": spec_hash,
                "source_revision": REV,
                "evaluation_version": spec["evaluation_version"],
                "experiment_manifest_sha256": SHA,
                "firewall_attestation_sha256": SHA,
                "artifact_sha256s": [SHA],
                "outcome": "PASS",
                "producer_id": "rri-001-worker",
                "producer_identity_sha256": "b" * 64,
                "independent_verifier_id": verifier,
                "independent_verifier_identity_sha256": ("c" if number == 1 else "d") * 64,
                "independent_verifier_receipt_sha256": ("e" if number == 1 else "f") * 64,
                "replication_id": replication,
                "replication_receipt_sha256": ("1" if number == 1 else "2") * 64,
                "notes": "synthetic contract-conformance fixture",
            }
        )

    decision = {
        "schema_version": "rac-residual-decision/1.0",
        "decision_id": "RAC-D-000001",
        "spec_sha256": spec_hash,
        "evidence_sha256s": [digest(bundle) for bundle in evidence],
        "status": "PROMOTABLE",
        "reason": "synthetic RRI-001 contract fixture",
        "human_gate_required": True,
        "automation_may_promote": False,
    }
    return {
        "contract": "rac-residual-candidate/1.0",
        "improvement_spec": spec,
        "evidence": evidence,
        "decision": decision,
        "authority": {
            "advisory_only": True,
            "human_gate_required": True,
            "automatic_promotion_forbidden": True,
        },
    }


class FixturePass:
    def run_pass(self, spec, pass_number):
        return {"candidate": candidate(), "tokens_used": 0, "observations": []}


def main() -> int:
    goal = GoalSpec(
        "rac_rri_001",
        "Verify the deterministic RAC improvement-envelope contract.",
        (
            SuccessCriterion(
                "contract",
                CheckType.MECHANICAL,
                "Verify hashes and evaluation binding.",
                "rac:contract_integrity",
            ),
            SuccessCriterion(
                "replication",
                CheckType.STRUCTURAL,
                "Verify replication and verifier independence.",
                "rac:replication_independence",
            ),
            SuccessCriterion(
                "authority",
                CheckType.STRUCTURAL,
                "Verify RAC authority remains external.",
                "rac:authority_boundary",
            ),
        ),
        1,
        1000,
        60,
        AmendmentRule(("operator",)),
    )
    registry = StationExtensionRegistry().register_module(RACModule())
    result = LoopController(
        goal, Verifier({}), FixturePass(), extensions=registry
    ).run()
    print(
        json.dumps(
            {
                "experiment": "RRI-001",
                "outcome": result.outcome.value,
                "passes": result.total_passes,
                "spec_hash": result.spec_hash,
                "verification": (
                    result.final_verification.overall_pass
                    if result.final_verification
                    else False
                ),
                "automatic_promotion": False,
            },
            sort_keys=True,
        )
    )
    return 0 if result.outcome == RunOutcome.SUCCESS else 1


if __name__ == "__main__":
    raise SystemExit(main())
