# Research claim and prior art

Date: 2026-09-17. Status: implemented research platform; central systems hypothesis not yet established by confirmatory live-model evaluation.

> **Current platform state:** [CURRENT_STATUS.md](CURRENT_STATUS.md)

## Working paper

The broader systems hypothesis is developed in:

**[Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems](papers/reliability-from-unreliable-computation.md)**

The research question is whether system-level AI reliability can improve without making each component model individually reliable when worker authority is constrained, execution is observable, evidence is retained, outputs are independently checked, and accepted state transitions remain under deterministic host control.

The key empirical distinction is between raw worker correctness `P(X)` and accepted-system correctness `P(X|A)`. A positive result requires more than rejection: accepted correctness must improve while acceptance coverage remains useful, and the improvement must be evaluated against orchestration cost, latency and throughput.

## Research apparatus

The repository contains bounded Factory worker contracts/runtime, Station-issued receipts and evidence-bus handoff, deterministic integration/scheduling, verifier-quality/adaptive-assurance components, orchestration-tax and economics/observability tooling, hash-locked workloads, ablations, statistics and fault injection, browser/WebVM execution, lifecycle/recovery tooling, soak infrastructure, bounded self-maintenance research and exact-source/retained-evidence claim discipline.

These mechanisms make the systems hypothesis testable. They do **not** prove it.

## Current evidence boundary

Current `main` is **`2b7cb626a9a327cf56ede847fa4e6ae6cdf9243f`**.

Recent merged mechanisms include #159 fresh-overlay poisoned-guest recovery, #168 solo-maintainer repository governance, and #153 bounded WebVM terminal-proof/control-unlock synchronization.

The final #153 candidate had its observed exact-head qualification set green and an exact-head maintainer attestation. The merged revision is nevertheless **not fully green**: current-main Pages run `35172926305` is **PASS**, but Controller/provider run `35172926291` is **FAIL** in Python 3.12 on the protected M4 `/proc/<pid>/status` observation race. That retained first main failure stays in the evidence record.

This is mechanism/integration evidence. It is not a paper-facing effect size, independent human assurance, every-host security qualification, model-quality evidence or long-duration reliability evidence.

## WebVM / provider research boundary

Retained diagnostics isolate a WebVM-specific, process-local CPython positive-duration timed-wait failure affecting at least `time.sleep()` and `select.select()`, while tested direct libc waits continue beyond the same narrow boundary. Merged #145 routes long-lived browser polling below the known Python timed-wait surface. The lower-level CPython/glibc/WebVM cause and any relationship to earlier interpreter/allocator corruption remain **UNKNOWN**.

Fresh production evidence later reached `Provider connected` on iPhone/WebKit but exposed `RESIDUAL_WORKER_POISONED` while Mission Control remained at `GUEST STARTING`. That observed mission is **FAIL** at the guest-recovery/product boundary; no valid live candidate completed the normal verifier/receipt path.

#159 adds a supported fresh-overlay recovery path without unpoisoning the old guest. Its browser proof used provider test-double coverage and a real local repository audit, not live model quality. The first production Pages run after #159 then retained a separate narrow-browser proof-parser failure; #153 repairs that acceptance-harness boundary and current-main Pages now passes.

A successful paid/live Puter execution on exact current main is still **UNKNOWN / not established** by the retained evidence reviewed here. Green transport/browser tests do not imply provider/model quality.

Issues #120/#126 remain open because trigger avoidance and individual green Pages runs do not establish long-run recurrence rate or root cause.

## Governance and research independence

Merged #168 establishes the repository's solo-maintainer merge-control model:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

This should be described as **maintainer-reviewed with automated qualification**, not as independent human assurance. #146's proposed generic repository-wide independent-human gate was closed unmerged/superseded.

This governance change does not erase claim-specific requirements for independent or third-party validation. A paper-facing security, release or scientific claim may still require evidence independent of the implementer/maintainer; that requirement must be stated and retained explicitly for the claim being made.

## Factory / protected evidence boundary

Issues #63/#48 are closed and M2/M3/M4 are implemented. M4 remains environment- and exact-revision-bound rather than universally qualified.

Current-main Controller/provider CI re-exposes the known protected M4 test observation race. PR #139 remains the isolated protected repair lane. If a selected research evidence path depends on #139 or downstream #134, preserve the complete protected-byte sequence: review the protected change under the applicable policy, make any ownership-baseline change deliberately, run fresh qualification after the pin change, then refresh/requalify dependent work. `BLOCKED`/`UNKNOWN` capability states do not become `PASS`.

## Qualification-methodology expansion

PR #152 proposes a broader Qualification v1 layer: source-bound evidence manifests, stateful lifecycle exploration, DSM fault evidence, mutation canaries, branch coverage, exact-wheel qualification, multi-browser journeys and process/elapsed-soak tooling.

Any prior result on an older base remains historical to that head. #152 must be refreshed/requalified against current main before it can support a current release claim. Virtual-day stress is not elapsed wall-clock soak; planned 24h/72h/30d workflows create no elapsed claim until the actual runs complete.

PRs #160–#167 are inference-engineering proposals/specifications unless their implementations later land and are qualified. They are not current empirical evidence.

Draft #169 adds privacy-safe, local-first demo diagnostic telemetry on current main. Its stated trust boundary is observational only; retained guest trace/`verify-trace` remain authoritative. Its qualification is still in progress and the maintainer-approval gate is not satisfied on the current draft head, so it is not accepted-main evidence.

## Proposed contribution

The original contribution was framed as **counterexample-directed residual delegation with evidence negotiation**: compile a checked workflow's unresolved frontier into a bounded, independently verifiable request while preserving accepted independent work and carrying content-bound receipts across model boundaries.

The broader hypothesis is:

> stochastic workers may remain individually unreliable if the surrounding system constrains their authority, observes execution, preserves evidence, independently checks candidate work and deterministically controls accepted state.

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

At minimum:

1. resolve or explicitly bound #120/#126 for any WebVM-dependent path;
2. retain fresh exact-revision live-provider evidence if the protocol depends on that provider path;
3. complete any protected #139/#134 sequence required by the selected evidence path;
4. independently qualify the selected evidence path to the degree required by the paper claim, rather than treating repository maintainer attestation as external scientific validation;
5. refresh any selected candidate after a material `main` move instead of inheriting stale-head qualification.

## Primary confirmatory experiment

Run one fixed model across frozen R0–R5 configurations and retain raw observations sufficient to recompute raw correctness `P(X)`, acceptance coverage `P(A)`, accepted correctness `P(X|A)`, AER/ASSR, false acceptance/rejection, verifier rejection/`UNKNOWN`, latency, throughput, rework/conflicts and directly measurable monetary/token/GPU cost.

A positive result requires `P(X|A)` to improve meaningfully over `P(X)` without collapsing `P(A)` toward zero. A falsifying result is equally important: if accepted correctness does not materially improve, or improvement is dominated by rejection, verifier leakage, cost or latency, the hypothesis is not supported for the tested domain.

## What is deliberately not claimed

The repository does not currently claim a new foundation model, a universal verifier/proof system, universally optimal routing, guaranteed token/cost savings, blanket production readiness, a fully green exact current-main qualification set, acceptable long-run WebVM reliability, successful current-main real-provider inference, independent human assurance from the solo-maintainer merge model, live-model proof of the central hypothesis, completed long-duration soak, autonomous recursive self-improvement, autonomous merge authority or first-in-literature status.

Receipts establish that stated checks ran over stated evidence under stated identities/revisions. They do not certify arbitrary truth beyond those contracts.
