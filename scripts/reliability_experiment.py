#!/usr/bin/env python3
"""Analyze and normalize Residual reliability evidence into publication artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from residual.experiments.adapters import external_market_observations, study_observations
from residual.experiments.reliability import (
    analyze_reliability,
    load_manifest,
    load_observations,
    render_markdown,
    write_artifacts,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Residual Experimental Release 1 reliability analysis")
    sub = parser.add_subparsers(dest="command", required=True)

    adapt_study = sub.add_parser("adapt-study", help="convert a frozen Study run directory into normalized observations")
    adapt_study.add_argument("run_dir")
    adapt_study.add_argument("--output", required=True)
    adapt_study.add_argument("--degradation-level", default="nominal")
    adapt_study.add_argument(
        "--map-mode", action="append", default=[], metavar="MODE=CONFIG",
        help="rename a Study mode to a preregistered reliability configuration; repeat as needed",
    )

    adapt_external = sub.add_parser("adapt-external", help="convert market-selected external assurance rows into normalized observations")
    adapt_external.add_argument("report")
    adapt_external.add_argument("--output", required=True)
    adapt_external.add_argument("--configuration", default="verified_compute_market")
    adapt_external.add_argument("--family", default="external_assurance")
    adapt_external.add_argument("--degradation-level", default="nominal")

    check = sub.add_parser("check", help="validate a frozen manifest and observations")
    check.add_argument("--manifest", required=True)
    check.add_argument("--observations", required=True)

    analyze = sub.add_parser("analyze", help="compute reliability metrics and write release artifacts")
    analyze.add_argument("--manifest", required=True)
    analyze.add_argument("--observations", required=True)
    analyze.add_argument("--output", required=True)

    report = sub.add_parser("report", help="render Markdown from a results.json artifact")
    report.add_argument("results")
    return parser


def _write_observations(path: str | Path, observations) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as stream:
        for observation in observations:
            stream.write(json.dumps(observation.payload(), sort_keys=True, separators=(",", ":")) + "\n")


def _mode_map(values: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit("--map-mode requires MODE=CONFIG")
        source, target = value.split("=", 1)
        source, target = source.strip(), target.strip()
        if not source or not target or source in mapping:
            raise SystemExit("invalid or duplicate --map-mode")
        mapping[source] = target
    return mapping


def main() -> int:
    args = _parser().parse_args()
    if args.command == "adapt-study":
        observations = study_observations(
            args.run_dir,
            mode_map=_mode_map(args.map_mode),
            degradation_level=args.degradation_level,
        )
        _write_observations(args.output, observations)
        print(json.dumps({"observations": len(observations), "output": str(Path(args.output).resolve())}, indent=2))
        return 0

    if args.command == "adapt-external":
        raw = json.loads(Path(args.report).read_text(encoding="utf-8"))
        observations = external_market_observations(
            raw,
            configuration=args.configuration,
            family=args.family,
            degradation_level=args.degradation_level,
        )
        _write_observations(args.output, observations)
        print(json.dumps({"observations": len(observations), "output": str(Path(args.output).resolve())}, indent=2))
        return 0

    if args.command in {"check", "analyze"}:
        manifest = load_manifest(args.manifest)
        observations = load_observations(args.observations)
        result = analyze_reliability(manifest, observations)
        if args.command == "check":
            print(json.dumps({
                "study_id": manifest.study_id,
                "manifest_sha256": manifest.sha256,
                "observations": len(observations),
                "result_sha256": result["sha256"],
                "status": "valid",
            }, indent=2, sort_keys=True))
            return 0
        write_artifacts(result, args.output)
        print(Path(args.output).resolve())
        return 0

    raw = json.loads(Path(args.results).read_text(encoding="utf-8"))
    print(render_markdown(raw))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
