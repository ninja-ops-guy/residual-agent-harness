"""Machine-readable evidence artifact generation (Gate B).

Runs the deterministic fixture through the collector and report builder and
writes a JSON artifact under evidence/obs/ capturing commit/tree identity,
runtime versions, raw observations, the Prometheus export, and the exported
reliability report (twice, proving hash stability).
"""
from __future__ import annotations

import json
import platform
import subprocess
import sys

from .exporter import render_telemetry_prometheus
from .fixtures import FIXTURE_ID, build_fixture_observations
from .metric_families import TelemetryCollector
from .report import build_reliability_report
from .schema import hash_observations


def git_identity(repo_path: str = ".") -> dict:
    def _git(*args):
        try:
            return subprocess.run(
                ["git", "-C", repo_path, *args],
                capture_output=True, text=True, check=True,
            ).stdout.strip()
        except Exception:
            return "unavailable"

    return {
        "commit": _git("rev-parse", "HEAD"),
        "tree": _git("rev-parse", "HEAD^{tree}"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
    }


def generate_evidence(repo_path: str = ".") -> dict:
    observations = build_fixture_observations()
    collector = TelemetryCollector()
    for obs in observations:
        collector.ingest(obs)
    identity = git_identity(repo_path)
    report_a = build_reliability_report(
        collector.observations, experiment_id=FIXTURE_ID, source_identity=identity)
    # Rebuild from a fresh fixture run: observations alone must reproduce the
    # same report hash (Gate C / acceptance).
    fresh = build_fixture_observations()
    report_b = build_reliability_report(
        fresh, experiment_id=FIXTURE_ID, source_identity=identity)
    reproduction_ok = report_a["report_hash"] == report_b["report_hash"]
    return {
        "spec": "SPEC-SWARM-OBS-006",
        "fixture_id": FIXTURE_ID,
        "identity": identity,
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "raw_observations": observations,
        "observation_hash": hash_observations(observations),
        "prometheus_export": render_telemetry_prometheus(collector).splitlines(),
        "report": report_a,
        "reproduction": {
            "first_report_hash": report_a["report_hash"],
            "second_report_hash": report_b["report_hash"],
            "identical_hash": reproduction_ok,
        },
    }


def main(argv=None) -> int:
    import argparse
    import pathlib

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="evidence/obs/obs006-evidence.json")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    artifact = generate_evidence(args.repo)
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    print(f"wrote {out_path} (reproduction_ok={artifact['reproduction']['identical_hash']})")
    return 0 if artifact["reproduction"]["identical_hash"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
