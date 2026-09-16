from __future__ import annotations

import hashlib
import json
import random
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from residual.core import canonical
from residual.factory.runtime_journal import JournalError, RuntimeJournal
from residual.factory.worker_contract import WorkerContract


@dataclass
class _Lane:
    task_id: str
    generation: int = 0
    serial: int = 0
    contract: WorkerContract | None = None
    state: str | None = None
    revoked: bool = False
    history: list[WorkerContract] = field(default_factory=list)

    @property
    def claimable(self) -> bool:
        return self.state is None or self.state in {"VIOLATED", "FAILED", "CANCELLED", "AUDIT_FAILED", "PURGED"}


def _contract(lane: _Lane) -> WorkerContract:
    lane.serial += 1
    lane.generation += 1
    suffix = f"{lane.task_id}{lane.serial}"
    return WorkerContract(
        task_id=lane.task_id,
        worker_id=f"Worker{suffix}",
        swarm_id="QualificationSwarm",
        execution_plan_hash="a" * 64,
        attempt_id=f"Attempt{suffix}",
        lease_id=f"Lease{suffix}",
        lease_generation=lane.generation,
        input_commit="b" * 40,
        workspace_root=f"/tmp/residual-qualification-{suffix}",
        inputs=("input.txt",), allowed_outputs=("output.txt",), forbidden=("secret/",),
        requirements=("ReqA",), acceptance=("CheckA",), dependencies=(),
        allowed_tools=("python",), forbidden_tools=("shell",), token_budget=1000,
        wall_clock_budget_s=5.0, max_tool_calls=5, max_file_writes=5, memory_limit_mb=128,
    )


def _expect_rejected(callable_, label: str) -> None:
    try:
        callable_()
    except JournalError:
        return
    raise AssertionError(f"invalid operation was accepted: {label}")


def _check_lane(journal: RuntimeJournal, lane: _Lane) -> None:
    if lane.contract is None:
        return
    rows = [r for r in journal.attempts() if r["attempt_id"] == lane.contract.attempt_id]
    if len(rows) != 1:
        raise AssertionError(f"attempt identity count={len(rows)} for {lane.contract.attempt_id}")
    if rows[0]["state"] != lane.state:
        raise AssertionError(f"state drift: model={lane.state} journal={rows[0]['state']}")
    expected = "current" if lane.state in {"RESERVED", "RUNNING"} and not lane.revoked else "revoked"
    actual = journal.lease_state(lane.contract)
    if actual != expected:
        raise AssertionError(f"lease drift: expected={expected} actual={actual}")
    for stale in lane.history[:-1]:
        if journal.lease_state(stale) != "revoked":
            raise AssertionError(f"stale lease regained authority: {stale.attempt_id}")


def run_history(seed: int, *, steps: int = 100, lanes: int = 3) -> dict[str, Any]:
    """Run a deterministic interleaving against the real RuntimeJournal.

    The explorer intentionally mixes valid transitions with invalid duplicate/stale
    operations. Every seed is replayable. A failure is returned as data rather
    than erased by an automatic retry.
    """
    rng = random.Random(seed)
    trace: list[dict[str, Any]] = []
    lane_models = [_Lane(f"Task{chr(65 + i)}") for i in range(lanes)]
    with tempfile.TemporaryDirectory(prefix="residual-history-") as temp:
        db = Path(temp) / "journal.sqlite3"
        journal = RuntimeJournal(db, trace_id=f"qualification-history-{seed}")
        failure: str | None = None
        try:
            for step in range(steps):
                lane = rng.choice(lane_models)
                action = rng.choice((
                    "claim", "start", "revoke", "finish_candidate", "finish_failed",
                    "purge", "restart", "stale_probe", "duplicate_finish", "duplicate_claim",
                ))
                outcome = "NOOP"
                contract = lane.contract
                if action == "claim" and lane.claimable:
                    contract = _contract(lane)
                    journal.claim(contract, source_hash="c" * 64,
                                  approval={"approved_by": "qualification-history"})
                    lane.contract = contract
                    lane.history.append(contract)
                    lane.state = "RESERVED"
                    lane.revoked = False
                    outcome = "APPLIED"
                elif action == "start" and contract is not None and lane.state == "RESERVED" and not lane.revoked:
                    journal.started(contract, 20000 + step)
                    lane.state = "RUNNING"
                    outcome = "APPLIED"
                elif action == "revoke" and contract is not None and lane.state in {"RESERVED", "RUNNING"} and not lane.revoked:
                    journal.revoke(contract.attempt_id)
                    lane.revoked = True
                    outcome = "APPLIED"
                elif action == "finish_candidate" and contract is not None and lane.state in {"RESERVED", "RUNNING"}:
                    if lane.revoked:
                        _expect_rejected(lambda: journal.finish(contract, "CANDIDATE"), "candidate after revoke")
                        outcome = "REJECTED_AS_EXPECTED"
                    else:
                        journal.finish(contract, "CANDIDATE", seed=seed, step=step)
                        lane.state = "CANDIDATE"
                        outcome = "APPLIED"
                elif action == "finish_failed" and contract is not None and lane.state in {"RESERVED", "RUNNING"}:
                    journal.finish(contract, "FAILED", seed=seed, step=step)
                    lane.state = "FAILED"
                    outcome = "APPLIED"
                elif action == "purge" and contract is not None and lane.state in {"CANDIDATE", "VIOLATED", "FAILED", "CANCELLED", "AUDIT_FAILED"}:
                    journal.mark_purged(contract.attempt_id)
                    lane.state = "PURGED"
                    outcome = "APPLIED"
                elif action == "restart":
                    journal = RuntimeJournal(db, trace_id=f"qualification-history-{seed}")
                    journal.observations()
                    outcome = "APPLIED"
                elif action == "stale_probe" and lane.history:
                    stale = rng.choice(lane.history[:-1] or lane.history)
                    expected = "current" if stale is lane.contract and lane.state in {"RESERVED", "RUNNING"} and not lane.revoked else "revoked"
                    if journal.lease_state(stale) != expected:
                        raise AssertionError(f"stale probe violated authority for {stale.attempt_id}")
                    outcome = "CHECKED"
                elif action == "duplicate_finish" and contract is not None and lane.state in {"CANDIDATE", "VIOLATED", "FAILED", "CANCELLED", "AUDIT_FAILED", "PURGED"}:
                    _expect_rejected(lambda: journal.finish(contract, "FAILED"), "duplicate terminal finish")
                    outcome = "REJECTED_AS_EXPECTED"
                elif action == "duplicate_claim" and contract is not None:
                    _expect_rejected(
                        lambda: journal.claim(contract, source_hash="c" * 64,
                                              approval={"approved_by": "qualification-history"}),
                        "duplicate identity claim",
                    )
                    outcome = "REJECTED_AS_EXPECTED"

                trace.append({"step": step, "lane": lane.task_id, "action": action, "outcome": outcome})
                for model in lane_models:
                    _check_lane(journal, model)
                journal.observations()
        except Exception as exc:
            failure = f"{type(exc).__name__}: {exc}"

        observations = journal.observations()
        # Observation IDs, timestamps and chain hashes are intentionally unique per
        # execution. Replay identity therefore hashes the deterministic semantic
        # payload stream rather than pretending the cryptographic journal bytes are
        # deterministic across runs.
        semantic_payloads = [o.payload for o in observations]
        semantic_digest = hashlib.sha256(canonical(semantic_payloads).encode("utf-8")).hexdigest()
        final_state = [
            {
                "task_id": lane.task_id,
                "attempt_id": lane.contract.attempt_id if lane.contract else None,
                "generation": lane.generation,
                "state": lane.state,
                "revoked": lane.revoked,
            }
            for lane in lane_models
        ]
        replay_digest = hashlib.sha256(
            canonical({"trace": trace, "payloads": semantic_payloads, "final_state": final_state}).encode("utf-8")
        ).hexdigest()
        return {
            "schema": "residual.qualification.history.v1",
            "seed": seed,
            "steps_requested": steps,
            "steps_executed": len(trace),
            "lanes": lanes,
            "result": "PASS" if failure is None else "FAIL",
            "failure": failure,
            "trace": trace,
            "final_state": final_state,
            "observation_count": len(observations),
            "semantic_observation_digest": semantic_digest,
            "replay_digest": replay_digest,
        }


def run_campaign(*, start_seed: int, seeds: int, steps: int, lanes: int = 3) -> dict[str, Any]:
    histories = [run_history(seed, steps=steps, lanes=lanes)
                 for seed in range(start_seed, start_seed + seeds)]
    failed = [h for h in histories if h["result"] != "PASS"]
    return {
        "schema": "residual.qualification.history-campaign.v1",
        "start_seed": start_seed,
        "seed_count": seeds,
        "steps_per_seed": steps,
        "lanes": lanes,
        "result": "PASS" if not failed else "FAIL",
        "failures": failed,
        "histories": histories,
    }


def write_campaign(report: dict[str, Any], path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
