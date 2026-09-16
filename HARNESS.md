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

Current `main` is **`f6f9bad84caccf68c7ab35e5788e756d12c55fb7`**, the merge of PR #156. The underlying #151 live-pipeline work remains present; #156 specifically repairs real Puter worker-envelope conformance by removing provider-side strict structured-output mode for dynamic obligation keys and restoring explicit build-envelope nesting guidance.

All seven observed main-push workflows passed on that exact merged revision. The capable-runner M4 workflow passed its fail-closed capability/zero-skip gate, and Pages run `35158939226` passed on attempt 1 through generated desktop+narrow proof, deployment, published real-guest execution and published narrow-Chromium acceptance.

These are exact-revision automated/browser results, not every-host qualification or independent review. PR #156 has **zero submitted reviews**, so current main is technically qualified but **review-provisional**.

The latest retained real-account provider evidence before #156 is still **FAIL** as `provider_protocol_invalid`: two actual remote calls produced no accepted obligation or artifact. Green post-merge provider/browser CI is not a real-account provider success. A fresh successful paid/live Puter run on exact current main is **UNKNOWN / not retained**.

Issues #120/#126 remain open. Retained WebVM diagnostics isolate a process-local CPython positive-duration timed-wait failure surface; the merged browser path avoids the known trigger, but the historical corruption-family root cause and acceptable recurrence rate remain **UNKNOWN**.

## Factory and governance boundaries

Issues #63 and #48 are closed; M2/M3/M4 are implemented and `implementation-status.yaml` is the implementation-presence manifest. M4 qualification remains evidence- and environment-bound. Namespace/capability-unavailable hosts are `BLOCKED`/`UNKNOWN`, not `PASS`.

PR #139 still modifies a protected M4 qualification test. Independent exact-head review, deliberate ownership-baseline handling and fresh qualification remain mandatory before that repair can support downstream #134. This documentation does not modify protected bytes, ownership pins, qualification anchors or evidence schemas.

Issue #144 tracks independent-review enforcement. PR #146 is now refreshed onto exact current main at head `c416d408149408ff8668a48d6e73eb1f3bf6347e` with the same four-file governance diff. Fresh exact-head CI and genuinely independent write-authorized approval are still required; platform ruleset enforcement remains a separate maintainer action after integration.

## Browser acceptance and qualification work

PR #89 retains an authoritative narrow-browser `FAIL` caused by a terminal-proof observation defect; that failure is not rerun away. PR #153 now consolidates the bounded #140/#150 repairs on exact current main at head `35cbf2ba060bc04aabb6cfd10fbf90dc8dbccb77`. Its earlier green evidence is historical; fresh exact-head qualification and genuinely independent review are still required before integration, and only then should #89 be refreshed/requalified.

PR #152 builds a broader evidence-first Qualification v1 framework. Its prior exact-head evidence remains tied to its pre-#156 base. It must refresh/requalify; virtual-day stress is not elapsed soak and a planned live-provider canary is not model-quality evidence.

## Evaluation guidance

The scripted benchmark remains useful as a controller regression fixture, not as evidence of live LLM reliability, token savings or API cost. Confirmatory research must bind results to exact source, workload, execution identity, verifier policy and retained artifacts.

Start with:

- [`docs/evaluation.md`](docs/evaluation.md)
- [`docs/research.md`](docs/research.md)
- [`docs/controlled-evaluation.md`](docs/controlled-evaluation.md)
- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)

## Current scope and non-claims

A passing check establishes only its declared condition. A verifier is not a universal proof oracle. Historical results remain tied to the exact revisions that produced them.

The repository does not currently claim universal worker correctness, universally optimal scheduling, guaranteed token/cost savings, blanket production readiness, every-host M4 qualification, completed release/recovery or elapsed-soak qualification, acceptable long-run WebVM reliability, successful post-#156 real-provider inference, proof of the central live-model reliability hypothesis, autonomous recursive self-improvement or autonomous merge authority.

For operational setup, use [`START-HERE.md`](START-HERE.md). For current repository-wide status, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).
