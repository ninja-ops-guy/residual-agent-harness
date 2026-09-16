"""Supplemental negative controls for the recursive-maintenance study.

The purpose is to distinguish provenance-bound documentation from semantic
self-documentation, and to stress evidence integrity under repeated mutation.
No core RESIDUAL code is modified.
"""
from __future__ import annotations

import json
import random
import tempfile
from pathlib import Path

from residual import (
    AmendmentRule,
    CheckResult,
    CheckType,
    GoalSpec,
    LoopController,
    RunOutcome,
    SuccessCriterion,
    Verifier,
)
from residual.core import ContractError
from residual.station.service import Station, demo_spec

SEED = 20260915


def make_goal(criteria, max_passes=2):
    return GoalSpec(
        goal_id="documentation-policy-negative-control",
        objective="Accept code only when the frozen contract says what must be true",
        success_criteria=tuple(criteria),
        max_passes=max_passes,
        token_budget=100,
        wall_clock_budget_s=30,
        amendment_rule=AmendmentRule(("operator",), 1),
    )


def documentation_policy_negative_control():
    code = SuccessCriterion("code", CheckType.MECHANICAL, "code healthy", "code")
    docs = SuccessCriterion("docs", CheckType.SEMANTIC, "docs synchronized", "docs")

    code_only = make_goal((code,), max_passes=1)
    code_only_verifier = Verifier({
        "code": lambda c, p: (CheckResult.PASS if c.get("healthy") else CheckResult.FAIL, "code")
    })

    class StaleDocsWorker:
        def run_pass(self, spec, pass_number):
            return {"candidate": {"healthy": True, "docs_synced": False}, "tokens_used": 1, "observations": []}

    code_only_result = LoopController(code_only, code_only_verifier, StaleDocsWorker()).run()

    code_and_docs = make_goal((code, docs), max_passes=1)
    dual_verifier = Verifier({
        "code": lambda c, p: (CheckResult.PASS if c.get("healthy") else CheckResult.FAIL, "code"),
        "docs": lambda c, p: (CheckResult.PASS if c.get("docs_synced") else CheckResult.FAIL, "docs"),
    })
    stale_result = LoopController(code_and_docs, dual_verifier, StaleDocsWorker()).run()

    unknown_docs_verifier = Verifier({
        "code": lambda c, p: (CheckResult.PASS, "code"),
        "docs": lambda c, p: (CheckResult.UNKNOWN, "documentation evidence unavailable"),
    })
    unknown_result = LoopController(code_and_docs, unknown_docs_verifier, StaleDocsWorker()).run()

    repairing_goal = make_goal((code, docs), max_passes=2)

    class DocsRepairWorker:
        def run_pass(self, spec, pass_number):
            return {
                "candidate": {"healthy": True, "docs_synced": pass_number >= 2},
                "tokens_used": 1,
                "observations": [],
            }

    repaired_result = LoopController(repairing_goal, dual_verifier, DocsRepairWorker()).run()

    return {
        "code_only_stale_docs_outcome": code_only_result.outcome.value,
        "code_only_stale_docs_accepted": code_only_result.outcome == RunOutcome.SUCCESS,
        "docs_required_stale_outcome": stale_result.outcome.value,
        "docs_required_stale_accepted": stale_result.outcome == RunOutcome.SUCCESS,
        "docs_unknown_outcome": unknown_result.outcome.value,
        "docs_unknown_accepted": unknown_result.outcome == RunOutcome.SUCCESS,
        "docs_repaired_outcome": repaired_result.outcome.value,
        "docs_repaired_passes": repaired_result.total_passes,
        "interpretation": (
            "Documentation freshness is enforceable when represented in the frozen acceptance contract, "
            "but it is not an implicit invariant of every mission."
        ),
    }


def artifact_tamper_fuzz(trials=100):
    rng = random.Random(SEED)
    detections = 0
    with tempfile.TemporaryDirectory() as directory:
        station = Station(directory)
        pid = station.create(demo_spec(), demo=True)["project_id"]
        result = station.batch(pid)
        artifact_id = result["control"]["evidence"]
        _, body = station.store.artifact(artifact_id)
        digest = artifact_id.split(":", 1)[1]
        artifact_path = station.store.root / "artifacts" / pid / digest
        original = bytes(body)

        for _ in range(trials):
            mutated = bytearray(original)
            pos = rng.randrange(len(mutated))
            mutated[pos] ^= rng.randrange(1, 256)
            artifact_path.write_bytes(mutated)
            try:
                station.store.artifact(artifact_id)
            except ContractError:
                detections += 1
            finally:
                artifact_path.write_bytes(original)

        extra_cases = {}
        for name, mutated in {
            "truncated": original[:-1],
            "appended": original + b"x",
            "replaced": b"tampered",
        }.items():
            artifact_path.write_bytes(mutated)
            detected = False
            try:
                station.store.artifact(artifact_id)
            except ContractError:
                detected = True
            finally:
                artifact_path.write_bytes(original)
            extra_cases[name] = detected

    return {
        "single_byte_mutation_trials": trials,
        "single_byte_mutation_detections": detections,
        "extra_mutation_cases": extra_cases,
    }


def main():
    out = {
        "schema_version": 1,
        "seed": SEED,
        "documentation_policy_negative_control": documentation_policy_negative_control(),
        "artifact_tamper_fuzz": artifact_tamper_fuzz(),
        "claim_scope": "negative control and evidence-integrity stress; no semantic-documentation model evaluated",
    }
    path = Path("runs/self-maintenance-study/supplement.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
