#!/usr/bin/env python3
"""Offline engineering measurements and pinned-source review probes.

No provider calls, accepted-state changes, or confirmatory workload execution.
Synthetic metadata counts are not concurrently running workers. All durations
measure real code; controller outcome timings are explicitly synthetic fixtures.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
from dataclasses import fields, replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import signal
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from observation_layer import Observation, ObservationKind, SCHEMA_VERSION, verify_chain
from residual.assurance.market import MarketProfile, VerifiedComputeMarket
from residual.core import canonical, digest
from residual.factory.evidence_receipts import ArtifactBinding, StationIdentity, WorkerReceipt
from residual.factory.m4_evidence import ReadyDagSnapshot
from residual.factory.m4_integrator import IntegrationReceipt
from residual.factory.m4_scheduler import M4AdaptiveScheduler, SchedulerNode
from residual.factory.models import ExecutionPlan, FactoryTask, Requirement
from residual.factory.runtime_workspace import ManagedWorktree, SafeFileBroker
from residual.factory.worker_contract import AttemptGuard, WorkerContract
from residual.providers import Prices, Usage

BASE = "dec571992a97b4ae80f0310aa32ffd8f542aef8c"
OTX = "0063e6400fa945acf2db393f7e9d30db02cb1139"
OBS = "058e25b3ca73de4528648b72b1901b2c319fe643"
PR81 = "30d1d020469d958d90969bc02946145c248e0adb"
SCHEMA = "residual.engineering-envelope.v1"
SOURCE_PATHS = (
    "scripts/engineering_envelope.py", "residual/core.py", "observation_layer/core.py",
    "residual/factory/evidence_receipts.py", "residual/factory/m4_integrator.py",
    "residual/factory/m4_evidence.py", "residual/factory/models.py",
    "residual/factory/worker_contract.py", "residual/factory/runtime_workspace.py",
    "residual/factory/m4_scheduler.py", "residual/factory/evidence_bus.py",
    "residual/assurance/market.py", "residual/providers.py",
    "residual/engine.py", "residual/study.py", "residual/station/worker.py",
    "residual/engines/provider_bridge.py", "residual/observability/metrics.py",
    "ai_providers/router.py", "ai_providers/core.py", "ai_providers/registry.py",
)


def git(*args, cwd=ROOT):
    return subprocess.check_output(["git", *args], cwd=cwd, stderr=subprocess.PIPE, timeout=20)


def source_identity():
    return {
        "git_sha": git("rev-parse", "HEAD").decode().strip(),
        "git_tree": git("rev-parse", "HEAD^{tree}").decode().strip(),
        "worktree_dirty": bool(git("status", "--porcelain")),
        "files": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCE_PATHS},
    }


@contextmanager
def deadline(seconds):
    """Bound each case; never claim a timeout is a measured success."""
    if not hasattr(signal, "setitimer"):
        raise RuntimeError("bounded measurements require POSIX setitimer")
    previous = signal.getsignal(signal.SIGALRM)

    def expired(_signum, _frame):
        raise TimeoutError("engineering case time budget exceeded")

    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def measure(name, size, operation, *, repeats=3, timeout_s=10):
    samples = []
    check = None
    try:
        with deadline(timeout_s):
            for _ in range(repeats):
                start = time.perf_counter_ns()
                check = operation()
                samples.append(time.perf_counter_ns() - start)
        status = "measured"
        error = None
    except (Exception, RecursionError) as exc:
        status = "timeout" if isinstance(exc, TimeoutError) else "error"
        # Do not serialize exception messages, paths, stdout or environment.
        error = type(exc).__name__
    return {"mechanism": name, "size": size, "status": status,
            "samples_ns": samples, "median_ns": statistics.median(samples) if status == "measured" else None,
            "result": check if status == "measured" else None, "error_type": error,
            "timeout_s": timeout_s, "repeats_requested": repeats}


def make_plan(count, shape="wide"):
    requirements = tuple(Requirement(f"r{i}", "Synthetic engineering requirement", ("fixture",)) for i in range(count))
    tasks = tuple(FactoryTask(f"t{i}", "Synthetic metadata; no worker launched", (f"r{i}",),
                             depends_on=(f"t{i-1}",) if shape == "chain" and i else ()) for i in range(count))
    return ExecutionPlan("Engineering only; excluded from paper dataset", requirements, tasks)


def make_receipt(count):
    identity = StationIdentity.generate()
    data = b"engineering fixture\n"
    sha = hashlib.sha256(data).hexdigest()
    receipt = WorkerReceipt(
        receipt_id="engineering", execution_plan_hash="1" * 64, task_id="t0", worker_id="w0",
        swarm_id="engineering", attempt_id="a0", engine_name="synthetic", engine_version="1",
        input_commit="2" * 40, output_commit="3" * 40, contract_hash="4" * 64,
        artifacts=tuple(ArtifactBinding(f"file{i}.txt", sha, len(data)) for i in range(count)),
        requirements_met=(("r0", True),), verification_results=(("fixture", "pass"),),
        overall_verdict="pass", verifier_identity="engineering-fixture", verifier_revision="5" * 64,
        issued_at_ns=1, station_key_id=identity.key_id, station_signature="pending",
    )
    return replace(receipt, station_signature=identity.sign(receipt.receipt_hash)), identity


def observation_case(count):
    previous = "GENESIS"
    observations = []
    for i in range(count):
        obs = Observation(f"e{i}", "engineering", ObservationKind.CUSTOM, i + 1, SCHEMA_VERSION,
                          previous, {"event": "synthetic", "sequence": i})
        observations.append(obs)
        previous = obs.digest
    if not verify_chain(observations, expected_head=previous, expected_count=count):
        raise AssertionError("generated chain does not verify")
    return {"count": count, "head": previous,
            "serialized_bytes": sum(len(o.canonical_bytes()) for o in observations)}


def scheduler_case(count):
    plan = make_plan(1)
    market = VerifiedComputeMarket()
    market.register(MarketProfile("synthetic@1", frozenset({"python"}), 0.01, 1.0, location="local"))
    nodes = tuple(SchedulerNode(f"node{i}", "synthetic@1", "local", frozenset({"python"}), capacity=1)
                  for i in range(count))
    scheduler = M4AdaptiveScheduler(plan, market, nodes)
    snapshot = ReadyDagSnapshot(plan.graph_hash, (), ("t0",), (), 1.0, ())

    def run():
        placement = scheduler.select_engine("t0", "python")
        measurements = scheduler.measure(snapshot, total_workers=count, active_workers=0,
                                         verification_queue_depth=0, integration_conflicts=0, integration_attempts=0)
        return {"selected_node": placement.node_id, "measurement_hash": measurements.measurement_hash,
                "synthetic_node_records": count, "launched_workers": 0}
    return run


def capture_case(count, timeout_s):
    """Real M2 broker capture. Setup/writes/cleanup are outside timing."""
    with tempfile.TemporaryDirectory(prefix="residual-capture-") as temp:
        root = Path(temp)
        repo = root / "repo"
        repo.mkdir()
        git("init", "-q", cwd=repo)
        git("-c", "user.name=Engineering", "-c", "user.email=engineering@localhost", "commit", "-qm", "empty", "--allow-empty", cwd=repo)
        commit = git("rev-parse", "HEAD", cwd=repo).decode().strip()
        contract = WorkerContract(task_id="t0", worker_id="w0", swarm_id="engineering", execution_plan_hash="1" * 64,
            attempt_id="a0", lease_id="lease0", lease_generation=1, input_commit=commit,
            workspace_root=str(root / "runtime" / "engineering" / "a0"), inputs=(), allowed_outputs=("out/",),
            forbidden=(), requirements=("r0",), acceptance=("fixture",), dependencies=(), allowed_tools=("write_file",),
            forbidden_tools=(), token_budget=0, wall_clock_budget_s=300, max_tool_calls=count,
            max_file_writes=count, memory_limit_mb=128)
        workspace = ManagedWorktree(repo, root / "runtime", contract)
        workspace.create()
        guard = AttemptGuard(contract, observe=lambda _event: None, terminate=lambda *_args: None)
        guard.start()
        broker = SafeFileBroker(workspace, guard)
        try:
            for i in range(count):
                broker.dispatch("write_file", {"path": f"out/file{i}.txt", "content": "x" * 1024})
            return measure("m2_broker_candidate_capture", {"files": count, "bytes_per_file": 1024},
                           lambda: workspace.capture(broker).to_dict(), repeats=1, timeout_s=timeout_s)
        finally:
            broker.close()
            workspace.discard()


@contextmanager
def pinned_package(sha, package):
    """Read Git objects into an isolated temporary import namespace; no checkout/fetch."""
    if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("an exact local Git SHA is required")
    alias = f"_engineering_{package}_{sha[:12]}"
    with tempfile.TemporaryDirectory(prefix="residual-review-") as temp:
        path = Path(temp) / package
        path.mkdir()
        prefix = f"residual/{package}/"
        paths = git("ls-tree", "-r", "--name-only", sha, "--", prefix).decode().splitlines()
        hashes = {}
        for source in paths:
            if not source.endswith(".py"):
                continue
            relative = Path(source).relative_to(prefix)
            target = path / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            raw = git("show", f"{sha}:{source}")
            target.write_bytes(raw)
            hashes[source] = hashlib.sha256(raw).hexdigest()
        spec = importlib.util.spec_from_file_location(alias, path / "__init__.py", submodule_search_locations=[str(path)])
        if spec is None or spec.loader is None:
            raise ValueError("pinned package is unavailable")
        module = importlib.util.module_from_spec(spec)
        sys.modules[alias] = module
        try:
            spec.loader.exec_module(module)
            yield module, {"git_sha": sha, "files": hashes}
        finally:
            for key in list(sys.modules):
                if key == alias or key.startswith(alias + "."):
                    sys.modules.pop(key, None)


def review_otx():
    with pinned_package(OTX, "otx") as (otx, source):
        controller = otx.OrchestrationTaxController()
        task = otx.Task("tiny0", "tiny-audit", "atomic", value=1.0, size=0.01)
        fixture = {
            "single": {otx.Phase.WORKER_EXECUTION: 0.01, otx.Phase.SCHEDULING: 0.001},
            "pair": {otx.Phase.WORKER_EXECUTION: 0.01, otx.Phase.SCHEDULING: 1.0},
            "swarm": {otx.Phase.WORKER_EXECUTION: 0.01, otx.Phase.SCHEDULING: 5.0},
        }
        choices = []
        for _ in range(30):
            obs = controller.select_topology(task)
            choices.append(obs.selected_topology)
            controller.record_outcome(obs.observation_id, otx.PhaseTiming(fixture[obs.selected_topology]), True)
        # Independent negative check: duplicate delivery must not count twice.
        last = controller.log.by_id(obs.observation_id)
        before = controller.model.sample_count(task.task_class, last.selected_topology)
        controller.record_outcome(obs.observation_id, otx.PhaseTiming(fixture[last.selected_topology]), True)
        after = controller.model.sample_count(task.task_class, last.selected_topology)
        return {"source": source, "fixture_kind": "hand-authored synthetic outcomes; not measured timings",
                "fixture_seconds": fixture, "choices": choices, "learned_single": choices[-10:] == ["single"] * 10,
                "duplicate_outcome_count_delta": after - before,
                "limits": ["No live quality/cost inference", "No forced exploration guarantee", "No runtime integration claim"]}


def review_observability():
    with pinned_package(OBS, "telemetry") as (obs, source):
        schema = obs.OBSERVATION_SCHEMA_VERSION
        events = [
            {"kind": "execution", "schema_version": schema, "task_class": "code", "task_id": "a", "outcome": "pass", "worker_seconds": 1.0, "correct": True},
            {"kind": "acceptance", "schema_version": schema, "task_class": "code", "task_id": "a", "correct": True},
            {"kind": "execution", "schema_version": schema, "task_class": "code", "task_id": "b", "outcome": "fail", "worker_seconds": 1.0, "correct": False},
        ]
        collector = obs.TelemetryCollector()
        for event in events:
            collector.ingest(event)
        before = obs.build_reliability_report(collector.observations)
        collector.registry["residual_obs_acceptances_total"].inc(("code",), 100)
        after = obs.build_reliability_report(collector.observations)
        duplicate = obs.build_reliability_report(events + [events[1]])
        collector.observations[0]["correct"] = False
        mutated = obs.build_reliability_report(collector.observations)
        wrong_type = obs.build_reliability_report([{**events[1], "correct": "true"}])
        return {"source": source, "fixture": events,
                "metrics_mutation_changes_report": before != after,
                "reported_p_x": before["report"]["aggregates"]["correctness"]["value"]["p_x"],
                "unique_execution_p_x": 0.5,
                "duplicate_acceptances": duplicate["report"]["aggregates"]["acceptance"]["value"]["accepted"],
                "mutable_raw_evidence_changes_report": before != mutated,
                "non_boolean_correct_accepted": wrong_type["report"]["aggregates"]["correctness"]["value"]["labeled"] == 1}


def cost_checks():
    prices = Prices(1.0, 2.0)
    return {
        "reported_100_in_50_out_usd": prices.cost(Usage(100, 50, source="reported")),
        "missing_usage_usd": prices.cost(Usage()),
        "estimated_usage_usd": prices.cost(Usage(100, 50, source="estimated")),
        "unsupported_cache_write_usd": prices.cost(Usage(100, 50, source="reported", cache_write_input_tokens=1)),
        "status": "native Prices arithmetic only; adapter coverage is source-reviewed, not end-to-end metering",
    }


def routing_accounting_probe():
    from ai_providers.core import ChatRequest, ChatResponse, Message, ProviderError, Role
    from ai_providers.registry import Registry
    from ai_providers.router import Router
    reservations, completions, order = [], [], []

    class FixtureProvider:
        def __init__(self, name, fail):
            self.name, self.fail = name, fail

        def chat(self, request):
            order.append(f"dispatch:{self.name}")
            if self.fail:
                raise ProviderError(provider=self.name, code="server_error", retryable=True, status=500)
            return ChatResponse(request.model, "fixture", usage={"prompt_tokens": 100, "completion_tokens": 50})

    def before(_provider, _request, meta):
        reservations.append(dict(meta))
        order.append(f"reserve:{meta['provider']}")

    def after(receipt):
        completions.append(dict(receipt))
        order.append(f"complete:{receipt['provider']}")

    registry = Registry()
    registry.register("openai", lambda: FixtureProvider("openai", True))
    registry.register("anthropic", lambda: FixtureProvider("anthropic", False))
    router = Router(registry, before_attempt=before, after_attempt=after)
    router.chat("openai:fixture", ChatRequest("fixture", (Message(Role.USER, "engineering fixture"),)), ["anthropic:fixture"])
    return {"kind": "offline fake transports through actual Router", "dispatch_order": order,
            "reserved_attempts": len(reservations), "completed_attempts": len(completions),
            "shared_request_id": len({r["request_id"] for r in completions}) == 1,
            "attempt_numbers": [r["attempt"] for r in completions],
            "statuses": [r["status"] for r in completions],
            "failed_usage": completions[0]["usage"],
            "completion_fields": sorted(completions[0]),
            "durable_metering": "not demonstrated: audit callbacks retain in memory only"}


def pr81_source_checks():
    paths = ["residual/factory/m4_integrator.py", "residual/factory/m4_safety.py", "residual/factory/m4_sandbox.py"]
    sources = {}
    receipt_fields = []
    for path in paths:
        raw = git("show", f"{PR81}:{path}")
        tree = ast.parse(raw)
        sources[path] = {"sha256": hashlib.sha256(raw).hexdigest(), "symbols": {
            node.name: {"first_line": node.lineno, "last_line": node.end_lineno}
            for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.ClassDef))}}
        if path.endswith("m4_integrator.py"):
            receipt = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "IntegrationReceipt")
            receipt_fields = [n.target.id for n in receipt.body if isinstance(n, ast.AnnAssign)]
    return {"git_sha": PR81, "status": "source inspection only; no #81 runtime qualification",
            "sources": sources, "integration_receipt_fields": receipt_fields,
            "verification_policy_hash_present": "verification_policy_hash" in receipt_fields,
            "candidate_binding": "output_commit -> pre-verification frozen Git tree; signed indirectly by receipt",
            "remaining_gaps": ["policy hash does not hash external verifier executable/dependencies",
                               "stdout/stderr hashes without persisted bytes are not reproducible outputs",
                               "ExecutionPlan lacks intrinsic workload cell hash"]}


def chain_schema_checks():
    integration = {f.name for f in fields(IntegrationReceipt)}
    worker = {f.name for f in fields(WorkerReceipt)}
    plan = {f.name for f in fields(ExecutionPlan)}
    return {"status": "schema/source audit; no final run receipt was supplied",
            "integration_receipt_fields": sorted(integration),
            "integration_has_verifier_revision": "verifier_revision" in integration,
            "integration_has_explicit_verified_tree_field": "verified_tree" in integration,
            "worker_has_contract_hash": "contract_hash" in worker,
            "worker_has_execution_plan_hash": "execution_plan_hash" in worker,
            "plan_has_workload_hash": "workload_hash" in plan,
            "end_to_end_proof": "BLOCKED: missing explicit edges and retained run artifact"}


def validate_sizes(values, maximum, label):
    if not values or any(type(v) is not int or v < 1 or v > maximum for v in values):
        raise ValueError(f"{label} must be integers between 1 and {maximum}")
    return list(dict.fromkeys(values))


def run(args):
    workers = validate_sizes(args.workers, 1000, "workers")
    observations = validate_sizes(args.observations, 100000, "observations")
    dags = validate_sizes(args.dag_nodes, 10000, "dag-nodes")
    artifacts = validate_sizes(args.artifacts, 10000, "artifacts")
    captures = validate_sizes(args.capture_files, 1000, "capture-files") if args.capture_files else []
    if not 1 <= args.repeats <= 10 or not 0 < args.timeout_s <= 60:
        raise ValueError("repeats must be 1..10 and timeout-s must be >0..60")
    cases = []
    for n in artifacts:
        receipt, identity = make_receipt(n)
        def receipt_op(receipt=receipt, identity=identity):
            decoded = WorkerReceipt.from_dict(json.loads(canonical(receipt.to_dict())))
            if not StationIdentity.verify(decoded, identity.public_bytes()):
                raise AssertionError("round-trip signature failed")
            return {"receipt_hash": decoded.receipt_hash, "artifact_count": len(decoded.artifacts)}
        cases.append(measure("worker_receipt_hash_roundtrip_signature_verify", {"artifacts": n}, receipt_op,
                             repeats=args.repeats, timeout_s=args.timeout_s))
    for n in workers:
        cases.append(measure("scheduler_select_and_measure", {"synthetic_node_records": n}, scheduler_case(n),
                             repeats=args.repeats, timeout_s=args.timeout_s))
    for n in observations:
        cases.append(measure("observation_chain_build_verify_serialize", {"observations": n}, lambda n=n: observation_case(n),
                             repeats=args.repeats, timeout_s=args.timeout_s))
    for n in dags:
        for shape in ("wide", "chain"):
            def plan_op(n=n, shape=shape):
                plan = make_plan(n, shape)
                ids = tuple(t.id for t in plan.tasks)
                ready, blocked = (ids, ()) if shape == "wide" else (ids[:1], ids[1:])
                snapshot = ReadyDagSnapshot(plan.graph_hash, (), ready, blocked, len(ready) / n, ())
                return {"plan_hash": plan.graph_hash, "snapshot_hash": snapshot.snapshot_hash}
            cases.append(measure("execution_plan_validate_hash_and_snapshot_hash", {"nodes": n, "shape": shape}, plan_op,
                                 repeats=args.repeats, timeout_s=args.timeout_s))
    for n in captures:
        cases.append(capture_case(n, args.timeout_s))
    document = {
        "schema_version": SCHEMA, "kind": "engineering-only", "confirmatory": False, "model_calls": 0,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": source_identity(),
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "cpu_count": os.cpu_count(), "clock": "perf_counter_ns"},
        "configuration": {"workers": workers, "observations": observations, "dag_nodes": dags,
                          "artifacts": artifacts, "capture_files": captures, "repeats": args.repeats,
                          "case_timeout_s": args.timeout_s},
        "cases": cases, "cost_arithmetic": cost_checks(), "routing_accounting_probe": routing_accounting_probe(),
        "chain_schema_audit": chain_schema_checks(),
        "unmeasured": [
            {"mechanism": "M4 verifier sandbox startup/output limits/verified snapshot/integration latency", "status": "BLOCKED pending #81 merge and qualified boundary"},
            {"mechanism": "simultaneously running 10/100/1000 workers or candidates", "status": "NOT RUN; scheduler node metadata only"},
            {"mechanism": "long receipt ancestry on EvidenceBus and durable 100k observation ingestion", "status": "NOT RUN; in-memory observation chains and plan DAGs measured separately"},
        ],
    }
    if args.review_refs:
        document["pinned_source_reviews"] = {"otx": review_otx(), "observability": review_observability(),
                                              "pr81": pr81_source_checks()}
    document["report_sha256"] = digest(document)
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, nargs="+", default=[10])
    parser.add_argument("--observations", type=int, nargs="+", default=[1000])
    parser.add_argument("--dag-nodes", type=int, nargs="+", default=[100])
    parser.add_argument("--artifacts", type=int, nargs="+", default=[10])
    parser.add_argument("--capture-files", type=int, nargs="+", default=[])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout-s", type=float, default=10.0)
    parser.add_argument("--review-refs", action="store_true", help="offline probes of pinned PR40/43 Git objects")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = run(args)
    except (ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        parser.exit(2, f"Engineering preparation failed: {type(exc).__name__}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Preserve every run; an existing result requires an explicitly different path.
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"{len(report['cases'])} engineering cases retained; no model calls")
    return 0 if all(case["status"] == "measured" for case in report["cases"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
