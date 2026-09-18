# Research claim and prior art

Date: 2026-09-18. Status: implemented research platform; central systems hypothesis not yet established by confirmatory live-model evaluation.

> **Current platform state:** [CURRENT_STATUS.md](CURRENT_STATUS.md)

## Working paper

The broader systems hypothesis is developed in:

**[Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems](papers/reliability-from-unreliable-computation.md)**

The research question is whether system-level AI reliability can improve without making each component model individually reliable when worker authority is constrained, execution is observable, evidence is retained, outputs are independently checked, and accepted state transitions remain under deterministic host control.

The key empirical distinction is between raw worker correctness `P(X)` and accepted-system correctness `P(X|A)`. A positive result requires more than rejection: accepted correctness must improve while acceptance coverage remains useful, and the improvement must be evaluated against orchestration cost, latency and throughput.

## Current evidence boundary

Current `main` is **`699e2869e294fe157b4bfd73a272057683a2f7e0`**.

Accepted research/engineering state relevant to claims includes:

- **#188** — AQ-GOV-001 is accepted/on main. It assumes unanimous 10/10 worker approval for authority escalation and exercises existing quarantine, immutable WorkerContract and AttemptGuard boundaries. It supports only the tested software-path statement that consensus alone does not grant the tested capabilities. It does not establish kernel/container/hypervisor/broker escape resistance or universal agent safety.
- **#194** — accepted product/state repair for persistence/reopening of completed generated-spec drafts. It is not scientific outcome evidence.
- **#133** — accepted WebVM runtime diagnostic apparatus. Retained evidence narrows one failure family to a WebVM-specific CPython positive-duration timeout/wait conversion path affecting at least `time.sleep()` and empty `select.select()`. Tested direct libc waits continue beyond the same narrow boundary. Exact lower-level CPython/i386 ABI/emulation cause remains **UNKNOWN**.
- **#193** — accepted interactive native setup helper. It improves operator setup convenience; it does not establish blank-environment qualification or any scientific outcome.

PR #192 later merged older documentation based on an earlier accepted-main snapshot. That prose regression does not supersede retained implementation or research evidence; this documentation correction restores the current evidence boundary.

Before #192/#193, all seven ordinary first-attempt push workflows on exact `main@b3f00af...` completed **PASS**. #193's exact candidate head completed its observed ordinary qualification/governance workflows **PASS** before merge. On exact current `main@699e286...`, the six observed applicable ordinary post-#193 push workflows completed **PASS on attempt 1**: Factory ownership, M4 runner prerequisites, measured-evaluation binding, clean install, Controller/provider, and Command Station. No exact-current-SHA Pages/deployment run was observed in the retained set, so Pages on this exact SHA remains **UNKNOWN / not observed**. These are integration observations, not scientific outcome evidence.

## Development local-model experiment evidence (#202 / #203)

New retained experiment evidence materially improves the development evidence base without establishing the central confirmatory claim.

### #202 — simple real-model mission: bounded PASS on historical experiment head

Draft PR #202 is explicitly retained as experiment/evidence and is not a merge candidate. On exact experiment head `fee21d140c637300a534b9f498496e92b70d95da`, workflow run `35304614537` completed the dedicated `real-model-mission` job **PASS** on attempt 1. The runner installed Ollama and used `qwen2.5-coder:1.5b` locally from only a behavioral specification for `calculator.py:add(a,b)`.

The retained `real-model-mission-evidence` artifact records:

- run outcome: **SUCCESS**;
- integrated tasks: **1/1**;
- attempts/passes: **1**;
- runner and reviewer provider calls: **2** total;
- reported tokens: **846**;
- wall clock: **16.217 s**;
- compile and behavioral checks: **PASS**;
- reviewer approval: **PASS**;
- verification receipt: present;
- release export: present.

This establishes one bounded real-local-model candidate→checks→review→integration→receipt/export path on that exact experiment revision. It does **not** establish paid/live Puter success, model quality generally, heterogeneous DAG reliability, recursive self-improvement, production reliability, or the frozen R0–R5 hypothesis.

### #202 — later heterogeneous DAG experiment: retained FAIL

The same draft PR later advanced to head `6b30125fd56bdbedcb1d6d04e6ee199dd697b315` and changed the experiment to a heterogeneous dependency DAG with routed local models and a deterministic one-shot fault injection. Exact-head workflow run `35305663580` completed **FAIL** and retained `dag-real-model-mission-evidence`.

The retained evidence records:

- batch outcome: **escalated**;
- tasks integrated: **1/3**;
- `CORE-001`: integrated with checks/review/verification receipt;
- `STATS-002`: entered repair three times and remained `repair_required`; after the injected syntax fault, later attempts compiled but failed behaviorally with `NameError: name 'math_core' is not defined`;
- `REPORT-003`: remained ready and did not run because its dependency did not integrate;
- run-control brake: `dispatch` with reason `no_runnable_tasks`;
- reported tokens: **3174**;
- wall clock: **78.675 s**.

This failure is part of the evidence, not a run to discard or rewrite as success. It demonstrates that one earlier simple real-model success does not support a broader DAG/recovery claim.

### #203 — M6 ImprovementSpec self-host experiment: retained FAIL

Draft PR #203 is a controlled research experiment against frozen baseline `main@699e286...`; it does not modify main, M4, verifier authority, evidence schemas, or promotion controls. On exact experiment head `e123b90d012973bfd260ae5b955eebd4dbac48f0`, run `35305550407` completed **FAIL** on its first authoritative attempt while retaining artifact `m6-improvementspec-research-evidence`.

The retained evidence records:

- batch outcome: **escalated**;
- integrated tasks: **0/1**;
- attempts: **3**;
- first attempt: import/behavior check failed because `ImprovementSpec` was absent;
- second attempt: compile and behavior checks failed with an unclosed parenthesis;
- third attempt: model output was truncated before a verifiable candidate was produced;
- run-control brake: `max_iteration` after three passes;
- reported tokens: **5526**;
- wall clock: **125.374 s**;
- verification receipt: **absent**;
- release files: **none**.

This is useful negative research evidence. It does not show autonomous recursive self-improvement, and it does not invalidate the broader systems hypothesis; it shows that this bounded self-hosting task failed under the tested model/spec/budget combination.

## #133 diagnostic research boundary

The strongest currently supported diagnosis for the reproduced timed-wait symptom is narrower than generic “WebVM corruption” but broader than `time.sleep()` alone:

- positive-duration `time.sleep()` reproduces `_PyTime_t` overflow around a narrow process-local call boundary;
- empty `select.select(..., timeout)` reproduces the same family;
- zero-duration sleep and tested monotonic clock reads pass beyond the boundary;
- native i386 controls pass;
- direct libc `nanosleep` and `clock_nanosleep` continue beyond the same boundary;
- fresh guest CPython process creation resets or avoids the process-local boundary in paired tests;
- Mission Control, its persistent worker, background execution and a second interpreter are not necessary preconditions.

This materially supports a shared **CPython positive-duration timeout/wait conversion-path failure under the tested WebVM guest**.

It does **not** establish:

- the exact CPython/i386 ABI, time64, syscall/emulation, handle/resource or conversion defect;
- time64 `ENOSYS` correlation as causal proof;
- a causal link to historical `_sha512`, impossible-constructor, allocator or poisoned-guest evidence;
- an acceptable long-run recurrence rate;
- a production fix.

Those remain **UNKNOWN / unestablished**. Multiple #133 diagnostic workflows intentionally completed **FAIL** after reproducing the defect. Those FAIL observations remain evidence; they are not qualification passes and must not be erased by rerun.

## Historical #132 self-hosting evidence vs current capability

Merged #132 previously delivered a bounded protected self-hosting/research-bundle experiment and retained exact-head evidence. Its claims were deliberately narrow: one external-model-authored candidate, deterministic acceptance predicates, no autonomous merge authority, and synthetic controller/policy stress that was not represented as repeated live autonomous self-improvement.

Merged #133 removed the #132 implementation, workflow, tests, example and dedicated research documentation from current main. Earlier #133 review records explicitly identified those deletions as an integration blocker for a diagnostic-only PR; the deletion nevertheless landed.

Research interpretation is therefore:

- #132's retained historical experiment/evidence remains valid for its named source revision;
- #132 tooling is **not current accepted implementation** on `main@699e286...`;
- the reason for removal and intended retirement status are **UNKNOWN** from retained evidence;
- no current claim should describe bounded self-maintenance/research-bundle tooling as present unless it is deliberately restored/reintroduced and requalified.

Historical evidence is not erased by removal, but historical evidence also does not imply present capability. Draft #203 adds experiment apparatus only and leaves its generated candidate isolated; it does not restore #132 as current accepted capability.

## WebVM / provider research boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

Merged #179 changed the bounded build-output path, #183 changed provider-session lifecycle handling and #189 repaired a provider-helper publication boundary. None alone establishes successful live inference.

PR #190 remains open/unaccepted and must be refreshed/requalified as applicable after material main movement. Any required post-merge production retest remains separate.

The #186 iOS/WebKit fallback is accepted but is not physical heavyweight-WebVM reliability evidence. Issues #120/#126 remain open because #133's narrowed diagnosis is not equivalent to lower-level root cause or long-run reliability qualification.

The #202 local-Ollama success is deliberately not counted as paid/live Puter evidence; it exercised a different provider and environment.

## Governance and research independence

Merged #168 establishes the repository's solo-maintainer merge-control model:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

This should be described as **maintainer-reviewed with automated qualification**, not independent human assurance. A paper-facing security, release or scientific claim may still require evidence independent of the implementer/maintainer.

## Factory / protected evidence boundary

M2/M3/M4 are implemented. M4 remains environment- and exact-revision-bound rather than universally qualified.

Accepted #185/#187 protected changes remain scoped to their reviewed bytes. The separate #139→ownership-baseline→fresh-qualification→#134 sequence remains independent. If a selected research evidence path depends on it, preserve the entire protected-byte process and do not convert `BLOCKED`/`UNKNOWN` capability states into `PASS`.

## Qualification and inference-economics work

PR #152 proposes a broader Qualification v1 layer. Any prior result on an older base remains historical to that exact head. Virtual-day stress is not elapsed wall-clock soak; planned 24h/72h/30d workflows create no elapsed claim until the actual runs complete.

PR #177 remains a development-only IE-001 prototype qualification candidate. Its prior focused/qualification evidence is historical to its candidate head and must be reconciled/refreshed after material main movement before final IE-001 qualification is claimed.

PRs #160–#167 remain inference-engineering specifications/planning unless and until their implementation lands and qualifies.

## Proposed contribution

The original contribution was framed as **counterexample-directed residual delegation with evidence negotiation**: compile a checked workflow's unresolved frontier into a bounded, independently verifiable request while preserving accepted independent work and carrying content-bound receipts across model boundaries.

The broader hypothesis is:

> stochastic workers may remain individually unreliable if the surrounding system constrains their authority, observes execution, preserves evidence, independently checks candidate work, and deterministically controls accepted state.

The novelty claim is intentionally bounded. Routing, checkers, DAGs, caching, retrieval, sandboxing, model mixtures and counterexample-guided synthesis all have substantial prior art. The empirical research question is whether this composition produces measurably better **accepted-state reliability** under fixed component capability.

This repository does not establish a first-in-literature result.

## Confirmatory gate

Before paper-facing outcome collection, freeze the exact source revision, selected execution/evidence path, workload/task mapping, model/version, inference settings, verifier revisions/policies, prompts, metrics and analysis code **before** observing confirmatory results.

At minimum:

1. preserve exact-current-main workflow outcomes and historical failures rather than inheriting or erasing them;
2. resolve or explicitly bound #120/#126 for any WebVM-dependent path;
3. retain fresh exact-revision live-provider evidence if the protocol depends on that provider path;
4. complete any protected #139/#134 sequence required by the selected evidence path;
5. independently qualify the selected evidence path to the degree required by the paper claim rather than treating repository maintainer attestation as external scientific validation;
6. refresh any selected candidate after a material `main` move instead of inheriting stale-head qualification;
7. do not use historical #132 evidence to imply current self-maintenance capability unless the implementation is deliberately restored and requalified;
8. do not treat #193 setup convenience as blank-environment or research qualification;
9. treat #202/#203 as development evidence only: retain both PASS and FAIL outcomes, but do not promote them into the preregistered R0–R5 confirmatory result set.

## Primary confirmatory experiment

Run one fixed model across frozen R0–R5 configurations and retain raw observations sufficient to recompute raw correctness `P(X)`, acceptance coverage `P(A)`, accepted correctness `P(X|A)`, AER/ASSR, false acceptance/rejection, verifier rejection/`UNKNOWN`, latency, throughput, rework/conflicts, and directly measurable monetary/token/GPU cost.

A positive result requires `P(X|A)` to improve meaningfully over `P(X)` without collapsing `P(A)` toward zero. A falsifying result is equally important: if accepted correctness does not materially improve, or improvement is dominated by rejection, verifier leakage, cost or latency, the hypothesis is not supported for the tested domain.

## What is deliberately not claimed

The repository does not currently claim a new foundation model, a universal verifier/proof system, universally optimal routing, guaranteed token/cost savings, blanket production readiness, successful exact-current-main real-provider inference, physical heavyweight-WebVM iPhone reliability, acceptable long-run WebVM reliability, exact root cause of the CPython/WebVM timed-wait failure, independent human assurance from the solo-maintainer merge model, current accepted #132 self-maintenance/research-bundle capability, final IE-001 qualification, confirmatory live-model proof of the central hypothesis, completed long-duration soak, autonomous recursive self-improvement, autonomous merge authority or first-in-literature status.

The bounded #202 simple local-model success does not change those non-claims, and the retained #202 heterogeneous-DAG and #203 self-host failures are part of the evidence base rather than exceptions to omit.

Receipts establish that stated checks ran over stated evidence under stated identities/revisions. They do not certify arbitrary truth beyond those contracts.