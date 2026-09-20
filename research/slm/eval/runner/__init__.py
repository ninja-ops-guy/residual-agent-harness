"""Shared evaluation runner for EXP-M6-SLM (SLM-01..05).

Executes frozen Control Bench v0 benchmark JSONL through category verifiers
and aggregates the frozen metrics of EVALUATION-PROTOCOL.md. Stdlib-only.

Hard rules (frozen):
* the runner never trains, never tunes, and never inspects results to modify
  the benchmark;
* benchmark items are never mutated; item digests are verified before any
  backend runs on an item;
* unknown verifier_ref -> BENCHMARK_DEFECT propagation (never silently
  repaired, never scored as success or failure);
* safety metrics (fner, avr) are computed and reported separately and are
  NEVER aggregated into vmsr or any composite score.
"""
from . import backends, runner, stats

__all__ = ["backends", "runner", "stats"]
