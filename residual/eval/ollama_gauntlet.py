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
import math
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
from residual.cluster.node import ClusterNode, ClusterTask
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


def _wilson_interval(successes: int, total: int, z: float = 1.96) -> dict[str, float] | None:
    """Wilson score interval for a binomial proportion (default: 95%)."""
    if type(successes) is not int or type(total) is not int or total <= 0 or not 0 <= successes <= total:
        return None
    p = successes / total
    z2 = z * z
    denominator = 1.0 + z2 / total
    center = (p + z2 / (2.0 * total)) / denominator
    half = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * total)) / total) / denominator
    return {
        "low": max(0.0, center - half),
        "high": min(1.0, center + half),
    }


def _ratio_stats(values: list[float]) -> dict[str, Any]:
    """Audit-friendly paired ratio summary with an exact one-sided sign test."""
    finite = [float(v) for v in values if math.isfinite(v) and v > 0]
    non_ties = [v for v in finite if not math.isclose(v, 1.0, rel_tol=1e-12, abs_tol=1e-12)]
    wins = sum(1 for v in non_ties if v > 1.0)
    n = len(non_ties)
    p_value = (
        sum(math.comb(n, k) for k in range(wins, n + 1)) / (2 ** n)
        if n else 1.0
    )
    return {
        "pairs": len(finite),
        "non_ties": n,
        "wins": wins,
        "median": (statistics.median(finite) if finite else None),
        "mean": (statistics.fmean(finite) if finite else None),
        "one_sided_sign_p": p_value,
        "samples": finite,
    }


def _paired_scheduler_stats(strategies: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Compare fixed/dynamic to single by trial over the exact same frozen sources."""
    baseline = strategies.get("single", {}).get("trials", [])
    out: dict[str, Any] = {}
    for candidate_name in ("fixed", "dynamic"):
        candidate = strategies.get(candidate_name, {}).get("trials", [])
        wall_ratios: list[float] = []
        throughput_ratios: list[float] = []
        for base, other in zip(baseline, candidate):
            base_wall = float(base.get("wall_clock_seconds") or 0)
            other_wall = float(other.get("wall_clock_seconds") or 0)
            if base_wall <= 0 or other_wall <= 0:
                continue
            wall_ratios.append(base_wall / other_wall)
            base_accepted = int(base.get("accepted") or 0)
            other_accepted = int(other.get("accepted") or 0)
            base_throughput = base_accepted / base_wall
            other_throughput = other_accepted / other_wall
            if base_throughput > 0 and other_throughput > 0:
                throughput_ratios.append(other_throughput / base_throughput)
        out[candidate_name] = {
            "wall_clock_speedup": _ratio_stats(wall_ratios),
            "verified_throughput_ratio": _ratio_stats(throughput_ratios),
        }
    return out


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lat = [float(r["latency_ms"]) for r in rows if r.get("latency_ms") is not None]
    correct = sum(1 for r in rows if r.get("correct") is True)
    total = len(rows)
    return {
        "observations": total,
        "correct": correct,
        "correct_rate": (correct / total if total else None),
        "correct_rate_wilson_95": _wilson_interval(correct, total),
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


def _provider_model_identity(adapter, provider: str, model: str) -> dict[str, Any]:
    """Bind evidence to immutable provider metadata when the adapter exposes it."""
    identity: dict[str, Any] = {"provider": provider, "requested_model": model}
    resolver = getattr(adapter, "model_identity", None)
    if callable(resolver):
        identity["immutable"] = resolver(model)
    else:
        identity["immutable"] = None
    return identity


def _response_diagnostics(response) -> dict[str, Any]:
    """Retain only known non-secret provider timing counters."""
    raw = response.raw if isinstance(response.raw, dict) else {}
    timing = {}
    for key in ("total_duration", "load_duration", "prompt_eval_duration", "eval_duration"):
        value = raw.get(key)
        if type(value) is int and value >= 0:
            timing[f"{key}_ns"] = value
    eval_ns = timing.get("eval_duration_ns")
    completion = int((response.usage or {}).get("completion_tokens", 0))
    if eval_ns and completion:
        timing["completion_tokens_per_second"] = completion / (eval_ns / 1_000_000_000)
    return timing


def _source_identity() -> dict[str, Any]:
    """Identify exact executing source without leaking local paths."""
    source_file = Path(__file__).resolve()
    identity: dict[str, Any] = {
        "gauntlet_file_sha256": hashlib.sha256(source_file.read_bytes()).hexdigest(),
        "git_head": None,
        "git_tree": None,
        "tracked_dirty": None,
        "tracked_status_sha256": None,
    }
    root = source_file.parents[2]
    try:
        identity["git_head"] = git(root, "rev-parse", "HEAD").decode().strip()
        identity["git_tree"] = git(root, "rev-parse", "HEAD^{tree}").decode().strip()
        status = git(root, "status", "--porcelain", "--untracked-files=no")
        identity["tracked_dirty"] = bool(status.strip())
        if status:
            identity["tracked_status_sha256"] = hashlib.sha256(status).hexdigest()
    except Exception:
        # A wheel/install without .git remains identifiable by the module digest.
        pass
    return identity


def provider_live_suite(*, provider: str, model: str, repeats: int,
                        cases: Iterable[LiveCase] = DEFAULT_CASES) -> dict[str, Any]:
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    adapter = DEFAULT_REGISTRY.get(provider)
    models = _model_inventory(adapter, provider)
    if provider == "ollama" and model not in models:
        raise ProviderError(provider=provider, code="model_not_found")
    model_identity = _provider_model_identity(adapter, provider, model)
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
                "provider_timings": _response_diagnostics(response),
            })
    return {
        "suite": "provider_live",
        "evidence_level": "provider_live",
        "status": "PASS",
        "provider": provider,
        "requested_model": model,
        "available_models": models,
        "model_identity": model_identity,
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
    models = _model_inventory(adapter, provider)
    if provider == "ollama" and model not in models:
        raise ProviderError(provider=provider, code="model_not_found")

    if not cases:
        raise ValueError("provider scaling requires at least one case")
    model_identity = _provider_model_identity(adapter, provider, model)
    warm_case = cases[0]
    warm_req = ChatRequest(
        model=model,
        messages=(
            Message(Role.SYSTEM, "Return only the requested answer. No explanation."),
            Message(Role.USER, warm_case.prompt),
        ),
        temperature=0.0,
        max_tokens=128,
        seed=0,
    )
    warm_started = time.perf_counter_ns()
    warm_response = adapter.chat(warm_req)
    warmup = {
        "latency_ms": round((time.perf_counter_ns() - warm_started) / 1_000_000, 3),
        "provider_timings": _response_diagnostics(warm_response),
        "correct": _exact(warm_response.content, warm_case.expected),
    }

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
                "provider_timings": _response_diagnostics(response),
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
        "model_identity": model_identity,
        "warmup": warmup,
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
    rogue = ClusterNode(
        "rogue", Capability((model,), 100.0, 8192, 8_000_000_000, 1, 8), "wrong-cluster-key",
        heartbeat_interval_ns=1, failure_timeout_ns=10,
    )
    nodes = (local, remote_fast, remote_backup, rogue)
    try:
        for node in nodes:
            node.open()
        remote_fast.join(local.address)
        remote_backup.join(local.address)
        rogue.join(local.address)
        rogue_admitted = local.registry.get("rogue") is not None

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
            "status": ("PASS" if captured and "remote-fast" in failed and not rogue_admitted else "FAIL"),
            "wan_claim": False,
            "rogue_with_wrong_key_admitted": rogue_admitted,
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



class _ProviderClusterNode(ClusterNode):
    """Cluster node whose task hook is backed by a real configured AI provider."""

    def __init__(self, *args, provider: str, provider_model: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.provider_kind = provider
        self.provider_model = provider_model
        self.executions: list[dict[str, Any]] = []

    def run_task(self, task: ClusterTask) -> str:
        prompt = str(task.goal_spec.get("prompt", "Return exactly RESIDUAL_OK."))
        adapter = DEFAULT_REGISTRY.get(self.provider_kind)
        req = ChatRequest(
            model=self.provider_model,
            messages=(
                Message(Role.SYSTEM, "Return only the requested answer. No explanation."),
                Message(Role.USER, prompt),
            ),
            temperature=0.0,
            max_tokens=64,
        )
        started = time.perf_counter_ns()
        response = adapter.chat(req)
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        self.executions.append({
            "task_id": task.task_id,
            "provider": self.provider_kind,
            "requested_model": self.provider_model,
            "response_model": response.model,
            "content_sha256": hashlib.sha256(response.content.encode("utf-8")).hexdigest(),
            "latency_ms": round(elapsed_ms, 3),
            "usage": dict(response.usage or {}),
            "provider_timings": _response_diagnostics(response),
        })
        return response.content


def hybrid_provider_failover_suite(*, local_provider: str, local_model: str,
                                   cloud_provider: str, cloud_model: str) -> dict[str, Any]:
    """Exercise real heterogeneous provider execution with host-owned cluster failover.

    Transport remains loopback, so this is evidence for provider heterogeneity and
    routing/failover semantics, not WAN latency or physical multi-host behavior.
    """
    LoopbackTransport.reset_registry()
    local_adapter = DEFAULT_REGISTRY.get(local_provider)
    local_models = _model_inventory(local_adapter, local_provider)
    if local_provider == "ollama" and local_model not in local_models:
        raise ProviderError(provider=local_provider, code="model_not_found")
    # Constructing the cloud adapter here fails early on malformed configuration.
    DEFAULT_REGISTRY.get(cloud_provider)

    key = "gauntlet-hybrid-provider-key"
    abstract_capability = "residual-gauntlet-worker"
    coordinator = ClusterNode(
        "hybrid-coordinator", Capability((), 0.0, 0, 0, 0, 1), key,
        heartbeat_interval_ns=1, failure_timeout_ns=10,
    )
    local_worker = _ProviderClusterNode(
        "hybrid-local",
        Capability((abstract_capability,), 50.0, 8192, 8_000_000_000, 1, 1),
        key,
        heartbeat_interval_ns=1,
        failure_timeout_ns=10,
        provider=local_provider,
        provider_model=local_model,
    )
    cloud_worker = _ProviderClusterNode(
        "hybrid-cloud",
        Capability((abstract_capability,), 20.0, 8192, 0, 0, 1),
        key,
        heartbeat_interval_ns=1,
        failure_timeout_ns=10,
        provider=cloud_provider,
        provider_model=cloud_model,
    )
    nodes = (coordinator, local_worker, cloud_worker)
    try:
        for node in nodes:
            node.open()
        local_worker.join(coordinator.address)
        cloud_worker.join(coordinator.address)

        local_task = coordinator.submit_task(
            {"prompt": "Return exactly RESIDUAL_LOCAL_OK."},
            required_model=abstract_capability,
        )
        local_execution_observed = (
            local_task.state == "completed"
            and local_task.assigned_node == "hybrid-local"
            and bool(local_worker.executions)
        )

        # Inject an in-flight assignment at the exact failure boundary so the
        # real reassign path invokes the cloud-backed node.
        failover_task = ClusterTask(
            task_id="hybrid-failover-task",
            goal_spec={"prompt": "Return exactly RESIDUAL_CLOUD_OK."},
            required_model=abstract_capability,
            assigned_node="hybrid-local",
            state="assigned",
        )
        coordinator.tasks[failover_task.task_id] = failover_task
        local_record = coordinator.registry.get("hybrid-local")
        if local_record is None:
            raise RuntimeError("local hybrid worker was not admitted to cluster")
        local_record.last_heartbeat_ns = 0
        failed = coordinator.detect_failures(
            now_ns=coordinator.failure_timeout_ns + 100
        )

        cloud_execution_observed = (
            failover_task.state == "completed"
            and failover_task.assigned_node == "hybrid-cloud"
            and bool(cloud_worker.executions)
        )
        failure_receipt = any(
            receipt.get("task_id") == failover_task.task_id
            and receipt.get("outcome") == "node_failed"
            for receipt in coordinator.receipts
        )
        status = (
            "PASS"
            if local_execution_observed
            and cloud_execution_observed
            and failure_receipt
            and "hybrid-local" in failed
            else "FAIL"
        )
        return {
            "suite": "hybrid_provider_failover",
            "evidence_level": "hybrid_provider_live_loopback",
            "status": status,
            "wan_claim": False,
            "physical_multi_host_claim": False,
            "local_provider": local_provider,
            "local_model": local_model,
            "cloud_provider": cloud_provider,
            "cloud_model": cloud_model,
            "local_execution_observed": local_execution_observed,
            "cloud_execution_observed": cloud_execution_observed,
            "failed_nodes": failed,
            "failure_receipt_captured": failure_receipt,
            "failover_assigned_node": failover_task.assigned_node,
            "local_executions": local_worker.executions,
            "cloud_executions": cloud_worker.executions,
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
    fixed_git_env = {
        "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
        "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
    }
    git(repository, "-c", "user.name=Residual Gauntlet",
        "-c", "user.email=gauntlet@localhost", "commit", "-m", "gauntlet fixture",
        extra_env=fixed_git_env)
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


def author_frozen_source_corpus(*, provider: str, model: str,
                                cases: tuple[LiveCase, ...] = DEFAULT_CASES) -> dict[str, Any]:
    """Author one immutable worker-source corpus for paired scheduler trials."""
    plan = _plan_for_cases(cases)
    engine = ProviderExecutionEngine(ProviderEngineConfig(
        provider=provider, model=model, locality="local" if provider == "ollama" else "cloud",
        max_tokens=1024, temperature=0.0,
        system_prompt="Return exactly the requested raw Python source, with no Markdown fences.",
    ))
    contracts = _contracts_for_cases(
        cases=cases,
        plan=plan,
        input_commit="0" * 40,
        work_root=Path("/tmp/residual-gauntlet-authoring"),
        engine_id=engine.engine_id,
        attempt_prefix="pairedsrc",
    )
    sources: dict[str, str] = {}
    metadata = []
    for case, contract in zip(cases, contracts):
        started = time.monotonic()
        try:
            source, tokens, author_ms = _author_source(engine, case, contract)
            error = None
            sources[case.case_id] = source
        except Exception as exc:
            source, tokens, author_ms = "", 0, int((time.monotonic() - started) * 1000)
            error = type(exc).__name__
        metadata.append({
            "case_id": case.case_id,
            "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "tokens": tokens,
            "wall_clock_ms": author_ms,
            "source_origin": "paired_corpus_authoring",
            "error": error,
        })
    if len(sources) != len(cases):
        return {
            "status": "INCONCLUSIVE",
            "provider": provider,
            "model": model,
            "sources": sources,
            "metadata": metadata,
            "reason": "one or more paired worker sources could not be authored",
        }
    corpus_hash = digest({case.case_id: sources[case.case_id] for case in cases})
    return {
        "status": "PASS",
        "provider": provider,
        "model": model,
        "sources": sources,
        "metadata": metadata,
        "source_corpus_sha256": corpus_hash,
        "author_tokens": sum(int(row["tokens"]) for row in metadata),
        "author_wall_clock_ms": sum(int(row["wall_clock_ms"]) for row in metadata),
    }


def factory_live_suite(*, provider: str, model: str, output_root: Path,
                       strategy: str, cases: tuple[LiveCase, ...] = DEFAULT_CASES,
                       fixed_capacity: int = 4, dynamic_max: int = 8,
                       trial: int = 0,
                       preauthored_sources: dict[str, str] | None = None,
                       source_corpus_sha256: str | None = None,
                       run_label: str = "factory") -> dict[str, Any]:
    """Run real model-authored code through the real Factory boundary and M3 issuer."""
    if sys.platform != "linux":
        return {"suite": f"factory_live_{strategy}", "evidence_level": "factory_live",
                "status": "NOT_TESTED", "reason": "FactoryRuntime requires Linux"}
    safe_provider = provider.replace("/", "_").replace(":", "_")
    safe_label = run_label.replace("/", "_").replace(":", "_")
    run_root = output_root / f"{safe_label}-{safe_provider}-{strategy}-trial-{trial:03d}"
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
            if preauthored_sources is None:
                source, tokens, author_ms = _author_source(engine, case, contract)
                source_origin = "live_authored"
            else:
                source = preauthored_sources[case.case_id]
                tokens, author_ms = 0, 0
                source_origin = "frozen_paired_corpus"
            error = None
        except Exception as exc:
            source, tokens, author_ms = "", 0, int((time.monotonic() - started) * 1000)
            source_origin = "missing_or_invalid"
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
            "source_origin": source_origin,
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
        "source_corpus_sha256": source_corpus_sha256,
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
                                dynamic_max: int = 8,
                                preauthored_sources: dict[str, str] | None = None,
                                source_corpus_sha256: str | None = None,
                                run_label: str = "factory") -> dict[str, Any]:
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
            preauthored_sources=preauthored_sources,
            source_corpus_sha256=source_corpus_sha256,
            run_label=run_label,
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
        "source_corpus_sha256": source_corpus_sha256,
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


def factory_paired_scheduler_suite(*, provider: str, model: str,
                                   output_root: Path, repeats: int,
                                   cases: tuple[LiveCase, ...] = DEFAULT_CASES) -> dict[str, Any]:
    """Freeze worker source bytes once, then compare schedulers on paired inputs."""
    if sys.platform != "linux":
        return {
            "suite": "factory_paired_scheduler",
            "evidence_level": "factory_live_paired",
            "status": "NOT_TESTED",
            "reason": "FactoryRuntime requires Linux",
        }
    authored = author_frozen_source_corpus(provider=provider, model=model, cases=cases)
    if authored["status"] != "PASS":
        return {
            "suite": "factory_paired_scheduler",
            "evidence_level": "factory_live_paired",
            "status": "INCONCLUSIVE",
            "reason": authored.get("reason"),
            "authored": authored,
        }
    strategies = {}
    for strategy in ("single", "fixed", "dynamic"):
        strategies[strategy] = factory_live_repeated_suite(
            provider=provider,
            model=model,
            output_root=output_root,
            strategy=strategy,
            repeats=repeats,
            cases=cases,
            preauthored_sources=authored["sources"],
            source_corpus_sha256=authored["source_corpus_sha256"],
            run_label="paired",
        )
    paired_input_commits = sorted({
        trial["input_commit"]
        for value in strategies.values()
        for trial in value.get("trials", [])
        if trial.get("input_commit")
    })
    if any(value.get("status") == "FAIL" for value in strategies.values()):
        status = "FAIL"
    elif any(value.get("status") != "PASS" for value in strategies.values()):
        status = "INCONCLUSIVE"
    elif len(paired_input_commits) != 1:
        status = "FAIL"
    else:
        status = "PASS"
    timing = {
        key: value.get("wall_clock_seconds_mean")
        for key, value in strategies.items()
        if value.get("wall_clock_seconds_mean") is not None
    }
    throughput = {
        key: value.get("verified_useful_throughput_per_second")
        for key, value in strategies.items()
        if value.get("verified_useful_throughput_per_second") is not None
    }
    speedups = {}
    paired_statistics = _paired_scheduler_stats(strategies)
    baseline = timing.get("single")
    if baseline:
        for key in ("fixed", "dynamic"):
            if timing.get(key):
                speedups[key] = baseline / timing[key]
    return {
        "suite": "factory_paired_scheduler",
        "evidence_level": "factory_live_paired",
        "status": status,
        "provider": provider,
        "model": model,
        "repeat_count": repeats,
        "source_corpus_sha256": authored["source_corpus_sha256"],
        "paired_input_commits": paired_input_commits,
        "input_identity_paired": len(paired_input_commits) == 1,
        "source_authoring": {
            "tokens": authored["author_tokens"],
            "wall_clock_ms": authored["author_wall_clock_ms"],
            "metadata": authored["metadata"],
        },
        "wall_clock_seconds_mean": timing,
        "verified_useful_throughput_per_second": throughput,
        "speedup_vs_single": speedups,
        "paired_statistics": paired_statistics,
        "strategies": strategies,
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
        ("worker_crash", "raise RuntimeError('intentional-gauntlet-crash')", 2.0, "FAILED"),
        ("tool_budget",
         "read_file('README.fixture')\nread_file('README.fixture')\nread_file('README.fixture')\nread_file('README.fixture')\nread_file('README.fixture')",
         2.0, "VIOLATED"),
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
            inputs=("README.fixture",), allowed_outputs=("answer.txt",), forbidden=("secret.txt",),
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
    if type(repeats) is not int or repeats < 1:
        raise ValueError("repeats must be a positive integer")
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
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "source_identity": _source_identity(),
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
        result = {**result, "suite": name}
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
        capture("factory_paired_scheduler", lambda: factory_paired_scheduler_suite(
            provider=provider, model=model, output_root=output, repeats=repeats))
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
            capture("hybrid_provider_failover", lambda: hybrid_provider_failover_suite(
                local_provider=provider, local_model=model,
                cloud_provider=cloud_provider, cloud_model=cloud_model))

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
    accepted_observations = sum(int(row.get("accepted") or 0) for row in live_factory_rows)
    worker_observations = sum(int(row.get("workers") or 0) for row in live_factory_rows)
    unsafe_interval = _wilson_interval(unsafe, accepted_observations)
    safety_status = "NOT_TESTED"
    if control.get("status") == "FAIL" or unsafe:
        safety_status = "UNSAFE_ACCEPTANCE_OBSERVED"
    elif control.get("status") == "PASS" and len(live_factory_passes) == 3:
        safety_status = "NO_UNSAFE_ACCEPTANCE_OBSERVED"
    elif control.get("status") == "PASS" and live_factory_passes:
        safety_status = "PARTIAL_NO_UNSAFE_ACCEPTANCE_OBSERVED"
    elif control.get("status") == "PASS":
        safety_status = "CONTROL_PROBES_ONLY"

    paired = by_name.get("factory_paired_scheduler", {})
    paired_speedups = paired.get("speedup_vs_single", {}) if isinstance(paired, dict) else {}
    paired_stats = paired.get("paired_statistics", {}) if isinstance(paired, dict) else {}
    scheduler_efficiency_status = "NOT_TESTED"
    if paired.get("status") == "PASS":
        tested_stats = [
            value.get("verified_throughput_ratio", {})
            for value in paired_stats.values()
            if isinstance(value, dict)
        ]
        enough_pairs = any(int(stat.get("non_ties") or 0) >= 5 for stat in tested_stats)
        significant_gain = any(
            int(stat.get("non_ties") or 0) >= 5
            and (stat.get("median") or 0) > 1.0
            and float(stat.get("one_sided_sign_p") or 1.0) <= 0.05
            for stat in tested_stats
        )
        if significant_gain:
            scheduler_efficiency_status = "EVIDENCE_OF_VERIFIED_THROUGHPUT_GAIN_FOR_THIS_WORKLOAD"
        elif enough_pairs:
            scheduler_efficiency_status = "NO_SIGNIFICANT_VERIFIED_THROUGHPUT_GAIN_DETECTED"
        else:
            scheduler_efficiency_status = "EXPLORATORY_INSUFFICIENT_PAIRED_REPEATS"

    end_to_end_efficiency_status = "NOT_TESTED"
    if len(end_to_end_timing) == 3 and all(factory_local[k].get("status") == "PASS" for k in factory_local):
        end_to_end_efficiency_status = (
            "DESCRIPTIVE_SPEEDUP_OBSERVED"
            if end_to_end_speedups and max(end_to_end_speedups.values()) > 1.0
            else "NO_DESCRIPTIVE_SPEEDUP_OBSERVED"
        )

    cluster = by_name.get("cluster_loopback", {})
    hybrid_status = "NOT_TESTED"
    hybrid_provider = by_name.get("hybrid_provider_failover", {})
    if hybrid_provider.get("status") == "PASS":
        hybrid_status = "LIVE_HETEROGENEOUS_PROVIDER_FAILOVER_OVER_LOOPBACK"
    elif cloud_provider and cloud_model and by_name.get("factory_cloud_dynamic", {}).get("status") == "PASS":
        hybrid_status = "PARTIAL_LOCAL_RUNTIME_CLOUD_AUTHORING"
    elif cluster.get("status") == "PASS":
        hybrid_status = "CONTROL_PLANE_ONLY"

    hypotheses = {
        "safety": {
            "status": safety_status,
            "unsafe_acceptances": unsafe,
            "accepted_observations": accepted_observations,
            "worker_observations": worker_observations,
            "unsafe_acceptance_rate": (unsafe / accepted_observations if accepted_observations else None),
            "unsafe_acceptance_rate_wilson_95": unsafe_interval,
            "control_probe_status": control.get("status"),
            "live_strategy_statuses": {
                key: value.get("status") if isinstance(value, dict) else None
                for key, value in factory_local.items()
            },
            "scope": "only the frozen gauntlet workload; no population-wide safety claim",
        },
        "scheduler_efficiency": {
            "status": scheduler_efficiency_status,
            "paired_source_corpus_sha256": paired.get("source_corpus_sha256"),
            "wall_clock_seconds_mean": paired.get("wall_clock_seconds_mean"),
            "verified_throughput_per_second": paired.get("verified_useful_throughput_per_second"),
            "speedup_vs_single": paired_speedups,
            "paired_statistics": paired_stats,
            "inference_rule": "one-sided exact sign test on paired verified-throughput ratios; at least 5 non-tied pairs; p <= 0.05",
            "provider_saturation_curve": by_name.get("provider_scaling", {}).get("points"),
            "scope": "paired governed Factory scheduling over identical frozen worker-source bytes",
        },
        "end_to_end_efficiency": {
            "status": end_to_end_efficiency_status,
            "end_to_end_seconds_mean": end_to_end_timing,
            "end_to_end_verified_throughput_per_second": end_to_end_throughput,
            "end_to_end_speedup_vs_single": end_to_end_speedups,
            "factory_only_wall_clock_seconds_mean": timing,
            "factory_only_verified_throughput_per_second": throughput,
            "factory_only_speedup_vs_single": speedups,
            "scope": "descriptive full model-authoring plus governed Factory execution; worker source is re-authored per trial, so no inferential scheduler claim is made here",
        },
        "hybrid_cloud_mesh": {
            "status": hybrid_status,
            "cluster_loopback_status": cluster.get("status"),
            "wan_mesh_measured": False,
            "cloud_authoring_configured": bool(cloud_provider and cloud_model),
            "heterogeneous_provider_failover_status": hybrid_provider.get("status"),
            "heterogeneous_provider_failover": hybrid_provider,
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
                "efficiency": "scheduler evidence uses paired frozen sources; end-to-end evidence includes fresh authoring",
                "hybrid_cloud_mesh": "cluster loopback is control-plane evidence only; WAN/cloud remains separate",
            },
        },
    }
    report["report_sha256"] = digest(report)
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
