"""CLI entry for deterministic fixture and genuine provider-backed live worker evaluation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .configs import CONFIGURATIONS
from .evidence import build_evidence_artifact, write_evidence_artifact
from .report import build_report, plotting_inputs, report_csv_rows
from .runner import recompute_from_records, run_study
from .workload import development_workload
from .live import probe_provider, run_live_worker


def run_fixture_study(out_dir: Path, repeats: int = 3,
                      root: Path | None = None) -> dict[str, object]:
    """End-to-end scripted fixture over R0-R5."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    workload = development_workload()
    records = run_study(workload, repeats=repeats, evidence_level="development_fixture")
    report = build_report(workload, records, evidence_level="development_fixture")
    recomputed = recompute_from_records(records)
    if recomputed != report["recomputed_probabilities"]:
        raise RuntimeError("recomputed probabilities diverge from report")
    stem = "fixture-study"
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


def run_live_worker_study(out_dir: Path, repeats: int, *, provider: str,
                          model: str) -> dict[str, object]:
    """Run genuine provider calls without pretending scripted controls were live."""
    if repeats < 3:
        raise ValueError("live evaluation requires at least 3 repeats")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    probe = probe_provider(provider=provider, model=model)
    workload = development_workload()
    observations = []
    for task in workload.slice_tasks("evaluation"):
        for repeat in range(repeats):
            obs = run_live_worker(task, repeat, provider=provider, model=model,
                                  seed=workload.seed)
            observations.append(obs.__dict__)
    payload = {
        "schema_version": "residual.live-worker-eval.v1",
        "evidence_level": "live_model_worker_only",
        "warning": "Provider execution is live; R0-R5 control-layer outcomes are not claimed by this artifact.",
        "workload_sha256": workload.sha256,
        "provider_probe": probe,
        "repeats": repeats,
        "observations": observations,
    }
    (out_dir / "live-worker-study.json").write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="residual.eval_frozen")
    parser.add_argument("--out", default="evidence/eval")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--live", action="store_true",
                        help="execute a genuine provider-backed worker study")
    parser.add_argument("--provider", default="ollama",
                        help="live provider (default: ollama)")
    parser.add_argument("--model",
                        help="required model id for --live")
    args = parser.parse_args(argv)
    if args.live:
        if not args.model:
            parser.error("--live requires --model; no synthetic fallback is permitted")
        result = run_live_worker_study(Path(args.out), args.repeats,
                                       provider=args.provider, model=args.model)
        print(json.dumps({
            "evidence_level": result["evidence_level"],
            "provider": args.provider,
            "model": args.model,
            "observations": len(result["observations"]),
            "workload_sha256": result["workload_sha256"],
        }, indent=2))
        return 0
    artifact = run_fixture_study(Path(args.out), args.repeats)
    print(json.dumps({"evidence_sha256": artifact["evidence_sha256"],
                      "report_sha256": artifact["results"]["report_sha256"],
                      "evidence_level": artifact["evidence_level"],
                      "configurations": [c.config_id for c in CONFIGURATIONS]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
