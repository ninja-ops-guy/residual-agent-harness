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

Current `main` is **`2e1341c99fd7b72452e3b8c5278b1f557871b783`**, produced by merged #183 on top of the accepted browser build-output path through #179.

Merged #179 provides a bounded 8192-token browser build ceiling/default, retains 1536 for non-build/source-grounded live mode, and classifies normalized provider truncation/incomplete completion fail-closed. Merged #183 adds bounded mobile provider-session lifecycle recovery: valid traffic refreshes liveness, the private channel capability can survive provider-tab reload through session storage, and an already signed-in Puter session can be restored when available. Neither change gives model output acceptance authority, changes protected Factory/M4 boundaries, or proves historical live-provider failure causality.

The final #183 head `0b520064cb9deff32dc7d1c261dcaf99f3dc2848` completed all observed PR workflows **PASS** and received exact-head maintainer attestation before merge. That is repository governance/engineering evidence, not independent scientific validation.

Exact merged-main `push` qualification is **mixed**: six of seven observed workflows are **PASS**, while **Command Station checks** run `35219212073` is retained **FAIL** on attempt 1 because the Python 3.11 full unittest step failed. Browser, Docker, Python 3.12 and Python 3.13 jobs passed. The exact failing test/cause is **UNKNOWN** from retained workflow metadata currently available. Pages run `35219212133` is **PASS** on attempt 1.

This mixed exact-revision result is mechanism/integration evidence. It is not a paper-facing effect size, paid/live provider success, model-quality evidence or long-duration reliability evidence. The current-main failure must remain in the evidence record rather than being inferred away from sibling passes or the green pre-merge candidate.

The earlier `main@2b7cb626...` protected M4 `/proc/<pid>/status` observation-race **FAIL** also remains historical evidence. Later green runs do not prove the protected race fixed; #139 remains the isolated protected repair lane.

## WebVM / provider research boundary

Retained diagnostics isolate a WebVM-specific, process-local CPython positive-duration timed-wait failure affecting at least `time.sleep()` and `select.select()`, while tested direct libc waits continue beyond the same narrow boundary. Merged #145 routes long-lived browser polling below the known Python timed-wait surface. The lower-level CPython/glibc/WebVM cause and any relationship to earlier interpreter/allocator corruption remain **UNKNOWN**.

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both separately counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary (`candidate_rejections=0`, `verification_elapsed_ms=0`), so candidate correctness and semantic verification remain **UNKNOWN**.

The historical mission exposed a 1536-token browser-build provider-output bound. #179 changed that bounded build path, but the evidence did not prove truncation caused the invalid responses. A fresh retained real-account mission on the exact deployed accepted revision is still required before successful live-provider execution can be claimed.

Fresh physical-device evidence from predecessor `main@250494f2...` reports desktop success while iPhone/WebKit crashes on the heavyweight WebVM path. No retained typed crash artifact is available, so the exact internal WebKit process-kill mechanism remains **UNKNOWN**. The separate follow-up/reload provider-session symptom motivated #183, but accepted implementation plus automated CI is not yet post-merge physical-device acceptance evidence.

Open #182 is a bounded iOS safe-mode candidate. Its current exact head has all observed technical workflows **PASS**, including dedicated WebKit preflight and Pages, but its maintainer gate is **FAIL/BLOCKED** and the branch predates #183. It must be refreshed/requalified and, if accepted, followed by first-attempt production Pages plus a physical iPhone retest before any positive device claim.

Issues #120/#126 remain open because trigger avoidance, added diagnostics, provider-session recovery and individual green browser runs do not establish long-run recurrence rate or root cause.

## Governance and research independence

Merged #168 establishes the repository's solo-maintainer merge-control model:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

This should be described as **maintainer-reviewed with automated qualification**, not independent human assurance. The governance change does not erase claim-specific requirements for independent or third-party validation. A paper-facing security, release or scientific claim may still require evidence independent of the implementer/maintainer; that requirement must be stated and retained explicitly for the claim being made.

## Factory / protected evidence boundary

Issues #63/#48 are closed and M2/M3/M4 are implemented. M4 remains environment- and exact-revision-bound rather than universally qualified.

PR #139 remains the isolated protected M4 observation-race repair. If a selected research evidence path depends on #139 or downstream #134, preserve the complete protected-byte sequence: review the protected change under the applicable policy, make any ownership-baseline change deliberately, run fresh qualification after the pin change, then refresh/requalify dependent work. `BLOCKED`/`UNKNOWN` capability states do not become `PASS`.

## Qualification and inference-economics work

PR #152 proposes a broader Qualification v1 layer. Any prior result on an older base remains historical to that head. Virtual-day stress is not elapsed wall-clock soak; planned 24h/72h/30d workflows create no elapsed claim until the actual runs complete.

PRs #160–#167 are inference-engineering specifications. Draft #177 is the development-only IE-001 prototype qualification candidate. Its focused suite reports **203 passed** and its branch reports Q1–Q10 plus maintainer-governance evidence, but **Q11 genuinely independent current-head technical review remains pending**. The candidate is not final IE-001 qualification or accepted production behavior, and its branch predates current main.

Draft #178 is a documentation-only IE-002 through IE-007 implementation backlog and makes no runtime speedup, token/cost reduction, routing, GPU or paper-facing result claim. Draft #175 remains a specification-only OpenViking/context-provider proposal with no runtime dependency or empirical evidence.

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

1. resolve the exact-current-main Command Station `FAIL` or explicitly exclude that affected path under a frozen rationale;
2. resolve or explicitly bound #120/#126 for any WebVM-dependent path;
3. retain fresh exact-revision live-provider evidence if the protocol depends on that provider path;
4. complete any protected #139/#134 sequence required by the selected evidence path;
5. independently qualify the selected evidence path to the degree required by the paper claim rather than treating repository maintainer attestation as external scientific validation;
6. refresh any selected candidate after a material `main` move instead of inheriting stale-head qualification.

## Primary confirmatory experiment

Run one fixed model across frozen R0–R5 configurations and retain raw observations sufficient to recompute raw correctness `P(X)`, acceptance coverage `P(A)`, accepted correctness `P(X|A)`, AER/ASSR, false acceptance/rejection, verifier rejection/`UNKNOWN`, latency, throughput, rework/conflicts and directly measurable monetary/token/GPU cost.

A positive result requires `P(X|A)` to improve meaningfully over `P(X)` without collapsing `P(A)` toward zero. A falsifying result is equally important: if accepted correctness does not materially improve, or improvement is dominated by rejection, verifier leakage, cost or latency, the hypothesis is not supported for the tested domain.

## What is deliberately not claimed

The repository does not currently claim a new foundation model, a universal verifier/proof system, universally optimal routing, guaranteed token/cost savings, blanket production readiness, an all-green exact-current-main workflow set, successful current-main real-provider inference, physical-iPhone WebVM reliability, acceptable long-run WebVM reliability, independent human assurance from the solo-maintainer merge model, final IE-001 qualification, live-model proof of the central hypothesis, completed long-duration soak, autonomous recursive self-improvement, autonomous merge authority or first-in-literature status.

Receipts establish that stated checks ran over stated evidence under stated identities/revisions. They do not certify arbitrary truth beyond those contracts.
