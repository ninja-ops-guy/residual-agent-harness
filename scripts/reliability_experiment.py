#!/usr/bin/env python3
"""Analyze frozen Residual reliability observations into publication artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

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


def main() -> int:
    args = _parser().parse_args()
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
