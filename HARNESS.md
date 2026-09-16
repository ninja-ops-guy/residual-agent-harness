# RESIDUAL core harness

**A verifier-first harness that delegates unresolved work without giving the worker acceptance authority.**

This document describes the original/core RESIDUAL harness layer. The repository has expanded into Command Station, Factory M2/M3/M4, distributed/runtime surfaces, Mission Control/WebVM, evaluation infrastructure and bounded self-maintenance research. For repository-wide qualification claims, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

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

The built-in demo is scripted and credential-free. It demonstrates controller behavior and evidence handling; it is not a live-model accuracy benchmark.

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

## Relationship to the broader platform

- **Command Station** provides operator-facing mission/run/provider control.
- **Factory M2** provides bounded worker contracts/runtime and host-owned termination.
- **Factory M3** provides Station-issued evidence/receipt handoff.
- **Factory M4** provides deterministic integration/scheduler authority and capable-runner qualification machinery.
- **Mission Control/WebVM** provides browser-facing real-guest workflows, artifact interaction and provider transport.
- **Evaluation/research** provides frozen workloads, statistics, fault campaigns, evidence bundles and economics/observability surfaces.
- **Self-maintenance research** includes bounded proposal/verification tooling with no autonomous merge authority.

## Current repository boundary

Current `main` is **`f2d58e779ad589fe1d08842c9efc40ec5214a213`**. PR #151 adds an event-backed Mission Control live-pipeline projection and stricter Puter transport while leaving the core harness acceptance authority and Factory/M4 evidence boundary unchanged.

All seven observed main-push qualification workflows passed on that exact merged revision. Capable-runner M4 run `35149837820` completed **142 tests + 84 subtests, zero skips**, and Pages run `35149837756` passed first-attempt generated and published desktop+narrow real-guest acceptance. These are exact-revision automated/browser results, not every-host qualification or independent review.

PR #151 has **zero submitted reviews**, so current main is technically qualified but **review-provisional**. Earlier merged #145/#147 also retain missing independent pre-merge acceptance as governance debt.

The post-merge browser proof used the explicit SDK test double and records `cloud_inference: NOT_RUN`. A fresh successful real-account Puter run on exact current main is therefore **UNKNOWN / not established**. The latest retained real-account path remains a fail-closed `provider_protocol_invalid` result with no accepted candidate.

Issues #120/#126 remain open. Retained WebVM diagnostics isolate a process-local CPython positive-duration timed-wait failure surface; the merged browser path avoids the known trigger, but the historical corruption-family root cause and acceptable recurrence rate remain **UNKNOWN**.

## Factory and governance boundaries

Issues #63 and #48 are closed; M2/M3/M4 are implemented and the implementation manifest is no longer the old pre-merge status snapshot. M4 qualification remains evidence- and environment-bound. Namespace/capability-unavailable hosts are `BLOCKED`/`UNKNOWN`, not `PASS`.

PR #139 still modifies a protected M4 qualification test. Independent exact-head review, deliberate ownership-baseline handling and fresh qualification remain mandatory before that repair can support downstream #134. This documentation does not modify protected bytes, ownership pins or evidence schemas.

Issue #144 tracks independent-review enforcement. PR #146 is rebuilt directly on current main and implements a fail-closed current-head review check, but platform ruleset enforcement still requires a maintainer action after independent acceptance.

## Browser acceptance and qualification work

PR #89 retains an authoritative narrow-browser `FAIL` caused by a terminal-proof observation defect; that failure is not rerun away. Closed-unmerged #140/#150 are superseded by current-main PR #153, which consolidates their bounded acceptance-harness repairs. #153 is still qualifying and has no submitted independent review, so no `PASS` is inherited from the stale branches.

Draft PR #152 builds a broader evidence-first qualification framework, but its workflows are still partial/in progress. The framework itself does not constitute completed release qualification or elapsed soak evidence.

## Evaluation guidance

The scripted benchmark remains useful as a controller regression fixture, not as evidence of live LLM reliability, token savings or API cost. Confirmatory research must bind results to exact source, workload, execution identity, verifier policy and retained artifacts.

Start with:

- [`docs/evaluation.md`](docs/evaluation.md)
- [`docs/research.md`](docs/research.md)
- [`docs/controlled-evaluation.md`](docs/controlled-evaluation.md)
- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)

## Current scope and non-claims

A passing check establishes only its declared condition. A verifier is not a universal proof oracle. Historical results remain tied to the exact revisions that produced them.

The repository does not currently claim universal worker correctness, universally optimal scheduling, guaranteed token/cost savings, blanket production readiness, every-host M4 qualification, completed release/recovery or elapsed-soak qualification, acceptable long-run WebVM reliability, successful post-#151 real-provider inference, proof of the central live-model reliability hypothesis, autonomous recursive self-improvement or autonomous merge authority.

For operational setup, use [`START-HERE.md`](START-HERE.md). For current repository-wide status, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).
