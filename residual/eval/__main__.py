"""CLI entry: run the frozen fixture study end-to-end and write artifacts.

Usage: python3 -m residual.eval [--out evidence/eval] [--repeats 3]

CI runs this scripted development fixture (EVAL-R10). Live-model runs must
pass --live and are labeled evidence_level=live_model, kept separate from
fixture aggregates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .configs import CONFIGURATIONS
from .evidence import build_evidence_artifact, write_evidence_artifact
from .report import build_report, plotting_inputs, report_csv_rows
from .runner import recompute_from_records, run_study
from .workload import development_workload


def run_fixture_study(out_dir: Path, repeats: int = 3, *, live: bool = False,
                      root: Path | None = None) -> dict[str, object]:
    """End-to-end fixture study over R0-R5; returns the evidence artifact."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    evidence_level = "live_model" if live else "development_fixture"
    workload = development_workload()
    records = run_study(workload, repeats=repeats, evidence_level=evidence_level)
    report = build_report(workload, records, evidence_level=evidence_level)

    # Gate C: independently recompute P(X), P(A), P(X|A) and bind into report.
    recomputed = recompute_from_records(records)
    if recomputed != report["recomputed_probabilities"]:
        raise RuntimeError("recomputed probabilities diverge from report")

    stem = "live-study" if live else "fixture-study"
    (out_dir / f"{stem}.json").write_text(
        json.dumps(report, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    (out_dir / f"{stem}.csv").write_text(report_csv_rows(report), encoding="utf-8")
    (out_dir / f"{stem}-plot-inputs.json").write_text(
        json.dumps(plotting_inputs(report), sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    artifact = build_evidence_artifact(report, root=root)
    write_evidence_artifact(artifact, out_dir / f"{stem}-evidence.json")
    return artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="residual.eval")
    parser.add_argument("--out", default="evidence/eval")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--live", action="store_true",
                        help="label the run as live_model evidence")
    args = parser.parse_args(argv)
    artifact = run_fixture_study(Path(args.out), args.repeats, live=args.live)
    print(json.dumps({"evidence_sha256": artifact["evidence_sha256"],
                      "report_sha256": artifact["results"]["report_sha256"],
                      "evidence_level": artifact["evidence_level"],
                      "configurations": [c.config_id for c in CONFIGURATIONS]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
