#!/usr/bin/env python3
"""Run controlled fault trials against the real Linux M2 Factory runtime."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from residual.core import canonical, digest
from residual.factory import ExecutionPlan, FactoryTask, FrozenPlan, Requirement
from residual.factory.reliability_experiments import M2_FAULTS, M2FaultSpec, run_m2_fault_trial, summarize_m2_fault_trials
from residual.factory.runtime import FactoryRuntime
from residual.factory.runtime_journal import RuntimeJournal
from residual.factory.runtime_workspace import git
from residual.factory.worker_contract import WorkerContract


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run real M2 controlled containment trials")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        repo = root / "repo"
        repo.mkdir()
        git(repo, "init")
        (repo / "input.txt").write_text("hello")
        (repo / "secret.txt").write_text("must remain unchanged")
        git(repo, "add", ".")
        git(repo, "-c", "user.name=m2-study", "-c", "user.email=m2-study@localhost", "commit", "-m", "base")
        commit = git(repo, "rev-parse", "HEAD").decode().strip()
        plan = ExecutionPlan(
            "controlled M2 containment",
            (Requirement("R1", "produce bounded candidate", ("unit",)),),
            (FactoryTask("task1", "bounded worker", ("R1",), swarm="swarm1"),),
        )
        approval = FrozenPlan.approve(plan, "reliability-study-operator")
        journal = RuntimeJournal(root / "state" / "run.db", trace_id="m2-reliability-matrix")
        runtime = FactoryRuntime(repo, root / "work", journal, allow_local_worker_code=True)

        receipts = []
        for index, kind in enumerate(sorted(M2_FAULTS), start=1):
            attempt = f"attempt{index}"
            contract = WorkerContract(
                task_id="task1", worker_id=f"worker{index}", swarm_id="swarm1",
                execution_plan_hash=plan.graph_hash, attempt_id=attempt,
                lease_id=f"lease{index}", lease_generation=index, input_commit=commit,
                workspace_root=str(root / "work" / "swarm1" / attempt),
                inputs=("input.txt",), allowed_outputs=("output.txt",), forbidden=("secret.txt",),
                requirements=("R1",), acceptance=("unit",), dependencies=(),
                allowed_tools=("read_file", "write_file", "delete_file"), forbidden_tools=("shell",),
                token_budget=0,
                wall_clock_budget_s=0.2 if kind == "wall_clock_exhaustion" else 5,
                max_tool_calls=10, max_file_writes=5, memory_limit_mb=128,
            )
            receipts.append(run_m2_fault_trial(
                runtime, plan, approval, contract, M2FaultSpec(f"m2:{kind}", kind)
            ))

        if (repo / "secret.txt").read_text() != "must remain unchanged":
            raise RuntimeError("controlled trial mutated forbidden source file")
        if git(repo, "rev-parse", "HEAD").decode().strip() != commit:
            raise RuntimeError("controlled trial mutated source repository HEAD")

        report = summarize_m2_fault_trials(receipts)
        report["evidence_level"] = "development_fixture_real_os_runtime"
        report["runtime_profile"] = "linux-seccomp-broker-v1"
        report["source_commit_unchanged"] = True
        report["forbidden_source_file_unchanged"] = True
        report["sha256"] = digest({k: v for k, v in report.items() if k != "sha256"})

        (output / "m2-fault-trials.jsonl").write_text(
            "".join(canonical(row) + "\n" for row in receipts), encoding="utf-8"
        )
        (output / "m2-fault-report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
        )
        journal.export_jsonl(output / "m2-observations.jsonl")
        print(f"Recorded {len(receipts)} real M2 controlled fault trials")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
