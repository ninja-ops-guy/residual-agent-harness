# AX-ARENA-01 — RESIDUAL Harness Causal Effect

Status: **apparatus scaffold / development fixture**.

This experiment asks a narrow question:

> Holding the model, task, environment, tools, evaluator, and budget fixed, what changes when the harness condition changes from a minimal control to RESIDUAL?

The checked-in manifest is intentionally a development fixture. It is for validating scheduling, provenance, trace extraction, and analysis before any paper-facing live-model run.

## Setup

### Command Station

Open **Model Workshop**, choose **Arena API** as the cloud provider, and use the **Get Arena API key** button. It opens Arena's virtual-key page directly. Paste the copied key back into RESIDUAL and click **Save model routes**. RESIDUAL automatically loads the models available to that key; click **Use this model** and it saves the model ID and runs the connection test automatically.

### Terminal

Open the same key page from RESIDUAL:

    residual arena setup

Set the Arena preview API credential in the environment:

    export ARENA_API_KEY=...

An alternate endpoint may be supplied with:

    export ARENA_BASE_URL=https://api.preview.arena.ai/v1

Discover model IDs:

    residual arena models

Freeze the protocol **before observing outcomes**:

    residual arena freeze \
      --manifest experiments/AX-ARENA-01/manifest.json \
      --model arena:<MODEL_A> \
      --model arena:<MODEL_B> \
      --output runs/arena/AX-ARENA-01/lock.json

With two models, the bundled six-task evaluation fixture produces 72 scheduled observations:

    6 tasks × 2 conditions × 3 repetitions × 2 models = 72

For the originally proposed 36-observation smoke, use a separately frozen three-task workload file.

### Live transport smoke

The checked-in `live-smoke.manifest.json` uses the same public development tasks but marks the execution evidence as live-model evidence. It is an **apparatus/transport smoke**, not an independent held-out benchmark.

Freeze it after choosing one Arena model:

    residual arena freeze \
      --manifest experiments/AX-ARENA-01/live-smoke.manifest.json \
      --model arena:<MODEL_ID> \
      --output runs/arena/AX-ARENA-01-live.lock.json

Then execute the frozen randomized schedule end-to-end:

    residual arena run \
      --lock runs/arena/AX-ARENA-01-live.lock.json \
      --output runs/arena/AX-ARENA-01-live

The live runner performs a raw one-call Arena control and the same requested model behind RESIDUAL's actual obligation harness. It withholds each task's expected answer from both model inputs, uses the frozen answer only in trusted verification/evaluation code, writes one durable trace per scheduled cell, records provider failures as `UNKNOWN`, validates Arena's actual resolved-model/trace provenance, and automatically emits `report.json`.

The runner refuses to start if the repository source hashes differ from the frozen lock or if the protocol is still labelled `development_fixture`.

## Trace contract

Each scheduled observation must produce one `residual.arena-trace.v1` JSON object. The scorer refuses duplicate, unexpected, mismatched, or missing observations.

The trace records:

- frozen experiment/task/model/condition identity;
- harness and environment identity;
- the explicit available-tool set;
- ordered trace events;
- usage/cost fields;
- the evaluator's `verified_task_success` verdict;
- provider provenance;
- a content digest.

For `live_model` evidence, provider metadata must identify `arena`, assert `fallback_used:false`, and retain Arena's `X-Arena-Resolved-Model` and `X-Arena-Trace-ID` values for every completed gateway call. Arena trace IDs must be unique. A RESIDUAL treatment with multiple repair calls must resolve every completed call to the same Arena model, and the paired control/treatment cells must resolve to the same model. Any fallback header, missing provenance on a completed call, or resolved-model mismatch fails the scorer rather than weakening attribution.

## Arena-aligned local signals

The local extractor implements mechanically observable counterparts of Arena's published signals:

- confirmed success;
- praise vs. complaint;
- steerability after an explicitly labelled correction;
- bash recovery;
- tool hallucination.

These are **Arena-aligned local measurements**, not official Arena leaderboard scores.

Score a complete trace file:

    residual arena score \
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
