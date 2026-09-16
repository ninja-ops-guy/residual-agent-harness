# RESIDUAL core harness

**A verifier-first harness that delegates unresolved work without giving the worker acceptance authority.**

This document describes the original/core RESIDUAL harness layer. The repository has grown beyond it into Command Station, Factory M2/M3/M4, distributed/runtime surfaces, Mission Control/WebVM, evaluation infrastructure and bounded self-maintenance research. For repository-wide qualification claims, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

## Core model

RESIDUAL decomposes a host-authored task into checked obligations. Local or remote workers propose results; the controller accepts only results that pass registered checks. Stronger or more expensive workers receive the unresolved frontier, relevant dependency values and bounded failure/evidence context rather than unilateral authority over accepted state.

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

## Run the core harness

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

The core harness supports bounded provider adapters including Ollama, OpenAI-compatible HTTP endpoints and custom Python/SDK providers. Command Station and Mission Control add broader provider-management and browser-provider surfaces. Configured provider failure does not silently substitute a demo worker, and disclosure/placement policies still govern what evidence may leave the local host.

For operator/provider setup, use [`README.md`](README.md) and [`START-HERE.md`](START-HERE.md).

## Core controller invariants

| Mechanism | Implemented behavior |
| --- | --- |
| Residual frontier | Escalated workers receive unresolved, currently solvable obligations rather than already accepted independent work |
| Independent checks | Model confidence and self-declared success do not accept a result |
| Counterexample feedback | Failed checks provide bounded task-specific failure information |
| Evidence pull | Workers request permitted evidence windows rather than arbitrary source access |
| Frozen accepted values | Later responses cannot silently overwrite accepted obligations |
| Dependency receipts | Accepted values bind to relevant contracts, evidence and parent receipts |
| Revalidated cache | Cache hits are checked again against current inputs and verifier state |
| Explicit budgets | Calls, request bytes and output limits are bounded before provider I/O |
| Honest accounting | Reported usage, modeled estimates and unknown usage remain distinct |
| Claim discipline | `FAIL`, `UNKNOWN`, malformed output, verifier exceptions and provider errors do not become `PASS` |

See [`docs/architecture.md`](docs/architecture.md) for the broader architecture and trust boundaries.

## Relationship to the broader platform

The core harness is now one layer of a larger system:

- **Command Station** provides operator-facing mission/run/provider control.
- **Factory M2** provides bounded worker contracts/runtime and host-owned termination.
- **Factory M3** provides Station-issued evidence/receipt handoff.
- **Factory M4** provides deterministic integration/scheduler authority and capable-runner qualification machinery.
- **Mission Control/WebVM** provides browser-facing real-guest workflows, artifact interaction and real-provider transport.
- **Evaluation/research** provides frozen workloads, statistics, fault campaigns, evidence bundles and economics/observability surfaces.
- **Self-maintenance research** includes bounded proposal/verification tooling with no autonomous merge authority.

Current `main` is **`0580c1e53ddb9163d2423d82c0bca846a6d68ba2`**. Its observed automated/browser qualification is **PASS**, while independent technical acceptance remains review-provisional because merged PRs #145 and #147 have no submitted reviews in the retained GitHub review record. The current browser/runtime path includes #145's libc-relative polling mitigation for long-lived WebVM paths and #147's Puter response-conformance hardening. Exact merged-main Pages run `35138502311` passed generated desktop+narrow browser proof plus published desktop/narrow acceptance. That is exact-revision browser evidence, not independent approval, live-provider quality or long-run WebVM reliability.

The latest retained real-account provider attempt before #147 remained **FAIL** as `provider_protocol_invalid`; no candidate was accepted. A successful post-#147 real-account run has not yet been retained, so live-provider acceptance remains **UNKNOWN / not established** despite green automated contract/browser CI.

Issues #120 and #126 remain open. Retained diagnostics isolate a WebVM-specific process-local CPython positive-duration timed-wait failure, while the merged runtime avoids that known surface in its long-lived browser polling. The historical guest-corruption root cause and acceptable recurrence rate remain **UNKNOWN**.

## Factory and governance boundaries

Issues #63 and #48 are closed; M2/M3/M4 are implemented and the implementation manifest is no longer the old pre-merge status snapshot. M4 qualification remains evidence- and environment-bound. Namespace-unavailable hosts are `BLOCKED`/`UNKNOWN`, not `PASS`.

PR #139 still changes a protected M4 qualification test. Its capable-runner evidence is not permission to advance the protected ownership pin automatically. Independent exact-head review, deliberate baseline handling and fresh qualification remain mandatory before that repair can support downstream #134 work.

Issue #144 tracks a separate governance gap: the repository expects independent technical acceptance for important integration work, but platform enforcement is not yet complete. PR #146 is a repository-side enforcement candidate and currently has a fail-closed independent-review check plus another red CI lane. PRs #145 and #147 have no submitted reviews in the retained GitHub review record, so their green CI must not be relabeled as independent approval.

## Evaluation guidance

The historical synthetic benchmark remains useful as a controller regression fixture, not as evidence of live LLM reliability, real token savings or API cost. Confirmatory research must bind results to exact source revisions, workload identity, execution identity, verifier policy and retained artifacts.

Start with:

- [`docs/evaluation.md`](docs/evaluation.md)
- [`docs/research.md`](docs/research.md)
- [`docs/controlled-evaluation.md`](docs/controlled-evaluation.md)
- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)

## Self-maintenance is bounded

Merged PR #132 retained one live external-model-authored research-bundle candidate and demonstrated that RESIDUAL can reconstruct, verify and classify a bounded maintenance proposal as `PR_READY` while retaining `merge_authorized=false`.

That trial does not establish repeated autonomous recursive self-improvement, independent external reviewer actors or autonomous repository merge authority. Its 100-generation, 1,000-fault and 200-document-policy campaigns are synthetic controller/policy stress experiments, not repeated live model-authored maintenance runs.

## Current scope and non-claims

A passing check establishes only its declared condition. A verifier is not a universal proof oracle. Plugins and host integrations remain trusted unless another boundary explicitly isolates them. Historical results remain tied to the exact revisions that produced them.

The repository does not currently claim universal worker correctness, a universally optimal scheduler, guaranteed token/cost savings, blanket production readiness, every-host M4 qualification, completed release/recovery or elapsed-soak qualification, acceptable long-run WebVM reliability, successful post-#147 real-provider inference, proof of the central live-model reliability hypothesis, autonomous recursive self-improvement or autonomous merge authority.

For operational setup, use [`START-HERE.md`](START-HERE.md). For current repository-wide status, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).
