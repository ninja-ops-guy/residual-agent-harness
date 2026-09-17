# Research claim and prior art

Date: 2026-09-17. Status: implemented research platform; central systems hypothesis not yet established by confirmatory live-model evaluation.

> **Current platform state:** [CURRENT_STATUS.md](CURRENT_STATUS.md)

## Working paper

The broader systems hypothesis is developed in:

**[Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems](papers/reliability-from-unreliable-computation.md)**

The research question is whether system-level AI reliability can improve without making each component model individually reliable when worker authority is constrained, execution is observable, evidence is retained, outputs are independently checked, and accepted state transitions remain under deterministic host control.

The key empirical distinction is between raw worker correctness `P(X)` and accepted-system correctness `P(X|A)`. A positive result requires more than rejection: accepted correctness must improve while acceptance coverage remains useful, and the improvement must be evaluated against orchestration cost, latency and throughput.

## Current evidence boundary

Current `main` is **`dcf1e5071deb624c637aa72df575089435d72ac9`**, produced by merged #189 on top of merged #187.

#187 accepts a protected M4 safety-test observation repair and the corresponding ownership-baseline pin. Its exact-head automated qualification and maintainer approval were PASS before merge, but this does not establish universal/capable-runner M4 qualification and does not erase the historical Controller/provider FAIL that motivated the repair.

#189 accepts a static Pages isolation-boundary repair that keeps the optional `/provider/` helper outside COOP/COEP response rewriting while preserving `/demo/` and heavyweight WebVM isolation. Its exact-head PR workflows, including Pages, were PASS before merge.

The first exact-current-main post-#189 push/deployment workflows were still queued at the latest observation. Therefore post-merge production qualification and provider-helper behavior remain pending/UNKNOWN rather than inferred PASS.

These are mechanism/integration/browser results. They are not paper-facing effect sizes, paid/live provider success, model-quality evidence, physical heavyweight-WebVM reliability evidence, or long-duration reliability evidence.

## WebVM / provider research boundary

Retained diagnostics isolate a WebVM-specific, process-local CPython positive-duration timed-wait failure affecting at least `time.sleep()` and `select.select()`, while tested direct libc waits continue beyond the same narrow boundary. The lower-level CPython/glibc/WebVM cause and any relationship to earlier interpreter/allocator corruption remain **UNKNOWN**.

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

#179 changed the bounded build-output path but did not prove truncation caused the historical invalid responses. #183 changed provider-session lifecycle handling but did not establish live semantic success. #189 repairs a separately observed provider-helper COI/CORP publication failure but still requires merged-revision production deployment and retained real-account evidence before live-provider success can be claimed.

The #186 iOS/WebKit fallback remains accepted. It routes unsupported/unqualified iOS WebKit to the lightweight walkthrough before heavyweight guest boot. This is not physical heavyweight-WebVM reliability evidence. Published physical-device validation remains open, and the lower-level WebKit process-kill mechanism remains **UNKNOWN**.

Issues #120/#126 remain open because trigger avoidance, recovery, safe fallback, added diagnostics and individual green browser runs do not establish long-run recurrence rate or root cause.

## Governance and research independence

Merged #168 establishes the repository's solo-maintainer merge-control model:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

This should be described as **maintainer-reviewed with automated qualification**, not independent human assurance. A paper-facing security, release or scientific claim may still require evidence independent of the implementer/maintainer.

## Factory / protected evidence boundary

M2/M3/M4 are implemented. M4 remains environment- and exact-revision-bound rather than universally qualified.

The #185 protected runtime-journal bytes and ownership-baseline advance remain accepted. #187 additionally accepts the protected M4 test observation repair and corresponding ownership pin. Their accepted claims are limited to those reviewed changes; acceptance does not erase unrelated historical Factory/M4 failures or establish every-host capability.

PR #139 and downstream #134 remain a separate protected sequence. If a selected research path depends on them, preserve their complete protected-byte sequence and refresh/requalify against current main.

## AQ-GOV-001 candidate

PR **#188** adds an observable adversarial lab for a specific governance failure mode: ten cooperating agents unanimously approve authority escalation and then attempt privileged tool registration, outbound posting, credential access, verifier disablement, protected-policy writes, WorkerContract mutation, self-verification, self-issued acceptance receipts, authority delegation, and privileged worker spawning.

The candidate exercises existing `QuarantineStore` / `ProposedAction`, immutable Factory `WorkerContract`, and `AttemptGuard` boundaries, plus a positive control that must remain usable. It is **unaccepted candidate evidence** until merged/qualified. It does not claim kernel/container/hypervisor/broker escape resistance.

## Qualification and inference-economics work

PR #152 proposes a broader Qualification v1 layer. Any prior result on an older base remains historical to that head. Virtual-day stress is not elapsed wall-clock soak; planned 24h/72h/30d workflows create no elapsed claim until the actual runs complete.

PRs #160–#167 are inference-engineering specifications. PR #177 remains a development-only IE-001 prototype qualification candidate. Its prior focused PASS/maintainer evidence is historical to its candidate head and must be reconciled/refreshed against the current IE-001 contract and applicable current-main qualification before final IE-001 qualification is claimed.

PR #190 is a provider-session recovery candidate based on the #187 merge before #189 and must be refreshed/requalified before integration. PR #191 is an unaccepted automated PR-review workflow candidate and is not part of the repository governance model until merged/qualified.

## Proposed contribution

The original contribution was framed as **counterexample-directed residual delegation with evidence negotiation**: compile a checked workflow's unresolved frontier into a bounded, independently verifiable request while preserving accepted independent work and carrying content-bound receipts across model boundaries.

The broader hypothesis is:

> stochastic workers may remain individually unreliable if the surrounding system constrains their authority, observes execution, preserves evidence, independently checks candidate work and deterministically controls accepted state.

The novelty claim is intentionally bounded. Routing, checkers, DAGs, caching, retrieval, sandboxing, model mixtures and counterexample-guided synthesis all have substantial prior art. The empirical research question is whether this composition produces measurably better **accepted-state reliability** under fixed component capability.

This repository does not establish a first-in-literature result.

## Confirmatory gate

Before paper-facing outcome collection, freeze the exact source revision, selected execution/evidence path, workload/task mapping, model/version, inference settings, verifier revisions/policies, prompts, metrics and analysis code **before** observing confirmatory results.

At minimum:

1. preserve retained exact-revision failures rather than treating later repairs as erasure;
2. resolve or explicitly bound #120/#126 for any WebVM-dependent path;
3. retain fresh exact-revision live-provider evidence if the protocol depends on that provider path;
4. complete any protected #139/#134 sequence required by the selected evidence path;
5. independently qualify the selected evidence path to the degree required by the paper claim rather than treating repository maintainer attestation as external scientific validation;
6. refresh any selected candidate after a material `main` move instead of inheriting stale-head qualification.

## Primary confirmatory experiment

Run one fixed model across frozen R0–R5 configurations and retain raw observations sufficient to recompute raw correctness `P(X)`, acceptance coverage `P(A)`, accepted correctness `P(X|A)`, AER/ASSR, false acceptance/rejection, verifier rejection/`UNKNOWN`, latency, throughput, rework/conflicts and directly measurable monetary/token/GPU cost.

A positive result requires `P(X|A)` to improve meaningfully over `P(X)` without collapsing `P(A)` toward zero. A falsifying result is equally important: if accepted correctness does not materially improve, or improvement is dominated by rejection, verifier leakage, cost or latency, the hypothesis is not supported for the tested domain.

## What is deliberately not claimed

The repository does not currently claim a new foundation model, a universal verifier/proof system, universally optimal routing, guaranteed token/cost savings, blanket production readiness, successful exact-current-main real-provider inference, physical heavyweight-WebVM iPhone reliability, acceptable long-run WebVM reliability, independent human assurance from the solo-maintainer merge model, final IE-001 qualification, accepted AQ-GOV-001 results, live-model proof of the central hypothesis, completed long-duration soak, autonomous recursive self-improvement, autonomous merge authority or first-in-literature status.

Receipts establish that stated checks ran over stated evidence under stated identities/revisions. They do not certify arbitrary truth beyond those contracts.
