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
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def _model_inventory(adapter, provider: str) -> list[str]:
    """Discover models when supported; explicit model execution is authoritative."""
    try:
        return adapter.list_models()
    except ProviderError as exc:
        if provider != "ollama" and exc.code == "not_implemented":
            return []
        raise


def provider_live_suite(*, provider: str, model: str, repeats: int,
                        cases: Iterable[LiveCase] = DEFAULT_CASES) -> dict[str, Any]:
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    adapter = DEFAULT_REGISTRY.get(provider)
    models = _model_inventory(adapter, provider)
    if provider == "ollama" and model not in models:
        raise ProviderError(provider=provider, code="model_not_found")
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


def provider_scaling_suite(*, provider: str, model: str, repeats: int,
                           cases: tuple[LiveCase, ...] = DEFAULT_CASES,
                           concurrencies: tuple[int, ...] = (1, 2, 4, 8)) -> dict[str, Any]:
    """Measure the real provider saturation curve without attributing it to RESIDUAL."""
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    adapter = DEFAULT_REGISTRY.get(provider)
    models = adapter.list_models()
    if provider == "ollama" and model not in models:
        raise ProviderError(provider=provider, code="model_not_found")

    work = [(case, repeat) for case in cases for repeat in range(repeats)]
    rows = []
    for concurrency in concurrencies:
        capacity = min(concurrency, len(work))
        started = time.monotonic()
        observations = []

        def execute(item):
            case, repeat = item
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
            call_started = time.perf_counter_ns()
            response = adapter.chat(req)
            elapsed_ms = (time.perf_counter_ns() - call_started) / 1_000_000
            usage = response.usage or {}
            return {
                "case_id": case.case_id,
                "repeat": repeat,
                "correct": _exact(response.content, case.expected),
                "latency_ms": round(elapsed_ms, 3),
                "input_tokens": int(usage.get("prompt_tokens", 0)),
                "output_tokens": int(usage.get("completion_tokens", 0)),
            }

        with ThreadPoolExecutor(max_workers=capacity) as pool:
            futures = [pool.submit(execute, item) for item in work]
            for future in as_completed(futures):
                observations.append(future.result())
        wall = time.monotonic() - started
        summary = _summary(observations)
        rows.append({
            "concurrency": concurrency,
            "effective_capacity": capacity,
            "wall_clock_seconds": wall,
            "requests_per_second": len(observations) / wall if wall > 0 else None,
            "summary": summary,
        })
    baseline = rows[0]["requests_per_second"]
    for row in rows:
        current = row["requests_per_second"]
        row["throughput_speedup_vs_1"] = (
            current / baseline if current is not None and baseline else None
        )
    return {
        "suite": "provider_scaling",
        "evidence_level": "provider_live",
        "status": "PASS",
        "provider": provider,
        "model": model,
        "points": rows,
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
    fence = chr(96) * 3
    if source.startswith(fence) or source.endswith(fence):
        raise ValueError("authoring model returned Markdown-fenced source")
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
                       fixed_capacity: int = 4, dynamic_max: int = 8,
                       trial: int = 0) -> dict[str, Any]:
    """Run real model-authored code through the real Factory boundary and M3 issuer."""
    if sys.platform != "linux":
        return {"suite": f"factory_live_{strategy}", "evidence_level": "factory_live",
                "status": "NOT_TESTED", "reason": "FactoryRuntime requires Linux"}
    safe_provider = provider.replace("/", "_").replace(":", "_")
    run_root = output_root / f"factory-{safe_provider}-{strategy}-trial-{trial:03d}"
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
        engine_id=engine_id, attempt_prefix=f"{strategy}{trial:03d}",
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
            # Independent post-admission grade: read the content-addressed artifact
            # back through signature/hash-verifying EvidenceBus APIs. This does not
            # reuse the pre-admission workspace read.
            accepted_bytes = bus.artifact(
                receipt.receipt_hash,
                contract.allowed_outputs[0],
                station_public_key=identity.public_bytes(),
            )
            if not _exact(accepted_bytes.decode("utf-8"), case.expected):
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
    queue_integrity = bus.verify_queue()
    (run_root / "receipts.json").write_text(
        json.dumps(receipt_docs, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    accepted = len(receipts)
    total = len(cases)
    author_seconds = sum(x["wall_clock_ms"] for x in authored) / 1000.0
    end_to_end_seconds = author_seconds + elapsed_s
    return {
        "suite": f"factory_live_{strategy}",
        "evidence_level": "factory_live",
        "status": ("FAIL" if unsafe_acceptances else ("PASS" if accepted else "INCONCLUSIVE")),
        "strategy": strategy,
        "trial": trial,
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
        "end_to_end_seconds": end_to_end_seconds,
        "end_to_end_verified_throughput_per_second": (accepted / end_to_end_seconds if end_to_end_seconds > 0 else None),
        "waves": waves,
        "authored": authored,
        "workers_detail": rows,
        "receipt_hashes": [r.receipt_hash for r in receipts],
        "evidence_queue": queue_integrity,
        "output_dir": str(run_root),
    }


def factory_live_repeated_suite(*, provider: str, model: str, output_root: Path,
                                strategy: str, repeats: int,
                                cases: tuple[LiveCase, ...] = DEFAULT_CASES,
                                fixed_capacity: int = 4,
                                dynamic_max: int = 8) -> dict[str, Any]:
    """Repeat the full model-authoring + Factory execution experiment."""
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    trials = []
    for trial in range(repeats):
        result = factory_live_suite(
            provider=provider,
            model=model,
            output_root=output_root,
            strategy=strategy,
            cases=cases,
            fixed_capacity=fixed_capacity,
            dynamic_max=dynamic_max,
            trial=trial,
        )
        trials.append(result)
        if result.get("status") == "NOT_TESTED":
            break

    tested = [r for r in trials if r.get("status") != "NOT_TESTED"]
    if not tested:
        return {
            "suite": f"factory_live_{strategy}",
            "evidence_level": "factory_live",
            "status": "NOT_TESTED",
            "strategy": strategy,
            "provider": provider,
            "model": model,
            "trials": trials,
        }

    wall = [float(r["wall_clock_seconds"]) for r in tested
            if r.get("wall_clock_seconds") is not None]
    end_to_end = [float(r["end_to_end_seconds"]) for r in tested
                  if r.get("end_to_end_seconds") is not None]
    total_accepted = sum(int(r.get("accepted") or 0) for r in tested)
    total_workers = sum(int(r.get("workers") or 0) for r in tested)
    unsafe = sum(int(r.get("unsafe_acceptances") or 0) for r in tested)
    author_tokens = sum(int(r.get("author_tokens") or 0) for r in tested)
    if unsafe:
        status = "FAIL"
    elif total_accepted == 0:
        status = "INCONCLUSIVE"
    elif any(r.get("status") == "FAIL" for r in tested):
        status = "FAIL"
    elif any(r.get("status") == "INCONCLUSIVE" for r in tested):
        status = "INCONCLUSIVE"
    else:
        status = "PASS"

    wall_total = sum(wall)
    end_to_end_total = sum(end_to_end)
    return {
        "suite": f"factory_live_{strategy}",
        "evidence_level": "factory_live",
        "status": status,
        "strategy": strategy,
        "provider": provider,
        "model": model,
        "repeat_count": len(tested),
        "workers": total_workers,
        "accepted": total_accepted,
        "rejected_or_failed": total_workers - total_accepted,
        "unsafe_acceptances": unsafe,
        "unsafe_acceptance_rate": unsafe / total_accepted if total_accepted else None,
        "wall_clock_seconds_total": wall_total,
        "wall_clock_seconds_mean": round(statistics.fmean(wall), 6) if wall else None,
        "wall_clock_seconds_p50": _percentile(wall, 0.50),
        "wall_clock_seconds_p95": _percentile(wall, 0.95),
        "verified_useful_throughput_per_second": (
            total_accepted / wall_total if wall_total > 0 else None
        ),
        "end_to_end_seconds_total": end_to_end_total,
        "end_to_end_seconds_mean": (round(statistics.fmean(end_to_end), 6) if end_to_end else None),
        "end_to_end_verified_throughput_per_second": (
            total_accepted / end_to_end_total if end_to_end_total > 0 else None
        ),
        "author_tokens": author_tokens,
        "trials": trials,
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
        ("forbidden_write", "write_file('secret.txt','pwned')", 2.0, "VIOLATED"),
        ("forbidden_read", "read_file('secret.txt')", 2.0, "VIOLATED"),
        ("write_budget", "write_file('answer.txt','a')\nwrite_file('answer.txt','b')", 2.0, "VIOLATED"),
        ("timeout", "while True:\n    pass", 0.25, "VIOLATED"),
        ("git_escape", "write_file('.git/config','pwned')", 2.0, "VIOLATED"),
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
        passed = status == expected and status != "EXCEPTION"
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
                 include_factory: bool = True, cloud_provider: str | None = None,
                 cloud_model: str | None = None) -> dict[str, Any]:
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
    capture("provider_scaling", lambda: provider_scaling_suite(
        provider=provider, model=model, repeats=repeats))
    capture("cluster_loopback", lambda: cluster_loopback_suite(model=model))
    if include_factory:
        capture("factory_control", lambda: factory_control_suite(output_root=output))
        for strategy in ("single", "fixed", "dynamic"):
            capture(f"factory_live_{strategy}", lambda strategy=strategy: factory_live_repeated_suite(
                provider=provider, model=model, output_root=output, strategy=strategy,
                repeats=repeats))
    if cloud_provider or cloud_model:
        if not (cloud_provider and cloud_model):
            suites.append({"suite": "cloud_provider_live", "status": "NOT_TESTED",
                           "reason": "cloud_provider and cloud_model must be supplied together"})
        else:
            capture("cloud_provider_live", lambda: provider_live_suite(
                provider=cloud_provider, model=cloud_model, repeats=repeats))
            if include_factory:
                capture("factory_cloud_dynamic", lambda: factory_live_repeated_suite(
                    provider=cloud_provider, model=cloud_model, output_root=output,
                    strategy="dynamic", repeats=repeats))

    end = _now_ns()
    evaluated = [s for s in suites if s.get("status") != "NOT_TESTED"]
    failed = [s for s in evaluated if s.get("status") == "FAIL"]
    inconclusive = [s for s in evaluated if s.get("status") == "INCONCLUSIVE"]

    by_name = {str(s.get("suite")): s for s in suites}
    factory_local = {key: by_name.get(f"factory_live_{key}") for key in ("single", "fixed", "dynamic")}
    timing = {key: value.get("wall_clock_seconds_mean") for key, value in factory_local.items()
              if isinstance(value, dict) and value.get("wall_clock_seconds_mean") is not None}
    throughput = {key: value.get("verified_useful_throughput_per_second")
                  for key, value in factory_local.items()
                  if isinstance(value, dict) and value.get("verified_useful_throughput_per_second") is not None}
    end_to_end_timing = {key: value.get("end_to_end_seconds_mean") for key, value in factory_local.items()
                         if isinstance(value, dict) and value.get("end_to_end_seconds_mean") is not None}
    end_to_end_throughput = {key: value.get("end_to_end_verified_throughput_per_second")
                            for key, value in factory_local.items()
                            if isinstance(value, dict) and value.get("end_to_end_verified_throughput_per_second") is not None}
    speedups = {}
    end_to_end_speedups = {}
    single_time = timing.get("single")
    if single_time:
        for key in ("fixed", "dynamic"):
            candidate = timing.get(key)
            if candidate:
                speedups[key] = single_time / candidate
    single_e2e = end_to_end_timing.get("single")
    if single_e2e:
        for key in ("fixed", "dynamic"):
            candidate = end_to_end_timing.get(key)
            if candidate:
                end_to_end_speedups[key] = single_e2e / candidate

    control = by_name.get("factory_control", {})
    live_factory_rows = [value for value in factory_local.values()
                         if isinstance(value, dict) and value.get("status") != "NOT_TESTED"]
    live_factory_passes = [value for value in live_factory_rows if value.get("status") == "PASS"]
    unsafe = sum(int(row.get("unsafe_acceptances") or 0) for row in live_factory_rows)
    safety_status = "NOT_TESTED"
    if control.get("status") == "FAIL" or unsafe:
        safety_status = "FAIL"
    elif control.get("status") == "PASS" and live_factory_passes:
        safety_status = "SUPPORTED"
    elif control.get("status") == "PASS":
        safety_status = "PARTIAL"

    efficiency_status = "NOT_TESTED"
    if len(end_to_end_timing) == 3 and all(factory_local[k].get("status") == "PASS" for k in factory_local):
        if end_to_end_speedups and max(end_to_end_speedups.values()) > 1.0:
            efficiency_status = "SUPPORTED_FOR_THIS_WORKLOAD"
        else:
            efficiency_status = "NOT_SUPPORTED_FOR_THIS_WORKLOAD"

    cluster = by_name.get("cluster_loopback", {})
    hybrid_status = "NOT_TESTED"
    if cloud_provider and cloud_model and by_name.get("factory_cloud_dynamic", {}).get("status") == "PASS":
        hybrid_status = "PARTIAL_LOCAL_RUNTIME_CLOUD_AUTHORING"
    elif cluster.get("status") == "PASS":
        hybrid_status = "CONTROL_PLANE_ONLY"

    hypotheses = {
        "safety": {"status": safety_status, "unsafe_acceptances": unsafe,
                   "control_probe_status": control.get("status")},
        "scheduler_efficiency": {
            "status": efficiency_status,
            "wall_clock_seconds": timing,
            "verified_throughput_per_second": throughput,
            "scheduler_speedup_vs_single": speedups,
            "end_to_end_seconds_mean": end_to_end_timing,
            "end_to_end_verified_throughput_per_second": end_to_end_throughput,
            "end_to_end_speedup_vs_single": end_to_end_speedups,
            "provider_saturation_curve": by_name.get("provider_scaling", {}).get("points"),
            "scope": "governed Factory scheduling; provider saturation reported separately; not an uncontrolled-swarm baseline",
        },
        "hybrid_cloud_mesh": {
            "status": hybrid_status,
            "cluster_loopback_status": cluster.get("status"),
            "wan_mesh_measured": False,
            "cloud_authoring_configured": bool(cloud_provider and cloud_model),
        },
    }

    report = {
        "schema_version": SCHEMA_VERSION,
        "started_at_ns": started,
        "finished_at_ns": end,
        "environment": {**environment, "cloud_provider": cloud_provider, "cloud_model": cloud_model},
        "suites": suites,
        "hypotheses": hypotheses,
        "overall": {
            "status": ("FAIL" if failed else ("INCONCLUSIVE" if inconclusive else ("PASS" if evaluated else "NOT_TESTED"))),
            "evaluated_suites": len(evaluated),
            "not_tested_suites": sum(1 for s in suites if s.get("status") == "NOT_TESTED"),
            "failed_suites": len(failed),
            "inconclusive_suites": len(inconclusive),
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
    parser.add_argument("--cloud-provider")
    parser.add_argument("--cloud-model")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_gauntlet(
        output=Path(args.output), provider=args.provider, model=args.model,
        repeats=args.repeats, include_factory=not args.no_factory,
        cloud_provider=args.cloud_provider, cloud_model=args.cloud_model,
    )
    print(json.dumps({
        "report": str(Path(args.output) / "gauntlet-report.json"),
        "status": report["overall"]["status"],
        "evaluated_suites": report["overall"]["evaluated_suites"],
        "not_tested_suites": report["overall"]["not_tested_suites"],
        "failed_suites": report["overall"]["failed_suites"],
    }, indent=2))
    if report["overall"]["status"] == "FAIL":
        return 1
    if report["overall"]["status"] == "INCONCLUSIVE":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
