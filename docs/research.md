# Research claim and prior art

Date: 2026-09-18. Status: implemented research platform; central systems hypothesis not yet established by confirmatory live-model evaluation.

> **Current platform state:** [CURRENT_STATUS.md](CURRENT_STATUS.md)

## Working paper

The broader systems hypothesis is developed in:

**[Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems](papers/reliability-from-unreliable-computation.md)**

The research question is whether system-level AI reliability can improve without making each component model individually reliable when worker authority is constrained, execution is observable, evidence is retained, outputs are independently checked, and accepted state transitions remain under deterministic host control.

The key empirical distinction is between raw worker correctness `P(X)` and accepted-system correctness `P(X|A)`. A positive result requires more than rejection: accepted correctness must improve while acceptance coverage remains useful, and the improvement must be evaluated against orchestration cost, latency and throughput.

## Current accepted engineering boundary

Current `main` is **`d665b188ccc5bb659fb37bc52ac387ab4d85f976`**.

Merged #200 hardens the native setup path; merged #205 restores the private provider channel across Mission Control reload/remount with validated session-scoped state; merged #218 applies bounded Station repair-loop remediation by carrying content-bound prior-candidate context into repair attempts while preserving clean baseline worktrees, clarifying transport-versus-file-language contracts, and unifying the bounded attempt ceiling at five. These are accepted engineering changes, not scientific results.

For exact `main@d665b18...`, seven observed ordinary `push` workflows completed **PASS on attempt 1**: Factory ownership, M4 runner prerequisites, measured-evaluation binding, clean install, Controller/provider, Command Station, and Pages/deployment. This is scoped mechanism/integration evidence only. It does not establish every-host M4 qualification, successful live Puter inference, long-run WebVM reliability, physical-device reliability, general autonomous self-maintenance, or a paper-facing effect size.

## Real-model experiment evidence: #202

Draft #202 retains both favorable and unfavorable evidence.

An earlier heterogeneous three-task DAG run on exact experiment head `6b30125...` remains **FAIL**: 1/3 tasks integrated, the repaired branch did not satisfy its behavioral check within the attempt budget, and the dependent reporting task did not run.

A later distinct exact-head run on `03c77d12...` is a bounded **PASS** using real local Ollama models:

- Qwen2.5-Coder 3B runner;
- Llama 3.2 1B reviewer;
- 3/3 tasks integrated;
- verification receipts retained for all three tasks;
- dependency lineage retained;
- deliberately bad candidates were rejected before later valid candidates integrated;
- release export was produced.

The later PASS does **not** erase the earlier FAIL. It establishes one bounded successful experiment on that exact revision/configuration, not general DAG reliability, provider-independent model quality, or production readiness.

## M6 self-maintenance experiments: #203, #204, #215, #217 and #220

Draft #203's first-authoritative ImprovementSpec self-host trial remains **FAIL**: 0/1 integrated, three attempts, max-iteration escalation, no verification receipt and no release.

Draft #204 repeated the bounded trial with Qwen2.5-Coder 7B. Its first-authoritative M6-SPEC-002 run also remains **FAIL**: 0/1 integrated, three passes, max-iteration escalation, no verification receipt and no release.

Draft #215 (M6-SPEC-003) exercised prior-candidate repair context with Qwen2.5-Coder 1.5B. Repair-context hashes were retained on attempts 2 and 3, but the authoritative run still finished **FAIL** with 0/1 integrated, no review, verification receipt, release or promotion. The retained candidates showed transport/source conflation.

Draft #217 (M6-SPEC-004) explicitly separated the outer transport JSON contract from file-language content while retaining prior-candidate context. The authoritative workflow retained evidence but the experiment remains **FAIL**: 0/1 integrated, three passes, max-iteration escalation, no review/receipt/release. The first candidate had an indentation error; attempts 2 and 3 imported a nonexistent `dataclasses.frozen` symbol.

Those negative experiments directly informed accepted #218. #218 changes the runtime repair context/contract and attempt envelope, but acceptance authority remains unchanged.

### M6-SPEC-006: first bounded corrected-runtime PASS

Draft #220 tests the corrected #218 runtime on exact experiment head **`7971a05798fbc77f7be344dd15f920adf1fad03c`** with local Qwen2.5-Coder 7B, a dedicated Ollama endpoint, the frozen ImprovementSpec checks, the five-attempt repair envelope, and an 1800-second mission budget.

The authoritative first run retained the following sequence:

- attempt 1 generated invalid Python importing `frozen` from `dataclasses`; the frozen check rejected it;
- attempt 2 fixed the import but still accepted whitespace-only invalid fields; the frozen behavioral assertion rejected it;
- attempt 3 incorporated repair context, passed 2/2 frozen checks, and advanced to review;
- Station review approved the candidate;
- 1/1 task integrated;
- a `residual.station.receipt.v2` verification receipt was retained;
- release export completed;
- batch control outcome was success after three passes.

Workflow run `35334715201` completed successfully on attempt 1 and retained artifact `m6-spec-006-corrected-runtime-evidence` (`10543236401`, artifact digest `sha256:ab7d8cfb639557510fff9789aa4c14a2ed940ecc71b37a5190fba0de84f13e61`). The retained trial reports four local-model calls, 9,217 reported tokens, no cloud token usage, and no unreported calls.

Interpretation is deliberately narrow:

- M6-SPEC-006 exact trial: **PASS**;
- accepted #218 repair-loop mechanism: **PASS on main within its tested engineering scope**;
- #203/#204/#215/#217: **remain FAIL**;
- general M6 repair reliability across seeds/tasks/models: **UNKNOWN / not established**;
- autonomous discovery of what to improve: **not established by this fixed-spec trial**;
- autonomous merge authority: **not granted**;
- central recursive/self-improvement hypothesis: **not established by one positive trial**.

The important research change is therefore not “M6 solved,” but that the retained sequence now contains both repeatable negative interventions and one bounded post-remediation positive intervention.

## Deterministic stress evidence: #206, #207 and #212

Draft #206 Campaign A is complete at its corrected exact experiment head `e173719...` against frozen baseline `699e286...`. The earlier apparatus revision is explicitly invalid because it would have tested GitHub's synthetic pull-request merge commit; only the corrected exact-head runs are used here. Workflow-level success means the experiments executed and retained artifacts, not that the scenarios passed.

Retained Campaign A evidence remains mixed and negative where stated:

- **STRESS-A4 repair pressure — BLOCKED / invalid for the intended intervention:** 0 faults were injected; the provider/structured-output call failed, usage became unknown, the host budget aborted after one pass, and 0/1 integrated.
- **STRESS-A5 DAG pressure — FAIL / incomplete:** 3/6 tasks integrated across five passes before `no_runnable_tasks` escalation; downstream tasks did not complete and no release export was attempted.
- **STRESS-A6 reliability — FAIL in the frozen campaign:** Qwen2.5-Coder 7B completed 0/3 successful trials, accepted rate 0.0, with each trial ending 0/1 integrated after the three-pass max-iteration brake.

The later #220 M6 PASS is a different exact intervention and does not rewrite those cells.

Draft #207 deterministic Campaign B retained mixed scenario-level evidence:

- **STRESS-B1 — FAIL:** token-budget exhaustion was recorded only after accepted integration/release had already occurred.
- **STRESS-B2 — PASS within the control:** the early-convergence control completed 2/2 tasks without the budget/max-iteration trips under study.
- **STRESS-B3 — FAIL:** a terminal verifier failure aborted the batch with 0 integrated, yet a non-empty release was still materialized afterward.
- **STRESS-B4 — mixed:** injected corrupt candidates were rejected and none integrated, a bounded containment **PASS**; however, the task did not recover to successful completion within the frozen pass budget.

Draft #212 Campaign C adds a deterministic failure matrix:

- malformed runner JSON: **PASS for fail-closed containment** in that exact scenario;
- invalid reviewer schema: **PASS for fail-closed containment** in that exact scenario;
- reviewer denial followed by approval: **PASS for that bounded recovery path**;
- transient HTTP 500: no integration occurred, but provider retry/failover success was not established;
- missing usage: **FAIL for accounting-before-authority** because a valid candidate integrated and received a receipt before the later `usage_unknown_or_invalid` host abort, corroborating #208.

A green research workflow means the apparatus executed and retained artifacts; it does not convert scenario-level FAIL/BLOCKED evidence into PASS.

## Open governance repair candidate: #214

Draft #214 targets #208 by mirroring token/deadline state into Station before review/integration and tightening release eligibility around successful run control. It remains unaccepted and is still based on predecessor `main@4608afa...` at head `d3e8a5ec...`. Because accepted main moved through #218 to `d665b18...`, #214 must be refreshed/requalified before acceptance.

Therefore the #207/#212 accounting-ordering defect remains an accepted-main **FAIL/open blocker**. #218/#220 repair-loop success is independent and must not be used as evidence that the authority-ordering problem is fixed.

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

1. preserve exact-revision failures, blocked interventions, the #220 bounded PASS, and mixed results rather than treating any later result as erasure;
2. repair/requalify the #207/#208 accounting/release-ordering defects, including the missing-usage case reproduced by #212, if the chosen path depends on those authority effects;
3. resolve or explicitly exclude #120/#126 for any WebVM-dependent protocol;
4. retain fresh exact-revision live-provider evidence if the protocol depends on that provider path;
5. complete any protected #139/#134 sequence required by the selected evidence path;
6. independently qualify the selected evidence path to the degree required by the paper claim;
7. freeze the protocol before outcome access and retain negative, rejected, `UNKNOWN`, `BLOCKED`, failed and missing cells.

## Primary confirmatory experiment

Run one fixed model across frozen R0–R5 configurations and retain raw observations sufficient to recompute raw correctness `P(X)`, acceptance coverage `P(A)`, accepted correctness `P(X|A)`, AER/ASSR, false acceptance/rejection, verifier rejection/`UNKNOWN`, latency, throughput, rework/conflicts and directly measurable monetary/token/GPU cost.

A positive result requires `P(X|A)` to improve meaningfully over `P(X)` without collapsing `P(A)` toward zero. A falsifying result is equally important: if accepted correctness does not materially improve, or improvement is dominated by rejection, verifier leakage, cost or latency, the hypothesis is not supported for the tested domain.

## What is deliberately not claimed

The repository does not currently claim a new foundation model, a universal verifier/proof system, universally optimal routing, guaranteed token/cost savings, blanket production readiness, successful exact-current-main real-provider inference, physical heavyweight-WebVM iPhone reliability, acceptable long-run WebVM reliability, independent human assurance from the solo-maintainer merge model, live-model proof of the central hypothesis, completed long-duration soak, general autonomous recursive self-improvement, autonomous merge authority or first-in-literature status.

Receipts establish that stated checks ran over stated evidence under stated identities/revisions. They do not certify arbitrary truth beyond those contracts.