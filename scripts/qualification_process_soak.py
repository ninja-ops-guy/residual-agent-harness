#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
import urllib.request
from pathlib import Path


def rss_bytes(pid: int) -> int:
    status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
    for line in status.splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("VmRSS unavailable")


def fd_count(pid: int) -> int:
    return len(list(Path(f"/proc/{pid}/fd").iterdir()))


def slope_per_hour(samples: list[dict], key: str, *, min_window_s: float) -> float | None:
    usable = [(float(s["elapsed_s"]), float(s[key])) for s in samples if s.get(key) is not None]
    if len(usable) < 3 or usable[-1][0] - usable[0][0] < min_window_s:
        return None
    xs = [x for x, _ in usable]
    ys = [y for _, y in usable]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    per_second = sum((x - mx) * (y - my) for x, y in usable) / denom
    return per_second * 3600.0


def probe(url: str, timeout: float) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = response.read(4096)
            return 200 <= response.status < 500 and bool(body), f"HTTP {response.status}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def terminate(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=10)
    except Exception:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run a live-process RESIDUAL soak and measure resource slopes")
    parser.add_argument("--duration-seconds", type=float, required=True)
    parser.add_argument("--interval-seconds", type=float, default=5.0)
    parser.add_argument("--startup-seconds", type=float, default=2.0)
    parser.add_argument("--probe-url")
    parser.add_argument("--probe-timeout", type=float, default=3.0)
    parser.add_argument("--max-probe-failures", type=int, default=0)
    parser.add_argument("--min-slope-window-seconds", type=float, default=300.0)
    parser.add_argument("--max-rss-growth-mib-per-hour", type=float, default=32.0)
    parser.add_argument("--max-fd-growth-per-hour", type=float, default=8.0)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("command required after --")
    if args.duration_seconds <= 0 or args.interval_seconds <= 0:
        parser.error("durations must be positive")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    log_path = args.output.with_suffix(".process.log")
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, text=True,
                                start_new_session=True)
        start = time.monotonic()
        samples: list[dict] = []
        probe_failures: list[dict] = []
        error: str | None = None
        try:
            time.sleep(args.startup_seconds)
            while time.monotonic() - start < args.duration_seconds:
                elapsed = time.monotonic() - start
                code = proc.poll()
                if code is not None:
                    error = f"process exited before soak completion with code {code}"
                    break
                sample = {"elapsed_s": round(elapsed, 6), "rss_bytes": None, "fd_count": None}
                try:
                    sample["rss_bytes"] = rss_bytes(proc.pid)
                    sample["fd_count"] = fd_count(proc.pid)
                except Exception as exc:
                    sample["metric_error"] = f"{type(exc).__name__}: {exc}"
                if args.probe_url:
                    ok, detail = probe(args.probe_url, args.probe_timeout)
                    sample["probe_ok"] = ok
                    sample["probe_detail"] = detail
                    if not ok:
                        probe_failures.append({"elapsed_s": elapsed, "detail": detail})
                samples.append(sample)
                time.sleep(args.interval_seconds)
        finally:
            terminate(proc)

    rss_slope = slope_per_hour(samples, "rss_bytes", min_window_s=args.min_slope_window_seconds)
    fd_slope = slope_per_hour(samples, "fd_count", min_window_s=args.min_slope_window_seconds)
    reasons: list[str] = []
    if error:
        reasons.append(error)
    if len(probe_failures) > args.max_probe_failures:
        reasons.append(f"probe failures {len(probe_failures)} > {args.max_probe_failures}")
    rss_limit = args.max_rss_growth_mib_per_hour * 1024 * 1024
    if rss_slope is not None and rss_slope > rss_limit:
        reasons.append(f"RSS growth {rss_slope / 1024 / 1024:.3f} MiB/hour > {args.max_rss_growth_mib_per_hour}")
    if fd_slope is not None and fd_slope > args.max_fd_growth_per_hour:
        reasons.append(f"FD growth {fd_slope:.3f}/hour > {args.max_fd_growth_per_hour}")
    if not samples:
        reasons.append("no resource samples collected")

    report = {
        "schema": "residual.qualification.process-soak.v1",
        "result": "PASS" if not reasons else "FAIL",
        "command": command,
        "pid": proc.pid,
        "duration_requested_s": args.duration_seconds,
        "sample_count": len(samples),
        "rss_growth_bytes_per_hour": rss_slope,
        "fd_growth_per_hour": fd_slope,
        "probe_failures": probe_failures,
        "thresholds": {
            "max_rss_growth_mib_per_hour": args.max_rss_growth_mib_per_hour,
            "max_fd_growth_per_hour": args.max_fd_growth_per_hour,
            "max_probe_failures": args.max_probe_failures,
            "min_slope_window_seconds": args.min_slope_window_seconds,
        },
        "reasons": reasons,
        "samples": samples,
        "process_log": str(log_path),
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
