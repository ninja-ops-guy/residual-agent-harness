"""Controlled lease-expiry and stale-result recovery benchmark.

The experiment claims a task through the real remote-worker API, fault-injects an
expired lease in Station state instead of waiting 15 minutes, runs the real recovery
path, proves the stale worker result is rejected, re-triages the blocked task, and
allows a healthy worker to reclaim, verify, review and integrate it.

Only the passage of time is injected. Lease validation, worker.expired admission,
stale-result rejection, triage, remote worker submission and integration are real.
"""
from __future__ import annotations

import json
import statistics
import tempfile
import threading
import time
import urllib.error
import uuid
from typing import Any

from residual.core import canonical, digest
from residual.providers import Reply, Usage
from residual.station.server import Server
from residual.station.service import Station
from residual.station.worker import WorkerClient


class LeaseHealthyProvider:
    placement = "local"
    model = "synthetic-lease-recovery-v1"

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
                path: f"LEASE RECOVERED {task_id}\n"
                for path in packet["writable_files"]
            }}),
            Usage(input_tokens=9, output_tokens=5, source="reported"),
            elapsed_ms=self.work_ms,
            finish_reason="stop",
        )


def _spec() -> str:
    manifest = {
        "schema_version": 1,
        "name": "Distributed lease recovery benchmark",
        "goal": "Measure stale-worker rejection and healthy-worker reclamation.",
        "tasks": [{
            "id": "LEASE-001",
            "title": "Recover an expired remote lease",
            "instruction": "Write the deterministic recovered result.",
            "files": ["lease/result.txt"],
            "context": [],
            "depends_on": [],
            "route": "local",
            "checks": [
                {"kind": "exists", "path": "lease/result.txt"},
                {"kind": "contains", "path": "lease/result.txt", "text": "LEASE RECOVERED LEASE-001"},
            ],
        }],
    }
    fence = chr(96) * 3
    return "# Distributed lease recovery benchmark\n\n" + fence + "json\n" + json.dumps(manifest) + "\n" + fence + "\n"


def _station(tmp: str):
    station = Station(tmp)
    pid = station.create(_spec(), demo=True)["project_id"]
    station.triage(pid)
    station.store.settings({"remote_workers_enabled": True})
    token = station.store.settings()["worker_token"]
    server = Server(("127.0.0.1", 0), station)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return station, pid, token, server, thread, f"http://127.0.0.1:{server.server_port}"


def _close(server, thread):
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def _baseline(work_ms: float) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="residual-lease-baseline-") as tmp:
        station, pid, token, server, thread, url = _station(tmp)
        try:
            client = WorkerClient(url, token)
            started = time.perf_counter_ns()
            if not client.run_once(pid, "healthy-baseline", LeaseHealthyProvider(work_ms), max_tokens=256):
                raise RuntimeError("baseline worker did not claim task")
            candidate = time.perf_counter_ns()
            task = station.store.project(pid)["tasks"][0]
            station.review(pid, task["id"])
            station.integrate(pid, task["id"])
            ended = time.perf_counter_ns()
            return {
                "candidate_ms": (candidate - started) / 1_000_000.0,
                "full_ms": (ended - started) / 1_000_000.0,
                "attempts": station.store.project(pid)["tasks"][0]["attempt"],
                "worker_metrics": station.worker_metrics(pid),
            }
        finally:
            _close(server, thread)


def _expire_task(station: Station, pid: str, task_id: str) -> None:
    """Fault injection: move only lease_until into the past."""
    with station.store.transaction() as connection:
        row = connection.execute(
            "SELECT value FROM tasks WHERE project=? AND id=?",
            (pid, task_id),
        ).fetchone()
        if row is None:
            raise RuntimeError("task disappeared before lease injection")
        task = json.loads(row[0])
        if task["state"] != "running":
            raise RuntimeError("lease injection requires a running task")
        task["lease_until"] = time.time() - 1.0
        connection.execute(
            "UPDATE tasks SET value=? WHERE project=? AND id=?",
            (canonical(task), pid, task_id),
        )


def _trial(work_ms: float) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="residual-lease-recovery-") as tmp:
        station, pid, token, server, thread, url = _station(tmp)
        try:
            crashed = WorkerClient(url, token)
            healthy = WorkerClient(url, token)

            started = time.perf_counter_ns()
            work = crashed.request("claim", {
                "project_id": pid,
                "task_id": "LEASE-001",
                "name": "crashed-worker",
            })["work"]
            claimed = time.perf_counter_ns()
            if not work:
                raise RuntimeError("crash worker did not claim task")

            _expire_task(station, pid, "LEASE-001")
            injected = time.perf_counter_ns()
            station.store.recover()
            recovered = time.perf_counter_ns()

            blocked = station.store.project(pid)["tasks"][0]
            if blocked["state"] != "blocked":
                raise RuntimeError(f"expired lease did not block task: {blocked['state']}")
            expired_events = [
                event for event in station.store.events(pid, 0, 100000)
                if event["event_type"] == "worker.expired"
            ]
            if not expired_events or expired_events[-1]["data"].get("owner") != "remote:crashed-worker":
                raise RuntimeError("expired worker identity was not retained")

            stale_files = {
                path: "LEASE RECOVERED LEASE-001\n"
                for path in work["packet"]["writable_files"]
            }
            stale_payload = {
                "project_id": pid,
                "task_id": "LEASE-001",
                "lease": work["lease"],
                "submission_id": "stale-" + uuid.uuid4().hex,
                "response": {"files": stale_files},
            }
            stale_rejected = False
            try:
                crashed.request("result", stale_payload)
            except urllib.error.HTTPError as exc:
                stale_rejected = exc.code == 400
            if not stale_rejected:
                raise RuntimeError("stale worker result was not rejected")

            retriage_started = time.perf_counter_ns()
            station.triage(pid)
            ready = station.store.project(pid)["tasks"][0]
            if ready["state"] != "ready":
                raise RuntimeError(f"expired task did not become ready after re-triage: {ready['state']}")
            retriaged = time.perf_counter_ns()

            if not healthy.run_once(pid, "healthy-reclaimer", LeaseHealthyProvider(work_ms), max_tokens=256):
                raise RuntimeError("healthy worker did not reclaim expired task")
            candidate = time.perf_counter_ns()
            task = station.store.project(pid)["tasks"][0]
            if task["state"] != "review_ready":
                raise RuntimeError(f"reclaimed task did not verify: {task['state']}")
            station.review(pid, task["id"])
            station.integrate(pid, task["id"])
            ended = time.perf_counter_ns()

            final = station.store.project(pid)["tasks"][0]
            metrics = station.worker_metrics(pid)
            by_worker = {row["worker"]: row for row in metrics["workers"]}
            return {
                "claim_ms": (claimed - started) / 1_000_000.0,
                "fault_injection_ms": (injected - claimed) / 1_000_000.0,
                "recover_scan_ms": (recovered - injected) / 1_000_000.0,
                "retriage_ms": (retriaged - retriage_started) / 1_000_000.0,
                "healthy_candidate_ms": (candidate - retriaged) / 1_000_000.0,
                "full_recovery_ms": (ended - started) / 1_000_000.0,
                "stale_result_rejected": stale_rejected,
                "all_integrated": final["state"] == "integrated",
                "attempts": final["attempt"],
                "expired_event_count": len(expired_events),
                "worker_metrics": metrics,
                "expired_worker_expirations": by_worker["crashed-worker"]["expirations"],
                "healthy_inference_median_ms": by_worker["healthy-reclaimer"]["inference_latency"]["median_ms"],
            }
        finally:
            _close(server, thread)


def run_station_lease_recovery_benchmark(*, work_ms: float = 40.0, repeats: int = 3) -> dict[str, Any]:
    if work_ms < 0 or repeats < 1:
        raise ValueError("invalid lease recovery benchmark bounds")
    baselines = []
    recoveries = []
    for repeat in range(repeats):
        baseline = _baseline(work_ms)
        baseline["repeat"] = repeat
        baselines.append(baseline)
        recovery = _trial(work_ms)
        recovery["repeat"] = repeat
        recoveries.append(recovery)

    baseline_full = statistics.median(row["full_ms"] for row in baselines)
    recovery_full = statistics.median(row["full_recovery_ms"] for row in recoveries)
    config = {"work_ms": work_ms, "repeats": repeats}
    return {
        "schema_version": "residual.distributed-lease-recovery.v1",
        "kind": "station-lease-expiry-recovery",
        "evidence_level": "development_fixture",
        "simulation": True,
        "configuration": config,
        "baseline_runs": baselines,
        "recovery_runs": recoveries,
        "summary": {
            "baseline_full_median_ms": baseline_full,
            "lease_recovery_full_median_ms": recovery_full,
            "lease_recovery_penalty_ms": recovery_full - baseline_full,
            "lease_recovery_penalty_ratio": recovery_full / baseline_full if baseline_full else None,
            "all_integrated": all(row["all_integrated"] for row in recoveries),
            "all_stale_results_rejected": all(row["stale_result_rejected"] for row in recoveries),
            "all_expirations_attributed": all(row["expired_worker_expirations"] == 1 for row in recoveries),
            "attempts": sorted({row["attempts"] for row in recoveries}),
        },
        "claim_boundary": (
            "The task is claimed through the real worker API and the real Station recovery, "
            "stale-result, re-triage, verification, review and integration paths are used. "
            "Only lease time passage is fault-injected by moving lease_until into the past; "
            "this is not evidence for real process-kill detection latency."
        ),
        "benchmark_hash": digest(config),
    }
