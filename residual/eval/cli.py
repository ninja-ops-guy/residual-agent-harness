"""CLI for SPEC-EVAL-001 comparative evidence.

The default driver is deliberately labelled simulated: it exercises the repository's
frozen workload and single/fixed/dynamic backend primitives without claiming measured
production performance. Measured Factory counters can be recorded through
``SpecEvaluationEvidence`` directly by production orchestration.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from observation_layer import ObservationBus
from observation_layer.sinks import JsonlFileSink
from residual.factory.evidence_receipts import StationIdentity

from .ablations import ABLATIONS
from .runner import DynamicSwarmBackend, FixedSwarmBackend, SingleAgentBackend
from .spec_eval import CostRates, ExecutionControls, RunCounters, SpecEvaluationEvidence
from .workload import FrozenWorkload


_BACKENDS = {
    "single": SingleAgentBackend,
    "fixed": lambda: FixedSwarmBackend(size=4),
    "dynamic": lambda: DynamicSwarmBackend(min_size=1, max_size=8),
}


def _configuration_list(value: str) -> tuple[str, ...]:
    configs = tuple(part.strip() for part in value.split(",") if part.strip())
    if len(configs) != len(set(configs)) or set(configs) != {"single", "fixed", "dynamic"}:
        raise argparse.ArgumentTypeError("configs must contain single,fixed,dynamic exactly once")
    return configs


def _simulated_counters(workload: FrozenWorkload, configuration: str,
                        run_index: int, seed: int) -> RunCounters:
    backend = _BACKENDS[configuration]()
    ablation = ABLATIONS["full"]
    results = []
    for task in workload.tasks:
        rng = random.Random(f"{seed}:{configuration}:{task.task_id}:{run_index}")
        results.append(backend.run_task(task, rng, None, ablation))

    elapsed_seconds = max(0.001, sum(result.elapsed_ms for result in results) / 1000.0)
    accepted = sum(1 for result in results if result.success)
    rejected = len(results) - accepted
    coordination_fraction = float(getattr(backend, "coordination_overhead", 0.0))
    # These are simulator counters, not production measurements. The evidence record
    # carries evidence_mode=simulated so downstream publication tooling cannot mistake
    # them for Factory wall-clock/GPU observations.
    return RunCounters(
        elapsed_seconds=elapsed_seconds,
        accepted_tasks=accepted,
        total_tasks=len(results),
        tokens_used=sum(result.tokens_used for result in results),
        gpu_seconds=0.0,
        coordination_seconds=min(elapsed_seconds, elapsed_seconds * coordination_fraction),
        rework_tasks=rejected,
        merge_conflicts=0,
        verifier_rejections=rejected,
        verifier_outputs=len(results),
        tests_passed=accepted,
        tests_total=len(results),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="residual evaluate",
        description="Run SPEC-EVAL-001 single/fixed/dynamic comparative evaluation",
    )
    parser.add_argument("--workload", required=True, help="FrozenWorkload JSON artifact")
    parser.add_argument("--configs", type=_configuration_list, default=("single", "fixed", "dynamic"),
                        help="comma-separated: single,fixed,dynamic")
    parser.add_argument("--runs", type=int, default=3, help="runs per configuration (minimum 3)")
    parser.add_argument("--seed", type=int, default=20260914)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--api-cost-per-1k-tokens", type=float, default=0.0)
    parser.add_argument("--gpu-cost-per-hour", type=float, default=0.0)
    parser.add_argument("--infrastructure-cost-per-run", type=float, default=0.0)
    parser.add_argument("--station-key", help="existing Station Ed25519 private key PEM")
    parser.add_argument("--output", default="runs/spec-eval/report.json")
    parser.add_argument("--observations", default="runs/spec-eval/observations.jsonl")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.runs < 3:
        raise ValueError("SPEC-EVAL-001 requires at least three runs per configuration")
    for name in ("api_cost_per_1k_tokens", "gpu_cost_per_hour", "infrastructure_cost_per_run"):
        if getattr(args, name) < 0:
            raise ValueError(f"{name} must be nonnegative")

    workload = FrozenWorkload.from_json(Path(args.workload).read_text(encoding="utf-8"))
    identity = (
        StationIdentity.load_private(args.station_key)
        if args.station_key else StationIdentity.generate()
    )
    output = Path(args.output)
    observations = Path(args.observations)
    output.parent.mkdir(parents=True, exist_ok=True)
    observations.parent.mkdir(parents=True, exist_ok=True)

    sink = JsonlFileSink(str(observations))
    bus = ObservationBus(sink=sink, trace_id=f"spec-eval-{workload.manifest_hash[:16]}")
    evidence = SpecEvaluationEvidence(workload, identity, observation_bus=bus, minimum_runs=args.runs)
    rates = CostRates(
        api_cost_per_1k_tokens=args.api_cost_per_1k_tokens,
        gpu_cost_per_hour=args.gpu_cost_per_hour,
        infrastructure_cost_per_run=args.infrastructure_cost_per_run,
    )
    controls = ExecutionControls(
        engine_ids=("residual-eval-simulator@v1",),
        model_versions=("deterministic-simulator-v1",),
        temperatures=(args.temperature,),
        seed=args.seed,
    )
    try:
        for configuration in args.configs:
            for run_index in range(args.runs):
                evidence.record_run(
                    configuration,
                    run_index,
                    _simulated_counters(workload, configuration, run_index, args.seed),
                    controls,
                    rates=rates,
                    evidence_mode="simulated",
                )
        report = evidence.build_report()
        bus.flush()
    finally:
        bus.close()

    document = report.to_dict()
    document["station_public_key_hex"] = identity.public_bytes().hex()
    document["identity_mode"] = "persistent" if args.station_key else "ephemeral-evaluation-only"
    document["evidence_notice"] = (
        "simulated backend evidence; do not cite as measured Factory production performance"
    )
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "report": str(output),
        "observations": str(observations),
        "report_hash": report.report_hash,
        "station_key_id": report.station_key_id,
        "identity_mode": document["identity_mode"],
        "evidence_mode": "simulated",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
