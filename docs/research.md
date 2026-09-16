# Research claim and prior art

Date: 2026-09-16. Status: implemented research platform; central systems hypothesis not yet established by confirmatory live-model evaluation.

> **Current platform state:** [CURRENT_STATUS.md](CURRENT_STATUS.md)

## Working paper

The broader systems hypothesis is developed in the IEEE-style working manuscript:

**[Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems](papers/reliability-from-unreliable-computation.md)**

The paper tests whether system-level AI reliability can improve without making each component model individually reliable when worker authority is constrained, execution is observable, evidence is retained, outputs are independently verified, and accepted state transitions are controlled.

The key empirical distinction is between raw worker correctness `P(X)` and accepted-system correctness `P(X|A)`. A positive result requires more than rejecting bad outputs: accepted correctness must improve while acceptance coverage remains useful, and the gain must be evaluated against orchestration cost, latency and throughput.

## Current research apparatus

The repository includes bounded Factory worker contracts and isolated execution; Station-issued receipts and evidence-bus handoff; deterministic integration/scheduling machinery; verifier-quality/adaptive-assurance components; orchestration-tax and economics/observability interfaces; hash-locked workloads, ablations, statistics and fault injection; browser/WebVM execution with retained real-guest acceptance evidence; lifecycle/recovery and soak infrastructure; bounded self-maintenance tooling; and exact-source/retained-evidence claim discipline.

These mechanisms make the systems hypothesis testable. They do **not** prove it.

## Current implementation boundary

Current `main` is **`f6f9bad84caccf68c7ab35e5788e756d12c55fb7`**, the merge of PR #156. Its seven observed main-push workflows are **PASS** for their exact automated/browser scopes. The capable-runner M4 workflow passed its fail-closed capability and zero-skip gate. Pages run `35158939226` passed on attempt 1 through generated and published desktop+narrow real-guest acceptance.

This evidence is revision- and environment-bound. It is not independent review, confirmatory model research, every-host security qualification, live-provider quality or long-duration reliability evidence.

PR #156 has zero submitted reviews, so current main is **technically qualified but review-provisional**. Earlier merged #136/#145/#147/#151 retain the same missing-independent-acceptance debt. Issue #144 and PR #146 address future enforcement; that policy work does not retroactively rewrite history.

## WebVM / provider evidence boundary

Retained diagnostics isolate a WebVM-specific, process-local CPython positive-duration timed-wait failure affecting at least `time.sleep()` and `select.select()` while tested direct libc waits pass beyond the same narrow boundary. The lower-level CPython/glibc/WebVM cause and any relationship to earlier interpreter/allocator-corruption symptoms remain **UNKNOWN**.

Merged #145 routes long-lived browser polling below that known Python timed-wait surface. PR #151 added the event-backed live-pipeline projection and stricter provider transport. Fresh real-account evidence on that surface then produced two real `openai/gpt-5.4-nano` calls that both failed closed as `provider_protocol_invalid`, with no accepted obligation or artifact.

PR #156 repairs the identified worker-envelope conformance regression by removing provider-side strict structured-output mode for the dynamic obligation-key envelope and restoring exact nested build guidance. Exact automated CI/browser evidence is `PASS` for those tested scopes.

The retained pre-#156 real-account path remains **FAIL**. A successful paid/live Puter acceptance on exact current main is **UNKNOWN / not established** until a fresh retained real-account run succeeds. Green SDK/contract/browser tests are not provider-quality evidence.

Issues #120/#126 remain open because avoidance of a narrow trigger does not establish long-run recurrence rate or historical root cause.

## Qualification-methodology expansion

PR #152 proposes a stronger, unified qualification layer: fail-closed evidence manifests, generated lifecycle/state exploration, DSM fault evidence, mutation canaries, branch coverage, exact-wheel qualification, multi-browser journeys, process-soak tooling and manual live-provider/elapsed-soak workflows.

Its current head is based on pre-#156 main. Prior workflow outcomes remain exact-head history and do not qualify the candidate against current main. The proposal itself is not qualification evidence. Virtual-day stress is not elapsed soak; planned 24h/72h/30d workflows produce no elapsed claim until the actual wall-clock runs complete; a live-provider canary would demonstrate one bounded execution path, not model quality.

## Governance and evidence independence

Issue #144 tracks the gap between the project's independent-review expectations and platform enforcement. PR #146 implements a fail-closed exact-head review check and is now refreshed onto exact current main at head `c416d408149408ff8668a48d6e73eb1f3bf6347e`; fresh qualification plus independent write-authorized current-head acceptance are required before integration. The active ruleset still requires a maintainer enforcement change after the governance PR itself is accepted.

Merged #156 has no submitted review. Its green CI remains valid automated evidence but must not be described as independent technical acceptance.

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

Before paper-facing outcome collection, freeze the exact source revision, selected execution/evidence path, workload/task mapping, model/version, inference settings, verifier revisions/policies, prompts, metrics and analysis code **before** observing confirmatory results.

Operational/reliability work that remains open must be scoped honestly:

1. resolve or explicitly bound #120/#126 for any WebVM-dependent research path;
2. retain fresh exact-revision real-provider evidence if the protocol depends on that provider path;
3. complete any required protected #139/#134 qualification sequence before using those adapter changes;
4. resolve #144/#146 independent-review enforcement for research/release integrations that require independent acceptance;
5. independently qualify whichever evidence path the live protocol selects rather than assuming green fixture CI is confirmatory evidence;
6. refresh any selected candidate after a later `main` move instead of inheriting stale-head qualification.

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

The repository does not currently claim a new foundation model, a universal verifier/proof system, universally optimal routing, guaranteed token/cost savings, blanket production readiness, acceptable long-run WebVM reliability, successful post-#156 real-provider inference, independent approval of every merged production-readiness change, live-model proof of the central hypothesis, completed long-duration soak, autonomous recursive self-improvement, autonomous merge authority or first-in-literature status.

Receipts establish that stated checks ran over stated evidence under stated identities/revisions. They do not certify arbitrary truth beyond those contracts.
