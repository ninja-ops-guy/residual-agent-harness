"""Heterogeneous/straggler remote-worker benchmark."""
from __future__ import annotations

import statistics
import tempfile
import threading
import time
from typing import Any

from residual.core import digest
from residual.station.server import Server
from residual.station.service import Station
from residual.station.worker import WorkerClient

from .distributed import SyntheticWorkerProvider, _station_spec


def _greedy_floor_ms(latencies_ms: tuple[float, ...], tasks: int) -> float:
    availability = [0.0 for _ in latencies_ms]
    for _ in range(tasks):
        index = min(range(len(availability)), key=lambda i: (availability[i], i))
        availability[index] += latencies_ms[index]
    return max(availability, default=0.0)


def _trial(*, latencies_ms: tuple[float, ...], tasks: int) -> dict[str, Any]:
    if not latencies_ms or any(value < 0 for value in latencies_ms):
        raise ValueError("latencies must be nonempty and nonnegative")
    with tempfile.TemporaryDirectory(prefix="residual-straggler-exp-") as tmp:
        station = Station(tmp)
        pid = station.create(_station_spec(tasks), demo=True)["project_id"]
        station.triage(pid)
        token = station.store.settings()["worker_token"]
        station.store.settings({"remote_workers_enabled": True})

        server = Server(("127.0.0.1", 0), station)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        url = f"http://127.0.0.1:{server.server_port}"

        barrier = threading.Barrier(len(latencies_ms) + 1)
        counts = [0] * len(latencies_ms)
        errors: list[str] = []

        def worker(index: int, work_ms: float):
            name = f"hetero-{index}"
            client = WorkerClient(url, token, worker_id=f"worker-hetero-{index}")
            provider = SyntheticWorkerProvider(work_ms)
            try:
                client.register(name, provider)
                barrier.wait()
                while client.run_once(pid, name, provider, max_tokens=256):
                    counts[index] += 1
            except Exception as exc:
                errors.append(f"{index}:{type(exc).__name__}")

        threads = [
            threading.Thread(target=worker, args=(index, latency), daemon=True)
            for index, latency in enumerate(latencies_ms)
        ]
        for thread in threads:
            thread.start()

        started = time.perf_counter_ns()
        barrier.wait()
        for thread in threads:
            thread.join(timeout=max(30.0, tasks * (max(latencies_ms) / 1000.0 + 2.0)))
        candidate_done = time.perf_counter_ns()

        try:
            if any(thread.is_alive() for thread in threads):
                raise RuntimeError("heterogeneous worker thread did not terminate")
            if errors:
                raise RuntimeError(f"heterogeneous worker errors: {errors}")
            project = station.store.project(pid)
            if any(task["state"] != "review_ready" for task in project["tasks"]):
                raise RuntimeError("heterogeneous candidate phase incomplete")

            for task in project["tasks"]:
                station.review(pid, task["id"])
                station.integrate(pid, task["id"])
            ended = time.perf_counter_ns()

            metrics = station.worker_metrics(pid)
            if len(metrics["instances"]) != len(latencies_ms):
                raise RuntimeError("not every configured heterogeneous worker registered")

            candidate_ms = (candidate_done - started) / 1_000_000.0
            full_ms = (ended - started) / 1_000_000.0
            floor = _greedy_floor_ms(latencies_ms, tasks)
            fastest = min(range(len(latencies_ms)), key=lambda i: (latencies_ms[i], i))
            slowest = max(range(len(latencies_ms)), key=lambda i: (latencies_ms[i], i))
            return {
                "latencies_ms": list(latencies_ms),
                "workers": len(latencies_ms),
                "tasks": tasks,
                "candidate_wall_ms": candidate_ms,
                "full_workflow_ms": full_ms,
                "greedy_synthetic_floor_ms": floor,
                "candidate_overhead_above_floor_ms": candidate_ms - floor,
                "distribution": {
                    f"hetero-{index}": {
                        "configured_latency_ms": latencies_ms[index],
                        "tasks": counts[index],
                    }
                    for index in range(len(latencies_ms))
                },
                "registered_worker_instances": len(metrics["instances"]),
                "workers_used": sum(1 for value in counts if value),
                "fastest_worker_task_share": counts[fastest] / tasks,
                "slowest_worker_task_share": counts[slowest] / tasks,
                "all_integrated": all(
                    task["state"] == "integrated"
                    for task in station.store.project(pid)["tasks"]
                ),
                "worker_inference_elapsed_ms": metrics["totals"]["inference_elapsed_ms"],
            }
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=5)


def run_straggler_benchmark(
    *,
    latencies_ms: tuple[float, ...] = (20.0, 20.0, 200.0),
    tasks: int = 12,
    repeats: int = 3,
) -> dict[str, Any]:
    if not latencies_ms or len(latencies_ms) > 16:
        raise ValueError("latencies must define 1..16 workers")
    if any(value < 0 for value in latencies_ms) or not 1 <= tasks <= 32 or repeats < 1:
        raise ValueError("invalid straggler benchmark bounds")

    runs = []
    for repeat in range(repeats):
        row = _trial(latencies_ms=latencies_ms, tasks=tasks)
        row["repeat"] = repeat
        runs.append(row)

    summary = {
        "candidate_wall_median_ms": statistics.median(row["candidate_wall_ms"] for row in runs),
        "full_workflow_median_ms": statistics.median(row["full_workflow_ms"] for row in runs),
        "greedy_synthetic_floor_ms": _greedy_floor_ms(latencies_ms, tasks),
        "candidate_overhead_above_floor_median_ms": statistics.median(
            row["candidate_overhead_above_floor_ms"] for row in runs
        ),
        "fastest_worker_task_share_median": statistics.median(
            row["fastest_worker_task_share"] for row in runs
        ),
        "slowest_worker_task_share_median": statistics.median(
            row["slowest_worker_task_share"] for row in runs
        ),
        "registered_worker_instances_min": min(row["registered_worker_instances"] for row in runs),
        "workers_used_min": min(row["workers_used"] for row in runs),
        "all_integrated": all(row["all_integrated"] for row in runs),
    }
    config = {
        "latencies_ms": list(latencies_ms),
        "tasks": tasks,
        "repeats": repeats,
    }
    return {
        "schema_version": "residual.distributed-straggler-experiment.v1",
        "kind": "station-heterogeneous-workers",
        "evidence_level": "development_fixture",
        "simulation": True,
        "configuration": config,
        "runs": runs,
        "summary": summary,
        "claim_boundary": (
            "Every configured worker is a real Station WorkerClient and remote-worker "
            "protocol participant, but per-worker provider time is a controlled synthetic "
            "delay and transport is loopback HTTP. Task-share differences are observations, "
            "not assumptions about physical or live-model scheduling."
        ),
        "benchmark_hash": digest(config),
    }
