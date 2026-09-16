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

from residual.qualification.evidence import GateResult, new_envelope, write_envelope

TIERS = {
    "24h": 24 * 60 * 60,
    "72h": 72 * 60 * 60,
    "30d": 30 * 24 * 60 * 60,
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
    evidence = args.output_dir / f"process-soak-{args.tier}.evidence.json"
    data_dir = args.output_dir / "station-data"
    started = now()
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
    result = GateResult.FAIL
    notes = [f"uninterrupted wall-clock tier={args.tier}"]
    if report.exists():
        try:
            payload = json.loads(report.read_text(encoding="utf-8"))
            if proc.returncode == 0 and payload.get("result") == "PASS":
                result = GateResult.PASS
        except Exception as exc:
            notes.append(f"unreadable soak report: {type(exc).__name__}")
    else:
        notes.append("soak report missing")
    envelope = new_envelope(
        f"process-soak-{args.tier}", result, root=ROOT, started_at=started,
        command=command, evidence_paths=[report, process_log], notes=notes,
        non_claims=["A completed tier applies only to the exact source/environment bound in this evidence."],
    )
    write_envelope(envelope, evidence)
    print(json.dumps(envelope.to_dict(), indent=2, sort_keys=True))
    return 0 if result == GateResult.PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
