# RESIDUAL current status

_Current-state check: 2026-09-24 12:32 UTC against `main@d796f36b75e730a0bab71bdba564206174393719`._

This document is a human-readable current-state summary, not a replacement for exact repository bytes, retained artifacts, workflow logs, issue/PR history, or maintainer/protected-byte governance. Historical PASS/FAIL/UNKNOWN/BLOCKED evidence remains bound to the exact revision, run attempt, and environment that produced it. Git history retains earlier detailed versions of this status document.

## Executive summary

Accepted `main` remains **`d796f36b75e730a0bab71bdba564206174393719`**, the merge of #304 (`fix(station): typed fail-closed reviewer findings (#209)`). No newer PR has merged into accepted main during this observation.

Release convergence remains **BLOCKED**. AUD-1 issue #353 remains **OPEN with no milestone**; physical F6-A/F6-B evidence remains **UNKNOWN / not established**; the independent Mason/LEGION re-audit is outstanding; the R4.1 seal-cardinality defect still prevents the erroneous seal from serving as authorization evidence; no corrected seal exists; the v1 deployment profile remains owner/operations-undecided; and no canary, release candidate, deployment, or production acceptance has been authorized.

Meaningful movement since the previous observation is concentrated in the release-readiness ledger:

- **#427** advanced from `1308115eda13af59b538fd3374a7e9f8a13f2b89` to **`9f959bc0021ec7f127978eb5cb50b020ceff05ce`** with an append-only 11:37 UTC delta recording PR-G27 action-pin audit tooling and AUD-1 C6 convergence.
- The delta correctly keeps PR-G27 itself **IN_PROGRESS**: #437's audit tooling is review-ready, but accepted-main workflows still use mutable external-action refs and final-tree immutable pin verification is not complete.
- It also records #438 as the unmerged C1-C6 AUD-1 successor lane and preserves the remaining independent-human, physical F6, Mason/LEGION, selected-head, integration, and resulting-main gates.
- Exact-head #427 repository technical CI is **PASS** for Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, and Control Plane. PR-Agent advisory is **FAIL**; its retrieved job summary shows the advisory execution failed and substantive-review verification was skipped, so no advisory PASS or human review is inferred. Vercel is **FAIL** because of the external deployment build-rate limit. Maintainer approval is **FAIL / no exact-head human attestation**.

The AUD-1 #438 exact head and its prior C6 qualification evidence are unchanged from the preceding observation; their status does not change accepted-main release authority.

## R4.1 evidence authority and canary boundary

The prior external R4.1 qualification record remains bounded to its authoritative candidate, evidence bytes, hashes, and gate results. The previously propagated ready-for-canary seal statement `44/44` is **invalid derived seal metadata** and must not be used as an authority claim.

Open PR **#415** established that the literal `44` was manually embedded after `sha256sum -c` verified hashes without deriving cardinality; authoritative immutable `SHA256SUMS` contains **50** valid non-empty entries. The defect affects derived seal metadata and semantic seal validity, not the candidate identity, authoritative evidence bytes, authoritative hashes, qualification gate results, or the manifest itself.

No corrected seal / Seal v3 exists. The current erroneous seal must not authorize canary execution. Canary execution remains **NOT AUTHORIZED / NOT EXECUTED**.

## AUD-1 security convergence

Owner issue **#353 remains OPEN with no milestone** and remains the pre-release security convergence boundary. Original candidate **#399** and physical-evidence helper **#403** remain frozen to their original bytes/evidence boundaries. The two required real-host F6 cases remain **UNKNOWN / not established**; no software fixture or hosted CI run substitutes for them.

Draft **#438** (`fix(aud1): bound worker control-plane drain`) is the current C1-C6 software-successor lane at exact head **`e815f33484352f100e11b8d075bb954a815244cc`**, stacked on #433 exact head `9b4f32ce71ba2f4520dc1d7c2d8826fa329bdf60`.

Its retained test-only predecessor **`8a2fc3eebef6821c2466a031968684f16b92861d`** preserves the first hosted C6 failure. Command Station run **35992708134** and Controller/provider run **35992708420** failed on that exact test-only head; Qualification v1 run **35992707951** also failed. The failing head was not rerun unchanged for green.

C6 is an availability defect in the C1 completion barrier: writer preference correctly blocked new admissions while credential rotation/disable waited for already-admitted worker operations, but the wait had no independent deadline. One admitted operation that never returned could therefore block the control operation indefinitely.

The repaired head preserves the completion-barrier policy while adding bounded failure:

- already-admitted worker operations are not preempted or rolled back;
- a pending control operation remains writer-preferred and blocks new admissions;
- successful rotation/disable still occurs only after admitted operations drain;
- an independent **600-second monotonic drain deadline** bounds the wait;
- deadline expiry raises `WorkerControlDrainTimeout` before the control context yields, so that control attempt has not applied credential/access mutation;
- the operator HTTP surface returns **503** instead of reporting success;
- writer-pending state is released after timeout so later admissions are not wedged.

Fresh exact-head #438 repository technical evidence is **PASS** for:

- Qualification v1 run **35993248678**;
- Command Station run **35993248773**;
- Controller/provider contracts run **35993248687**;
- clean install run **35993248554**;
- Factory ownership run **35993248841**;
- measured-evaluation binding run **35993248642**;
- Control Plane run **35993248873**;
- Pages/browser proof run **35993248775**.

The retained handoff records Qualification v1 as 25 required gates present with no missing gates, exact tree **`ee0009145f0dcc8207eceda98719db04a9af46cf`**, final qualification artifact **10805272548**, and artifact ZIP SHA-256 **`e65db86f0ab714526962f1d0417ab34a31805aa74a15ab19daaa2ad34953c4f2`**. These claims remain exact-head/candidate-scoped.

PR-Agent advisory run **35993248511** is **FAIL** and is not security evidence or human approval. The owner handoff records that the configured OpenAI account had no credits remaining and that no substantive advisory review was produced. Vercel status is **PASS**. Maintainer approval is **FAIL** because there is no exact-head write-capable human attestation; submitted human reviews remain zero at the retained handoff boundary.

#438 remains **OPEN / DRAFT / UNMERGED / UNACCEPTED**. It does not select the release successor, retarget #403, establish either physical F6 case, provide Mason/LEGION independent review, authorize merge/deployment/release, or change the frozen #399/#403 evidence boundary.

Required AUD-1 sequence remains: genuine independent human review of exact #438 C1-C6 and the completion-barrier/bounded-failure tradeoff -> deliberate successor selection -> helper reconciliation for that exact target -> separately retained F6-A and F6-B physical evidence -> Mason/LEGION independent read-only re-audit -> exact-head qualification and owner attestation -> guarded merge -> authoritative new-main qualification -> final RC recovery/elapsed-soak evidence.

## Release-readiness convergence ledger

Draft **#427** (`docs(v1): add master release-readiness convergence ledger`) is **OPEN / DRAFT / UNMERGED / UNACCEPTED** at exact head **`9f959bc0021ec7f127978eb5cb50b020ceff05ce`**.

Its latest commit, `docs(v1): record PR-G27 and AUD-1 C6 convergence`, has parent `1308115eda13af59b538fd3374a7e9f8a13f2b89` and adds only `docs/v1/V1_MASTER_READINESS_DELTA_20260924_1137.md`. The delta is review-only and authorizes no canary, merge, physical test, deployment, attestation, tag, release, provider workload, elapsed soak, credential/topology mutation, or modification of frozen R4.1/Seal v2 evidence.

The new delta records two bounded changes without broadening acceptance:

- **PR-G27:** #437 audit tooling advances to **READY_FOR_REVIEW**, while PR-G27 remains **IN_PROGRESS** because active accepted-main workflows still contain mutable external-action references, reviewed immutable commit selections have not been applied across the active workflow set, pinned-syntax/security assertions still need reconciliation, and final-candidate retained audit evidence is absent. Docker/container image digests remain separate.
- **AUD-1 C6:** #438 is recorded as the current unmerged C1-C6 successor with exact-head technical PASS evidence, while independent human review, deliberate successor selection, #403/helper reconciliation, physical F6-A/F6-B, Mason/LEGION re-audit, owner attestation, guarded integration, and authoritative resulting-main qualification all remain outstanding.

Exact-head #427 workflow evidence at `9f959bc...` is **PASS** for Qualification v1 run **35994440481**, Controller/provider contracts run **35994440459**, Command Station run **35994440524**, clean install run **35994440425**, Factory ownership run **35994440423**, measured-evaluation binding run **35994440510**, and Control Plane run **35994440496**. PR-Agent advisory run **35994440447** is **FAIL**; the retrieved job summary shows the advisory execution step failed and the substantive-review verification step was skipped. Maintainer approval run **35994440422** is **FAIL** because no exact-head write-capable human attestation exists. Vercel is **FAIL** with the explicit external status `Deployment rate limited — retry in 24 hours.`

The ledger continues to keep release ordering fail-closed: canary remains unauthorized/unexecuted; the actual v1 deployment/trust/SLO/RPO/RTO/backup/HA/soak profile remains blocked on owner/operations decisions; AUD-1 independent/physical closure remains outstanding; and exact-RC recovery/soak/provenance plus explicit human release authorization remain future gates.

## PR-G07 / PR-G21 — recovery qualification

Draft **#435** (`feat(release): validate v1 recovery evidence`) is **OPEN / DRAFT / UNMERGED / UNACCEPTED** at exact head **`378207e511550532dbba60e8d4ae489666aa6c09`**, based directly on accepted main.

It changes only:

- `docs/v1/V1_RECOVERY_QUALIFICATION.md`
- `scripts/validate_v1_recovery_evidence.py`
- `tests/test_v1_recovery_evidence.py`

The contract deliberately prevents existing HADR simulation/unit tests from being mistaken for production recovery qualification. It requires future observed evidence bound to an approved deployment profile and exact RC, including backup readability/integrity, durable-component coverage, exact restore binding, measured RPO/RTO, rollback verification, immutable evidence retention, and human Qualification Lead approval. Validator output is `VALIDATION_ONLY`.

Current exact-head #435 repository technical workflows are **PASS** for Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent. Maintainer approval is **FAIL / no exact-head human attestation**. Vercel is **FAIL** because the deployment service reports an external 24-hour build-rate limit; this is not reclassified as a RESIDUAL product-test failure.

Repository-side PR-G07/PR-G21 tooling is **READY_FOR_REVIEW**. The actual backup/restore and rollback gates remain **IN_PROGRESS**, because no separately authorized production-shaped backup, restore, or rollback exercise has executed against the approved deployment profile and exact selected RC.

## PR-G29 supporting evidence — broad-suite environment triage

Review-only **#436** (`[Review only] Document broad-suite environment triage`) is **OPEN / UNMERGED / UNACCEPTED** at exact head **`5cc1f40a048c2f99f8ec615d662e6e19a0d89468`**.

It changes only `REPRODUCTION.md`, `TEST_ENVIRONMENT_MATRIX.md`, and `TEST_FAILURE_CLASSIFICATION.json`. It records the previously reported 1121-test broad-suite result as 5 failures / 95 errors / 29 skips, classifies all 129 non-passing outcomes, and reports 87/87 affected tests passing outside the managed process sandbox. No deterministic real product regression is claimed from that triage, and the original failures remain retained evidence rather than being erased.

Current exact-head #436 repository technical workflows are **PASS** for Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent. Vercel is **PASS**. Maintainer approval is **FAIL / no exact-head human attestation**.

This supports the environment/capability classification behind #430/ENV-G01. It does not establish production readiness and does not authorize reclassifying unrelated failures as PASS.

## PR-G27 — immutable GitHub Actions dependency identity

Draft **#437** (`feat(release): add immutable GitHub Actions pin audit`) is **OPEN / DRAFT / UNMERGED / UNACCEPTED** at repaired exact head **`46bdfd51c7ea1ff31ab7e3701b894b329010ff50`**.

It changes only:

- `docs/v1/V1_SUPPLY_CHAIN_ACTION_PINNING.md`
- `scripts/validate_github_action_pins.py`
- `tests/test_github_action_pins.py`

Direct search of accepted `main@d796f36...` confirms active workflows still use mutable major-tag references including `actions/checkout@v4` and `actions/upload-artifact@v4`. This is a supply-chain identity/immutability gap; it is **not evidence that an action was compromised**.

#437's validator requires external Actions/reusable-workflow references to use 40-hex commit identities, ignores repository-local `./` actions, leaves `docker://` digest policy to a separate gate, and emits `PASS | BLOCKED` with `execution_claim: VALIDATION_ONLY`. The current repaired head also fail-closes unexpected workflow enumeration/read/report-write I/O errors; the PR intentionally does **not** bulk-rewrite active workflows.

Current exact-head #437 repository technical workflows are **PASS** for Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent. Maintainer approval is **FAIL / no exact-head human attestation**. Vercel is **FAIL** because of the same external 24-hour deployment build-rate limit, not a demonstrated RESIDUAL product-test failure.

PR-G27 therefore remains **IN_PROGRESS**. Review of the audit contract, deliberate selection/review of exact external-action commits, remediation of active workflows without weakening existing checkout/security assertions, fresh exact-head CI, and a retained final-tree audit are still required before this gate can become VERIFIED.

## Other release-preparation candidates

These remain review-only/unaccepted and do not authorize canary, RC, tag, deployment, or production acceptance:

- **#428** separates frozen R4.1 canary provenance from the eventual post-convergence RC; no RC is selected.
- **#429** proposes to align `residual.__version__` with current project metadata; final `1.0.0` normalization remains an RC-creation action.
- **#430** adds ENV-G01 capability preflight without retroactively converting restricted-environment failures into product failures or PASS.
- **#432** adds a fail-closed deployment-profile schema/validator but does not choose topology, tenancy, SLO, RPO, RTO, backup, soak, or HA policy.
- **#434** adds the PR-G30 incident-response qualification plan/validator; no incident drill has executed and PR-G30 remains **IN_PROGRESS**.

## Qualification and trust-boundary discipline

`PASS`, `FAIL`, `UNKNOWN`, and `BLOCKED` remain exact-claim states. A PASS on one revision does not transfer to changed bytes. A candidate finding does not become an accepted defect until its scope and evidence are reviewed. A documented external result does not override contradictory or missing repository-local evidence. Missing physical or operational evidence remains `UNKNOWN / not established` or `BLOCKED`, as appropriate, rather than inferred from software tests.

Still **UNKNOWN / not established** or **BLOCKED** by accepted-main hosted PASS results:

- universal/every-host M4 qualification;
- true 24h/72h/30d elapsed soak evidence;
- physical F6-A/F6-B authority-loss reliability on the selected AUD-1 successor;
- Mason/LEGION closure of AUD-1;
- a valid corrected R4.1 seal suitable for authorization review;
- live R4.1 canary success;
- accepted R4.1/R5 Shared Comms implementation on main;
- an approved v1 deployment/trust/SLO/RPO/RTO/backup/HA/soak profile;
- executed and independently retained PR-G30 incident-response drill evidence;
- executed and independently retained PR-G07/PR-G21 production-shaped recovery evidence;
- immutable reviewed external GitHub Action pins across the final release workflow tree;
- an exact post-convergence v1 release candidate with required recovery/soak/provenance evidence;
- blanket production readiness.

The accepted Factory/M4 ownership baseline and protected-byte set remain whatever the committed ownership baseline on main records. This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, evidence schemas, provider authority, security implementation, licensing authority, or acceptance authority.

`implementation-status.yaml` remains an implementation-presence manifest, not a release-qualification manifest.

## Documentation scope

This reconciliation changes only `docs/CURRENT_STATUS.md` on the existing dedicated documentation branch. Accepted main has not changed since the previous observation. No new accepted-main claim requires an edit to `README.md`, `HARNESS.md`, `START-HERE.md`, or `implementation-status.yaml`; those files are intentionally unchanged in this observation.

Because this status document records qualification anchors, corrected evidence-authority interpretation, ownership-baseline context, active security successors, retained failures/unknowns, and release/canary trust-boundary state, the documentation PR must **not** be merged automatically. Exact-head human review/attestation remains required.
