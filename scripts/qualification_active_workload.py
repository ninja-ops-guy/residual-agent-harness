#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

from residual.station.service import DEMO_FILES, Station, demo_spec


BAD_HEALTH = {"files": {"station/health.py": "def status(services):\n    return 'ready'\n"}}


def run_campaign(*, cycles: int, root: Path) -> dict:
    started = time.monotonic()
    root.mkdir(parents=True, exist_ok=True)
    station = Station(root)
    records = []
    failure = None
    try:
        for index in range(cycles):
            cycle_start = time.monotonic()
            pid = station.create(demo_spec(), demo=True)["project_id"]
            station.triage(pid)

            # Deliberately create one real verification failure before recovery.
            work = station.prepare(pid, f"active-soak-bad-{index}", "OPS-101")
            if not work:
                raise AssertionError("OPS-101 was not claimable for injected repair")
            station.finish(work, BAD_HEALTH)
            if station.store.task(pid, "OPS-101")["state"] != "repair_required":
                raise AssertionError("injected bad candidate did not enter repair_required")

            # Reopen periodically to exercise recovery from durable state mid-mission.
            # Restart is an explicit owner handoff; two live Station owners are forbidden.
            if index % 2:
                station.close()
                station = Station(root)
                if station.store.task(pid, "OPS-101")["state"] != "repair_required":
                    raise AssertionError("repair_required state did not survive Station reopen")

            repaired = station.run_one(pid, "OPS-101", owner=f"active-soak-repair-{index}")
            if not repaired or station.store.task(pid, "OPS-101")["state"] != "review_ready":
                raise AssertionError("repair attempt did not reach review_ready")
            station.review(pid, "OPS-101")
            station.integrate(pid, "OPS-101")

            result = station.batch(pid)
            project = station.store.project(pid)
            if result["control"]["outcome"] == "aborted":
                raise AssertionError("controlled batch aborted")
            if not all(task["state"] == "integrated" for task in project["tasks"]):
                raise AssertionError("active workload did not integrate every task")

            release = station.export(pid)
            if not release.get("id"):
                raise AssertionError("release export did not produce an artifact")
            station.close()
            reopened = Station(root)
            persisted = reopened.store.project(pid)
            if not all(task["state"] == "integrated" for task in persisted["tasks"]):
                raise AssertionError("integrated state did not survive reopen")
            reopened.store.artifact(release["id"])
            station = reopened

            records.append({
                "cycle": index,
                "project_id": pid,
                "elapsed_s": round(time.monotonic() - cycle_start, 6),
                "events": station.metrics(pid)["events"],
                "repair_attempt": station.store.task(pid, "OPS-101")["attempt"],
                "release_id": release["id"],
            })
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            station.close()
        except Exception as close_exc:
            if failure is None:
                failure = f"{type(close_exc).__name__}: {close_exc}"

    return {
        "schema": "residual.qualification.active-workload.v1",
        "result": "PASS" if failure is None and len(records) == cycles else "FAIL",
        "cycles_requested": cycles,
        "cycles_completed": len(records),
        "elapsed_s": round(time.monotonic() - started, 6),
        "failure": failure,
        "records": records,
        "non_claim": "This is an active lifecycle/recovery stress campaign, not elapsed 24h/72h/30d operational evidence.",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run active RESIDUAL create/fail/repair/review/integrate/export stress")
    parser.add_argument("--cycles", type=int, default=8)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not 1 <= args.cycles <= 1000:
        parser.error("--cycles must be 1..1000")

    if args.root is None:
        with tempfile.TemporaryDirectory(prefix="residual-active-workload-") as temp:
            report = run_campaign(cycles=args.cycles, root=Path(temp))
    else:
        report = run_campaign(cycles=args.cycles, root=args.root)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
