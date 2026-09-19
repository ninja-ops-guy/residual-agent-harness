# Research claim and prior art

Date: 2026-09-19. Status: implemented research platform; central systems hypothesis not yet established by confirmatory live-model evaluation.

> **Current platform state:** [CURRENT_STATUS.md](CURRENT_STATUS.md)

## Working paper

The broader systems hypothesis is developed in:

**[Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems](papers/reliability-from-unreliable-computation.md)**

The research question is whether system-level AI reliability can improve without making each component model individually reliable when worker authority is constrained, execution is observable, evidence is retained, outputs are independently checked, and accepted state transitions remain under deterministic host control.

The key empirical distinction is between raw worker correctness `P(X)` and accepted-system correctness `P(X|A)`. A positive result requires more than rejection: accepted correctness must improve while acceptance coverage remains useful, and the improvement must be evaluated against orchestration cost, latency, and throughput.

## Current accepted engineering boundary

Current `main` is **`2f9dda3882f39c28a1c766859b1bf9579eea7911`**, produced by merged #338 after merged #336/#337 on 2026-09-19.

#337 repairs PR-Agent advisory publication/concurrency governance. #336 adds a guest-filesystem durability boundary before reusable Mission Control/WebVM completion. #338 adds a bounded contention-only `RuntimeJournal` constructor-admission retry and advances the protected Factory ownership pin for the reviewed runtime-journal blob. These are engineering/governance changes, not scientific results, and none broadens the central research claim.

The exact #338 PR head had a maintainer attestation, but its PR-Agent advisory was **FAIL / unavailable** because the configured review models returned `credit_balance_exhausted`; no substantive advisory was published. That absence is retained as an evidence gap rather than treated as PASS.

Accepted #276 requires a first non-cancelling production Pages attempt for every new `main` SHA. Exact-current-main run **`35452581203`**, attempt 1, completed **PASS**. Generated desktop+narrow proof, deployment, published desktop exact-revision/real-guest execution, and the published narrow-Chromium verification all passed without rerun.

Retained live-proof artifact: `webvm-live-proof-35452581203-1`, SHA-256 `eed4f0722e43af9362eb62bad122de3521e6f391d92b6388b582c92ef1bff63f`. This is a scoped production publication/browser/real-guest result, not model-quality evidence and not evidence for the central systems hypothesis.

Historical release failures remain evidence. In particular, predecessor `d89c5d94...` run `35449637725` attempt 1 remains **FAIL** at the narrow retained-evidence path with lower-level cause **UNKNOWN**; the new exact-main PASS does not establish a long-run recurrence rate or erase #120/#126/#335 reliability concerns.

Open #340 contains implementation-only Moonshot/Kimi and Kimi Claw/OpenClaw adapters. Draft #341 contains the separated `EXP-NESTED-SWARM-001` governed evaluation and is explicitly research-only. Neither changes accepted research or provider claims.

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

Key retained cells remain mixed:

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

#319 retains the first frozen M6-MESH-001 crossover pilot. Both sequential and two-call concurrent conditions passed their six obligation checks. Retained mean wall time is about **2.1899 s sequential** versus **1.8300 s concurrent** across three repeats on one local Ollama host.

This is **positive bounded pilot evidence**, not a general mesh-efficiency result. Three repeats on one host with warm-up/order sensitivity are insufficient for a durable performance claim. General distributed mesh/swarm efficiency remains **UNKNOWN / not established**.

## Research Workbench and nested-runtime candidates

Open **#323** proposes a built-in Research Workbench. Its first planned authoritative pilot remains **BLOCKED** until the branch is rebased and requalified on a main containing the accepted #288 authority repair.

Draft **#341 / EXP-NESTED-SWARM-001** is a governed nested-runtime research track split from provider implementation #340. It may define apparatus, contracts, or preregistration, but its draft status is not a scientific result. General nested-swarm benefit, recursive improvement, and provider-independent gains remain **UNKNOWN / not established**.

## Security and deployment evidence are not research results

Merged #320, #328, #330, #337, #336 and #338 improve accepted engineering/security/governance behavior in their reviewed scope, but they do not establish the systems hypothesis.

Production Vercel header enforcement remains **UNKNOWN / pending**. Exact-current-main production Pages is a scoped **PASS** on run `35452581203` attempt 1. Neither result is a model-quality or research-hypothesis measurement.

#338's exact-head PR-Agent advisory failure remains a separate governance evidence gap. A merged protected change plus a green production Pages run is not independent scientific or security review.

## WebVM / provider research boundary

Historical retained real-account iPhone/WebKit + Puter mission `m-b98fe1b9beb440cdb1b8dfe855ad5778` reached `openai/gpt-5.4-nano` twice. Both counted calls failed closed as `provider_protocol_invalid`; no candidate crossed the protocol boundary, so candidate correctness and semantic verification remain **UNKNOWN**.

Accepted provider/session/bootstrap/publication repairs do not substitute for fresh real-account semantic evidence. The #186 iOS/WebKit fallback remains accepted, but it is not physical heavyweight-WebVM reliability evidence. Issues #120/#126/#335 remain relevant because bounded mitigations and individual green revisions do not establish long-run recurrence rate or root cause.

## Factory / protected evidence boundary

M2/M3/M4 are implemented. M4 remains environment- and exact-revision-bound rather than universally qualified.

Merged #338 changed protected RuntimeJournal bytes and the Factory ownership pin in a reviewed protected sequence. Current-main Factory ownership CI passes, but that is scoped to the pinned protected bytes and does not create every-host or universal M4 qualification.

Qualification-v1 remains branch evidence only. Open #152 remains at exact testing head **`aeba9962918c3659693e1efcd5603275cfb77cb4`**. Exact-head run **`35448856959` attempt 1 is FAIL**. Real bubblewrap provisioning, selftests, toxic-provider, M4 and the visible sibling jobs passed; the required deterministic job still failed at `Full deterministic regression gate`, causing the aggregate to fail closed. The retained summary does not establish the lower-level deterministic-regression cause, so that cause remains **UNKNOWN**.

#152 remains unaccepted, and because current main has advanced through protected #338, it must reconcile and requalify before any merge-readiness claim. Predecessor positive and negative runs remain historical exact-head evidence only. `implementation-status.yaml` remains an implementation-presence manifest, not a qualification manifest.

## Governance and research independence

Merged #168 establishes repository merge control as:

`implementation → automated qualification/review → exact-head maintainer attestation → merge`

This is **maintainer-reviewed with automated qualification**, not independent human assurance. A paper-facing security, release, or scientific claim may still require evidence independent of the implementer/maintainer. Where an automated advisory is unavailable or fails, as on the #338 merge head, that absence must remain visible.

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
4. treat #341 as draft apparatus until a frozen governed experiment actually runs and retains interpretable evidence;
5. resolve or explicitly exclude #120/#126/#335 for any WebVM-dependent protocol;
6. retain fresh exact-revision live-provider evidence if the protocol depends on that provider path;
7. preserve any protected ownership/requalification sequence required by the selected evidence path, including #338 where relevant;
8. independently qualify the selected evidence path to the degree required by the paper claim;
9. keep `PASS`, `FAIL`, `UNKNOWN`, `BLOCKED`, missing, and rejected cells in the retained evidence package.

Until those gates are met, the central systems hypothesis remains **UNKNOWN / not established by confirmatory live-model evaluation**.
