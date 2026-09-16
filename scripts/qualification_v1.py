#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from residual.qualification.evidence import GateResult, new_envelope, write_envelope
from residual.qualification.failures import FailureClass, FailureObservation, append_failure
from residual.qualification.manifest import aggregate_manifest, write_manifest
from residual.qualification.schedule import run_campaign, run_history, write_campaign


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def junit_counts(path: Path | None) -> tuple[int, int, int]:
    if path is None or not path.exists():
        return (0, 0, 0)
    root = ET.parse(path).getroot()
    cases = list(root.iter("testcase"))
    skips = sum(case.find("skipped") is not None for case in cases)
    failures = sum(case.find("failure") is not None for case in cases)
    errors = sum(case.find("error") is not None for case in cases)
    return skips, failures, errors


def command_run(args: argparse.Namespace) -> int:
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("run requires a command after --")
    started = now()
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text(
        "$ " + " ".join(command) + "\n\n[stdout]\n" + proc.stdout + "\n[stderr]\n" + proc.stderr,
        encoding="utf-8",
    )
    skips, failures, errors = junit_counts(args.junit)
    result = GateResult.PASS if proc.returncode == 0 and failures == 0 and errors == 0 else GateResult.FAIL
    notes = []
    if args.zero_skips and skips:
        result = GateResult.FAIL
        notes.append(f"zero-skip gate observed {skips} skips")
    if args.unknown_count:
        result = GateResult.FAIL
        notes.append(f"required gate observed {args.unknown_count} UNKNOWN outcomes")

    required_files = list(args.evidence_path)
    if args.junit is not None:
        required_files.append(args.junit)
    missing_required = [path for path in required_files if not path.is_file()]
    if missing_required:
        result = GateResult.FAIL
        notes.append(
            "required evidence missing or not a regular file: "
            + ", ".join(str(path) for path in missing_required)
        )

    evidence = [args.log, *[path for path in args.evidence_path if path.is_file()]]
    if args.junit is not None and args.junit.is_file():
        evidence.append(args.junit)
    envelope = new_envelope(
        args.gate_id, result, root=ROOT, started_at=started, command=command,
        evidence_paths=evidence, skip_count=skips, unknown_count=args.unknown_count,
        notes=notes, non_claims=args.non_claim,
    )
    write_envelope(envelope, args.output)
    print(json.dumps(envelope.to_dict(), indent=2, sort_keys=True))
    return 0 if result == GateResult.PASS else 1


def history_run(args: argparse.Namespace) -> int:
    started = now()
    report = run_campaign(start_seed=args.start_seed, seeds=args.seeds, steps=args.steps, lanes=args.lanes)

    # Replay one exact seed twice as part of the required gate, rather than only
    # trusting that the generator records a seed. Raw observation UUIDs/times are
    # intentionally excluded by schedule.py; semantic trace/state identity must match.
    replay_a = run_history(args.start_seed, steps=args.steps, lanes=args.lanes)
    replay_b = run_history(args.start_seed, steps=args.steps, lanes=args.lanes)
    replay_ok = bool(
        replay_a["result"] == replay_b["result"] == "PASS"
        and replay_a["trace"] == replay_b["trace"]
        and replay_a["final_state"] == replay_b["final_state"]
        and replay_a["semantic_observation_digest"] == replay_b["semantic_observation_digest"]
        and replay_a["replay_digest"] == replay_b["replay_digest"]
    )
    report["replay_check"] = {
        "seed": args.start_seed,
        "result": "PASS" if replay_ok else "FAIL",
        "first_digest": replay_a.get("replay_digest"),
        "second_digest": replay_b.get("replay_digest"),
    }
    if not replay_ok:
        report["result"] = "FAIL"
        report.setdefault("failures", []).append({
            "seed": args.start_seed,
            "failure": "semantic replay mismatch",
            "first": replay_a,
            "second": replay_b,
        })

    write_campaign(report, args.report)
    result = GateResult.PASS if report["result"] == "PASS" else GateResult.FAIL
    envelope = new_envelope(
        args.gate_id, result, root=ROOT, started_at=started,
        command=["qualification-history", f"--seeds={args.seeds}", f"--steps={args.steps}"],
        evidence_paths=[args.report],
        notes=[
            f"deterministic seeds {args.start_seed}..{args.start_seed + args.seeds - 1}",
            f"same-seed semantic replay check={'PASS' if replay_ok else 'FAIL'}",
        ],
    )
    write_envelope(envelope, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if result == GateResult.PASS else 1


def manifest_run(args: argparse.Namespace) -> int:
    manifest = aggregate_manifest(args.evidence, required_gates=args.required, artifact_paths=args.artifact)
    write_manifest(manifest, args.output)
    print(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))
    return 0 if manifest.result == GateResult.PASS else 1


def failure_run(args: argparse.Namespace) -> int:
    evidence = json.loads(args.evidence_json) if args.evidence_json else {}
    observation = FailureObservation(
        gate_id=args.gate_id,
        classification=FailureClass(args.classification),
        summary=args.summary,
        evidence=evidence,
        predecessor_id=args.predecessor,
    )
    append_failure(args.ledger, observation)
    print(json.dumps(observation.to_dict(), indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RESIDUAL Qualification v1 orchestration")
    sub = parser.add_subparsers(dest="subcommand", required=True)

    run = sub.add_parser("run", help="execute one gate and emit an evidence envelope")
    run.add_argument("--gate-id", required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--log", type=Path, required=True)
    run.add_argument("--junit", type=Path)
    run.add_argument("--evidence-path", action="append", type=Path, default=[])
    run.add_argument("--zero-skips", action="store_true")
    run.add_argument("--unknown-count", type=int, default=0)
    run.add_argument("--non-claim", action="append", default=[])
    run.add_argument("command", nargs=argparse.REMAINDER)
    run.set_defaults(func=command_run)

    history = sub.add_parser("history", help="run deterministic schedule/fault history exploration")
    history.add_argument("--gate-id", default="distributed-history")
    history.add_argument("--output", type=Path, required=True)
    history.add_argument("--report", type=Path, required=True)
    history.add_argument("--start-seed", type=int, default=20260916)
    history.add_argument("--seeds", type=int, default=50)
    history.add_argument("--steps", type=int, default=100)
    history.add_argument("--lanes", type=int, default=3)
    history.set_defaults(func=history_run)

    manifest = sub.add_parser("manifest", help="aggregate same-revision evidence into a fail-closed certificate")
    manifest.add_argument("--evidence", action="append", type=Path, required=True)
    manifest.add_argument("--required", action="append", required=True)
    manifest.add_argument("--artifact", action="append", type=Path, default=[])
    manifest.add_argument("--output", type=Path, required=True)
    manifest.set_defaults(func=manifest_run)

    failure = sub.add_parser("failure", help="append a retained failure classification observation")
    failure.add_argument("--ledger", type=Path, required=True)
    failure.add_argument("--gate-id", required=True)
    failure.add_argument("--classification", choices=[c.value for c in FailureClass], default="UNCLASSIFIED")
    failure.add_argument("--summary", required=True)
    failure.add_argument("--evidence-json")
    failure.add_argument("--predecessor")
    failure.set_defaults(func=failure_run)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
