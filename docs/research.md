# Research claim and prior art

Date: 2026-09-19. Status: implemented research platform; central systems hypothesis not yet established by confirmatory live-model evaluation.

> **Current platform state:** [CURRENT_STATUS.md](CURRENT_STATUS.md)

## Working paper

The broader systems hypothesis is developed in:

**[Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems](papers/reliability-from-unreliable-computation.md)**

The research question is whether system-level AI reliability can improve without making each component model individually reliable when worker authority is constrained, execution is observable, evidence is retained, outputs are independently checked, and accepted state transitions remain under deterministic host control.

The key empirical distinction is between raw worker correctness `P(X)` and accepted-system correctness `P(X|A)`. A positive result requires more than rejection: accepted correctness must improve while acceptance coverage remains useful, and the improvement must be evaluated against orchestration cost, latency and throughput.

## Current accepted engineering boundary

Current `main` is **`e7b72ad18df5729f16d36771971c8a8828d71a10`**.

Recent accepted engineering/governance changes relevant to research interpretation include #275, which repairs exact-head maintainer-approval status publication, and #276, which ensures every merged-main SHA receives a non-cancelling authoritative production Pages attempt. These are engineering/qualification changes, not scientific results.

The first authoritative production Pages attempt for exact current main is **run `35410875305`, attempt 1, FAIL**. Generated desktop+narrow artifact proof and deployment passed; published live guest verification failed and the subsequent published narrow check was skipped. This is exact-revision production qualification evidence. It is **not** a model-quality result, a paid/live Puter result, or proof of the central research hypothesis. The lower-level cause remains **UNKNOWN from the currently inspected retained metadata**.

Controller/provider, Command Station and Factory ownership have retained exact-main PASS results in their named scopes. Those PASS results do not override the production Pages FAIL and do not establish universal/capable-runner M4 qualification, live provider quality, physical-device reliability or a paper-facing effect size.

## Real-model development evidence: #202

Draft #202 retains both favorable and unfavorable evidence.

An earlier heterogeneous three-task DAG run on exact experiment head `6b30125...` remains **FAIL**: 1/3 tasks integrated, the repaired branch did not satisfy its behavioral check within the attempt budget, and the dependent reporting task did not run.

A later distinct exact-head run on `03c77d12...` is a bounded **PASS** using real local Ollama models: 3/3 tasks integrated, verification receipts and dependency lineage were retained, deliberate bad candidates/reviewer outputs were rejected, repair succeeded, and release export completed.

The later PASS does **not** erase the earlier FAIL. It establishes one bounded successful experiment on that exact revision/configuration, not general DAG reliability, provider-independent model quality or production readiness.

## M6 self-maintenance evidence

The bounded self-host sequence remains mixed:

- **#203 / M6-SPEC-001:** **FAIL**, 0/1 integrated, no verification receipt/release.
- **#204 / M6-SPEC-002:** **FAIL**, 0/1 integrated after the bounded pass budget.
- **#215 / M6-SPEC-003:** **FAIL** despite prior-candidate repair context.
- **#217 / M6-SPEC-004:** **FAIL** after transport/source clarification; no review/receipt/release.
- **#220 / M6-SPEC-006:** bounded corrected-path **PASS**: earlier bad candidates were rejected, a later candidate satisfied frozen checks, independent review approved it, the exact reviewed head integrated, a receipt was issued and release export completed.

The #220 PASS is important positive evidence but does not establish general autonomous self-maintenance or recursive self-improvement.

## Deterministic stress evidence: #206, #207 and #212

Research workflow `success` means the apparatus executed and retained evidence; it does not convert scenario-level FAIL/BLOCKED outcomes into PASS.

Retained Campaign A evidence includes:

- **STRESS-A4:** **BLOCKED / invalid for the intended repair-pressure intervention** because the intended fault was not injected before provider/usage failure.
- **STRESS-A5:** **FAIL / incomplete**, 3/6 DAG tasks integrated before escalation with no release.
- **STRESS-A6:** **FAIL in scope**, 0/3 successful Qwen2.5-Coder 7B trials in the frozen campaign.

Retained Campaign B/C evidence includes:

- **#207 STRESS-B1:** **FAIL** — exhausted-budget accounting was observed after accepted integration/release.
- **#207 STRESS-B2:** bounded control **PASS**.
- **#207 STRESS-B3:** **FAIL** — a non-empty release materialized after terminal verifier failure.
- **#207 STRESS-B4:** corrupt-candidate containment **PASS**, recovery-to-success **FAIL / not achieved**.
- **#212 malformed-runner / invalid-reviewer containment:** bounded **PASS** cells.
- **#212 denial→approval recovery:** bounded **PASS**.
- **#212 transient HTTP 500:** failover success remains **UNKNOWN / not established**.
- **#212 missing usage:** **FAIL for accounting-before-authority** because integration plus a receipt occurred before a later `usage_unknown_or_invalid` abort.

These failures remain active blockers for stronger claims that budget, unknown usage or terminal verifier state always precedes all accepted-state/release effects. Candidate repairs are not accepted evidence until merged and the applicable scenarios are requalified.

## M6.2 evidence-driven autonomous discovery

The M6.2 sequence deliberately separates execution, representation, evidence-grounding, semantic-review, evidence-use, metric identity, provenance and Planner-transcription failures.

Key retained cells:

- **#244 / 007 and #246 / 007B:** experiment execution **FAIL** before a valid discovery proposal.
- **#249 / 007C:** bounded autonomous-discovery **FAIL** after malformed/repeated/truncated candidates exhausted the five-pass brake.
- **#250/#251/#252/#254:** bounded **FAIL** cells after typed output reached deterministic admission but repeatedly requested already-measured evidence.
- **#255 / 007H:** semantic-review **FAIL** for causal overclaim, non-falsifiable acceptance and preservation-criteria defects.
- **#257 / 007J:** first retained bounded autonomous-discovery **PASS at formal MeasurementGap admission**. Receipt: `09f3bbc0dba17ca7344b485cf4a8757dc11382e0ac2f6b46ece8fb7f74bd80c9`.
- **#259/#262/#263:** bounded post-gap/evidence-resolver/active-query **FAIL** cells because the Scientist continued requesting already-present or already-resolved evidence.
- **#264 / 007O:** workflow/receipt integrity succeeded, but the scientific conclusion is **UNKNOWN** because the admitted metric identity/semantics were ambiguous. Receipt integrity is not semantic truth.
- **#274 / 007S:** bounded **PASS** for registry/receipt semantic-binding controls.
- **#273/#277:** retained provenance/Planner **FAIL** cells; #277 positively demonstrates host-owned provenance binding while the overall experiment still fails at Planner transcription.

The Metric Registry and proof-carrying derivation-graph line (#265/#270/#298/#299/#300) exists to prevent ambiguous/duplicate metric and semantic-custody errors. Until those positive admission conditions are accepted and satisfied, **M6-008 remains BLOCKED**.

General autonomous discovery and recursive self-improvement remain **UNKNOWN / not established**. A single successful admission does not establish a general recursive-improvement capability.

## New experimental branches do not change accepted capability

Recent draft research/integration work includes #293 (M7 governed recursive mission), #313 (A2A semantic-feasibility spike) and #314 (Vector/Wire-Pod verified continual-learning experiment). Their own stated boundaries keep them experimental/unaccepted and preserve external promotion/qualification gates. They therefore do not change accepted `main` capability or justify an autonomous self-promotion claim.

## WebVM / provider research boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

Current-main production Pages failure `35410875305` occurs at published live guest verification after generated proof and deployment passed. It must remain a production qualification **FAIL**, but the inspected workflow metadata does not justify reclassifying it as provider/model-quality failure.

The #186 iOS/WebKit fallback remains accepted. It is not physical heavyweight-WebVM reliability evidence. Issues #120/#126 remain open because bounded mitigations and individual green runs do not establish long-run recurrence rate or root cause.

## Factory / protected evidence boundary

M2/M3/M4 are implemented. M4 remains environment- and exact-revision-bound rather than universally qualified.

Accepted #185/#187 protected changes retain their exact reviewed scope. PR #139 and downstream #134 remain a separate protected sequence. Qualification-v1 work on its separate testing branch, including #303/#312, is branch evidence only unless and until the applicable production sequence is deliberately accepted.

`implementation-status.yaml` remains an implementation-presence manifest, not a qualification manifest.

## Governance and research independence

Merged #168 establishes repository merge control as:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

This is **maintainer-reviewed with automated qualification**, not independent human assurance. A paper-facing security, release or scientific claim may still require evidence independent of the implementer/maintainer.

Issue #305 also remains open for Actions queue saturation. Queue delay is an operational qualification problem, not evidence of scientific success or failure. Open #307 is a candidate fan-out repair and is not accepted until merged and observed effective.

## Proposed contribution

The original contribution was framed as **counterexample-directed residual delegation with evidence negotiation**: compile a checked workflow's unresolved frontier into a bounded, independently verifiable request while preserving accepted independent work and carrying content-bound receipts across model boundaries.

The broader hypothesis is:

> stochastic workers may remain individually unreliable if the surrounding system constrains their authority, observes execution, preserves evidence, independently checks candidate work and deterministically controls accepted state.

The novelty claim is intentionally bounded. Routing, checkers, DAGs, caching, retrieval, sandboxing, model mixtures and counterexample-guided synthesis all have substantial prior art. The empirical research question is whether this composition produces measurably better **accepted-state reliability** under fixed component capability.

This repository does not establish a first-in-literature result.

## Confirmatory gate

Before paper-facing outcome collection, freeze exact source, execution/evidence path, workload/task mapping, model/version, inference settings, verifier policies, prompts, metrics and analysis code **before** observing confirmatory results.

At minimum:

1. preserve exact-revision failures, blocked interventions and mixed results rather than treating later PASSes as erasure;
2. repair/requalify the #207/#208/#212 accounting/release-ordering defects if the chosen path depends on those authority effects;
3. resolve or explicitly exclude #120/#126 for any WebVM-dependent protocol;
4. retain fresh exact-revision live-provider evidence if the protocol depends on that provider path;
5. preserve any protected ownership/requalification sequence required by the selected evidence path;
6. independently qualify the selected evidence path to the degree required by the paper claim;
7. freeze the protocol before outcome access and retain negative, rejected, `UNKNOWN`, `BLOCKED`, failed and missing cells.

## Primary confirmatory experiment

Run one fixed model across frozen R0–R5 configurations and retain raw observations sufficient to recompute raw correctness `P(X)`, acceptance coverage `P(A)`, accepted correctness `P(X|A)`, AER/ASSR, false acceptance/rejection, verifier rejection/`UNKNOWN`, latency, throughput, rework/conflicts and directly measurable monetary/token/GPU cost.

A positive result requires `P(X|A)` to improve meaningfully over `P(X)` without collapsing `P(A)` toward zero. A falsifying result is equally important: if accepted correctness does not materially improve, or improvement is dominated by rejection, verifier leakage, cost or latency, the hypothesis is not supported for the tested domain.

## What is deliberately not claimed

The repository does not currently claim a new foundation model, a universal verifier/proof system, universally optimal routing, guaranteed token/cost savings, blanket production readiness, successful exact-current-main real-provider inference, physical heavyweight-WebVM iPhone reliability, acceptable long-run WebVM reliability, independent human assurance from the solo-maintainer merge model, live-model proof of the central hypothesis, completed long-duration soak, autonomous recursive self-improvement, autonomous merge authority or first-in-literature status.

Receipts establish that stated checks ran over stated evidence under stated identities/revisions. They do not certify arbitrary truth beyond those contracts.