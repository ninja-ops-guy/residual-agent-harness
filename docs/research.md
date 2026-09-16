# Research claim and prior art

Date: 2026-09-14. Status: implemented research platform; central systems hypothesis not yet established by live-model evaluation.

> **Current platform state:** [CURRENT_STATUS.md](CURRENT_STATUS.md)

## Working paper

The broader systems hypothesis is developed in the IEEE-style working manuscript:

**[Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems](papers/reliability-from-unreliable-computation.md)**

The paper tests the hypothesis that system-level AI reliability can improve without increasing individual model reliability when model actions are constrained, execution is observable, outputs are independently verified, and accepted results are integrated deterministically.

The key empirical distinction is between raw worker correctness `P(X)` and accepted-system correctness `P(X|A)`. A positive result requires more than rejecting bad outputs: accepted correctness must improve while acceptance coverage remains useful, and the reliability gain must be evaluated against orchestration cost, latency and throughput.

## Current research apparatus

The repository now contains more than the original residual-delegation prototype. The current research instrument includes:

- bounded Factory worker contracts and isolated execution;
- Station-issued receipts and evidence-bus handoff;
- deterministic integration and scheduler machinery;
- verifier-quality/adaptive-assurance components;
- orchestration-tax research interfaces;
- a hash-locked `FrozenWorkload` evaluation package with repeated runs, ablations, statistics, reporting, fault injection and measured Factory hooks;
- sandbox/red-team, cluster, lifecycle/recovery, observability and soak infrastructure;
- retained exact-commit verification/evidence practices.

These mechanisms make the systems hypothesis testable. They do **not** by themselves prove it.

## Proposed contribution

The original contribution was framed as **counterexample-directed residual delegation with evidence negotiation**: compile a checked workflow's unaccepted frontier into a small, independently verifiable request for a stronger model while preserving accepted independent work and carrying content-bound dependency receipts across model boundaries.

The project has since generalized that idea into a broader reliability/control-plane hypothesis:

> stochastic workers may remain individually unreliable if the surrounding system constrains their authority, observes execution, preserves evidence, independently verifies candidate work and deterministically controls what becomes accepted state.

The novelty claim is intentionally bounded. Local/cloud mixtures, fallback routing, checkers, DAGs, content-addressed caching, evidence retrieval, sandboxing and ensemble ideas all have substantial prior art. The research question is whether these mechanisms can be composed into a system that produces measurably better **accepted-state reliability** under fixed component capability.

This repository does not establish a first-in-literature result.

## Relevant prior art

| Work | Existing idea | Boundary of this project's claim |
| --- | --- | --- |
| [FrugalGPT](https://arxiv.org/abs/2305.05176) | Cost-aware model cascades | RESIDUAL treats verifier-defined acceptance and residual evidence as control-plane inputs rather than only cost/quality routing signals |
| [RouteLLM](https://arxiv.org/abs/2406.18665) | Learned model routing | Routing is adjacent; the central question here is evidence-gated acceptance and deterministic state transition |
| [ReWOO](https://arxiv.org/abs/2305.18323) | Separating reasoning from tool observations | Deterministic offloading/context reduction are established; RESIDUAL additionally tracks explicit obligations and trusted acceptance boundaries |
| [Small Language Models are the Future of Agentic AI](https://arxiv.org/abs/2506.02153) | Heterogeneous/specialized agents | Heterogeneous workers motivate the architecture but are not a novelty claim |
| [LLMLingua-2](https://arxiv.org/abs/2403.12968) | Learned prompt compression | RESIDUAL uses explicit evidence intervals/receipts rather than a learned compressor |
| [Counterexample-Guided Inductive Synthesis](https://people.csail.mit.edu/asolar/SynthesisCourse/Lecture17.htm) | Candidate generation with counterexample feedback | Verifier-guided repair predates LLMs; the current systems hypothesis concerns containment and accepted-state reliability |
| [Proof-Carrying Code](https://doi.org/10.1145/263699.263712) | Untrusted producer supplies checkable evidence | Strong conceptual precedent for separating production from trusted acceptance |
| [Model Checking](https://mitpress.mit.edu/9780262032704/model-checking/) | Independent verification of state/system properties | Provides the formal-systems precedent for treating correctness as an external check rather than a generator assertion |

Comparative statements about RESIDUAL are our interpretation, not claims made by those authors.

## Current development evidence

Development evidence currently supports the existence and testability of the control mechanisms, including:

- bounded worker execution and contract violations;
- evidence/receipt integrity and trusted-consumption checks;
- deterministic integration invariants and conflict/verification rejection paths;
- sandbox/red-team containment;
- evaluation workload locking, repeated-run execution, ablation/report/statistics plumbing;
- cluster/lifecycle/recovery and observability surfaces.

A large integrated milestone at `412b66c35f7c0e1ac479fe60a5b7d33d5510e3af` recorded 1,033 tests plus 166 subtests green on that exact tree. Current `main` has moved beyond that point, so the result is historical exact-tree evidence, not blanket qualification of later commits.

Controlled development fault experiments against earlier M2/M3/M4 trees demonstrated containment in the declared fault matrices. Those are bounded fixture results and must not be generalized to production or arbitrary workloads.

## Current blockers before stronger empirical claims

### M4 qualification

Issue #63 tracks four trust-boundary gaps that must be closed before current M4 should support live/paper-facing reliability claims:

1. accepted-tree identity must remain bound to the artifact tree that was actually verified;
2. filesystem writes must use race-resistant non-following traversal/policies;
3. candidate-dependent verifier execution needs an explicit bounded verification execution boundary;
4. unavailable/corrupt/incomparable Git evidence must remain `UNKNOWN`/error instead of being conflated with path absence.

### Traceability drift

Issue #48 tracks stale `implementation-status.yaml` entries that still mark M2/M3/M4/EVAL `not_started`. The code exists; the generated status view is stale. That documentation inconsistency must be reconciled before using the manifest as paper evidence.

### Reproducibility classification

Clean-install qualification work retained an initial Python 3.11 failure in two timing-sensitive Factory OS tests that passed unchanged on rerun. The source of that nondeterminism must be classified rather than hidden by retry policy.

### Measured-evidence provenance

PR #71's reviewed Factory adapter still permits replay to count as independent repetitions, unsigned/run-unbound topology, drift between measured and frozen task populations, and unqualified verifier-boundary labels. A signature over the resulting report does not repair invalid source evidence.

Before using that adapter for confirmatory results, correct and independently requalify fresh execution/run binding, cross-repetition replay rejection, authenticated scheduler evidence over the run interval, the exact approved workload-to-task mapping, and the qualified verifier policy/execution boundary. Resume must preserve the original run identity rather than count recovered evidence as new execution. These measurement requirements remain separate from closing #63, #48 and the timing issue.

A live R0–R5 protocol can explicitly exclude this Factory adapter and use a different independently qualified evidence path. It must still satisfy the applicable guarantees in the [live evaluation gate](evaluation.md#live-evaluation-gate); a different path must not be assumed sound merely because PR #71 is not used.

## Next confirmatory experiment

After the blockers above are closed or explicitly excluded through a qualified alternative, freeze the implementation, selected execution/evidence adapter, model configuration, verifier revisions and policies, task corpus and mapping, prompts, inference settings, evaluation metrics and analysis code **before** observing live results. Retain the selected path's qualification evidence alongside the frozen protocol.

The primary experiment should run one fixed model across R0–R5 configurations and retain raw observations sufficient to recompute:

- raw correctness `P(X)`;
- acceptance coverage `P(A)`;
- accepted correctness `P(X|A)`;
- Accepted Error Rate (AER);
- accepted-system success/ASSR;
- false acceptance and false rejection;
- verifier rejection/UNKNOWN rates;
- latency, throughput, rework/conflicts and monetary/token/GPU cost where measurable.

A positive result requires `P(X|A)` to improve meaningfully over `P(X)` without collapsing `P(A)` toward zero. The result must then be tested under model degradation and heterogeneous routing to determine whether weaker/lower-cost compute remains useful under the same acceptance boundary.

The falsifying outcome is straightforward: if the acceptance architecture does not materially improve accepted correctness, or if the improvement is dominated by rejection, verifier leakage, excessive cost or excessive latency, the central hypothesis is not supported for the tested domain.

## What is deliberately not claimed

The repository does not currently claim:

- a new foundation model;
- a universal verifier or universal proof system;
- universally optimal routing/scheduling;
- guaranteed token/cost savings;
- guaranteed preservation of model quality;
- production readiness for every deployment;
- live-model proof of the reliability-from-unreliable-computation hypothesis;
- first-in-literature status.

Receipts establish that stated checks ran over stated evidence under stated identities/revisions. They do not certify arbitrary truth beyond those contracts.
