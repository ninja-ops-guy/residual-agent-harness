# AX-21 research check-in — 2026-10-07

**Status:** append-only research record / review only. **Authority effect:** none. No deployment, merge, native enrollment, canary, security certification, release, or autonomous-operation authority is granted by this note.

## Inspection boundary and provenance

Inspected accepted `main@8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`; draft PRs [#533](https://github.com/ninja-ops-guy/residual-agent-harness/pull/533), [#534](https://github.com/ninja-ops-guy/residual-agent-harness/pull/534), [#535](https://github.com/ninja-ops-guy/residual-agent-harness/pull/535), new [#536](https://github.com/ninja-ops-guy/residual-agent-harness/pull/536) and [#537](https://github.com/ninja-ops-guy/residual-agent-harness/pull/537); the #536/#537 GitHub Actions job outcomes and aggregate logs; and #537's checked-in runner/mesh audit and TARGET_COMPOSITION record. This pass did not independently execute swarm agents, native OpenClaw on physical hosts, or a release candidate. Author-local test reports are not elevated to independent reproduction. Earlier AX-21 negatives (including #533 stale-producer selection) remain retained.

## Material observation 1 — partial-run qualification must bind producer *job results* as well as artifact bytes

**Preceding control:** #533 HEAD `5de913ab40d685ff15cb4e9e7229cfe9a43810bd` fixed self-ingestion of retained final aggregate artifacts, but its controlled attempts 2/3 still selected stale attempt-1 soak evidence even after a newer producer upload. A prepared selector alone would not detect a failed/cancelled producer that never uploaded a newer artifact.

**New candidate:** #536 HEAD `3747a794e176c06d776fe278c798ec448c0fb83e`, TREE `54c89d9f6ae4c68865dbec90cc81d7eefd2088a4`, draft on accepted main. The PR introduces a full direct-result map of 17 producer job keys (19 producer identities after matrix expansion) and requires all direct results to be successful before selecting source/attempt-bound producer artifacts. It retains selection/rejection records and attempt-qualified artifact directories. Author-run **19 local unittest cases PASS** cover normal reuse and negative cases (failure, cancellation, skipped/unknown status, missing/extra keys, source/attempt mismatch, ambiguity). This is local apparatus testing, not hosted success proof.

**Fresh hosted negative:** [Qualification-v1 run 37664951697](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/37664951697) on the current PR head completed with the overall run marked CANCELLED. The job listing shows **17 producer jobs succeeded; deterministic and browser(WebKit) jobs were CANCELLED**. The aggregate job **FAILED**. Its log passed the exact direct-result map to the selector and recorded:
`unsuccessful qualification producers: {'deterministic': 'cancelled', 'browser': 'cancelled'}`.
The selector returned a nonzero exit and uploaded a small rejection artifact `11503898776`; there is no passing aggregate from that run.

**What this establishes:** a real incomplete hosted producer matrix was not promoted to a passing aggregate under #536's gate. This is bounded fail-closed apparatus evidence for those two observed cancellations. It does **not** prove the positive partial-rerun path, controlled cancel-before-upload / fail-before-upload injection, or complete initial exact-head qualification. The reason the two hosted jobs were cancelled was not established; do not classify them as product-runtime failures or as deliberate fault injections. The PR records that the connector does not expose the needed workflow-dispatch/cancellation interface, so those proposed controlled probes remain NOT RUN.

**Falsified inference carried forward:** selecting the newest *available* artifact is sufficient to establish freshness. If the newest producer failed before upload, the retained older PASS can still look available unless the direct producer result is part of the admission oracle.

## Material observation 2 — separate runner/mesh lineage can be absent without establishing mesh-free deployment

**New review artifact:** #537 HEAD `941f203f14284208a40017aa85d169e1b803c216`, stacked on review-only #534, audits exact #527 source HEAD `f9c1a82b381420d4337391f0803983fb178cd197` / TREE `94f84922d9348b1422e549083a18ae428d12b0b2`. Its [TARGET_COMPOSITION](https://github.com/ninja-ops-guy/residual-agent-harness/blob/941f203f14284208a40017aa85d169e1b803c216/docs/v1/TARGET_COMPOSITION.md) calls the bounded composition `NO_SEPARATE_RUNNER_MESH_BYTES_REQUIRED`: #400/#404/#493 are non-ancestors, and the identified SC-MESH/SC-E Station modules/services are absent from the audited source/package paths. The checked-in [audit.json](https://github.com/ninja-ops-guy/residual-agent-harness/blob/941f203f14284208a40017aa85d169e1b803c216/docs/v1/evidence/runner-mesh-20261007/audit.json) binds specific lineage identities, manifest hashes and wheel members.

**Important negative/contradiction retained:** the audit expressly finds `residual/mesh/__init__.py` and `residual/mesh/node.py` still included in the wheel, byte-identical to accepted main. These are earlier federated-mesh prototype files, not the historical Station SC-MESH implementation. Accordingly, `NO_SEPARATE_RUNNER_MESH_BYTES_REQUIRED` is a scoped dependency judgement for an exact composed package, **not** a claim that all mesh-named code is absent, that a final artifact has an enforced negative scope guard, or that no deployed host uses external mesh/plugin components.

**Author-local bounded measurements:** 21 Python source tests plus 8 subtests PASS; 185 OpenClaw control tests PASS; a poisoned-cwd isolated wheel-install proof PASS with 360 source-matched installed files and 5 Station/client scenarios. The artifact inventory reports two different wheel digests from different build methods; no reproducible-build equivalence is claimed. No live DELL/DBOX/LEGION host inventory or installed native hook/cancel/restart proof was executed for this audit.

**Fresh hosted negative:** [Qualification-v1 run 37665297758](https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/37665297758) was marked CANCELLED. The browser(Firefox) producer was CANCELLED; the other 18 producer jobs succeeded. The aggregate job **FAILED** with `missing required gates: browser-firefox`. This is qualification incompleteness, not evidence of a Firefox runtime defect; its cancellation cause is UNKNOWN. Other listed substantive workflows passed, but the entire candidate is not qualification-v1 PASS and has no independent review/release authority.

**Interpretation:** a transparent negative dependency audit can close a *source-specific planning ambiguity* without implying a universal architectural exclusion. Exact source/package membership, imported runtime paths, installed artifacts, selected composition and live-host inventory are separate evidence strata. #537's READY_FOR_REVIEW ledger row does not equal MERGED_AND_REQUALIFIED.

## Baseline comparison; negative-result retention

Frozen/pre-release AX-21 control remains: approximately 11 cold agent queries plus human synthesis to reconstruct the P5 dashboard, 15+ manual reports per session reconciled into external ledgers, and an observed B0-6 local 7B path of approximately 16.4 s without verifier exception. These are retained before-condition measurements, **not** newly measured today. R2 provider continuity remained `PASS_SANDBOX_BOOTSTRAP_ONLY` even with 215 green tests; previously observed circuit, crash-window, authority, verifier-publication and producer-selection negatives are not overwritten by today's successors.

No new frozen seat-roster/failover receipt, physical F6, native MissionSync proof, Orpheus Runner R0 operational result, independent post-release no-help three-host run, or valid P5 after-condition was found in this inspection. Do not infer reduced human coordination or sustained autonomous recursive development.

## Operator actions and intervention accounting

Interventions identifiable in the retained record include writing and publishing #536 and #537, author-run local tests, manual exact-lineage/package audit and interpretation, release-readiness ledger edits, and PR/qualification review gating. A hosted cancellation is an observation; absent a causal audit, **do not invent a human cancellation intervention**. No observed autonomous first-recursive-improvement completion or intervention-free owner-absence result occurred in this pass.

## RES-UP / ImprovementSpec candidates (proposals, not implementations)

- `RES-UP-QUAL-PRODUCER-TERMINAL-RESULT-BINDING-001`: for each direct producer, retain terminal `success/failure/cancelled/skipped/unknown` and bind it to the checked-out source/run/attempt and selected artifact. Any non-success is an aggregate HOLD/FAIL even if an older PASS exists.
- `RES-UP-QUAL-PRODUCER-ATTEMPT-REUSE-001`: distinguish untouched jobs legitimately reusable from an earlier attempt from jobs explicitly rerun in the new attempt; require an admissible artifact for each, or reject.
- `RES-UP-QUALIFICATION-CANCELLATION-PROVENANCE-001`: record job cancellation cause separately from aggregate failure and candidate-test failure without making the missing evidence disappear.
- `RES-UP-RELEASE-NEGATIVE-DEPENDENCY-GUARD-001`: give excluded runner/mesh lineages a candidate/package-level negative guard and re-evaluate when composition/runtime host manifests change.
- `RES-UP-COMPOSITION-LAYER-SCOPE-001`: type `source not imported`, `wheel not packaged`, `deployed host not present`, and `release explicitly excludes` separately; do not promote a source audit into deployment policy.

Prospective tests:
- `EXP-QUAL-PRODUCER-MISSING-UPLOAD-01`: frozen success/cancel/fail-before-upload matrix with an intentionally retained older PASS; independently check selected/rejected artifact IDs, job-result provenance and final aggregate.
- `EXP-COMPOSITION-NEGATIVE-GUARD-01`: inject one excluded SC-MESH/SC-E dependency into a synthetic candidate/package manifest to test whether the negative scope guard detects it, without deploying to live hosts.

## Paper-safe conclusion

Today adds **one observed fail-closed incomplete-producer gate** and **one source/package-level negative dependency audit**, accompanied by two actual *incomplete* hosted qualification runs. A source-qualified or locally tested artifact is not whole-composition qualified, and the absence of a newly uploaded producer artifact cannot be interpreted as producer success. Conversely, absence of a separately imported runner/mesh lineage from the audited wheel cannot be generalized into a live-host exclusion or broad security/autonomy claim.

**Release status:** accepted main unchanged at inspection; `V1_RELEASE_HOLD` preserved; #536 and #537 are drafts; no current exact-head full Qualification-v1 PASS, independent release review, canary or final release designation follows. All historical failed/inconclusive observations remain retained.

## Direct evidence pointers

- #536: https://github.com/ninja-ops-guy/residual-agent-harness/pull/536
- #536 hosted run: https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/37664951697
- #537: https://github.com/ninja-ops-guy/residual-agent-harness/pull/537
- #537 hosted run: https://github.com/ninja-ops-guy/residual-agent-harness/actions/runs/37665297758
- #537 composition: https://github.com/ninja-ops-guy/residual-agent-harness/blob/941f203f14284208a40017aa85d169e1b803c216/docs/v1/TARGET_COMPOSITION.md
- #537 bounded audit: https://github.com/ninja-ops-guy/residual-agent-harness/blob/941f203f14284208a40017aa85d169e1b803c216/docs/v1/evidence/runner-mesh-20261007/audit.json
- Previous research note: https://github.com/ninja-ops-guy/residual-agent-harness/blob/docs/ax21-research-checkin-2026-10-06/docs/swarm/ax-21-research-checkin-2026-10-06.md
