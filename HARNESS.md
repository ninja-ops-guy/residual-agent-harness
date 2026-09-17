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
- **Mission Control/WebVM** provides browser-facing real-guest workflows, artifact interaction, provider transport and whole-guest fresh-overlay recovery after a poisoned worker.
- **Evaluation/research** provides frozen workloads, statistics, fault campaigns, evidence bundles and economics/observability surfaces.
- **Self-maintenance research** includes bounded proposal/verification tooling with no autonomous merge authority.

## Current repository boundary

Current `main` is **`2b7cb626a9a327cf56ede847fa4e6ae6cdf9243f`**. It contains merged #159 poisoned-guest fresh-overlay recovery, merged #168 solo-maintainer governance, and merged #153 browser terminal-proof/control-unlock acceptance repairs.

The final #153 candidate was green for its applicable exact-head workflows and carried the exact-head maintainer attestation required by the repository's current governance model. That does not make the merged revision fully green: current-main Controller/provider run `35172926291` is **FAIL** in Python 3.12, while current-main Pages run `35172926305` is **PASS**.

The red lane is a retained protected M4 safety-test observation race in `test_timeout_kills_process_group_not_only_parent`: `/proc/<pid>/status` disappeared between `exists()` and `read_text()`, raising `FileNotFoundError`. Python 3.11 completed the same controller/provider workflow successfully; Python 3.13 was cancelled after the matrix failure. The exact main workflow therefore remains **FAIL**, not an inferred pass.

## Live provider / WebVM boundary

A retained post-#156 iPhone/WebKit public-demo attempt reached **`Provider connected`** but then exposed **`RESIDUAL_WORKER_POISONED`** while Mission Control remained at **`GUEST STARTING`**. That observed end-to-end mission is **FAIL** at the guest-recovery/product boundary. No valid paid/live provider candidate completed the normal verifier path, so successful paid/live Puter execution remains **UNKNOWN**.

#159 merged the fresh-overlay recovery design while preserving the poison fence. Its candidate qualification demonstrated browser recovery with test-double provider coverage and a real local repository audit, not live provider/model quality. The first post-merge #159 production Pages proof then retained a separate narrow-browser parser failure in which the real `:0` exit marker was interpreted as `:0503`. #153 fixes that proof-boundary defect; current-main Pages is green, but a fresh real-account iPhone/WebKit success still has not been established by the retained evidence reviewed here.

Issues #120/#126 remain open. Timed-wait diagnostics, historical browser-runtime corruption and the production poison event are reliability evidence. Their exact root-cause relationship remains **UNKNOWN**.

## Factory and trust-boundary constraints

Issues #63 and #48 are closed. M2/M3/M4 are implemented and `implementation-status.yaml` remains the implementation-presence manifest. M4 qualification stays environment-bound; namespace/capability-unavailable execution is `BLOCKED`/`UNKNOWN`, not `PASS`.

PR #139 isolates the protected `/proc/<pid>/status` test-race repair. Because it changes the protected M4 qualification surface, the ownership-baseline / protected-byte process must be handled deliberately and followed by fresh qualification. This documentation does not alter that baseline, any protected M4 implementation/test byte, qualification anchor, or evidence schema.

## Governance boundary

Merged PR #168 establishes the repository's solo-maintainer approval model: automated qualification plus an exact-head maintainer attestation is the repository merge-control mechanism. It explicitly does **not** represent independent human assurance. #146's proposed repository-wide independent-human gate was closed unmerged/superseded.

A specific release, research or security claim may still require independent or third-party evidence. The governance model does not broaden those claims.

## Evaluation guidance

The scripted benchmark remains useful as a controller regression fixture, not as evidence of live LLM reliability, token savings or API cost. Confirmatory research must bind results to exact source, workload, execution identity, verifier policy and retained artifacts.

Start with:

- [`docs/evaluation.md`](docs/evaluation.md)
- [`docs/research.md`](docs/research.md)
- [`docs/controlled-evaluation.md`](docs/controlled-evaluation.md)
- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)

## Current scope and non-claims

A passing check establishes only its declared condition. Historical results remain tied to the exact revisions that produced them.

The repository does not currently claim universal worker correctness, guaranteed savings, blanket production readiness, every-host M4 qualification, completed release/recovery or elapsed-soak qualification, acceptable long-run WebVM reliability, successful current-main end-to-end paid/live provider execution, root cause of the poisoned-guest/browser-runtime failure family, proof of the central live-model reliability hypothesis, autonomous recursive self-improvement or autonomous merge authority.

For operational setup, use [`START-HERE.md`](START-HERE.md). For current repository-wide status, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).
