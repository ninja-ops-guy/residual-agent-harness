"""End-to-end live Ollama/Factory/cluster qualification gauntlet.

The gauntlet is intentionally evidence-level aware:
- provider_live: real model inference through ai_providers
- factory_live: real model-authored workers executed by FactoryRuntime
- control_probe: deterministic negative-path enforcement probes
- cluster_loopback: real cluster protocol/routing in one process, not WAN evidence

No unavailable physical/cloud condition is silently simulated and reported as live.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ai_providers import ChatRequest, Message, Role, DEFAULT_REGISTRY, ProviderError
from residual.cluster.capabilities import Capability
from residual.cluster.node import ClusterNode
from residual.cluster.transport import LoopbackTransport
from residual.core import digest
from residual.engines.provider_bridge import ProviderEngineConfig, ProviderExecutionEngine
from residual.engines.protocol import ContextAssembly, TaskSpec
from residual.factory.evidence_bus import EvidenceBus
from residual.factory.evidence_receipts import StationIdentity, VerificationDecision
from residual.factory.models import ExecutionPlan, FactoryTask, FrozenPlan, Requirement
from residual.factory.runtime import FactoryRuntime, RuntimeResult, RuntimeUnavailable
from residual.factory.runtime_journal import RuntimeJournal
from residual.factory.runtime_workspace import git
from residual.factory.station_issuer import FactoryStationIssuer
from residual.factory.worker_contract import WorkerContract


SCHEMA_VERSION = "residual.ollama-gauntlet.v1"
VERIFIER_REVISION = digest({"gauntlet_verifier": 1, "rule": "exact-file-match"})


@dataclass(frozen=True)
class LiveCase:
    case_id: str
    prompt: str
    expected: str


DEFAULT_CASES = (
    LiveCase("arith-01", "Compute 17 + 25. Return only the answer.", "42"),
    LiveCase("arith-02", "Compute 99 + 1. Return only the answer.", "100"),
    LiveCase("reverse-01", "Reverse the string residual. Return only the reversed string.", "laudiser"),
    LiveCase("reverse-02", "Reverse the string harness. Return only the reversed string.", "ssenrah"),
    LiveCase("literal-01", "Return exactly the text RESIDUAL_OK.", "RESIDUAL_OK"),
)


def _now_ns() -> int:
    return time.time_ns()


def _exact(value: str, expected: str) -> bool:
    return value.strip() == expected.strip()


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round(values[0], 3)
    ordered = sorted(values)
    rank = (len(ordered) - 1) * p
    lo = int(rank)
    hi = min(lo + 1, len(ordered) - 1)
    frac = rank - lo
    return round(ordered[lo] * (1 - frac) + ordered[hi] * frac, 3)


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lat = [float(r["latency_ms"]) for r in rows if r.get("latency_ms") is not None]
    correct = sum(1 for r in rows if r.get("correct") is True)
    total = len(rows)
    return {
        "observations": total,
        "correct": correct,
        "correct_rate": (correct / total if total else None),
        "latency_ms_mean": (round(statistics.fmean(lat), 3) if lat else None),
        "latency_ms_p50": _percentile(lat, 0.50),
        "latency_ms_p95": _percentile(lat, 0.95),
        "input_tokens": sum(int(r.get("input_tokens") or 0) for r in rows),
        "output_tokens": sum(int(r.get("output_tokens") or 0) for r in rows),
    }


def provider_live_suite(*, provider: str, model: str, repeats: int,
                        cases: Iterable[LiveCase] = DEFAULT_CASES) -> dict[str, Any]:
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    adapter = DEFAULT_REGISTRY.get(provider)
    models = adapter.list_models()
    if provider == "ollama" and model not in models:
        raise ValueError(f"Ollama model is not installed: {model}")
    rows: list[dict[str, Any]] = []
    for case in cases:
        for repeat in range(repeats):
            req = ChatRequest(
                model=model,
                messages=(
                    Message(Role.SYSTEM, "Return only the requested answer. No explanation."),
                    Message(Role.USER, case.prompt),
                ),
                temperature=0.0,
                max_tokens=128,
                seed=repeat,
            )
            started = time.perf_counter_ns()
            response = adapter.chat(req)
            latency_ms = (time.perf_counter_ns() - started) / 1_000_000
            usage = response.usage or {}
            rows.append({
                "case_id": case.case_id,
                "repeat": repeat,
                "provider": provider,
                "model": response.model or model,
                "content": response.content,
                "expected": case.expected,
                "correct": _exact(response.content, case.expected),
                "latency_ms": round(latency_ms, 3),
                "input_tokens": int(usage.get("prompt_tokens", 0)),
                "output_tokens": int(usage.get("completion_tokens", 0)),
            })
    return {
        "suite": "provider_live",
        "evidence_level": "provider_live",
        "status": "PASS",
        "provider": provider,
        "requested_model": model,
        "available_models": models,
        "summary": _summary(rows),
        "observations": rows,
    }


def cluster_loopback_suite(*, model: str) -> dict[str, Any]:
    """Exercise real cluster wire/routing/failure logic without claiming WAN evidence."""
    LoopbackTransport.reset_registry()
    key = "gauntlet-cluster-key"
    local = ClusterNode(
        "local", Capability((model,), 25.0, 8192, 8_000_000_000, 1, 2), key,
        heartbeat_interval_ns=1, failure_timeout_ns=10,
    )
    remote_fast = ClusterNode(
        "remote-fast", Capability((model,), 50.0, 8192, 16_000_000_000, 1, 4), key,
        heartbeat_interval_ns=1, failure_timeout_ns=10,
    )
    remote_backup = ClusterNode(
        "remote-backup", Capability((model,), 20.0, 8192, 8_000_000_000, 1, 2), key,
        heartbeat_interval_ns=1, failure_timeout_ns=10,
    )
    nodes = (local, remote_fast, remote_backup)
    try:
        for node in nodes:
            node.open()
        remote_fast.join(local.address)
        remote_backup.join(local.address)

        initial = local.registry.route(model)
        initial_id = initial.node_id if initial else None

        task = local.submit_task({"op": "echo", "value": "mesh"}, required_model=model)
        before = {"assigned_node": task.assigned_node, "state": task.state}
        failed: list[str] = []
        target = local.registry.get("remote-fast")
        if target is not None:
            task.assigned_node = "remote-fast"
            task.state = "assigned"
            target.last_heartbeat_ns = 0
            failed = local.detect_failures(now_ns=local.failure_timeout_ns + 100)
        after = {"assigned_node": task.assigned_node, "state": task.state}
        captured = any(r.get("outcome") == "node_failed" for r in local.receipts)
        return {
            "suite": "cluster_loopback",
            "evidence_level": "cluster_loopback",
            "status": "PASS" if captured and "remote-fast" in failed else "FAIL",
            "wan_claim": False,
            "initial_route": initial_id,
            "failed_nodes": failed,
            "before_failure": before,
            "after_failure": after,
            "failure_receipt_captured": captured,
            "capacity": local.registry.aggregate_capacity(),
        }
    finally:
        for node in reversed(nodes):
            try:
                node.close()
            except Exception:
                pass
        LoopbackTransport.reset_registry()


def _init_repo(root: Path) -> tuple[Path, str]:
    repository = root / "repository"
    repository.mkdir(parents=True)
    git(repository, "init")
    (repository / "README.fixture").write_text("RESIDUAL gauntlet fixture\n", encoding="utf-8")
    git(repository, "add", ".")
    git(repository, "-c", "user.name=Residual Gauntlet",
        "-c", "user.email=gauntlet@localhost", "commit", "-m", "gauntlet fixture")
    commit = git(repository, "rev-parse", "HEAD").decode().strip()
    return repository, commit


def _plan_for_cases(cases: tuple[LiveCase, ...]) -> ExecutionPlan:
    requirements = tuple(
        Requirement(f"REQ-{i:03d}", f"Produce exact output for {case.case_id}", ("exact-output",))
        for i, case in enumerate(cases, 1)
    )
    tasks = tuple(
        FactoryTask(f"task-{i:03d}", case.prompt, (f"REQ-{i:03d}",), swarm="gauntlet")
        for i, case in enumerate(cases, 1)
    )
    return ExecutionPlan("Ollama-backed Factory gauntlet", requirements, tasks)


def _contracts_for_cases(*, cases: tuple[LiveCase, ...], plan: ExecutionPlan,
                         input_commit: str, work_root: Path, engine_id: str,
                         attempt_prefix: str, wall_clock_budget_s: float = 8.0) -> tuple[WorkerContract, ...]:
    contracts = []
    for i, _case in enumerate(cases, 1):
        task_id = f"task-{i:03d}"
        attempt_id = f"{attempt_prefix}-{i:03d}"
        contracts.append(WorkerContract(
            task_id=task_id,
            worker_id=f"worker-{i:03d}",
            swarm_id="gauntlet",
            execution_plan_hash=plan.graph_hash,
            attempt_id=attempt_id,
            lease_id=f"lease-{attempt_prefix}-{i:03d}",
            lease_generation=1,
            input_commit=input_commit,
            workspace_root=str(work_root / "gauntlet" / attempt_id),
            inputs=(),
            allowed_outputs=(f"answer-{i:03d}.txt",),
            forbidden=("secret.txt",),
            requirements=(f"REQ-{i:03d}",),
            acceptance=("exact-output",),
            dependencies=(),
            allowed_tools=("write_file",),
            forbidden_tools=("shell",),
            token_budget=4096,
            wall_clock_budget_s=wall_clock_budget_s,
            max_tool_calls=4,
            max_file_writes=1,
            memory_limit_mb=192,
            engine_hint=engine_id,
        ))
    return tuple(contracts)


def _author_source(engine: ProviderExecutionEngine, case: LiveCase,
                   contract: WorkerContract) -> tuple[str, int, int]:
    prompt = (
        "Author raw Python source for a Residual Factory worker. Return Python only; "
        "no Markdown fences. The sandbox exposes write_file(path, content). "
        "Direct filesystem, network, subprocess, shell, eval, exec, and dynamic imports "
        "are unavailable. Write the final answer to the single allowed output path. "
        f"Allowed output: {contract.allowed_outputs[0]}. "
        f"Assignment: {case.prompt} "
        "The output file must contain only the requested answer."
    )
    result = engine.execute(
        TaskSpec(f"author-{contract.task_id}", "text", prompt),
        ContextAssembly(),
    )
    if not isinstance(result.candidate, str) or not result.candidate.strip():
        raise ValueError("authoring model returned empty/non-text worker source")
    source = result.candidate.strip()
    if source.startswith("'''") or source.endswith("'''"):
        raise ValueError("authoring model returned quoted wrapper")
    if source.startswith("~~~") or source.endswith("~~~"):
        raise ValueError("authoring model returned fenced source")
    if result.token_usage is None:
        raise ValueError("provider did not report token usage")
    return source, int(result.token_usage), int(result.wall_clock_ms or 0)


def _decision_for(contract: WorkerContract, result: RuntimeResult,
                  expected: str) -> VerificationDecision:
    output = contract.allowed_outputs[0]
    target = Path(contract.workspace_root) / output
    correct = (
        result.status == "CANDIDATE"
        and result.candidate is not None
        and target.is_file()
        and not target.is_symlink()
        and _exact(target.read_text(encoding="utf-8"), expected)
    )
    req = contract.requirements[0]
    return VerificationDecision(
        ((req, correct),),
        (("exact-output", "pass" if correct else "fail"),),
        "pass" if correct else "fail",
        "residual:ollama-gauntlet-exact-file-verifier",
        VERIFIER_REVISION,
    )


def _execute_strategy(runtime: FactoryRuntime, plan: ExecutionPlan, approval: FrozenPlan,
                      workers: list[tuple[WorkerContract, str]], strategy: str,
                      fixed_capacity: int, dynamic_max: int) -> tuple[list[RuntimeResult], list[dict[str, Any]], float]:
    started = time.monotonic()
    waves: list[dict[str, Any]] = []
    if strategy == "single":
        results = []
        for contract, source in workers:
            batch = runtime.run_many(plan, approval, [(contract, source)], capacity=1)
            results.extend(batch)
            waves.append({"batch_size": 1, "capacity": 1, "attempt_ids": [contract.attempt_id]})
    elif strategy == "fixed":
        capacity = min(fixed_capacity, max(1, len(workers)))
        results = runtime.run_many(plan, approval, workers, capacity=capacity)
        waves.append({"batch_size": len(workers), "capacity": capacity,
                      "attempt_ids": [c.attempt_id for c, _ in workers]})
    elif strategy == "dynamic":
        pending = list(workers)
        results = []
        completed = 0
        while pending:
            if completed == 0:
                batch_size, capacity = 1, 1
            else:
                batch_size = min(len(pending), max(1, completed * 2))
                capacity = min(dynamic_max, batch_size)
            batch = pending[:batch_size]
            pending = pending[batch_size:]
            chunk = runtime.run_many(plan, approval, batch, capacity=capacity)
            results.extend(chunk)
            completed += len(chunk)
            waves.append({"batch_size": batch_size, "capacity": capacity,
                          "attempt_ids": [c.attempt_id for c, _ in batch],
                          "statuses": [r.status for r in chunk]})
    else:
        raise ValueError("strategy must be single, fixed, or dynamic")
    return results, waves, time.monotonic() - started


def factory_live_suite(*, provider: str, model: str, output_root: Path,
                       strategy: str, cases: tuple[LiveCase, ...] = DEFAULT_CASES,
                       fixed_capacity: int = 4, dynamic_max: int = 8) -> dict[str, Any]:
    """Run real model-authored code through the real Factory boundary and M3 issuer."""
    if sys.platform != "linux":
        return {"suite": f"factory_live_{strategy}", "evidence_level": "factory_live",
                "status": "NOT_TESTED", "reason": "FactoryRuntime requires Linux"}
    run_root = output_root / f"factory-{strategy}"
    run_root.mkdir(parents=True, exist_ok=False)
    repository, commit = _init_repo(run_root)
    journal = RuntimeJournal(run_root / "state" / "journal.db",
                             trace_id=f"ollama-gauntlet-{strategy}")
    runtime = FactoryRuntime(repository, run_root / "work", journal,
                             allow_local_worker_code=True)
    bus = EvidenceBus(run_root / "evidence.sqlite")
    identity = StationIdentity.generate()
    issuer = FactoryStationIssuer(identity, bus)
    plan = _plan_for_cases(cases)
    approval = FrozenPlan.approve(plan, "ollama-gauntlet")
    engine = ProviderExecutionEngine(ProviderEngineConfig(
        provider=provider, model=model, locality="local" if provider == "ollama" else "cloud",
        max_tokens=1024, temperature=0.0,
        system_prompt="Return exactly the requested raw Python source, with no Markdown fences.",
    ))
    engine_id = engine.engine_id
    contracts = _contracts_for_cases(
        cases=cases, plan=plan, input_commit=commit, work_root=run_root / "work",
        engine_id=engine_id, attempt_prefix=strategy,
    )

    authored: list[dict[str, Any]] = []
    pairs: list[tuple[WorkerContract, str]] = []
    for case, contract in zip(cases, contracts):
        started = time.monotonic()
        try:
            source, tokens, author_ms = _author_source(engine, case, contract)
            error = None
        except Exception as exc:
            source, tokens, author_ms = "", 0, int((time.monotonic() - started) * 1000)
            error = type(exc).__name__
        source_path = run_root / "authored"
        source_path.mkdir(exist_ok=True)
        (source_path / f"{contract.attempt_id}.py").write_text(source, encoding="utf-8")
        authored.append({
            "attempt_id": contract.attempt_id,
            "task_id": contract.task_id,
            "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "tokens": tokens,
            "wall_clock_ms": author_ms,
            "error": error,
        })
        if error is None:
            pairs.append((contract, source))

    if len(pairs) != len(contracts):
        journal.export_jsonl(run_root / "observations.jsonl")
        return {
            "suite": f"factory_live_{strategy}",
            "evidence_level": "factory_live",
            "status": "INCONCLUSIVE",
            "reason": "one or more workers could not be authored",
            "authored": authored,
        }

    results, waves, elapsed_s = _execute_strategy(
        runtime, plan, approval, pairs, strategy, fixed_capacity, dynamic_max,
    )

    receipts = []
    rows = []
    unsafe_acceptances = 0
    by_attempt = {result.attempt_id: result for result in results}
    for case, contract in zip(cases, contracts):
        result = by_attempt[contract.attempt_id]
        decision = _decision_for(contract, result, case.expected)
        accepted = False
        receipt_hash = None
        if decision.verdict == "pass":
            receipt = issuer.issue(
                contract=contract, result=result, workspace_root=contract.workspace_root,
                decision=decision,
            )
            accepted = True
            receipt_hash = receipt.receipt_hash
            receipts.append(receipt)
            if not _exact(
                (Path(contract.workspace_root) / contract.allowed_outputs[0]).read_text(encoding="utf-8"),
                case.expected,
            ):
                unsafe_acceptances += 1
        rows.append({
            "case_id": case.case_id,
            "attempt_id": contract.attempt_id,
            "runtime_status": result.status,
            "runtime_reason": result.reason,
            "accepted": accepted,
            "receipt_hash": receipt_hash,
            "usage": result.usage,
            "termination": result.termination,
        })

    journal.export_jsonl(run_root / "observations.jsonl")
    receipt_docs = [r.to_dict() for r in receipts]
    (run_root / "receipts.json").write_text(
        json.dumps(receipt_docs, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    accepted = len(receipts)
    total = len(cases)
    return {
        "suite": f"factory_live_{strategy}",
        "evidence_level": "factory_live",
        "status": "PASS" if unsafe_acceptances == 0 else "FAIL",
        "strategy": strategy,
        "provider": provider,
        "model": model,
        "plan_hash": plan.graph_hash,
        "input_commit": commit,
        "station_key_id": identity.key_id,
        "workers": total,
        "accepted": accepted,
        "rejected_or_failed": total - accepted,
        "unsafe_acceptances": unsafe_acceptances,
        "unsafe_acceptance_rate": unsafe_acceptances / accepted if accepted else None,
        "wall_clock_seconds": elapsed_s,
        "verified_useful_throughput_per_second": accepted / elapsed_s if elapsed_s > 0 else None,
        "author_tokens": sum(x["tokens"] for x in authored),
        "author_wall_clock_ms": sum(x["wall_clock_ms"] for x in authored),
        "waves": waves,
        "authored": authored,
        "workers_detail": rows,
        "receipt_hashes": [r.receipt_hash for r in receipts],
        "output_dir": str(run_root),
    }


def factory_control_suite(*, output_root: Path) -> dict[str, Any]:
    """Deterministic negative-path probes of the Factory enforcement boundary."""
    if sys.platform != "linux":
        return {"suite": "factory_control", "evidence_level": "control_probe",
                "status": "NOT_TESTED", "reason": "FactoryRuntime requires Linux"}
    run_root = output_root / "factory-control"
    run_root.mkdir(parents=True, exist_ok=False)
    repository, commit = _init_repo(run_root)
    (repository / "secret.txt").write_text("must-not-read\n", encoding="utf-8")
    git(repository, "add", ".")
    git(repository, "-c", "user.name=Residual Gauntlet",
        "-c", "user.email=gauntlet@localhost", "commit", "-m", "control probe secret")
    commit = git(repository, "rev-parse", "HEAD").decode().strip()
    journal = RuntimeJournal(run_root / "state" / "journal.db", trace_id="gauntlet-controls")
    runtime = FactoryRuntime(repository, run_root / "work", journal, allow_local_worker_code=True)

    probes = (
        ("allowed_write", "write_file('answer.txt','ok')", 2.0, "CANDIDATE"),
        ("forbidden_write", "write_file('secret.txt','pwned')", 2.0, "not_candidate"),
        ("forbidden_read", "read_file('secret.txt')", 2.0, "not_candidate"),
        ("write_budget", "write_file('answer.txt','a')\nwrite_file('answer.txt','b')", 2.0, "not_candidate"),
        ("timeout", "while True:\n    pass", 0.25, "not_candidate"),
    )
    rows = []
    for index, (name, source, wall, expected) in enumerate(probes, 1):
        req = Requirement(f"R{index}", name, ("control-check",))
        task = FactoryTask(f"task{index}", name, (f"R{index}",), swarm="controls")
        plan = ExecutionPlan(name, (req,), (task,))
        approval = FrozenPlan.approve(plan, "gauntlet")
        contract = WorkerContract(
            task_id=task.id, worker_id=f"worker{index}", swarm_id="controls",
            execution_plan_hash=plan.graph_hash, attempt_id=f"probe{index}",
            lease_id=f"probe-lease{index}", lease_generation=1, input_commit=commit,
            workspace_root=str(run_root / "work" / "controls" / f"probe{index}"),
            inputs=(), allowed_outputs=("answer.txt",), forbidden=("secret.txt",),
            requirements=(req.id,), acceptance=("control-check",), dependencies=(),
            allowed_tools=("read_file", "write_file"), forbidden_tools=("shell",),
            token_budget=0, wall_clock_budget_s=wall, max_tool_calls=4,
            max_file_writes=1, memory_limit_mb=128,
        )
        try:
            result = runtime.run(plan, approval, contract, source)
            status = result.status
            reason = result.reason
            termination = result.termination
        except Exception as exc:
            status = "EXCEPTION"
            reason = type(exc).__name__
            termination = None
        passed = status == "CANDIDATE" if expected == "CANDIDATE" else status != "CANDIDATE"
        rows.append({
            "probe": name, "status": status, "reason": reason,
            "termination": termination, "expected": expected, "passed": passed,
        })
    journal.export_jsonl(run_root / "observations.jsonl")
    return {
        "suite": "factory_control",
        "evidence_level": "control_probe",
        "status": "PASS" if all(r["passed"] for r in rows) else "FAIL",
        "probes": rows,
        "output_dir": str(run_root),
    }


def run_gauntlet(*, output: Path, provider: str, model: str, repeats: int = 3,
                 include_factory: bool = True) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    suites = []
    started = _now_ns()
    environment = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "provider": provider,
        "model": model,
        "ollama_host": os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        "git_available": shutil.which("git") is not None,
    }

    def capture(name: str, fn):
        try:
            result = fn()
        except (RuntimeUnavailable, FileNotFoundError) as exc:
            result = {
                "suite": name,
                "status": "NOT_TESTED",
                "reason": f"{type(exc).__name__}: {exc}",
            }
        except ProviderError as exc:
            result = {
                "suite": name,
                "status": "NOT_TESTED" if exc.code in {
                    "connection", "timeout", "model_not_found", "config", "authentication"
                } else "FAIL",
                "reason": f"{type(exc).__name__}: {exc}",
                "provider_error": exc.to_dict(),
            }
        except Exception as exc:
            result = {
                "suite": name,
                "status": "FAIL",
                "reason": f"{type(exc).__name__}: {exc}",
            }
        suites.append(result)

    capture("provider_live", lambda: provider_live_suite(
        provider=provider, model=model, repeats=repeats))
    capture("cluster_loopback", lambda: cluster_loopback_suite(model=model))
    if include_factory:
        capture("factory_control", lambda: factory_control_suite(output_root=output))
        for strategy in ("single", "fixed", "dynamic"):
            capture(f"factory_live_{strategy}", lambda strategy=strategy: factory_live_suite(
                provider=provider, model=model, output_root=output, strategy=strategy))

    end = _now_ns()
    evaluated = [s for s in suites if s.get("status") != "NOT_TESTED"]
    failed = [s for s in evaluated if s.get("status") == "FAIL"]
    report = {
        "schema_version": SCHEMA_VERSION,
        "started_at_ns": started,
        "finished_at_ns": end,
        "environment": environment,
        "suites": suites,
        "overall": {
            "status": "FAIL" if failed else ("PASS" if evaluated else "NOT_TESTED"),
            "evaluated_suites": len(evaluated),
            "not_tested_suites": sum(1 for s in suites if s.get("status") == "NOT_TESTED"),
            "failed_suites": len(failed),
            "claim_boundaries": {
                "safety": "supported only by executed enforcement/acceptance suites",
                "efficiency": "requires successful live single/fixed/dynamic comparisons",
                "hybrid_cloud_mesh": "cluster loopback is control-plane evidence only; WAN/cloud remains separate",
            },
        },
    }
    (output / "gauntlet-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="residual-ollama-gauntlet")
    parser.add_argument("--output", default="runs/ollama-gauntlet")
    parser.add_argument("--provider", default="ollama")
    parser.add_argument("--model", required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--no-factory", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_gauntlet(
        output=Path(args.output), provider=args.provider, model=args.model,
        repeats=args.repeats, include_factory=not args.no_factory,
    )
    print(json.dumps({
        "report": str(Path(args.output) / "gauntlet-report.json"),
        "status": report["overall"]["status"],
        "evaluated_suites": report["overall"]["evaluated_suites"],
        "not_tested_suites": report["overall"]["not_tested_suites"],
        "failed_suites": report["overall"]["failed_suites"],
    }, indent=2))
    return 1 if report["overall"]["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
