"""Dependency-aware distributed Station pipeline benchmark."""
from __future__ import annotations

import json
import math
import statistics
import tempfile
import threading
import time
from typing import Any

from residual.core import canonical, digest
from residual.providers import Reply, Usage
from residual.station.server import Server
from residual.station.service import Station
from residual.station.worker import WorkerClient


class PipelineProvider:
    placement = "local"
    model = "synthetic-pipeline-v1"

    def __init__(self, work_ms: float):
        self.work_ms = float(work_ms)

    def wire_size(self, packet: dict, max_tokens: int) -> int:
        return len(canonical({"packet": packet, "max_tokens": max_tokens}).encode())

    def generate(self, packet: dict, max_output_tokens: int) -> Reply:
        if self.work_ms:
            time.sleep(self.work_ms / 1000.0)
        task_id = packet["task_id"]
        return Reply(
            canonical({"files": {
                path: f"PIPELINE {task_id}\n"
                for path in packet["writable_files"]
            }}),
            Usage(input_tokens=8, output_tokens=4, source="reported"),
            elapsed_ms=self.work_ms,
            finish_reason="stop",
        )


def _spec(width: int, depth: int) -> str:
    if not 1 <= width <= 8 or not 1 <= depth <= 8 or width * depth > 32:
        raise ValueError("pipeline width/depth exceeds fixture bounds")
    tasks = []
    for layer in range(depth):
        for lane in range(width):
            task_id = f"PIPE-{layer + 1:02d}-{lane + 1:02d}"
            path = f"pipeline/l{layer + 1:02d}_n{lane + 1:02d}.txt"
            depends = [] if layer == 0 else [f"PIPE-{layer:02d}-{lane + 1:02d}"]
            tasks.append({
                "id": task_id,
                "title": f"Pipeline layer {layer + 1} lane {lane + 1}",
                "instruction": f"Write deterministic output for {task_id}.",
                "files": [path],
                "context": [],
                "depends_on": depends,
                "route": "local",
                "checks": [
                    {"kind": "exists", "path": path},
                    {"kind": "contains", "path": path, "text": f"PIPELINE {task_id}"},
                ],
            })
    manifest = {
        "schema_version": 1,
        "name": "Distributed dependency pipeline",
        "goal": "Measure distributed workers across dependency-gated integration waves.",
        "tasks": tasks,
    }
    fence = chr(96) * 3
    return "# Distributed dependency pipeline\n\n" + fence + "json\n" + json.dumps(manifest) + "\n" + fence + "\n"


def _trial(*, workers: int, width: int, depth: int, work_ms: float) -> dict[str, Any]:
    if not 1 <= workers <= 16:
        raise ValueError("workers must be 1..16")
    task_count = width * depth
    with tempfile.TemporaryDirectory(prefix="residual-pipeline-exp-") as tmp:
        station = Station(tmp)
        pid = station.create(_spec(width, depth), demo=True)["project_id"]
        station.triage(pid)
        settings = station.store.settings()
        station.store.settings({"remote_workers_enabled": True})
        token = settings["worker_token"]

        server = Server(("127.0.0.1", 0), station)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        url = f"http://127.0.0.1:{server.server_port}"

        barrier = threading.Barrier(workers + 2)
        stop = threading.Event()
        worker_counts = [0] * workers
        worker_errors: list[str] = []
        integration_errors: list[str] = []
        integrated_at: dict[str, float] = {}

        def done() -> bool:
            return all(t["state"] == "integrated" for t in station.store.project(pid)["tasks"])

        def worker_loop(index: int):
            client = WorkerClient(url, token)
            provider = PipelineProvider(work_ms)
            barrier.wait()
            idle = 0
            while not stop.is_set():
                try:
                    worked = client.run_once(pid, f"pipeline-{index}", provider, max_tokens=256)
                except Exception as exc:
                    worker_errors.append(type(exc).__name__)
                    stop.set()
                    return
                if worked:
                    worker_counts[index] += 1
                    idle = 0
                    continue
                if done():
                    return
                idle += 1
                if idle > 10000:
                    worker_errors.append("WorkerStalled")
                    stop.set()
                    return
                time.sleep(0.005)

        def coordinator():
            barrier.wait()
            while not stop.is_set():
                if done():
                    return
                progressed = False
                for task in station.store.project(pid)["tasks"]:
                    if task["state"] != "review_ready":
                        continue
                    try:
                        station.review(pid, task["id"])
                        station.integrate(pid, task["id"])
                        integrated_at[task["id"]] = time.perf_counter()
                        progressed = True
                    except Exception as exc:
                        integration_errors.append(type(exc).__name__)
                        stop.set()
                        return
                if not progressed:
                    time.sleep(0.003)

        worker_threads = [
            threading.Thread(target=worker_loop, args=(index,), daemon=True)
            for index in range(workers)
        ]
        coordinator_thread = threading.Thread(target=coordinator, daemon=True)
        for thread in worker_threads:
            thread.start()
        coordinator_thread.start()

        started = time.perf_counter()
        barrier.wait()
        timeout = max(30.0, task_count * (work_ms / 1000.0 + 2.0))
        coordinator_thread.join(timeout=timeout)
        for thread in worker_threads:
            thread.join(timeout=5)
        ended = time.perf_counter()
        stop.set()

        try:
            if coordinator_thread.is_alive() or any(t.is_alive() for t in worker_threads):
                raise RuntimeError("pipeline experiment did not terminate")
            if worker_errors or integration_errors:
                raise RuntimeError(f"pipeline errors: workers={worker_errors}, integration={integration_errors}")
            project = station.store.project(pid)
            if any(task["state"] != "integrated" for task in project["tasks"]):
                raise RuntimeError("pipeline did not integrate every task")
            wall_ms = (ended - started) * 1000.0
            events = station.store.events(pid, 0, 100000)
            return {
                "workers": workers,
                "width": width,
                "depth": depth,
                "tasks": task_count,
                "work_ms": work_ms,
                "wall_ms": wall_ms,
                "throughput_tasks_s": task_count / (wall_ms / 1000.0),
                "worker_distribution": {
                    f"pipeline-{index}": count for index, count in enumerate(worker_counts)
                },
                "workers_used": sum(1 for count in worker_counts if count),
                "all_integrated": True,
                "integration_count": sum(
                    event["event_type"] == "integration.completed" for event in events
                ),
                "event_head": events[-1]["hash"] if events else None,
                "reported_worker_calls": station.metrics(pid)["calls"],
                "critical_path_work_ms": depth * work_ms,
                "serial_worker_work_ms": task_count * work_ms,
                "synthetic_scheduling_lower_bound_ms": max(depth, math.ceil(task_count / workers)) * work_ms,
                "observed_overhead_above_synthetic_floor_ms": wall_ms - (max(depth, math.ceil(task_count / workers)) * work_ms),
            }
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=5)


def run_station_pipeline_benchmark(
    *,
    worker_counts: tuple[int, ...] = (1, 2, 4),
    width: int = 4,
    depth: int = 2,
    work_ms: float = 40.0,
    repeats: int = 1,
) -> dict[str, Any]:
    if not worker_counts or len(worker_counts) != len(set(worker_counts)):
        raise ValueError("worker_counts must be unique and nonempty")
    if repeats < 1:
        raise ValueError("repeats must be positive")
    runs = []
    for workers in worker_counts:
        for repeat in range(repeats):
            row = _trial(
                workers=workers, width=width, depth=depth, work_ms=work_ms
            )
            row["repeat"] = repeat
            runs.append(row)

    baseline_workers = min(worker_counts)
    baseline = statistics.median(
        row["wall_ms"] for row in runs if row["workers"] == baseline_workers
    )
    summary = []
    for workers in worker_counts:
        group = [row for row in runs if row["workers"] == workers]
        wall = statistics.median(row["wall_ms"] for row in group)
        speedup = baseline / wall if wall else 0.0
        worker_multiplier = workers / baseline_workers
        summary.append({
            "workers": workers,
            "relative_worker_multiplier": worker_multiplier,
            "wall_median_ms": wall,
            "speedup_vs_min_workers": speedup,
            "parallel_efficiency": speedup / worker_multiplier,
            "throughput_median_tasks_s": statistics.median(
                row["throughput_tasks_s"] for row in group
            ),
            "observed_overhead_above_synthetic_floor_median_ms": statistics.median(
                row["observed_overhead_above_synthetic_floor_ms"] for row in group
            ),
            "workers_used_min": min(row["workers_used"] for row in group),
            "all_integrated": all(row["all_integrated"] for row in group),
        })

    return {
        "schema_version": "residual.distributed-pipeline-experiment.v1",
        "kind": "station-dependency-pipeline",
        "evidence_level": "development_fixture",
        "simulation": True,
        "workload": {
            "width": width,
            "depth": depth,
            "tasks": width * depth,
            "synthetic_worker_latency_ms": work_ms,
            "worker_counts": list(worker_counts),
            "repeats": repeats,
        },
        "runs": runs,
        "summary": summary,
        "claim_boundary": (
            "Exercises the real Station HTTP worker lease/submit path while a real "
            "coordinator reviews and integrates completed prerequisites to unlock "
            "later DAG waves. Model work is a synthetic delay and all nodes are "
            "loopback threads, so physical distributed scaling is not claimed."
        ),
        "benchmark_hash": digest({
            "kind": "station-dependency-pipeline",
            "width": width,
            "depth": depth,
            "work_ms": work_ms,
            "workers": list(worker_counts),
            "repeats": repeats,
        }),
    }
