# Research claim and prior art

Date: 2026-09-16. Status: implemented research platform; central systems hypothesis not yet established by confirmatory live-model evaluation.

> **Current platform state:** [CURRENT_STATUS.md](CURRENT_STATUS.md)

## Working paper

The broader systems hypothesis is developed in the IEEE-style working manuscript:

**[Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems](papers/reliability-from-unreliable-computation.md)**

The paper tests whether system-level AI reliability can improve without making each component model individually reliable when worker authority is constrained, execution is observable, evidence is retained, outputs are independently verified, and accepted state transitions are controlled.

The key empirical distinction is between raw worker correctness `P(X)` and accepted-system correctness `P(X|A)`. A positive result requires more than rejecting bad outputs: accepted correctness must improve while acceptance coverage remains useful, and the gain must be evaluated against orchestration cost, latency and throughput.

## Current research apparatus

The repository includes:

- bounded Factory worker contracts and isolated execution;
- Station-issued receipts and evidence-bus handoff;
- deterministic integration/scheduling machinery;
- verifier-quality/adaptive-assurance components;
- orchestration-tax and economics/observability research interfaces;
- hash-locked workloads, repeated runs, ablations, statistics, reporting and fault injection under `residual/eval/`;
- browser/WebVM execution with retained real-guest acceptance evidence;
- cluster, lifecycle/recovery and soak infrastructure;
- bounded self-maintenance and frozen research-bundle tooling;
- exact-source/retained-evidence claim discipline.

These mechanisms make the systems hypothesis testable. They do **not** prove it.

## Current implementation boundary

Current `main` is `0580c1e53ddb9163d2423d82c0bca846a6d68ba2`. Its observed automated/browser qualification is **PASS**, while independent technical acceptance remains review-provisional because merged PRs #145 and #147 have no submitted reviews in the retained GitHub review record. Issues #63 and #48 are closed; M2/M3/M4/EVAL are no longer accurately described by the old pre-merge `not_started` status language.

Current exact-main CI/browser evidence is strong for mechanism and integration checks, including Pages generated/published desktop+narrow WebVM acceptance. That evidence remains revision- and environment-bound. It is not independent review, confirmatory model research, every-host security qualification, live-provider quality or long-duration reliability evidence.

## WebVM / provider evidence boundary

Retained diagnostics isolate a WebVM-specific, process-local CPython positive-duration timed-wait failure affecting at least `time.sleep()` and `select.select()` while tested direct libc waits pass beyond the same narrow boundary. The lower-level CPython/glibc/WebVM cause and any relationship to earlier interpreter/allocator-corruption symptoms remain **UNKNOWN**.

Merged PR #145 routes the long-lived browser polling paths below that known Python timed-wait surface. Merged PR #147 then tightens real Puter response conformance. Exact automated CI/browser evidence is `PASS` for those tested scopes.

The latest retained real-account provider attempt before #147 is still **FAIL** as `provider_protocol_invalid`, with no accepted obligation/artifact. A successful real-account post-#147 run is not yet retained, so live-provider acceptance remains **UNKNOWN / not established**. This provider work is operational evidence, not a confirmatory research result.

Issues #120/#126 remain open because mitigation of a narrow trigger does not establish long-run recurrence rate or historical root cause.

## Governance and evidence independence

Issue #144 tracks the gap between the project's independent-review expectations and current platform enforcement. PR #146 is a repository-side enforcement candidate, but its current exact head is not green and no qualifying approval is present.

Merged PRs #145 and #147 have no submitted reviews in the retained GitHub review record. Their green exact-head and merged-main CI remains valid automated evidence, but it must not be described as independent technical acceptance. This is governance debt to be addressed explicitly, not retroactively rewritten.

## Proposed contribution

The original contribution was framed as **counterexample-directed residual delegation with evidence negotiation**: compile a checked workflow's unresolved frontier into a bounded, independently verifiable request while preserving accepted independent work and carrying content-bound receipts across model boundaries.

The project has generalized that idea into a broader systems hypothesis:

> stochastic workers may remain individually unreliable if the surrounding system constrains their authority, observes execution, preserves evidence, independently verifies candidate work and deterministically controls accepted state.

The novelty claim is intentionally bounded. Routing, checkers, DAGs, caching, retrieval, sandboxing, model mixtures and counterexample-guided synthesis all have substantial prior art. The empirical research question is whether this composition produces measurably better **accepted-state reliability** under fixed component capability.

This repository does not establish a first-in-literature result.

## Relevant prior art

| Work | Existing idea | Boundary of this project's claim |
| --- | --- | --- |
| [FrugalGPT](https://arxiv.org/abs/2305.05176) | Cost-aware model cascades | RESIDUAL treats verifier-defined acceptance/evidence as control-plane inputs, not only routing signals |
| [RouteLLM](https://arxiv.org/abs/2406.18665) | Learned model routing | Routing is adjacent; the central question is evidence-gated acceptance and state transition |
| [ReWOO](https://arxiv.org/abs/2305.18323) | Separating reasoning from tool observations | RESIDUAL additionally tracks explicit obligations and trusted acceptance boundaries |
| [Small Language Models are the Future of Agentic AI](https://arxiv.org/abs/2506.02153) | Heterogeneous/specialized agents | Heterogeneous workers motivate the architecture but are not a novelty claim |
| [LLMLingua-2](https://arxiv.org/abs/2403.12968) | Learned prompt compression | RESIDUAL uses explicit evidence/receipt structures rather than a learned compressor |
| [Counterexample-Guided Inductive Synthesis](https://people.csail.mit.edu/asolar/SynthesisCourse/Lecture17.htm) | Candidate generation with counterexample feedback | Verifier-guided repair predates LLMs; this project tests a systems-level containment/acceptance architecture |
| [Proof-Carrying Code](https://doi.org/10.1145/263699.263712) | Untrusted producer supplies checkable evidence | Strong precedent for separating production from trusted acceptance |
| [Model Checking](https://mitpress.mit.edu/9780262032704/model-checking/) | Independent verification of state/system properties | Formal-systems precedent for externalized correctness checks |

Comparative statements about RESIDUAL are our interpretation, not claims made by those authors.

## Confirmatory gate

Before paper-facing outcome collection, freeze the exact source revision, selected execution/evidence path, workload/task mapping, model/version, inference settings, verifier revisions/policies, prompts, metrics and analysis code. Do this **before** observing confirmatory results.

Operational/reliability work that remains open must be scoped honestly:

1. resolve or explicitly bound the #120/#126 WebVM reliability risk for any WebVM-dependent research path;
2. retain fresh real-provider evidence if the selected research protocol depends on that provider path;
3. complete any required protected #139/#134 qualification sequence before using those adapter changes;
4. resolve the #144 independent-review enforcement gap for research/release integrations that require independent acceptance;
5. independently qualify whichever evidence path the live protocol selects rather than assuming green fixture CI is confirmatory evidence.

## Primary confirmatory experiment

Run one fixed model across the frozen R0–R5 configurations and retain raw observations sufficient to recompute:

- raw correctness `P(X)`;
- acceptance coverage `P(A)`;
- accepted correctness `P(X|A)`;
- Accepted Error Rate (AER);
- accepted-system success / ASSR;
- false acceptance and false rejection;
- verifier rejection / `UNKNOWN` rates;
- latency, throughput, rework/conflicts;
- monetary/token/GPU cost where directly measurable.

A positive result requires `P(X|A)` to improve meaningfully over `P(X)` without collapsing `P(A)` toward zero. Then test model degradation and heterogeneous routing under the same acceptance boundary.

A falsifying outcome is equally important: if accepted correctness does not materially improve, or if any improvement is dominated by rejection, verifier leakage, cost or latency, the hypothesis is not supported for the tested domain.

## What is deliberately not claimed

The repository does not currently claim a new foundation model, a universal verifier/proof system, universally optimal routing, guaranteed token/cost savings, blanket production readiness, acceptable long-run WebVM reliability, successful post-#147 real-provider inference, independent approval of every merged production-readiness change, live-model proof of the central hypothesis, completed long-duration soak, autonomous recursive self-improvement, autonomous merge authority or first-in-literature status.

Receipts establish that stated checks ran over stated evidence under stated identities/revisions. They do not certify arbitrary truth beyond those contracts.
