# Research claim and prior art

Date: 2026-09-18. Status: implemented research platform; central systems hypothesis not yet established by confirmatory live-model evaluation.

> **Current platform state:** [CURRENT_STATUS.md](CURRENT_STATUS.md)

## Working paper

The broader systems hypothesis is developed in:

**[Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems](papers/reliability-from-unreliable-computation.md)**

The research question is whether system-level AI reliability can improve without making each component model individually reliable when worker authority is constrained, execution is observable, evidence is retained, outputs are independently checked, and accepted state transitions remain under deterministic host control.

The key empirical distinction is between raw worker correctness `P(X)` and accepted-system correctness `P(X|A)`. A positive result requires more than rejection: accepted correctness must improve while acceptance coverage remains useful, and the improvement must be evaluated against orchestration cost, latency and throughput.

## Current accepted engineering boundary

Current `main` is **`4608afabf5de4c87d77aaf149dfc12538d364f43`**.

Merged #200 hardens the native setup path; merged #205 restores the private provider channel across Mission Control reload/remount with validated session-scoped state. These are accepted engineering changes, not scientific results.

The exact-current-main Actions set observed for `4608afa...` is complete with no pending, cancelled, or failing run in the retained exact-SHA query used for this refresh; a sampled Controller/provider run completed **PASS on attempt 1**. This is scoped mechanism/integration evidence only. It does not establish every-host M4 qualification, successful live Puter inference, long-run WebVM reliability, physical-device reliability, or a paper-facing effect size.

## Real-model experiment evidence: #202

Draft #202 retains both favorable and unfavorable evidence.

An earlier heterogeneous three-task DAG run on exact experiment head `6b30125...` remains **FAIL**: 1/3 tasks integrated, the repaired branch did not satisfy its behavioral check within the attempt budget, and the dependent reporting task did not run.

A later distinct exact-head run on `03c77d12...` is a bounded **PASS** using real local Ollama models:

- Qwen2.5-Coder 3B runner;
- Llama 3.2 1B reviewer;
- 3/3 tasks integrated;
- verification receipts retained for all three tasks;
- dependency lineage retained;
- a deliberately corrupted first candidate was rejected and repaired before later integration;
- an out-of-contract write was rejected before a later valid candidate;
- invalid/truncated reviewer output was rejected before a valid review;
- release export was produced.

The later PASS does **not** erase the earlier FAIL. It establishes one bounded successful experiment on that exact revision/configuration, not general DAG reliability, provider-independent model quality, or production readiness.

## M6 self-maintenance experiments: #203 and #204

Draft #203's first-authoritative ImprovementSpec self-host trial remains **FAIL**: 0/1 integrated, three attempts, max-iteration escalation, no verification receipt and no release.

Draft #204 repeated the bounded trial with Qwen2.5-Coder 7B. Its first-authoritative M6-SPEC-002 run also remains **FAIL**: 0/1 integrated, three passes, max-iteration escalation, no verification receipt and no release. The stronger model changed the observed candidate defects but did not satisfy the frozen contract within the pass budget.

These are useful negative results. They do **not** establish autonomous recursive self-improvement and do not restore previously removed #132 self-maintenance tooling as current accepted capability.

## Deterministic stress evidence: #206 and #207

Draft #206 preregisters stress campaign A against a frozen baseline. At the latest observation its dedicated campaign workflow is still **PENDING / in progress**. No scenario outcome from that campaign is promoted before the retained run completes.

Draft #207 deterministic campaign B has completed its research workflow and retained mixed scenario-level evidence:

- **STRESS-B1 — FAIL:** token-budget exhaustion was recorded only after accepted integration/release had already occurred. This falsifies the stronger ordering claim for that exact scenario.
- **STRESS-B2 — PASS within the control:** the early-convergence control completed 2/2 tasks without the budget/max-iteration trips under study.
- **STRESS-B3 — FAIL:** a terminal verifier failure aborted the batch with 0 integrated, yet a non-empty release was still materialized afterward. This is a fail-closed release-eligibility defect for that exact scenario.
- **STRESS-B4 — mixed:** injected corrupt candidates were rejected and none integrated, which is a bounded containment **PASS**; however, the task did not recover to successful completion within the frozen pass budget, so recovery-to-success is **FAIL / not achieved** and general repair reliability remains **UNKNOWN**.

A green research workflow means the apparatus executed and retained artifacts; it does not convert scenario-level FAIL evidence into PASS.

The #207 findings are currently more important than another favorable demonstration because they identify control-ordering conditions that must be repaired/requalified before stronger fail-closed governance claims are made.

## WebVM / provider research boundary

Retained diagnostics isolate a WebVM-specific, process-local CPython positive-duration timed-wait failure affecting at least `time.sleep()` and `select.select()` in the tested guest/runtime combination. The lower-level CPython/glibc/WebVM cause and any relationship to earlier interpreter/allocator corruption remain **UNKNOWN**.

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

#179, #183, #189 and #205 repair bounded build-output, provider-session, publication and reload-recovery surfaces. None alone establishes live semantic success. Fresh retained exact-deployed-revision candidate→verifier→receipt evidence remains required.

The #186 iOS/WebKit fallback remains accepted. It is not physical heavyweight-WebVM reliability evidence. Issues #120/#126 remain open because bounded mitigations and individual green runs do not establish long-run recurrence rate or root cause.

## Factory / protected evidence boundary

M2/M3/M4 are implemented. M4 remains environment- and exact-revision-bound rather than universally qualified.

Accepted #185/#187 protected changes retain their exact reviewed scope. PR #139 and downstream #134 remain a separate protected sequence. If a selected research path depends on them, preserve the complete ownership-baseline/requalification sequence and never convert `BLOCKED`/`UNKNOWN` into `PASS`.

## Governance and research independence

Merged #168 establishes repository merge control as:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

This is **maintainer-reviewed with automated qualification**, not independent human assurance. A paper-facing security, release or scientific claim may still require evidence independent of the implementer/maintainer.

## Proposed contribution

The original contribution was framed as **counterexample-directed residual delegation with evidence negotiation**: compile a checked workflow's unresolved frontier into a bounded, independently verifiable request while preserving accepted independent work and carrying content-bound receipts across model boundaries.

The broader hypothesis is:

> stochastic workers may remain individually unreliable if the surrounding system constrains their authority, observes execution, preserves evidence, independently checks candidate work and deterministically controls accepted state.

The novelty claim is intentionally bounded. Routing, checkers, DAGs, caching, retrieval, sandboxing, model mixtures and counterexample-guided synthesis all have substantial prior art. The empirical research question is whether this composition produces measurably better **accepted-state reliability** under fixed component capability.

This repository does not establish a first-in-literature result.

## Confirmatory gate

Before paper-facing outcome collection, freeze exact source, execution/evidence path, workload/task mapping, model/version, inference settings, verifier policies, prompts, metrics and analysis code **before** observing confirmatory results.

At minimum:

1. preserve exact-revision failures and mixed results rather than treating later PASSes as erasure;
2. repair/requalify any #207 governance-ordering defect required by the chosen path;
3. resolve or explicitly exclude #120/#126 for any WebVM-dependent protocol;
4. retain fresh exact-revision live-provider evidence if the protocol depends on that provider path;
5. complete any protected #139/#134 sequence required by the selected evidence path;
6. independently qualify the selected evidence path to the degree required by the paper claim;
7. freeze the protocol before outcome access and retain negative, rejected, `UNKNOWN`, failed and missing cells.

## Primary confirmatory experiment

Run one fixed model across frozen R0–R5 configurations and retain raw observations sufficient to recompute raw correctness `P(X)`, acceptance coverage `P(A)`, accepted correctness `P(X|A)`, AER/ASSR, false acceptance/rejection, verifier rejection/`UNKNOWN`, latency, throughput, rework/conflicts and directly measurable monetary/token/GPU cost.

A positive result requires `P(X|A)` to improve meaningfully over `P(X)` without collapsing `P(A)` toward zero. A falsifying result is equally important: if accepted correctness does not materially improve, or improvement is dominated by rejection, verifier leakage, cost or latency, the hypothesis is not supported for the tested domain.

## What is deliberately not claimed

The repository does not currently claim a new foundation model, a universal verifier/proof system, universally optimal routing, guaranteed token/cost savings, blanket production readiness, successful exact-current-main real-provider inference, physical heavyweight-WebVM iPhone reliability, acceptable long-run WebVM reliability, independent human assurance from the solo-maintainer merge model, live-model proof of the central hypothesis, completed long-duration soak, autonomous recursive self-improvement, autonomous merge authority or first-in-literature status.

Receipts establish that stated checks ran over stated evidence under stated identities/revisions. They do not certify arbitrary truth beyond those contracts.