# RESIDUAL core harness

**A verifier-first harness that delegates the unresolved part of a task without giving the worker acceptance authority.**

This document describes the original/core RESIDUAL harness interface. The repository has grown beyond this layer into Command Station, Factory M2/M3/M4, distributed/runtime surfaces, Mission Control/WebVM, evaluation infrastructure, and bounded self-maintenance research. For current repository-wide qualification claims, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

## Core model

RESIDUAL decomposes a host-authored task into checked obligations. Local or remote workers propose results; the controller accepts only results that pass registered checks. Stronger or more expensive workers receive the remaining frontier, relevant dependency values, and concrete failure feedback rather than an unrestricted copy of every previously accepted result.

```text
Goal / task
  ↓
Obligation DAG + checks
  ↓
Worker proposal
  ↓
Independent verification
  ├─ PASS → freeze accepted value + receipt
  └─ FAIL / UNKNOWN → residual + counterexample → retry / escalate
```

The worker may be capable, weak, stochastic or wrong. The controller owns acceptance.

## Run the core harness immediately

From the repository root:

```bash
python3 -m residual demo
python3 -m residual verify-trace runs/latest/trace.jsonl --result runs/latest/result.json
python3 -m residual benchmark --output runs/benchmark.json
python3 -m unittest discover -s tests -v
```

Optional editable installation:

```bash
python3 -m pip install -e .
residual demo
```

The built-in demo is scripted and credential-free. It demonstrates controller behavior and evidence handling; it is not a live-model accuracy benchmark.

## Bring your own models

The core harness supports bounded provider adapters including Ollama, OpenAI-compatible HTTP endpoints, and custom Python/SDK providers. Command Station adds broader provider-management surfaces; see [`README.md`](README.md) and [`START-HERE.md`](START-HERE.md) for the current platform-level provider list and setup flow.

For a simple Ollama/OpenAI-compatible configuration, start from the examples under `examples/` and keep secrets in environment variables or the Station’s protected local settings rather than source control.

Example:

```bash
ollama serve
export RESIDUAL_EXPERT_API_KEY='your-provider-key'
python3 -m residual run examples/incident/task.json --config config.local.toml
```

Configured provider failure does not silently substitute a demo worker. Placement/disclosure policies still govern what evidence may leave the local host.

## Core controller invariants

| Mechanism | Implemented behavior |
| --- | --- |
| Residual frontier | Escalated workers receive unresolved, currently solvable obligations rather than already accepted independent work |
| Independent checks | Model confidence and self-declared success do not accept a result |
| Counterexample feedback | Failed checks provide bounded task-specific failure information |
| Evidence pull | Workers request exact permitted evidence windows rather than arbitrary source access |
| Frozen accepted values | Later responses cannot silently overwrite accepted obligations |
| Dependency receipts | Accepted values bind to relevant contracts, evidence and parent receipts |
| Revalidated cache | Cache hits are checked again against current inputs and verifier state |
| Explicit budgets | Calls, request bytes and output limits are bounded before provider I/O |
| Honest accounting | Reported usage, modeled estimates, unknown usage and configured prices remain distinct |
| Claim discipline | `FAIL`, `UNKNOWN`, malformed output, verifier exceptions and provider errors do not become PASS |

See [`docs/architecture.md`](docs/architecture.md) for the current architecture and trust boundaries.

## Evaluation guidance

The historical synthetic incident benchmark remains useful as a controller regression fixture, not as evidence of live LLM reliability, real token savings or API cost. Current confirmatory research uses the evaluation and reproducibility materials under `docs/` and must bind results to exact retained artifacts and exact source revisions.

Start with:

- [`docs/evaluation.md`](docs/evaluation.md)
- [`docs/research.md`](docs/research.md)
- [`docs/controlled-evaluation.md`](docs/controlled-evaluation.md)
- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)

## Relationship to the broader platform

The core harness is now one layer of a larger system:

- **Command Station** provides operator-facing mission/run/provider control.
- **Factory M2** provides bounded worker contracts/runtime and host-owned termination.
- **Factory M3** provides Station-issued evidence/receipt handoff.
- **Factory M4** provides deterministic integration/scheduler authority and a fail-closed capable-runner qualification path.
- **Mission Control/WebVM** provides browser-facing guest workflows and artifact interaction, with an active reliability gate tracked separately from Factory/M4 trust.
- **Evaluation/research** provides frozen workloads, statistics, fault campaigns and artifact-derived reporting.
- **Self-maintenance research** now includes a bounded controller and frozen research-bundle tooling from PR #132.

Current accepted `main` is `f1e62936a7ce72b801c852c1d7428d4c6ed4152c`. Exact-current-main Factory ownership, measured-binding, clean-install, capable-runner M4 workflow, Command Station, controller/provider and Pages workflows completed successfully after PR #132 merged. See `docs/CURRENT_STATUS.md` for run identities and the current non-claims.

## Self-maintenance is bounded, not autonomous merge authority

PR #132 retained one live external-model-authored research-bundle candidate and demonstrated that RESIDUAL can reconstruct, verify and classify a bounded maintenance proposal as `PR_READY` while retaining `merge_authorized=false`.

That trial does **not** establish repeated autonomous recursive self-improvement, independent external reviewer actors, or autonomous repository merge authority. Its 100-generation, 1,000-fault and 200-document-policy campaigns are synthetic controller/policy stress experiments, not repeated live model-authored maintenance runs.

## Current scope and non-claims

A passing check establishes only its declared condition. A verifier is not a universal proof oracle. Plugins and host integrations remain trusted unless another boundary explicitly isolates them. Historical results remain tied to the exact revisions that produced them.

The repository does not currently claim:

- universal correctness of worker outputs;
- a universally optimal scheduler or routing policy;
- guaranteed token/cost savings;
- blanket production readiness;
- acceptable long-run WebVM failure rate;
- every-host M4 qualification;
- completed release/recovery or elapsed soak qualification;
- proof of the central live-model reliability hypothesis;
- autonomous recursive self-improvement or autonomous merge authority.

For operational setup, use [`START-HERE.md`](START-HERE.md). For repository-wide status, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).
