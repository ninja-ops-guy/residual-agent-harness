#!/usr/bin/env python3
"""Release-candidate soak driver with fail-closed resumable evidence.

This wrapper drives ``residual.soak.SoakHarness`` one day at a time and keeps
release evidence separate from the frozen measured-evaluation protocol.  It
does not certify a release.  A final COMPLETE record is emitted only after all
configured soak days finish; ``--max-days`` produces a typed PAUSED rehearsal.

The evidence journal is hash chained.  In addition, every stable boundary is
bound by an HMAC-signed checkpoint containing the complete journal digest,
chain head, record count, state digest and resume parameters.  On resume the
checkpoint and any previous retention manifest are verified before new work is
accepted.  This makes ordinary tail truncation/state replacement detectable
instead of relying on the chain's internal links alone.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from pathlib import Path
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from residual.soak import InjectionMix, SoakConfig, SoakHarness, SoakState  # noqa: E402

CHECKPOINT_SCHEMA = "residual.release-soak.checkpoint.v1"
MANIFEST_SCHEMA = "residual.release-soak.retention.v2"


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _atomic_json(path, data):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


class Journal:
    """Hash-chained typed journal: each record embeds sha256(previous line)."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._prev = "0" * 64
        if self.path.exists():
            ok, _records, error = self.verify()
            if not ok:
                raise RuntimeError(f"evidence-chain break in existing journal: {error}")
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self._prev = hashlib.sha256(line.encode("utf-8")).hexdigest()

    def append(self, record_type, payload):
        record = {
            "type": record_type,
            "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "prev_hash": self._prev,
            "payload": payload,
        }
        line = json.dumps(record, sort_keys=True)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
        self._prev = hashlib.sha256(line.encode("utf-8")).hexdigest()
        return record

    def verify(self):
        prev = "0" * 64
        records = []
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            return False, [], f"journal unreadable: {exc}"
        for lineno, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                return False, records, f"line {lineno} not JSON: {exc}"
            if not isinstance(record, dict) or record.get("prev_hash") != prev:
                return False, records, f"line {lineno} chain break"
            prev = hashlib.sha256(line.encode("utf-8")).hexdigest()
            records.append(record)
        return True, records, ""

    @property
    def head(self):
        return self._prev

    @property
    def count(self):
        ok, records, error = self.verify()
        if not ok:
            raise RuntimeError(error)
        return len(records)


def free_mb(path):
    return shutil.disk_usage(path).free // (1024 * 1024)


def _checkpoint_payload(out_dir, journal, state, status):
    state_path = Path(out_dir) / "soak-state.json"
    return {
        "schema": CHECKPOINT_SCHEMA,
        "status": status,
        "journal_chain_head": journal.head,
        "journal_record_count": journal.count,
        "journal_sha256": _sha256_file(journal.path),
        "state_sha256": _sha256_file(state_path),
        "state": {
            "seed": state.seed,
            "tasks_per_day": state.tasks_per_day,
            "total_days": state.total_days,
            "next_day": state.next_day,
        },
    }


def write_checkpoint(out_dir, journal, state, station_key, status):
    payload = _checkpoint_payload(out_dir, journal, state, status)
    envelope = {
        "payload": payload,
        "hmac_sha256": hmac.new(station_key, _canonical(payload), hashlib.sha256).hexdigest(),
    }
    _atomic_json(Path(out_dir) / "soak-checkpoint.json", envelope)
    return envelope


def verify_checkpoint(out_dir, journal, station_key):
    path = Path(out_dir) / "soak-checkpoint.json"
    if not path.exists():
        return None
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
        payload = envelope["payload"]
        signature = envelope["hmac_sha256"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid soak checkpoint: {exc}") from exc
    expected = hmac.new(station_key, _canonical(payload), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(str(signature), expected):
        raise RuntimeError("soak checkpoint HMAC verification failed")
    if payload.get("schema") != CHECKPOINT_SCHEMA:
        raise RuntimeError(f"unsupported soak checkpoint schema: {payload.get('schema')}")
    ok, records, error = journal.verify()
    if not ok:
        raise RuntimeError(f"journal failed checkpoint verification: {error}")
    checks = {
        "journal_chain_head": journal.head,
        "journal_record_count": len(records),
        "journal_sha256": _sha256_file(journal.path),
    }
    for key, actual in checks.items():
        if payload.get(key) != actual:
            raise RuntimeError(f"checkpoint {key} mismatch")
    state_path = Path(out_dir) / "soak-state.json"
    if not state_path.is_file() or payload.get("state_sha256") != _sha256_file(state_path):
        raise RuntimeError("checkpoint state digest mismatch")
    return payload


def verify_retention_manifest(out_dir, journal):
    path = Path(out_dir) / "retention-manifest.json"
    if not path.exists():
        return
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"retention manifest unreadable: {exc}") from exc
    if manifest.get("schema") not in ("residual.release-soak.retention.v1", MANIFEST_SCHEMA):
        raise RuntimeError(f"unsupported retention manifest schema: {manifest.get('schema')}")
    if manifest.get("journal_chain_head") != journal.head:
        raise RuntimeError("retention manifest journal head mismatch")
    if "journal_record_count" in manifest and manifest["journal_record_count"] != journal.count:
        raise RuntimeError("retention manifest journal record-count mismatch")
    for rel, expected in manifest.get("retained_files_sha256", {}).items():
        target = Path(out_dir) / rel
        if not target.is_file() or _sha256_file(target) != expected:
            raise RuntimeError(f"retained file digest mismatch: {rel}")


def _validate_state(state, *, days, tasks_per_day, seed):
    expected = (seed, tasks_per_day, days)
    actual = (state.seed, state.tasks_per_day, state.total_days)
    if actual != expected:
        raise RuntimeError(
            "resume configuration mismatch: "
            f"state(seed,tasks_per_day,total_days)={actual} requested={expected}")
    if not 0 <= state.next_day <= state.total_days:
        raise RuntimeError("resume state next_day is outside configured range")


def _validate_history(journal, state):
    ok, records, error = journal.verify()
    if not ok:
        raise RuntimeError(error)
    days = [r.get("payload", {}).get("day") for r in records if r.get("type") == "DAY"]
    if days != list(range(state.next_day)):
        raise RuntimeError(
            f"journal/state day history mismatch: journal={days!r} state.next_day={state.next_day}")
    return records


def run_soak(*, out_dir, days, tasks_per_day, seed, station_key,
             max_exceptions, brake_fn_limit, min_free_mb, max_days=None,
             allow_below_minimum=False):
    if not isinstance(station_key, (bytes, bytearray)) or len(station_key) < 16:
        raise ValueError("station_key must contain at least 16 bytes")
    if days <= 0 or tasks_per_day <= 0:
        raise ValueError("days and tasks_per_day must be positive")
    if max_days is not None and max_days < 0:
        raise ValueError("max_days must be non-negative")
    if max_exceptions < 0 or min_free_mb < 0 or not 0 <= brake_fn_limit <= 1:
        raise ValueError("invalid stop-criterion bounds")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    journal = Journal(out_dir / "soak-journal.jsonl")
    existing_records = _validate_history(journal, SoakState(seed, tasks_per_day, days)) if not (out_dir / "soak-state.json").exists() and journal.count == 0 else None

    checkpoint = verify_checkpoint(out_dir, journal, station_key)
    verify_retention_manifest(out_dir, journal)

    config = SoakConfig(seed=seed, total_days=days,
                        tasks_per_day=tasks_per_day,
                        injection_mix=InjectionMix())
    harness = SoakHarness(config, bytes(station_key),
                          state_path=str(out_dir / "soak-state.json"),
                          enforce_load_minimum=not allow_below_minimum)
    try:
        state = SoakState.load(out_dir / "soak-state.json")
        harness.state = state
    except FileNotFoundError:
        if journal.count or checkpoint is not None:
            raise RuntimeError("resume evidence exists without soak-state.json")
        state = harness.state
        state.save(harness.state_path)

    _validate_state(state, days=days, tasks_per_day=tasks_per_day, seed=seed)
    records = _validate_history(journal, state)
    if checkpoint is not None:
        cp_state = checkpoint.get("state", {})
        if cp_state != {"seed": state.seed, "tasks_per_day": state.tasks_per_day,
                        "total_days": state.total_days, "next_day": state.next_day}:
            raise RuntimeError("checkpoint resume-state fields mismatch")
        if checkpoint.get("status") == "STOPPED":
            raise RuntimeError("stopped soak cannot resume without a new evidence directory")
        if checkpoint.get("status") == "COMPLETE":
            if not state.complete or not records or records[-1].get("type") != "COMPLETE":
                raise RuntimeError("COMPLETE checkpoint does not match terminal state/journal")
            return {"status": "COMPLETE", "days_completed": state.days_completed}
    elif records:
        raise RuntimeError("existing soak journal has no trusted checkpoint")

    record_type = "START" if not records else "RESUME"
    journal.append(record_type, {
        "config": {"days": days, "tasks_per_day": tasks_per_day,
                   "seed": seed, "max_days": max_days,
                   "below_minimum_load_rehearsal": allow_below_minimum},
        "stop_criteria": {"max_exceptions": max_exceptions,
                          "brake_fn_daily_limit": brake_fn_limit,
                          "min_free_mb": min_free_mb},
        "resumed_from_day": state.next_day,
    })
    state.save(harness.state_path)
    write_checkpoint(out_dir, journal, state, station_key, "RUNNING")

    def stop(reason_type, detail):
        journal.append("STOP", {"criterion": reason_type, "detail": detail})
        state.save(harness.state_path)
        write_checkpoint(out_dir, journal, state, station_key, "STOPPED")
        finalize(out_dir, journal, harness, status="STOPPED", stopped=reason_type)
        return {"status": "STOPPED", "criterion": reason_type, "detail": detail}

    limit = state.total_days if max_days is None else min(state.total_days, max_days)
    while state.next_day < limit:
        if free_mb(out_dir) < min_free_mb:
            return stop("resource_exhaustion",
                        f"free disk below {min_free_mb} MB at {out_dir}")
        ok, _, error = journal.verify()
        if not ok:
            _atomic_json(out_dir / "evidence-chain-failure.json", {
                "status": "STOPPED", "criterion": "evidence_chain_break", "detail": error})
            return {"status": "STOPPED", "criterion": "evidence_chain_break", "detail": error}
        day = state.next_day
        try:
            day_metrics = harness.run_day(day)
        except Exception as exc:
            return stop("crash", f"{type(exc).__name__}: {exc}")
        state.metrics.merge(day_metrics)
        state.next_day = day + 1
        journal.append("DAY", {"day": day, "metrics": day_metrics.to_dict()})
        state.save(harness.state_path)
        write_checkpoint(out_dir, journal, state, station_key, "RUNNING")
        rates = day_metrics.to_dict()["rates"]
        if state.metrics.unhandled_exceptions > max_exceptions:
            return stop("error_budget",
                        f"unhandled_exceptions={state.metrics.unhandled_exceptions} > {max_exceptions}")
        brake_fn = rates.get("brake_fn_rate")
        if brake_fn is not None and brake_fn > brake_fn_limit:
            return stop("error_budget",
                        f"day {day} brake FN rate {brake_fn} > {brake_fn_limit}")

    if not state.complete:
        journal.append("PAUSED", {
            "days_completed": state.days_completed,
            "days_remaining": state.total_days - state.days_completed,
            "rehearsal_cap": max_days,
        })
        state.save(harness.state_path)
        write_checkpoint(out_dir, journal, state, station_key, "PAUSED")
        finalize(out_dir, journal, harness, status="PAUSED", stopped=None, write_report=False)
        return {"status": "PAUSED", "days_completed": state.days_completed}

    journal.append("COMPLETE", {"days_completed": state.days_completed})
    state.save(harness.state_path)
    write_checkpoint(out_dir, journal, state, station_key, "COMPLETE")
    finalize(out_dir, journal, harness, status="COMPLETE", stopped=None)
    return {"status": "COMPLETE", "days_completed": state.days_completed}


def finalize(out_dir, journal, harness, *, status, stopped, write_report=True):
    report_path = Path(out_dir) / "report.json"
    if write_report:
        report = harness.report(signed=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    elif report_path.exists():
        report_path.unlink()

    files = {}
    for path in sorted(Path(out_dir).rglob("*")):
        if path.is_file() and path.name != "retention-manifest.json":
            files[str(path.relative_to(out_dir))] = _sha256_file(path)
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "status": status,
        "stopped_on": stopped,
        "journal_chain_head": journal.head,
        "journal_record_count": journal.count,
        "retained_files_sha256": files,
        "instruction": "retain this entire directory unmodified; verify the HMAC checkpoint, journal chain/head/count, and every retained digest before citing it",
    }
    _atomic_json(Path(out_dir) / "retention-manifest.json", manifest)


def _station_key(value):
    try:
        key = bytes.fromhex(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("station key must be hexadecimal") from exc
    if len(key) < 16:
        raise argparse.ArgumentTypeError("station key must decode to at least 16 bytes")
    return key


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("runs/release-soak"))
    parser.add_argument("--days", type=int, default=30,
                        help="N9-R9 default: 30 consecutive days")
    parser.add_argument("--tasks-per-day", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260914)
    parser.add_argument("--station-key-hex", required=True, type=_station_key,
                        help="Station identity HMAC key (hex) for report/checkpoint signing")
    parser.add_argument("--max-exceptions", type=int, default=0)
    parser.add_argument("--brake-fn-limit", type=float, default=0.01)
    parser.add_argument("--min-free-mb", type=int, default=512)
    parser.add_argument("--max-days", type=int, default=None,
                        help="rehearsal cap; final runs omit this; yields PAUSED, never COMPLETE")
    parser.add_argument("--allow-below-minimum", action="store_true",
                        help="rehearsal only: permit < 1000 tasks/day; recorded in evidence")
    args = parser.parse_args(argv)
    result = run_soak(
        out_dir=args.out, days=args.days, tasks_per_day=args.tasks_per_day,
        seed=args.seed, station_key=args.station_key_hex,
        max_exceptions=args.max_exceptions,
        brake_fn_limit=args.brake_fn_limit, min_free_mb=args.min_free_mb,
        max_days=args.max_days, allow_below_minimum=args.allow_below_minimum)
    print(json.dumps(result, indent=2))
    return {"COMPLETE": 0, "PAUSED": 0, "STOPPED": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
