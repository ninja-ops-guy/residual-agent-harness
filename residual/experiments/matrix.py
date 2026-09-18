"""Reproducible experiment matrix for distributed RESIDUAL control paths."""
from __future__ import annotations

from typing import Any

from residual.core import digest

from .distributed import run_station_distributed_benchmark
from .pipeline import run_station_pipeline_benchmark
from .recovery import run_station_recovery_benchmark


def run_experiment_matrix(
    *,
    worker_counts: tuple[int, ...] = (1, 2, 4),
    latencies_ms: tuple[float, ...] = (0.0, 40.0, 200.0),
    independent_tasks: int = 8,
    pipeline_width: int = 4,
    pipeline_depth: int = 2,
    repeats: int = 1,
    include_recovery: bool = True,
) -> dict[str, Any]:
    if not worker_counts or len(worker_counts) != len(set(worker_counts)):
        raise ValueError("worker_counts must be unique and nonempty")
    if not latencies_ms or any(value < 0 for value in latencies_ms):
        raise ValueError("latencies_ms must be nonempty and nonnegative")
    if len(latencies_ms) != len(set(latencies_ms)):
        raise ValueError("latencies_ms must be unique")
    if repeats < 1:
        raise ValueError("repeats must be positive")

    cells = []
    for latency in latencies_ms:
        independent = run_station_distributed_benchmark(
            worker_counts=worker_counts,
            tasks=independent_tasks,
            work_ms=latency,
            repeats=repeats,
        )
        pipeline = run_station_pipeline_benchmark(
            worker_counts=worker_counts,
            width=pipeline_width,
            depth=pipeline_depth,
            work_ms=latency,
            repeats=repeats,
        )
        recovery = (
            run_station_recovery_benchmark(
                bad_ms=max(0.0, latency / 2.0),
                good_ms=latency,
                repeats=repeats,
            )
            if include_recovery else None
        )

        independent_best = max(
            independent["summary"],
            key=lambda row: row["full_workflow_speedup_vs_min_workers"],
        )
        pipeline_best = max(
            pipeline["summary"],
            key=lambda row: row["speedup_vs_min_workers"],
        )
        cells.append({
            "synthetic_worker_latency_ms": latency,
            "independent": independent,
            "pipeline": pipeline,
            "recovery": recovery,
            "derived": {
                "independent_best_workers": independent_best["workers"],
                "independent_best_candidate_speedup": max(
                    row["candidate_speedup_vs_min_workers"]
                    for row in independent["summary"]
                ),
                "independent_best_full_workflow_speedup": independent_best[
                    "full_workflow_speedup_vs_min_workers"
                ],
                "pipeline_best_workers": pipeline_best["workers"],
                "pipeline_best_speedup": pipeline_best["speedup_vs_min_workers"],
                "recovery_penalty_ratio": (
                    recovery["summary"]["recovery_penalty_ratio"]
                    if recovery else None
                ),
            },
        })

    config = {
        "worker_counts": list(worker_counts),
        "latencies_ms": list(latencies_ms),
        "independent_tasks": independent_tasks,
        "pipeline_width": pipeline_width,
        "pipeline_depth": pipeline_depth,
        "repeats": repeats,
        "include_recovery": include_recovery,
    }
    return {
        "schema_version": "residual.distributed-experiment-matrix.v1",
        "evidence_level": "development_fixture",
        "simulation": True,
        "configuration": config,
        "cells": cells,
        "claim_boundary": (
            "This matrix composes controlled loopback development fixtures. It is "
            "designed to identify where control-plane and integration overhead become "
            "material as synthetic model latency changes. It is not live-model, "
            "physical-network, or model-quality evidence."
        ),
        "matrix_hash": digest(config),
    }
