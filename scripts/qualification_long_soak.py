#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from residual.qualification.evidence import GateResult, new_envelope, source_identity, write_envelope

TIERS = {
    "24h": 24 * 60 * 60,
    "72h": 72 * 60 * 60,
    "30d": 30 * 24 * 60 * 60,
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def source_continuity_ok(start: dict, end: dict) -> bool:
    return bool(
        start.get("commit")
        and start.get("tree")
        and end.get("commit")
        and end.get("tree")
        and start.get("tracked_source_dirty") is False
        and end.get("tracked_source_dirty") is False
        and start.get("commit") == end.get("commit")
        and start.get("tree") == end.get("tree")
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run an uninterrupted wall-clock RESIDUAL soak tier")
    parser.add_argument("--tier", choices=sorted(TIERS), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8910)
    parser.add_argument("--interval-seconds", type=float, default=30.0)
    parser.add_argument("--max-rss-growth-mib-per-hour", type=float, default=16.0)
    parser.add_argument("--max-fd-growth-per-hour", type=float, default=4.0)
    args = parser.parse_args(argv)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = args.output_dir / f"process-soak-{args.tier}.json"
    process_log = report.with_suffix(".process.log")
    continuity_path = args.output_dir / f"process-soak-{args.tier}.source-continuity.json"
    evidence = args.output_dir / f"process-soak-{args.tier}.evidence.json"
    data_dir = args.output_dir / "station-data"
    started = now()
    source_start = source_identity(ROOT)
    command = [
        sys.executable, str(ROOT / "scripts" / "qualification_process_soak.py"),
        "--duration-seconds", str(TIERS[args.tier]),
        "--interval-seconds", str(args.interval_seconds),
        "--startup-seconds", "5",
        "--probe-url", f"http://127.0.0.1:{args.port}/",
        "--probe-timeout", "5",
        "--max-probe-failures", "0",
        "--min-slope-window-seconds", "3600",
        "--max-rss-growth-mib-per-hour", str(args.max_rss_growth_mib_per_hour),
        "--max-fd-growth-per-hour", str(args.max_fd_growth_per_hour),
        "--output", str(report),
        "--", sys.executable, "-m", "residual.station.server",
        "--port", str(args.port), "--data", str(data_dir),
    ]
    proc = subprocess.run(command, cwd=ROOT, check=False)
    source_end = source_identity(ROOT)
    continuity_ok = source_continuity_ok(source_start, source_end)
    continuity = {
        "schema": "residual.qualification.source-continuity.v1",
        "result": "PASS" if continuity_ok else "FAIL",
        "start": source_start,
        "end": source_end,
    }
    continuity_path.write_text(json.dumps(continuity, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = GateResult.FAIL
    notes = [f"uninterrupted wall-clock tier={args.tier}"]
    report_pass = False
    if report.is_file():
        try:
            payload = json.loads(report.read_text(encoding="utf-8"))
            report_pass = proc.returncode == 0 and payload.get("result") == "PASS"
        except Exception as exc:
            notes.append(f"unreadable soak report: {type(exc).__name__}")
    else:
        notes.append("soak report missing or not a regular file")
    if not process_log.is_file():
        notes.append("process log missing or not a regular file")
    if not continuity_ok:
        notes.append("source commit/tree cleanliness or continuity was not established")
    if report_pass and process_log.is_file() and continuity_ok:
        result = GateResult.PASS

    envelope = new_envelope(
        f"process-soak-{args.tier}", result, root=ROOT, started_at=started,
        command=command, evidence_paths=[report, process_log, continuity_path], notes=notes,
        non_claims=["A completed tier applies only to the exact source/environment bound in this evidence."],
    )
    write_envelope(envelope, evidence)
    print(json.dumps(envelope.to_dict(), indent=2, sort_keys=True))
    return 0 if result == GateResult.PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
