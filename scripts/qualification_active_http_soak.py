#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from scripts.qualification_process_soak import fd_count, rss_bytes, slope_per_hour, terminate


def request(url: str, path: str, *, token: str | None = None, body=None, timeout: float = 10.0):
    data = None if body is None else json.dumps(body, separators=(",", ":")).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Station-Token"] = token
    req = urllib.request.Request(url + path, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = response.read(5_000_000)
        if not 200 <= response.status < 300:
            raise RuntimeError(f"HTTP {response.status}")
        return json.loads(payload)


def wait_bootstrap(url: str, deadline: float):
    last = None
    while time.monotonic() < deadline:
        try:
            return request(url, "/api/bootstrap", timeout=1.0)
        except Exception as exc:
            last = exc
            time.sleep(0.1)
    raise RuntimeError(f"Station did not become ready: {type(last).__name__ if last else 'unknown'}")


def wait_job(url: str, token: str, jid: str, deadline: float):
    while time.monotonic() < deadline:
        jobs = request(url, "/api/jobs", token=token)
        job = next((item for item in jobs["jobs"] if item["id"] == jid), None)
        if job and job["state"] in {"completed", "failed", "interrupted"}:
            return job
        time.sleep(0.05)
    raise RuntimeError(f"job {jid} did not reach a terminal state")


def run_campaign(*, cycles: int, port: int, root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    data_dir = root / "station-data"
    url = f"http://127.0.0.1:{port}"
    log_path = root / "station.log"
    log = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "residual.station.server", "--port", str(port), "--data", str(data_dir)],
        stdout=log, stderr=subprocess.STDOUT, text=True, start_new_session=True,
    )
    started = time.monotonic()
    records = []
    failure = None
    samples = []
    try:
        bootstrap = wait_bootstrap(url, time.monotonic() + 20)
        token = bootstrap["token"]
        samples.append({"elapsed_s": 0.0, "rss_bytes": rss_bytes(proc.pid), "fd_count": fd_count(proc.pid)})
        for index in range(cycles):
            cycle_started = time.monotonic()
            created = request(url, "/api/demo", token=token, body={})
            pid = created["project_id"]

            launched = request(url, f"/api/projects/{pid}/run", token=token, body={})
            job = wait_job(url, token, launched["job_id"], time.monotonic() + 90)
            if job["state"] != "completed":
                raise RuntimeError(f"mission job {job['state']}: {job.get('detail')}")
            project = request(url, f"/api/projects/{pid}", token=token)["project"]
            if not all(task["state"] == "integrated" for task in project["tasks"]):
                raise AssertionError("HTTP mission returned without integrating every task")

            exported = request(url, f"/api/projects/{pid}/export", token=token, body={})
            release_job = wait_job(url, token, exported["job_id"], time.monotonic() + 30)
            if release_job["state"] != "completed" or not release_job.get("result", {}).get("id"):
                raise AssertionError("HTTP release export did not complete with an artifact")

            jobs = request(url, "/api/jobs", token=token)["jobs"]
            orphan = [item["id"] for item in jobs if item["state"] in {"queued", "running"}]
            if orphan:
                raise AssertionError(f"orphan active jobs after cycle: {orphan[:5]}")

            sample = {
                "elapsed_s": round(time.monotonic() - started, 6),
                "rss_bytes": rss_bytes(proc.pid),
                "fd_count": fd_count(proc.pid),
            }
            samples.append(sample)
            records.append({
                "cycle": index,
                "project_id": pid,
                "job_id": launched["job_id"],
                "release_job_id": exported["job_id"],
                "elapsed_s": round(time.monotonic() - cycle_started, 6),
                **sample,
            })
            if proc.poll() is not None:
                raise RuntimeError(f"Station exited during active HTTP workload with code {proc.returncode}")
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        process_alive = proc.poll() is None
        terminate(proc)
        log.close()

    elapsed = time.monotonic() - started
    rss_delta = (samples[-1]["rss_bytes"] - samples[0]["rss_bytes"]) if len(samples) >= 2 else None
    fd_delta = (samples[-1]["fd_count"] - samples[0]["fd_count"]) if len(samples) >= 2 else None
    # Per-hour slopes are informational on short PR campaigns and become meaningful
    # on the deeper nightly run. Hard caps below catch obvious handle/memory leaks now.
    rss_slope = slope_per_hour(samples, "rss_bytes", min_window_s=1.0) if len(samples) >= 3 else None
    fd_slope = slope_per_hour(samples, "fd_count", min_window_s=1.0) if len(samples) >= 3 else None
    reasons = []
    if failure:
        reasons.append(failure)
    if len(records) != cycles:
        reasons.append(f"completed {len(records)} of {cycles} workload cycles")
    if not process_alive:
        reasons.append("Station was not alive at workload completion")
    if fd_delta is None or fd_delta > 12:
        reasons.append(f"file descriptor delta exceeded bound: {fd_delta}")
    if rss_delta is None or rss_delta > 96 * 1024 * 1024:
        reasons.append(f"RSS delta exceeded 96 MiB bound: {rss_delta}")

    return {
        "schema": "residual.qualification.active-http-soak.v1",
        "result": "PASS" if not reasons else "FAIL",
        "cycles_requested": cycles,
        "cycles_completed": len(records),
        "elapsed_s": round(elapsed, 6),
        "station_alive_at_completion": process_alive,
        "rss_delta_bytes": rss_delta,
        "fd_delta": fd_delta,
        "rss_slope_bytes_per_hour": rss_slope,
        "fd_slope_per_hour": fd_slope,
        "reasons": reasons,
        "samples": samples,
        "records": records,
        "process_log": str(log_path),
        "non_claim": "Short active HTTP stress is bug-discovery evidence; it is not substituted for elapsed 24h/72h/30d qualification.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Stress the real Station HTTP/job lifecycle while monitoring its process")
    parser.add_argument("--cycles", type=int, default=6)
    parser.add_argument("--port", type=int, default=8893)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--root", type=Path)
    args = parser.parse_args(argv)
    if not 1 <= args.cycles <= 1000:
        parser.error("--cycles must be 1..1000")

    if args.root:
        report = run_campaign(cycles=args.cycles, port=args.port, root=args.root)
    else:
        with tempfile.TemporaryDirectory(prefix="residual-active-http-") as temp:
            report = run_campaign(cycles=args.cycles, port=args.port, root=Path(temp))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
