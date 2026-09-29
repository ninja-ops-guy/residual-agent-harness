# AX-21 / RESIDUAL Research Check-in — 2026-09-28

**Status:** MATERIAL UPDATE / OBSERVED / NOT FROZEN  
**Accepted main observed:** `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`  
**Comparison anchor:** candidate pre-release AX-21 baseline plus the append-only 2026-09-27 check-in.

This record preserves bounded research findings. It does not rewrite the AX-21 baseline, authorize physical experiments, select an RC, close v1, or generalize bounded tests into whole-system security/autonomy claims.

## Material findings

### A. Shared Comms mechanism corroboration and release-scope boundary

Repository review of the current #404 lineage (`7783081c858ad9ddf98b2e64e740e1104ae5d08b`) independently corroborates the mechanism classes behind retained #426 observations: first-receipt semantic binding is incomplete, recovery integrity is not independently re-established before all delivery activity, and concurrent recovery lacks a durable single-owner transition at the inspected layer.

This is source corroboration, not a fresh dynamic reproduction and not evidence of exploitability.

The same surfaces are absent from accepted `main@8369f0dc...` and QD-2 `05e01731208957e85cf72cf02a925b0660fca144`. That narrows current v1 applicability but does not itself prove enforceable release exclusion.

**Candidates:** `RES-UP-SC-RECEIPT-SEMANTIC-BINDING-001`, `RES-UP-SC-RECOVERY-INTEGRITY-001`, `RES-UP-SC-RECOVERY-FENCING-001`, `RES-UP-RELEASE-NEGATIVE-SCOPE-GUARD-001`.

### B. AUD1-C4 preserved a retry-classification first failure

#431 retains a test-only first-failure head `a980274c6a3d5b3b479a18466a7877d1207476ab` in which an explicit result-authority denial was handled by a generic retry/fallback path instead of producing immediate authority surrender. That failing head was not rerun unchanged for green.

A separate repaired successor `a9c00474606b2bd5733ae5eef00a52d59b0aa89b` classifies explicit authority loss before generic transport recovery. Fresh exact-head evidence reports Qualification-v1 PASS, a 25/25 required-gate manifest with zero skips/UNKNOWN, and PASS on the named Command Station, controller/provider, clean-install, Factory-ownership, measured-binding, Control Plane, and Pages workflows.

No independent human review, helper reconciliation, physical F6, merge, deployment, soak, or release acceptance follows from those software results.

**Falsified assumption:** generic bounded transport retry semantics are automatically safe for explicit authority-denial outcomes.

**Candidates:** `RES-UP-AUTHORITY-DENIAL-TERMINAL-CLASS-001`, `RES-UP-RETRY-SEMANTIC-CLASSIFICATION-001`, `EXP-AUD1-DENIAL-VS-TRANSPORT-01`.

### C. Exact-subject qualification non-transfer was exercised on #486

#486 is the current-main successor for previously reviewed #478 release-control hardening.

- base: `main@8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`
- head: `9a247e313015a7daeee8aba089221b54debcf395`
- one commit ahead / zero behind
- exactly seven release-control files in scope

Historical #478 results were not reused. Fresh exact-head #486 workflows report PASS for Qualification-v1, Command Station, controller/provider, clean install, Factory ownership, Control Plane, measured-evaluation binding, Vercel, and Snyk.

The maintainer gate remains red because exact-head human attestation is absent, and GitHub records zero submitted human reviews. The advisory PR-Agent run also failed at its external model-call dependency and published no substantive advisory. Treat that as an apparatus/dependency failure, not as a candidate-test failure.

**Conclusion:** prior qualification does not transfer across a new exact repository composition even when intended control semantics are carried forward.

**Candidates:** `RES-UP-EVIDENCE-NONTRANSFER-ENFORCEMENT-001`, `RES-UP-CI-FAILURE-PROVENANCE-001`.

### D. Human authority remains measurable infrastructure

#431 still requires independent technical review before deliberate successor selection and later physical qualification work. #486 still requires exact-head human review/attestation before release-control admission.

These are operator interventions and must remain visible in coordination/autonomy metrics.

### E. No new live-swarm receipt in this review window

No newer frozen live-swarm receipt was found that supersedes the 2026-09-27 Shared Comms preflight observation. Therefore this record does not invent a new fleet readiness count, Shared Comms PASS, O1 completion, Mason recovery result, REQ-LP-1 replication count, or P5 after-condition.

## Baseline comparison

The pre-release AX-21 findings remain directionally intact:

- Evidence-over-consensus is strengthened by keeping dynamic reproduction, source corroboration, and release applicability separate.
- Diagnostic quality remains an autonomy constraint: authority denial, transport failure, candidate failure, and reviewer/dependency failure need different machine states.
- Presence/telemetry/evidence remain separate from exact-subject qualification.
- Human coordination remains visible infrastructure.
- Recursive improvement is supported only in the bounded sequence failure -> preserve -> analyze -> repair successor -> requalify; sustained autonomous recursive development is not established.

## P5 control condition

#349 remains open/draft at `625e1ce97919098dbe9d586ffcaf4b2a94257184`, unchanged since 2026-09-20. No valid post-intervention replay exists.

Frozen before-condition remains:
- Station answers directly: No
- approximately 11 cold agent queries
- human synthesis required
- external coordination state required
- 15+ reports/session synthesized

No operator-friction improvement is claimed.

## Negative results preserved

- #431 retained authority-denial retry/fallback failure.
- #426 findings remain distinct from later source corroboration.
- #486 exact-head human attestation is absent.
- #486 advisory reviewer dependency failed and produced no substantive advisory.
- no physical F6 result was found this cycle.
- no new live-swarm receipt was found this cycle.
- no formal GitHub release exists.

## Paper-safe conclusions

Supported:
- authority-denial semantics must be separated from ordinary transport recovery;
- server-side denial and client-side surrender are distinct control properties;
- source analysis can corroborate mechanism without replacing reproduction;
- source absence narrows applicability but does not equal release exclusion;
- qualification should remain bound to exact subject identity/composition;
- candidate failures and evaluation/reviewer dependency failures should be typed separately;
- human review/release authority remain measurable parts of the current system;
- first-failure retention plus separately qualified repair successors improves longitudinal interpretability.

Not supported:
- general RESIDUAL security;
- exploitability of the inspected Shared Comms findings;
- Shared Comms production qualification;
- physical F6 success;
- P5 improvement;
- fleet-wide autonomous recovery;
- sustained autonomous recursive development;
- RC selection or v1 release closure.

## Next evidence

1. Run a bounded authority-denial vs transport-failure classification experiment and retain attempt count, authority state, fallback state, and accepted-mutation outcome.
2. Resolve Shared Comms v1 scope explicitly: either qualify the relevant repaired controls on the exact admitted source or prove enforced exclusion on the exact selected RC/artifact.
3. Obtain independent review of the #431 successor before helper reconciliation.
4. Keep #486 technical qualification separate from future human review and later RC evidence.
5. Record reviewer/provider failures as apparatus/dependency outcomes rather than candidate failures.
6. Do not update P5 until the identical frozen question is replayed after a genuinely integrated intervention.
7. Preserve the next live swarm run as a seat-keyed, evidence-classed observation with operator actions and final disposition.

**Disposition: MATERIAL UPDATE — PRESERVE.**
