"""Experimental distributed-workflow and mesh-protocol benchmarks.

The Station benchmark exercises the real loopback HTTP worker API, task leasing,
candidate Git worktrees, deterministic checks, scripted demo review, and sequential
integration. The worker provider is synthetic and sleeps to model inference work;
therefore this is development evidence, not a live-model or physical-network claim.

The mesh benchmark measures the in-process signed/hash-chained protocol and verified
history catch-up. It does not establish WAN/LAN transport performance.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import statistics
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from residual.core import ContractError, canonical, digest
from residual.mesh import MeshIdentity, MeshMessageKind, MeshNode, MeshSession
from residual.providers import Reply, Usage
from residual.station.server import Server
from residual.station.service import Station
from residual.station.worker import WorkerClient
from residual.cluster import Capability, ClusterNode, LoopbackTransport
from residual.experiments.pipeline import run_station_pipeline_benchmark
from residual.experiments.recovery import run_station_recovery_benchmark


SCHEMA = "residual.distributed-experiment.v1"


class SyntheticWorkerProvider:
    """Deterministic remote-worker fixture with controllable work latency."""

    placement = "local"
    model = "synthetic-worker-v1"

    def __init__(self, work_ms: float):
        if work_ms < 0:
            raise ValueError("work_ms must be nonnegative")
        self.work_ms = float(work_ms)

    def wire_size(self, packet: dict, max_tokens: int) -> int:
        return len(canonical({"packet": packet, "max_tokens": max_tokens}).encode())

    def generate(self, packet: dict, max_output_tokens: int) -> Reply:
        if self.work_ms:
            time.sleep(self.work_ms / 1000.0)
        task_id = packet["task_id"]
        files = {
            path: f"RESULT {task_id}\n"
            for path in packet["writable_files"]
        }
        return Reply(
            canonical({"files": files}),
            Usage(input_tokens=8, output_tokens=4, source="reported"),
            elapsed_ms=self.work_ms,
            finish_reason="stop",
        )


def _station_spec(task_count: int) -> str:
    if not 1 <= task_count <= 32:
        raise ValueError("task_count must be 1..32")
    tasks = []
    for index in range(task_count):
        task_id = f"EXP-{index + 1:03d}"
        path = f"bench/task_{index + 1:03d}.txt"
        tasks.append({
            "id": task_id,
            "title": f"Distributed fixture {index + 1}",
            "instruction": f"Write the deterministic result for {task_id}.",
            "files": [path],
            "context": [],
            "depends_on": [],
            "route": "local",
            "checks": [
                {"kind": "exists", "path": path},
                {"kind": "contains", "path": path, "text": f"RESULT {task_id}"},
            ],
        })
    manifest = {
        "schema_version": 1,
        "name": "Distributed worker benchmark",
        "goal": "Measure real Station worker orchestration with synthetic inference latency.",
        "tasks": tasks,
    }
    fence = chr(96) * 3
    return "# Distributed worker benchmark\n\n" + fence + "json\n" + json.dumps(manifest) + "\n" + fence + "\n"


def _trial(*, workers: int, tasks: int, work_ms: float) -> dict[str, Any]:
    if not 1 <= workers <= 16:
        raise ValueError("workers must be 1..16")
    with tempfile.TemporaryDirectory(prefix="residual-distributed-exp-") as tmp:
        station = Station(tmp)
        pid = station.create(_station_spec(tasks), demo=True)["project_id"]
        station.triage(pid)
        settings = station.store.settings()
        token = settings["worker_token"]
        station.store.settings({"remote_workers_enabled": True})

        server = Server(("127.0.0.1", 0), station)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}"

        barrier = threading.Barrier(workers + 1)
        counts = [0 for _ in range(workers)]
        errors: list[str] = []

        def run_worker(index: int) -> None:
            client = WorkerClient(url, token)
            provider = SyntheticWorkerProvider(work_ms)
            barrier.wait()
            try:
                while client.run_once(pid, f"bench-{index}", provider, max_tokens=256):
                    counts[index] += 1
            except Exception as exc:
                errors.append(type(exc).__name__)

        threads = [
            threading.Thread(target=run_worker, args=(index,), daemon=True)
            for index in range(workers)
        ]
        for worker in threads:
            worker.start()

        candidate_started = time.perf_counter_ns()
        barrier.wait()
        for worker in threads:
            worker.join(timeout=max(30.0, tasks * (work_ms / 1000.0 + 2.0)))
        candidate_finished = time.perf_counter_ns()

        try:
            if any(worker.is_alive() for worker in threads):
                raise RuntimeError("worker thread did not terminate")
            if errors:
                raise RuntimeError(f"worker errors: {errors}")
            project = station.store.project(pid)
            states = {task["id"]: task["state"] for task in project["tasks"]}
            if set(states.values()) != {"review_ready"}:
                raise RuntimeError(f"candidate phase incomplete: {states}")

            integration_started = time.perf_counter_ns()
            for task in station.store.project(pid)["tasks"]:
                station.review(pid, task["id"])
                station.integrate(pid, task["id"])
            integration_finished = time.perf_counter_ns()

            project = station.store.project(pid)
            if any(task["state"] != "integrated" for task in project["tasks"]):
                raise RuntimeError("full distributed workflow did not integrate")
            worker_metrics = station.worker_metrics(pid)
            events = station.store.events(pid, 0, 100000)
            candidate_ms = (candidate_finished - candidate_started) / 1_000_000.0
            integration_ms = (integration_finished - integration_started) / 1_000_000.0
            total_ms = candidate_ms + integration_ms
            distribution = {f"bench-{i}": counts[i] for i in range(workers)}
            return {
                "workers": workers,
                "tasks": tasks,
                "work_ms": work_ms,
                "candidate_wall_ms": candidate_ms,
                "integration_tail_ms": integration_ms,
                "full_workflow_ms": total_ms,
                "candidate_throughput_tasks_s": tasks / (candidate_ms / 1000.0),
                "synthetic_scheduling_lower_bound_ms": math.ceil(tasks / workers) * work_ms,
                "candidate_overhead_above_synthetic_floor_ms": candidate_ms - (math.ceil(tasks / workers) * work_ms),
                "worker_distribution": distribution,
                "workers_used": sum(1 for value in counts if value),
                "events": len(events),
                "event_head": events[-1]["hash"] if events else None,
                "all_integrated": True,
                "reported_worker_calls": station.metrics(pid)["calls"],
                "registered_worker_instances": len(worker_metrics["instances"]),
                "worker_inference_elapsed_ms": worker_metrics["totals"]["inference_elapsed_ms"],
                "project_id": pid,
            }
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def run_station_distributed_benchmark(
    *,
    worker_counts: tuple[int, ...] = (1, 2, 4),
    tasks: int = 8,
    work_ms: float = 40.0,
    repeats: int = 1,
) -> dict[str, Any]:
    if not worker_counts or len(set(worker_counts)) != len(worker_counts):
        raise ValueError("worker_counts must be unique and nonempty")
    if repeats < 1:
        raise ValueError("repeats must be positive")

    runs = []
    for workers in worker_counts:
        for repeat in range(repeats):
            result = _trial(workers=workers, tasks=tasks, work_ms=work_ms)
            result["repeat"] = repeat
            runs.append(result)

    summaries = []
    baseline_workers = min(worker_counts)
    baseline_runs = [r for r in runs if r["workers"] == baseline_workers]
    baseline_candidate = statistics.median(r["candidate_wall_ms"] for r in baseline_runs)
    baseline_full = statistics.median(r["full_workflow_ms"] for r in baseline_runs)
    for workers in worker_counts:
        group = [r for r in runs if r["workers"] == workers]
        candidate = statistics.median(r["candidate_wall_ms"] for r in group)
        full = statistics.median(r["full_workflow_ms"] for r in group)
        candidate_speedup = baseline_candidate / candidate if candidate else 0.0
        full_speedup = baseline_full / full if full else 0.0
        worker_multiplier = workers / baseline_workers
        summaries.append({
            "workers": workers,
            "relative_worker_multiplier": worker_multiplier,
            "candidate_wall_median_ms": candidate,
            "full_workflow_median_ms": full,
            "candidate_speedup_vs_min_workers": candidate_speedup,
            "full_workflow_speedup_vs_min_workers": full_speedup,
            "candidate_parallel_efficiency": candidate_speedup / worker_multiplier,
            "full_workflow_parallel_efficiency": full_speedup / worker_multiplier,
            "integration_tail_fraction": statistics.median(
                r["integration_tail_ms"] / r["full_workflow_ms"] for r in group
            ),
            "candidate_overhead_above_synthetic_floor_median_ms": statistics.median(
                r["candidate_overhead_above_synthetic_floor_ms"] for r in group
            ),
            "candidate_throughput_median_tasks_s": statistics.median(
                r["candidate_throughput_tasks_s"] for r in group
            ),
            "workers_used_min": min(r["workers_used"] for r in group),
            "registered_worker_instances_min": min(r["registered_worker_instances"] for r in group),
            "worker_inference_elapsed_median_ms": statistics.median(r["worker_inference_elapsed_ms"] for r in group),
            "all_integrated": all(r["all_integrated"] for r in group),
        })

    return {
        "schema_version": SCHEMA,
        "kind": "station-distributed-worker",
        "evidence_level": "development_fixture",
        "simulation": True,
        "workload": {
            "tasks": tasks,
            "synthetic_worker_latency_ms": work_ms,
            "worker_counts": list(worker_counts),
            "repeats": repeats,
        },
        "runs": runs,
        "summary": summaries,
        "claim_boundary": (
            "Uses the real Station HTTP worker API, leases, candidate Git worktrees, "
            "deterministic checks, scripted demo review, and integration. Worker "
            "inference latency is synthetic and all workers are loopback threads; "
            "this does not establish physical-network or live-model scaling."
        ),
        "benchmark_hash": digest({
            "kind": "station-distributed-worker",
            "tasks": tasks,
            "work_ms": work_ms,
            "worker_counts": list(worker_counts),
            "repeats": repeats,
        }),
    }


def _mesh_pair():
    key_a = hashlib.sha256(b"a").digest()
    key_b = hashlib.sha256(b"b").digest()
    keys = {"pk-a": key_a, "pk-b": key_b}

    def sign(key):
        return lambda data: hmac.new(key, data, hashlib.sha256).hexdigest()

    def verify(public_key, data, signature):
        key = keys.get(public_key)
        return bool(key) and hmac.compare_digest(
            hmac.new(key, data, hashlib.sha256).hexdigest(), signature
        )

    now = time.time_ns()
    a = MeshNode(MeshIdentity("dev-a", "A", "pk-a", ("chat",), "loopback://a", now), sign(key_a), verify)
    b = MeshNode(MeshIdentity("dev-b", "B", "pk-b", ("chat",), "loopback://b", now), sign(key_b), verify)
    a.connect_peer(b.identity)
    b.connect_peer(a.identity)
    return a, b


def run_mesh_protocol_benchmark(*, messages: int = 1000, repeats: int = 3, peers: int = 4) -> dict[str, Any]:
    if not 1 <= messages <= 10000 or repeats < 1 or not 2 <= peers <= 16:
        raise ValueError("invalid mesh benchmark bounds")
    runs = []
    for repeat in range(repeats):
        a, b = _mesh_pair()
        started = time.perf_counter_ns()
        for index in range(messages):
            a.send_message(MeshMessageKind.CHAT, content=f"message-{index}")
        produced = time.perf_counter_ns()
        appended = b.sync_history(a.chat.messages)
        synced = time.perf_counter_ns()
        if appended != messages or not a.chat.verify() or not b.chat.verify() or a.chat.head_hash != b.chat.head_hash:
            raise RuntimeError("mesh benchmark integrity failure")
        produce_ms = (produced - started) / 1_000_000.0
        sync_ms = (synced - produced) / 1_000_000.0
        runs.append({
            "repeat": repeat,
            "messages": messages,
            "produce_ms": produce_ms,
            "verified_catchup_ms": sync_ms,
            "produce_messages_s": messages / (produce_ms / 1000.0),
            "catchup_messages_s": messages / (sync_ms / 1000.0),
            "head_hash": a.chat.head_hash,
        })

    keys = {f"pk-{index}": hashlib.sha256(f"peer-{index}".encode()).digest() for index in range(peers)}
    def session_verify(public_key, data, signature):
        key = keys.get(public_key)
        return bool(key) and hmac.compare_digest(
            hmac.new(key, data, hashlib.sha256).hexdigest(), signature
        )
    session = MeshSession("benchmark-room")
    session_nodes = []
    for index in range(peers):
        key = keys[f"pk-{index}"]
        member = MeshNode(
            MeshIdentity(
                f"dev-{index}", f"P{index}", f"pk-{index}", ("chat",),
                f"loopback://peer-{index}", time.time_ns(),
            ),
            lambda data, key=key: hmac.new(key, data, hashlib.sha256).hexdigest(),
            session_verify,
        )
        session.join(member)
        session_nodes.append(member)
    fanout_started = time.perf_counter_ns()
    for index in range(messages):
        _, receipt = session.chat("dev-0", f"fanout-{index}")
        if not receipt.converged:
            raise RuntimeError("mesh fanout benchmark diverged")
    fanout_ms = (time.perf_counter_ns() - fanout_started) / 1_000_000.0
    fanout_remote_deliveries = messages * (peers - 1)
    fanout_replica_updates = messages * peers

    LoopbackTransport.reset_registry()
    a = ClusterNode("a", Capability(models=("fixture",), tokens_per_second=1.0), "key")
    b = ClusterNode("b", Capability(models=("fixture",), tokens_per_second=1.0), "key")
    a.open(); b.open()
    try:
        join_started = time.perf_counter_ns()
        joined = b.join(bootstrap_address=a.address)
        join_ms = (time.perf_counter_ns() - join_started) / 1_000_000.0
        if not joined["joined"]:
            raise RuntimeError("cluster join benchmark failed")
    finally:
        a.close(); b.close(); LoopbackTransport.reset_registry()

    return {
        "schema_version": SCHEMA,
        "kind": "mesh-protocol",
        "evidence_level": "development_fixture",
        "simulation": False,
        "messages": messages,
        "repeats": repeats,
        "peers": peers,
        "runs": runs,
        "summary": {
            "produce_median_messages_s": statistics.median(r["produce_messages_s"] for r in runs),
            "catchup_median_messages_s": statistics.median(r["catchup_messages_s"] for r in runs),
            "verified_join_ms": join_ms,
            "fanout_ms": fanout_ms,
            "fanout_remote_deliveries_s": fanout_remote_deliveries / (fanout_ms / 1000.0),
            "fanout_replica_updates_s": fanout_replica_updates / (fanout_ms / 1000.0),
        },
        "claim_boundary": (
            "Measures real in-process signing, hashing, append, catch-up verification, "
            "and loopback JOIN/JOIN_ACK. It does not measure mDNS, physical LAN, WAN "
            "relay, encryption/rekeying, or divergent-history consensus."
        ),
        "benchmark_hash": digest({
            "kind": "mesh-protocol", "messages": messages, "repeats": repeats, "peers": peers
        }),
    }


def _write(path: str | None, value: dict) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(payload, encoding="utf-8")
    print(payload, end="")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="residual experiment", description="Run RESIDUAL development experiments")
    sub = parser.add_subparsers(dest="experiment", required=True)

    distributed = sub.add_parser("distributed", help="Benchmark real Station remote-worker orchestration")
    distributed.add_argument("--workers", nargs="+", type=int, default=[1, 2, 4])
    distributed.add_argument("--tasks", type=int, default=8)
    distributed.add_argument("--work-ms", type=float, default=40.0)
    distributed.add_argument("--repeats", type=int, default=1)
    distributed.add_argument("--output")

    pipeline = sub.add_parser("pipeline", help="Benchmark dependency-gated distributed Station workflows")
    pipeline.add_argument("--workers", nargs="+", type=int, default=[1, 2, 4])
    pipeline.add_argument("--width", type=int, default=4)
    pipeline.add_argument("--depth", type=int, default=2)
    pipeline.add_argument("--work-ms", type=float, default=40.0)
    pipeline.add_argument("--repeats", type=int, default=1)
    pipeline.add_argument("--output")

    bridge = sub.add_parser("bridge", help="Benchmark Station-to-mesh observability fanout")
    bridge.add_argument("--members", nargs="+", type=int, default=[2, 4, 8])
    bridge.add_argument("--repeats", type=int, default=3)
    bridge.add_argument("--output")

    matrix = sub.add_parser("matrix", help="Sweep worker counts and synthetic inference latencies")
    matrix.add_argument("--workers", nargs="+", type=int, default=[1, 2, 4])
    matrix.add_argument("--latencies-ms", nargs="+", type=float, default=[0.0, 40.0, 200.0])
    matrix.add_argument("--tasks", type=int, default=8)
    matrix.add_argument("--pipeline-width", type=int, default=4)
    matrix.add_argument("--pipeline-depth", type=int, default=2)
    matrix.add_argument("--repeats", type=int, default=1)
    matrix.add_argument("--no-recovery", action="store_true")
    matrix.add_argument("--output")

    lease = sub.add_parser("lease-recovery", help="Benchmark expired-lease recovery and stale-result rejection")
    lease.add_argument("--work-ms", type=float, default=40.0)
    lease.add_argument("--repeats", type=int, default=3)
    lease.add_argument("--output")

    recovery = sub.add_parser("recovery", help="Benchmark fail-closed remote-worker repair recovery")
    recovery.add_argument("--bad-ms", type=float, default=20.0)
    recovery.add_argument("--good-ms", type=float, default=40.0)
    recovery.add_argument("--repeats", type=int, default=3)
    recovery.add_argument("--output")

    straggler = sub.add_parser("straggler", help="Benchmark heterogeneous and straggling distributed workers")
    straggler.add_argument("--latencies-ms", nargs="+", type=float, default=[20.0, 20.0, 200.0])
    straggler.add_argument("--tasks", type=int, default=12)
    straggler.add_argument("--repeats", type=int, default=3)
    straggler.add_argument("--output")

    mesh = sub.add_parser("mesh", help="Benchmark signed mesh history and cluster join")
    mesh.add_argument("--messages", type=int, default=1000)
    mesh.add_argument("--repeats", type=int, default=3)
    mesh.add_argument("--peers", type=int, default=4)
    mesh.add_argument("--output")

    args = parser.parse_args(argv)
    try:
        if args.experiment == "distributed":
            report = run_station_distributed_benchmark(
                worker_counts=tuple(args.workers),
                tasks=args.tasks,
                work_ms=args.work_ms,
                repeats=args.repeats,
            )
        elif args.experiment == "pipeline":
            report = run_station_pipeline_benchmark(
                worker_counts=tuple(args.workers),
                width=args.width,
                depth=args.depth,
                work_ms=args.work_ms,
                repeats=args.repeats,
            )
        elif args.experiment == "bridge":
            from residual.experiments.bridge import run_station_mesh_bridge_benchmark
            report = run_station_mesh_bridge_benchmark(
                member_counts=tuple(args.members),
                repeats=args.repeats,
            )
        elif args.experiment == "matrix":
            from residual.experiments.matrix import run_experiment_matrix
            report = run_experiment_matrix(
                worker_counts=tuple(args.workers),
                latencies_ms=tuple(args.latencies_ms),
                independent_tasks=args.tasks,
                pipeline_width=args.pipeline_width,
                pipeline_depth=args.pipeline_depth,
                repeats=args.repeats,
                include_recovery=not args.no_recovery,
            )
        elif args.experiment == "lease-recovery":
            from residual.experiments.lease_recovery import run_station_lease_recovery_benchmark
            report = run_station_lease_recovery_benchmark(
                work_ms=args.work_ms,
                repeats=args.repeats,
            )
        elif args.experiment == "recovery":
            report = run_station_recovery_benchmark(
                bad_ms=args.bad_ms,
                good_ms=args.good_ms,
                repeats=args.repeats,
            )
        elif args.experiment == "straggler":
            from residual.experiments.straggler import run_straggler_benchmark
            report = run_straggler_benchmark(
                latencies_ms=tuple(args.latencies_ms),
                tasks=args.tasks,
                repeats=args.repeats,
            )
        else:
            report = run_mesh_protocol_benchmark(messages=args.messages, repeats=args.repeats, peers=args.peers)
        _write(args.output, report)
        return 0
    except (ContractError, OSError, ValueError, RuntimeError) as exc:
        import sys
        print(f"residual experiment: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
