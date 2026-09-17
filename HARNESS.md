# RESIDUAL core harness

**A verifier-first harness that delegates unresolved work without giving the worker acceptance authority.**

This document describes the original/core RESIDUAL harness layer. The repository has expanded into Command Station, Factory M2/M3/M4, Mission Control/WebVM, evaluation infrastructure, adversarial authority testing, and runtime-diagnostic tooling. For repository-wide qualification claims, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

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
| Claim discipline | `FAIL`, `UNKNOWN`, `BLOCKED`, malformed output, verifier exceptions and provider errors do not become `PASS` |

## Relationship to the broader platform

- **Command Station** provides operator-facing mission/run/provider control. Merged #194 retains completed generated-spec drafts and lets operators reopen them after the initiating watcher is gone.
- **Factory M2** provides bounded worker contracts/runtime and host-owned termination.
- **Factory M3** provides Station-issued evidence/receipt handoff.
- **Factory M4** provides deterministic integration/scheduler authority and capable-runner qualification machinery.
- **Mission Control/WebVM** provides browser-facing real-guest workflows, provider transport, fresh-overlay recovery, iOS/WebKit fallback, privacy-safe diagnostics, and the #133 runtime discriminator suite.
- **Evaluation/research** provides frozen workloads, statistics, fault campaigns, evidence bundles, economics/observability surfaces, and merged AQ-GOV-001 authority-escalation testing.

The protected self-hosting/research-bundle surface merged in #132 is no longer present on current main because #133 removed its implementation, tests, workflow, example, and dedicated docs. #132 remains historical retained evidence, not current accepted capability.

## Current repository boundary

Current `main` is **`b3f00af29c7507f4c0e218884e491c2fc792d984`**.

Since `main@dcf1e507...`:

- **#188 merged** AQ-GOV-001. It tests a bounded software invariant under unanimous worker approval: consensus is not authority. The lab does not establish kernel/container/hypervisor/broker escape resistance.
- **#194 merged** the completed-draft visibility/reopen repair in Command Station.
- **#133 merged** WebVM runtime discriminators. Retained evidence narrows one reproducible failure family to a WebVM-specific CPython positive-duration timeout/wait conversion path affecting at least `time.sleep()` and empty `select.select()`, while direct libc wait controls continue beyond the same boundary. Exact lower-level cause remains **UNKNOWN**.

#133 also removed accepted #132 self-hosting/research-bundle bytes. Earlier review records identified those deletions as incompatible with the PR's diagnostic-only description. Current documentation therefore does not count those removed bytes as implemented capability and does not assume the removal was an intended retirement decision.

The first seven ordinary `push` workflows on exact merged `main@b3f00af...` were **PENDING/queued** at the latest observation. Candidate-head PASS results are not inherited by the merge SHA.

On #133's exact final candidate head, Factory ownership, measured binding, Browser VM Demo, Control Plane, clean install, Controller/provider, Command Station, Pages, and the maintainer approval gate were **PASS**. Several diagnostic workflows intentionally ended **FAIL** after reproducing the failure being studied; those are retained diagnostic outcomes, not qualification passes and not failures to erase by rerun.

## Live provider / WebVM boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

Merged #179 changed the bounded browser build-output path, #183 repaired provider-session lifecycle behavior, and #189 repaired the provider-helper publication boundary. None is, by itself, retained proof of successful paid/live Puter inference.

The accepted #186 fallback routes detected iOS/iPadOS WebKit to the lightweight walkthrough before heavyweight guest boot. This is not a PASS claim for heavyweight WebVM on physical iPhone Safari.

Issues #120/#126 remain open. #133 materially narrows the timed-wait symptom but does not establish the exact CPython/i386 ABI/emulation cause, the relationship to older corruption evidence, or an acceptable long-run recurrence rate.

## Factory and trust-boundary constraints

M2/M3/M4 are implemented and `implementation-status.yaml` is the implementation-presence manifest. M4 qualification remains exact-revision/environment bound; namespace/capability-unavailable execution is `BLOCKED`/`UNKNOWN`, not `PASS`.

Accepted #185/#187 protected-byte changes remain scoped to their reviewed behavior. The separate #139→ownership-baseline→fresh-qualification→#134 sequence remains independent. This documentation branch changes no Factory/M4 implementation or test, ownership baseline, qualification anchor, or evidence schema.

## Governance boundary

Merged #168 establishes the repository's solo-maintainer approval model:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

It explicitly does **not** represent independent human assurance. A specific release, security, or research claim may still require independent or third-party evidence.

PR #191 was closed unmerged and is not accepted governance.

## Evaluation guidance

The scripted benchmark remains useful as a controller regression fixture, not as evidence of live LLM reliability, token savings, or API cost. Confirmatory research must bind results to exact source, workload, execution identity, verifier policy, and retained artifacts.

Start with:

- [`docs/evaluation.md`](docs/evaluation.md)
- [`docs/research.md`](docs/research.md)
- [`docs/controlled-evaluation.md`](docs/controlled-evaluation.md)
- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)

#188 is now accepted research apparatus with deliberately bounded claims. #190, #152, and #177 require refresh/requalification after the material main move before current release/research claims use their older candidate evidence. #193 remains an unaccepted setup-script candidate.

## Current scope and non-claims

A passing check establishes only its declared condition. Historical results remain tied to the exact revisions that produced them.

The repository does not currently claim universal worker correctness, guaranteed savings, blanket production readiness, every-host M4 qualification, completed blank-environment/recovery/elapsed-soak qualification, acceptable long-run WebVM reliability, successful exact-current-main paid/live provider execution, physical heavyweight-WebVM iPhone reliability, root cause of the browser-runtime failure family, current accepted #132 self-maintenance/research-bundle capability, final IE-001 qualification, proof of the central live-model reliability hypothesis, autonomous recursive self-improvement, or autonomous merge authority.

For operational setup, use [`START-HERE.md`](START-HERE.md). For current repository-wide status, use [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).
