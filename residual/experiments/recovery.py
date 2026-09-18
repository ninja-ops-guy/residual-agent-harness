"""Controlled distributed repair/recovery benchmark.

A deliberately bad remote worker submits a syntactically valid but verifier-failing
candidate. A healthy worker then reclaims the resulting repair task through the
normal Station worker API, receives the retained repair context, and produces a
verified candidate which is reviewed and integrated.

This measures fail-closed repair overhead, not process-crash/lease-expiry recovery.
"""
from __future__ import annotations

import json
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



class HealthyRepairProvider:
    placement = "local"
    model = "synthetic-healthy-worker-v1"

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
                path: f"RESULT {task_id}\n"
                for path in packet["writable_files"]
            }}),
            Usage(input_tokens=8, output_tokens=4, source="reported"),
            elapsed_ms=self.work_ms,
            finish_reason="stop",
        )


def _station_spec() -> str:
    manifest = {
        "schema_version": 1,
        "name": "Distributed recovery benchmark",
        "goal": "Measure fail-closed repair recovery through the real Station worker path.",
        "tasks": [{
            "id": "REC-001",
            "title": "Recover a verifier-failing distributed candidate",
            "instruction": "Write the deterministic result for REC-001.",
            "files": ["recovery/result.txt"],
            "context": [],
            "depends_on": [],
            "route": "local",
            "checks": [
                {"kind": "exists", "path": "recovery/result.txt"},
                {"kind": "contains", "path": "recovery/result.txt", "text": "RESULT REC-001"},
            ],
        }],
    }
    fence = chr(96) * 3
    return "# Distributed recovery benchmark\n\n" + fence + "json\n" + json.dumps(manifest) + "\n" + fence + "\n"


class VerifierFailingProvider:
    placement = "local"
    model = "synthetic-bad-worker-v1"

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
                path: f"BROKEN {task_id}\n"
                for path in packet["writable_files"]
            }}),
            Usage(input_tokens=8, output_tokens=4, source="reported"),
            elapsed_ms=self.work_ms,
            finish_reason="stop",
        )


def _new_station(tmp: str):
    station = Station(tmp)
    pid = station.create(_station_spec(), demo=True)["project_id"]
    station.triage(pid)
    token = station.store.settings()["worker_token"]
    station.store.settings({"remote_workers_enabled": True})
    server = Server(("127.0.0.1", 0), station)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return station, pid, token, server, thread, f"http://127.0.0.1:{server.server_port}"


def _close(server, thread):
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def _baseline(*, good_ms: float) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="residual-recovery-baseline-") as tmp:
        station, pid, token, server, thread, url = _new_station(tmp)
        try:
            client = WorkerClient(url, token)
            started = time.perf_counter_ns()
            if not client.run_once(pid, "healthy-baseline", HealthyRepairProvider(good_ms), max_tokens=256):
                raise RuntimeError("baseline worker did not claim task")
            candidate_done = time.perf_counter_ns()
            task = station.store.project(pid)["tasks"][0]
            if task["state"] != "review_ready":
                raise RuntimeError(f"baseline candidate not review-ready: {task['state']}")
            station.review(pid, task["id"])
            station.integrate(pid, task["id"])
            ended = time.perf_counter_ns()
            return {
                "candidate_ms": (candidate_done - started) / 1_000_000.0,
                "full_ms": (ended - started) / 1_000_000.0,
                "attempts": station.store.project(pid)["tasks"][0]["attempt"],
                "calls": station.metrics(pid)["calls"],
            }
        finally:
            _close(server, thread)


def _recovery(*, bad_ms: float, good_ms: float) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="residual-recovery-exp-") as tmp:
        station, pid, token, server, thread, url = _new_station(tmp)
        try:
            bad = WorkerClient(url, token)
            healthy = WorkerClient(url, token)
            started = time.perf_counter_ns()

            if not bad.run_once(pid, "bad-worker", VerifierFailingProvider(bad_ms), max_tokens=256):
                raise RuntimeError("bad worker did not claim task")
            failed_at = time.perf_counter_ns()
            failed = station.store.project(pid)["tasks"][0]
            if failed["state"] != "repair_required":
                raise RuntimeError(f"bad worker did not fail closed: {failed['state']}")
            findings = tuple(failed.get("findings", ()))
            if not findings:
                raise RuntimeError("failed candidate did not retain repair findings")

            if not healthy.run_once(pid, "healthy-repair", SyntheticWorkerProvider(good_ms), max_tokens=256):
                raise RuntimeError("healthy worker did not reclaim repair task")
            repaired_at = time.perf_counter_ns()
            repaired = station.store.project(pid)["tasks"][0]
            if repaired["state"] != "review_ready":
                raise RuntimeError(f"repair candidate not review-ready: {repaired['state']}")

            station.review(pid, repaired["id"])
            station.integrate(pid, repaired["id"])
            ended = time.perf_counter_ns()

            task = station.store.project(pid)["tasks"][0]
            events = station.store.events(pid, 0, 100000)
            return {
                "failed_attempt_ms": (failed_at - started) / 1_000_000.0,
                "repair_candidate_ms": (repaired_at - failed_at) / 1_000_000.0,
                "full_recovery_ms": (ended - started) / 1_000_000.0,
                "attempts": task["attempt"],
                "calls": station.metrics(pid)["calls"],
                "all_integrated": task["state"] == "integrated",
                "repair_findings_retained": bool(findings),
                "event_head": events[-1]["hash"] if events else None,
                "event_count": len(events),
            }
        finally:
            _close(server, thread)


def run_station_recovery_benchmark(
    *,
    bad_ms: float = 20.0,
    good_ms: float = 40.0,
    repeats: int = 3,
) -> dict[str, Any]:
    if bad_ms < 0 or good_ms < 0 or repeats < 1:
        raise ValueError("invalid recovery benchmark bounds")

    baselines = []
    recoveries = []
    for repeat in range(repeats):
        base = _baseline(good_ms=good_ms)
        base["repeat"] = repeat
        baselines.append(base)
        recovery = _recovery(bad_ms=bad_ms, good_ms=good_ms)
        recovery["repeat"] = repeat
        recoveries.append(recovery)

    baseline_full = statistics.median(row["full_ms"] for row in baselines)
    recovery_full = statistics.median(row["full_recovery_ms"] for row in recoveries)
    return {
        "schema_version": "residual.distributed-recovery-experiment.v1",
        "kind": "station-verifier-failure-repair",
        "evidence_level": "development_fixture",
        "simulation": True,
        "workload": {
            "bad_worker_latency_ms": bad_ms,
            "healthy_worker_latency_ms": good_ms,
            "repeats": repeats,
        },
        "baseline_runs": baselines,
        "recovery_runs": recoveries,
        "summary": {
            "baseline_full_median_ms": baseline_full,
            "recovery_full_median_ms": recovery_full,
            "recovery_penalty_ms": recovery_full - baseline_full,
            "recovery_penalty_ratio": recovery_full / baseline_full if baseline_full else None,
            "all_recovered_and_integrated": all(row["all_integrated"] for row in recoveries),
            "all_failures_retained_findings": all(row["repair_findings_retained"] for row in recoveries),
            "attempts_per_recovery": sorted({row["attempts"] for row in recoveries}),
            "calls_per_recovery": sorted({row["calls"] for row in recoveries}),
        },
        "claim_boundary": (
            "The first worker returns a real verifier-failing candidate through the "
            "normal remote-worker API; the healthy worker reclaims the resulting "
            "repair_required task and normal review/integration gates complete. "
            "This does not simulate a crashed process, heartbeat loss, or lease expiry."
        ),
        "benchmark_hash": digest({
            "kind": "station-verifier-failure-repair",
            "bad_ms": bad_ms,
            "good_ms": good_ms,
            "repeats": repeats,
        }),
    }
