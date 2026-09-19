# Research claim and prior art

Date: 2026-09-19. Status: implemented research platform; central systems hypothesis not yet established by confirmatory live-model evaluation.

> **Current platform state:** [CURRENT_STATUS.md](CURRENT_STATUS.md)

## Working paper

The broader systems hypothesis is developed in:

**[Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems](papers/reliability-from-unreliable-computation.md)**

The research question is whether system-level AI reliability can improve without making each component model individually reliable when worker authority is constrained, execution is observable, evidence is retained, outputs are independently checked, and accepted state transitions remain under deterministic host control.

The key empirical distinction is between raw worker correctness `P(X)` and accepted-system correctness `P(X|A)`. A positive result requires more than rejection: accepted correctness must improve while acceptance coverage remains useful, and the improvement must be evaluated against orchestration cost, latency, and throughput.

## Current accepted engineering boundary

Current `main` is **`3bfa6abac719bb1ca5db225b32df347ae2afc079`**, produced by merged #330. No newer production-main commit landed in this check.

Recent accepted engineering changes matter to interpretation but are not scientific results:

- **#307** repairs duplicate feature-branch CI fan-out while preserving non-cancelling production evidence;
- **#260** accepts the provider-bootstrap guard;
- **#288** closes product issue #208 with pre-dispatch Station budget/deadline admission and exact run-control-bound export eligibility;
- **#320** accepts repository-side CSP/anti-clickjacking configuration, while production Vercel header validation remains pending;
- **#328** accepts the non-workflow core execution/egress/XML security hardening;
- **#330** accepts the remaining workflow checkout credential-persistence hardening (`persist-credentials: false`) with structural regression coverage while preserving accepted workflow-trigger semantics.

None of these merges establishes the central research hypothesis, live-provider model quality, universal M4 qualification, or a paper-facing effect size.

Accepted #276 requires a new non-cancelling production Pages attempt for every `main` SHA. Exact-current-main run **`35437556200`**, attempt 1, completed **FAIL**. The generated artifact/browser proof, deployment, published revision identity, and desktop real-guest path passed, while the required narrow/mobile Chromium acceptance failed after several successful live-guest/Workbench stages. Retained live-proof artifact `10582812524` has SHA-256 `868ca31506d278a335ff95d3607adbd13c14edaec8b161c1b45ac013e7f7c8b8`; the lower-level cause is **UNKNOWN**. The prior run `35431634267` remains a scoped **PASS for exact revision `0a675017...` only**; the earlier `e7b72ad...` Pages FAIL remains retained exact-revision evidence.

Open #336 has a branch-only generated Pages **PASS** on exact head `92aca285...`, but it is not accepted or production evidence. It remains held behind #337, which repairs a PR Agent fail-open publication/concurrency defect discovered when an exhausted review provider produced only a failure/status comment. #337 is itself unaccepted with PR Agent advisory and protected maintainer approval **FAIL**. These are engineering/governance observations, not scientific results. If either branch head changes, exact-head evidence must be regenerated; if a repair later reaches `main`, the new production SHA still requires its own first authoritative Pages attempt.

No Pages outcome establishes the central systems hypothesis, provider/model quality, physical heavyweight-WebVM reliability, or any paper-facing effect size. The current failure recorded `cloud_inference` as `NOT_RUN`, so it is not evidence of live Puter/model failure.

## Real-model development evidence

Draft #202 retains both favorable and unfavorable evidence. An earlier heterogeneous three-task DAG run remains **FAIL**, while a later distinct exact-head run is a bounded **PASS** using real local Ollama models with 3/3 tasks integrated, retained receipts/dependency lineage, rejected bad candidates/reviewer outputs, successful repair, and release export.

The later PASS does **not** erase the earlier FAIL. It establishes one bounded successful experiment on that exact revision/configuration, not general DAG reliability, provider-independent model quality, or production readiness.

## M6 self-maintenance evidence

The bounded self-host sequence remains mixed:

- **#203 / M6-SPEC-001:** **FAIL**;
- **#204 / M6-SPEC-002:** **FAIL**;
- **#215 / M6-SPEC-003:** **FAIL**;
- **#217 / M6-SPEC-004:** **FAIL**;
- **#220 / M6-SPEC-006:** bounded corrected-path **PASS**.

The #220 PASS is positive evidence but does not establish general autonomous self-maintenance or recursive self-improvement.

## Deterministic stress evidence: #206, #207 and #212

A green research workflow means the apparatus executed and retained artifacts; it does not convert scenario-level FAIL/BLOCKED evidence into PASS.

Retained Campaign B/C evidence includes:

- **#207 STRESS-B1:** **FAIL** — exhausted-budget accounting was observed after accepted integration/release on the frozen baseline.
- **#207 STRESS-B2:** bounded control **PASS**.
- **#207 STRESS-B3:** **FAIL** — a non-empty release materialized after terminal verifier failure.
- **#207 STRESS-B4:** corrupt-candidate containment **PASS**, recovery-to-success **FAIL / not achieved**.
- **#212 malformed-runner / invalid-reviewer containment:** bounded **PASS** cells.
- **#212 denial→approval recovery:** bounded **PASS**.
- **#212 transient HTTP 500:** failover success remains **UNKNOWN / not established**.
- **#212 missing usage:** **FAIL for accounting-before-authority** because integration plus a receipt occurred before the later `usage_unknown_or_invalid` abort on that frozen baseline.

Merged **#288** repairs the tracked product defect (#208) with host-owned pre-dispatch admission and bound export eligibility. That merge changes accepted product behavior; it does not retroactively turn frozen #207/#212 cells into PASS. Stronger present-tense claims about budget exhaustion, unknown usage, or release ordering require fresh requalification against the accepted repair and remain **UNKNOWN pending repaired-path requalification** until then.

## M6.2 evidence-driven autonomous discovery

The M6.2 sequence deliberately separates execution, representation, evidence grounding, semantic review, evidence use, metric identity, provenance, and Planner-transcription failures.

Key retained cells:

- **#244/#246:** experiment execution **FAIL** before a valid discovery proposal;
- **#249:** bounded autonomous-discovery **FAIL** after malformed/repeated/truncated candidates;
- **#250/#251/#252/#254:** deterministic admission **FAIL** for already-measured evidence requests;
- **#255:** semantic-review **FAIL**;
- **#257:** first retained bounded autonomous-discovery **PASS at formal MeasurementGap admission**;
- **#259/#262/#263:** post-gap/evidence-resolver/active-query **FAIL** cells;
- **#264:** workflow/receipt integrity succeeded, but scientific conclusion **UNKNOWN** because admitted metric identity/semantics were ambiguous;
- **#274:** bounded **PASS** for registry/receipt semantic-binding controls;
- **#273/#277:** provenance/Planner **FAIL** cells, with positive host-owned provenance evidence inside an overall failed path.

General autonomous discovery and recursive self-improvement remain **UNKNOWN / not established**. **M6-008 remains BLOCKED** until its required positive semantic/derivation admission gates are actually satisfied.

## M6-MESH-001 cooperative-efficiency pilot

Open **#319** retains the first frozen M6-MESH-001 crossover pilot. Both sequential and two-call concurrent conditions passed their six obligation checks. Retained mean wall time is about **2.1899 s sequential** versus **1.8300 s concurrent** across three repeats on one local Ollama host.

This is **positive bounded pilot evidence**, not a general mesh-efficiency result. Three repeats on one host with warm-up/order sensitivity are insufficient for a durable performance claim. General distributed mesh/swarm efficiency remains **UNKNOWN / not established**.

## Research Workbench candidate: #323

Open **#323** proposes a built-in Research Workbench that binds experiment identity and frozen definitions into Station governance. Its first planned pilot remains **BLOCKED** until the Workbench is rebased and requalified on a main containing the accepted #288 authority repair.

Therefore:

- Workbench implementation candidate: **UNACCEPTED / draft**;
- previous exact-head qualification results: retained historical branch evidence;
- first authoritative M6-WB-001 trial: **BLOCKED / not run** pending rebase and fresh qualification;
- staged experiment definitions: definition availability only, not experimental evidence.

## Security and deployment evidence are not research results

Merged #320, #328, and #330 improve accepted engineering/security controls, but they do not establish the systems hypothesis.

- #320 production Vercel header enforcement remains **UNKNOWN / pending** until retained production inspection/security validation exists.
- #328 source/runtime security hardening is accepted for its reviewed scope.
- #330 workflow checkout credential-persistence hardening is accepted for its reviewed scope.
- stale overlapping #324 must not be merged wholesale.
- scanner/vendor confidence is not scientific or repository acceptance evidence.

Exact-current-main production Pages qualification is **FAIL** on run `35437556200`, attempt 1, because the required narrow/mobile acceptance failed. The desktop/real-guest path within that run remains a scoped sub-check PASS. This is release/browser qualification evidence only, not model-quality or research-hypothesis evidence.

## WebVM / provider research boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

Accepted provider/session/bootstrap/publication repairs do not substitute for fresh real-account semantic evidence. The #186 iOS/WebKit fallback remains accepted, but it is not physical heavyweight-WebVM reliability evidence. Issues #120/#126 remain open because bounded mitigations and individual green runs do not establish long-run recurrence rate or root cause.

## Factory / protected evidence boundary

M2/M3/M4 are implemented. M4 remains environment- and exact-revision-bound rather than universally qualified.

Accepted #185/#187 protected changes retain their exact reviewed scope. PR #139 and downstream #134 remain a separate protected sequence.

Qualification-v1 remains branch evidence only. Reverse-merge **#333** moved open #152 to exact testing head **`11c0ac67f60f61a7243bcc79ce803d588a89aa94`**. Exact-head run **`35443955204` attempt 1 is FAIL**. Its retained final manifest names `deterministic-regression`, `qualification-selftests`, and `toxic-provider-matrix` as required failures. The deterministic regression failure includes seven enterprise sandbox tests where the hosted runner reported `kernel-level sandbox isolation unavailable`. The selftest and toxic-provider failures both include the full provider-mission qualifier returning FAIL; the lower-level cause remains **UNKNOWN** from retained evidence. Factory ownership, M4 prerequisites, browser VM, Controller/provider, Command Station, clean install and several other surrounding lanes are PASS, but partial PASS does not override the aggregate required-gate FAIL. Protected maintainer approval and PR Agent advisory are also FAIL.

The predecessor `24816ebc...` positive technical evidence remains historical and exact-head bound; it is not inherited by `11c0ac67...`. Therefore #152 remains **UNACCEPTED** and none of its branch PASSes establish current-main or paper-facing qualification.

`implementation-status.yaml` remains an implementation-presence manifest, not a qualification manifest.

## Governance and research independence

Merged #168 establishes repository merge control as:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

This is **maintainer-reviewed with automated qualification**, not independent human assurance. A paper-facing security, release, or scientific claim may still require evidence independent of the implementer/maintainer.

The #336/#337 sequence reinforces this boundary: a bot failure/status comment is not substantive advisory evidence. #337's repair remains unaccepted until its own required gates are satisfied, and #336 remains held behind it.

Issue #305's historical queue saturation remains evidence. #307 is accepted as the structural fan-out repair. The current queued-run snapshot is **0**; transient queue state does not erase first-attempt evidence or authorize skipped qualification.

## Proposed contribution

The original contribution was framed as **counterexample-directed residual delegation with evidence negotiation**: compile a checked workflow's unresolved frontier into a bounded, independently verifiable request while preserving accepted independent work and carrying content-bound receipts across model boundaries.

The broader hypothesis is:

> stochastic workers may remain individually unreliable if the surrounding system constrains their authority, observes execution, preserves evidence, independently checks candidate work and deterministically controls accepted state.

The novelty claim is intentionally bounded. Routing, checkers, DAGs, caching, retrieval, sandboxing, model mixtures, and counterexample-guided synthesis all have substantial prior art. The empirical research question is whether this composition produces measurably better **accepted-state reliability** under fixed component capability.

This repository does not establish a first-in-literature result.

## Confirmatory gate

Before paper-facing outcome collection, freeze exact source, execution/evidence path, workload/task mapping, model/version, inference settings, verifier policies, prompts, metrics, and analysis code **before** observing confirmatory results.

At minimum:

1. preserve exact-revision failures, blocked interventions, and mixed results rather than treating later PASSes as erasure;
2. requalify any selected path affected by historical #207/#208/#212 authority-ordering failures against accepted #288;
3. rebase/requalify #323 before using the Workbench for an authoritative trial;
4. resolve or explicitly exclude #120/#126 for any WebVM-dependent protocol;
5. retain fresh exact-revision live-provider evidence if the protocol depends on that provider path;
6. preserve any protected ownership/requalification sequence required by the selected evidence path;
7. independently qualify the selected evidence path to the degree required by the paper claim;
8. keep `PASS`, `FAIL`, `UNKNOWN`, `BLOCKED`, missing, and rejected cells in the retained evidence package.

Until those gates are met, the central systems hypothesis remains **UNKNOWN / not established by confirmatory live-model evaluation**.
