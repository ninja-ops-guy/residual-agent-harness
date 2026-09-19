# AX-ARENA-01 — RESIDUAL Harness Causal Effect

Status: **apparatus scaffold / development fixture**.

This experiment asks a narrow question:

> Holding the model, task, environment, tools, evaluator, and budget fixed, what changes when the harness condition changes from a minimal control to RESIDUAL?

The checked-in manifest is intentionally a development fixture. It is for validating scheduling, provenance, trace extraction, and analysis before any paper-facing live-model run.

## Setup

Set the Arena preview API credential in the environment:

    export ARENA_API_KEY=...

An alternate endpoint may be supplied with:

    export ARENA_BASE_URL=https://api.preview.arena.ai/v1

Discover model IDs:

    python -m residual.workbench arena models

Freeze the protocol **before observing outcomes**:

    python -m residual.workbench arena freeze \
      --manifest experiments/AX-ARENA-01/manifest.json \
      --model arena:<MODEL_A> \
      --model arena:<MODEL_B> \
      --output runs/arena/AX-ARENA-01/lock.json

With two models, the bundled six-task evaluation fixture produces 72 scheduled observations:

    6 tasks × 2 conditions × 3 repetitions × 2 models = 72

For the originally proposed 36-observation smoke, use a separately frozen three-task workload file.

## Trace contract

Each scheduled observation must produce one `residual.arena-trace.v1` JSON object. The scorer refuses duplicate, unexpected, mismatched, or missing observations.

The trace records:

- frozen experiment/task/model/condition identity;
- harness and environment identity;
- the explicit available-tool set;
- ordered trace events;
- usage/cost fields;
- independent `verified_task_success`;
- provider provenance;
- a content digest.

For `live_model` evidence, provider metadata must identify `arena` and assert `fallback_used: false`. Server-side or unrecorded fallback is deliberately outside the protocol because it would contaminate the model-treatment label.

## Arena-aligned local signals

The local extractor implements mechanically observable counterparts of Arena's published signals:

- confirmed success;
- praise vs. complaint;
- steerability after an explicitly labelled correction;
- bash recovery;
- tool hallucination.

These are **Arena-aligned local measurements**, not official Arena leaderboard scores.

Score a complete trace file:

    python -m residual.workbench arena score \
      --lock runs/arena/AX-ARENA-01/lock.json \
      --traces runs/arena/AX-ARENA-01/traces.jsonl \
      --output runs/arena/AX-ARENA-01/report.json

The report includes per-model/per-condition aggregates plus a paired RESIDUAL-minus-control success-rate estimate with a deterministic task-cluster bootstrap interval.

## Promotion path

1. Synthetic/unit qualification.
2. Development-fixture smoke.
3. Freeze an independently authored task corpus and hidden evaluator.
4. Change the manifest evidence level to `live_model`.
5. Freeze exact Arena model IDs, environment, tool set, prompts, budgets, evaluator, and source revision.
6. Run control and RESIDUAL conditions from the frozen schedule.
7. Retain failures, UNKNOWNs, rejected work, provider errors, and incomplete cells.
8. Only then interpret harness effects.

Do not use the development fixture as evidence that RESIDUAL outperforms another harness or model.
