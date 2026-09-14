from __future__ import annotations

import argparse
import json
from pathlib import Path

from residual.assurance.external import ExternalEvidenceRunner, LiveEngineSpec, load_external_suite
from residual.assurance.preregistered import (
    build_evidence_bundle,
    load_engine_config_payload,
    load_preregistration,
    preregister_from_files,
    verify_preregistration,
    write_preregistration,
)
from residual.engines.provider_bridge import ProviderEngineConfig, ProviderExecutionEngine


def load_engines(path: str | Path):
    raw = load_engine_config_payload(path)
    specs = []
    for item in raw["engines"]:
        allowed = {"provider", "model", "capabilities", "locality", "max_tokens", "temperature",
                   "system_prompt", "cost_per_task", "privacy_class", "location"}
        if set(item) - allowed:
            raise ValueError("invalid engine entry")
        config = ProviderEngineConfig(
            provider=item["provider"],
            model=item["model"],
            capabilities=tuple(item.get("capabilities", ["text"])),
            locality=item.get("locality", "cloud"),
            max_tokens=item.get("max_tokens", 2048),
            temperature=item.get("temperature", 0.0),
            system_prompt=item.get("system_prompt", "Return only the requested answer."),
        )
        specs.append(LiveEngineSpec(
            ProviderExecutionEngine(config),
            cost_per_task=float(item.get("cost_per_task", 0.0)),
            privacy_class=int(item.get("privacy_class", 0)),
            location=item.get("location", "unknown"),
        ))
    return tuple(specs)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run preregistered external assurance evidence")
    sub = parser.add_subparsers(dest="command", required=True)

    h = sub.add_parser("hash", help="print the canonical suite hash before execution")
    h.add_argument("--suite", required=True)

    pre = sub.add_parser("preregister", help="freeze suite, engines, hypotheses and stopping rule")
    pre.add_argument("--suite", required=True)
    pre.add_argument("--engines", required=True)
    pre.add_argument("--study-id", required=True)
    pre.add_argument("--registered-at", required=True)
    pre.add_argument("--hypothesis", action="append", required=True)
    pre.add_argument("--primary-metric", default="market_success_rate")
    pre.add_argument("--secondary-metric", action="append", default=[])
    pre.add_argument("--maximum-budget-usd", type=float, required=True)
    pre.add_argument("--runner-revision", required=True)
    pre.add_argument("--notes", default="")
    pre.add_argument("--output", required=True)

    verify = sub.add_parser("verify", help="verify a frozen manifest against suite and engine config")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--suite", required=True)
    verify.add_argument("--engines", required=True)

    run = sub.add_parser("run", help="run a manifest-gated external suite against live heterogeneous engines")
    run.add_argument("--manifest", required=True)
    run.add_argument("--suite", required=True)
    run.add_argument("--engines", required=True)
    run.add_argument("--output", required=True, help="evidence bundle output path")

    args = parser.parse_args(argv)
    if args.command == "hash":
        print(load_external_suite(args.suite).sha256)
        return 0

    if args.command == "preregister":
        manifest = preregister_from_files(
            study_id=args.study_id,
            registered_at=args.registered_at,
            suite_path=args.suite,
            engines_path=args.engines,
            hypotheses=tuple(args.hypothesis),
            primary_metric=args.primary_metric,
            secondary_metrics=tuple(args.secondary_metric),
            maximum_budget_usd=args.maximum_budget_usd,
            runner_revision=args.runner_revision,
            notes=args.notes,
        )
        write_preregistration(args.output, manifest)
        print(json.dumps({"manifest_sha256": manifest.sha256, "output": str(args.output)}, sort_keys=True))
        return 0

    suite = load_external_suite(args.suite)
    manifest = load_preregistration(args.manifest)
    verify_preregistration(manifest, suite, args.engines)
    if args.command == "verify":
        print(json.dumps({"verified": True, "manifest_sha256": manifest.sha256}, sort_keys=True))
        return 0

    report = ExternalEvidenceRunner(
        suite,
        load_engines(args.engines),
        maximum_budget_usd=manifest.maximum_budget_usd,
    ).run()
    bundle = build_evidence_bundle(
        manifest=manifest,
        suite=suite,
        engines_path=args.engines,
        report=report,
    )
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(bundle, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
