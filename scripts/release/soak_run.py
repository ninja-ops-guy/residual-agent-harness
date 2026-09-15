#!/usr/bin/env python3
"""Release-candidate soak driver with explicit stop criteria and
hash-chained artifact retention.

Wraps residual.soak.SoakHarness (SPEC-NINE-002): drives one soak day at a
time, snapshots typed per-day metrics into a hash-chained JSONL journal
(sampling cadence: once per soak day), enforces STOP CRITERIA after every
day, and writes the final HMAC-signed SoakTestReport (N9-R11).

STOP CRITERIA (each halt writes a typed STOP record before exiting 2):
  - error budget:      unhandled_exceptions > --max-exceptions (default 0)
                       cumulative, OR daily brake FN rate > 1% (N9-R10 limit)
  - crash:             the harness itself raises (recorded, evidence kept)
  - evidence-chain:    the day journal fails verify_chain() before a new
                       day is appended (tamper/truncation detection)
  - resource:          free disk at --out drops below --min-free-mb

Artifact retention: everything lands under --out (default
runs/release-soak/): soak-journal.jsonl (hash-chained day samples),
soak-state.json (resumable state), report.json (signed), and
retention-manifest.json binding every retained file's SHA-256 to the
journal chain head. Retain the whole directory; do not prune.

Workload mix: residual.soak's NetOps/SecOps synthetic templates with the
configured InjectionMix (bad configs, missing dependencies, adversarial
inputs) plus the N9-R12 red team exercise. The frozen R0-R5 measured
evaluation (residual/eval_frozen) is a separate gate and is NOT part of
the soak workload; see docs/release/SOAK_PLAN.md.

Non-claims: running this driver produces soak evidence; it certifies no
release. Final soak runs target the accepted release candidate after the
#108 sandbox-timing repair lands.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from residual.soak import (  # noqa: E402
    InjectionMix,
    SoakConfig,
    SoakHarness,
    SoakState,
)


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Journal:
    """Hash-chained typed journal: each record embeds sha256(prev line)."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            ok, records, error = self.verify()
            if not ok:
                raise RuntimeError(
                    f"evidence-chain break in existing journal: {error}")
            self._prev = hashlib.sha256(
                (json.dumps(records[-1], sort_keys=True)).encode()
            ).hexdigest() if records else "0" * 64
        else:
            self._prev = "0" * 64

    def append(self, record_type, payload):
        record = {
            "type": record_type,
            "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "prev_hash": self._prev,
            "payload": payload,
        }
        line = json.dumps(record, sort_keys=True)
        self._prev = hashlib.sha256(line.encode("utf-8")).hexdigest()
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        return record

    def verify(self):
        prev = "0" * 64
        records = []
        for lineno, line in enumerate(
                self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("prev_hash") != prev:
                return False, records, f"line {lineno} chain break"
            prev = hashlib.sha256(line.encode("utf-8")).hexdigest()
            records.append(record)
        return True, records, ""

    @property
    def head(self):
        return self._prev


def free_mb(path):
    return shutil.disk_usage(path).free // (1024 * 1024)


def run_soak(*, out_dir, days, tasks_per_day, seed, station_key,
             max_exceptions, brake_fn_limit, min_free_mb, max_days=None,
             allow_below_minimum=False):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    journal = Journal(out_dir / "soak-journal.jsonl")
    config = SoakConfig(seed=seed, total_days=days,
                        tasks_per_day=tasks_per_day,
                        injection_mix=InjectionMix())
    harness = SoakHarness(config, station_key,
                          state_path=str(out_dir / "soak-state.json"),
                          enforce_load_minimum=not allow_below_minimum)

    def stop(reason_type, detail):
        journal.append("STOP", {"criterion": reason_type, "detail": detail})
        finalize(out_dir, journal, harness, stopped=reason_type)
        return {"status": "STOPPED", "criterion": reason_type,
                "detail": detail}

    try:
        state = SoakState.load(out_dir / "soak-state.json")
        harness.state = state
    except FileNotFoundError:
        state = harness.state

    journal.append("START", {
        "config": {"days": days, "tasks_per_day": tasks_per_day,
                   "seed": seed, "max_days": max_days,
                   "below_minimum_load_rehearsal": allow_below_minimum},
        "stop_criteria": {"max_exceptions": max_exceptions,
                          "brake_fn_daily_limit": brake_fn_limit,
                          "min_free_mb": min_free_mb},
    })
    limit = state.total_days if max_days is None else min(state.total_days,
                                                          max_days)
    while state.next_day < limit:
        if free_mb(out_dir) < min_free_mb:
            return stop("resource_exhaustion",
                        f"free disk below {min_free_mb} MB at {out_dir}")
        ok, _, error = journal.verify()
        if not ok:
            return stop("evidence_chain_break", error)
        day = state.next_day
        try:
            day_metrics = harness.run_day(day)
        except Exception as exc:  # crash stop criterion
            return stop("crash", f"{type(exc).__name__}: {exc}")
        state.metrics.merge(day_metrics)
        state.next_day = day + 1
        if harness.state_path:
            state.save(harness.state_path)
        rates = day_metrics.to_dict()["rates"]
        journal.append("DAY", {"day": day, "metrics": day_metrics.to_dict()})
        if state.metrics.unhandled_exceptions > max_exceptions:
            return stop("error_budget",
                        f"unhandled_exceptions="
                        f"{state.metrics.unhandled_exceptions} > "
                        f"{max_exceptions}")
        brake_fn = rates.get("brake_fn_rate")
        if brake_fn is not None and brake_fn > brake_fn_limit:
            return stop("error_budget",
                        f"day {day} brake FN rate {brake_fn} > "
                        f"{brake_fn_limit}")
    journal.append("COMPLETE", {"days_completed": state.days_completed})
    finalize(out_dir, journal, harness, stopped=None)
    return {"status": "COMPLETE", "days_completed": state.days_completed}


def finalize(out_dir, journal, harness, stopped):
    report = harness.report(signed=True)
    report_path = Path(out_dir) / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n",
                           encoding="utf-8")
    files = {}
    for path in sorted(Path(out_dir).rglob("*")):
        if path.is_file() and path.name != "retention-manifest.json":
            files[str(path.relative_to(out_dir))] = _sha256_file(path)
    manifest = {
        "schema": "residual.release-soak.retention.v1",
        "stopped_on": stopped,
        "journal_chain_head": journal.head,
        "retained_files_sha256": files,
        "instruction": "retain this entire directory unmodified; verify "
                       "soak-journal.jsonl with Journal.verify() and each "
                       "file against this manifest before citing it",
    }
    (Path(out_dir) / "retention-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("runs/release-soak"))
    parser.add_argument("--days", type=int, default=30,
                        help="N9-R9 default: 30 consecutive days")
    parser.add_argument("--tasks-per-day", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260914)
    parser.add_argument("--station-key-hex", required=True,
                        help="Station identity key (hex) for report signing")
    parser.add_argument("--max-exceptions", type=int, default=0,
                        help="error budget: halt above this many cumulative "
                             "unhandled exceptions")
    parser.add_argument("--brake-fn-limit", type=float, default=0.01,
                        help="error budget: daily brake FN rate limit "
                             "(N9-R10: <= 1%)")
    parser.add_argument("--min-free-mb", type=int, default=512,
                        help="resource stop: halt below this much free disk")
    parser.add_argument("--max-days", type=int, default=None,
                        help="rehearsal cap; final runs omit this")
    parser.add_argument("--allow-below-minimum", action="store_true",
                        help="rehearsal only: permit < 1000 tasks/day "
                             "(N9-R9 minimum); recorded in the journal")
    args = parser.parse_args(argv)
    result = run_soak(
        out_dir=args.out, days=args.days, tasks_per_day=args.tasks_per_day,
        seed=args.seed, station_key=bytes.fromhex(args.station_key_hex),
        max_exceptions=args.max_exceptions,
        brake_fn_limit=args.brake_fn_limit, min_free_mb=args.min_free_mb,
        max_days=args.max_days,
        allow_below_minimum=args.allow_below_minimum)
    print(json.dumps(result, indent=2))
    return {"COMPLETE": 0, "STOPPED": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
