# RESIDUAL current status

_Current-state check: 2026-09-24 14:23 UTC against `main@d796f36b75e730a0bab71bdba564206174393719`._

This document is a human-readable current-state summary, not a replacement for exact repository bytes, retained artifacts, workflow logs, issue/PR history, or maintainer/protected-byte governance. Historical PASS/FAIL/UNKNOWN/BLOCKED evidence remains bound to the exact revision, run attempt, and environment that produced it. Git history retains earlier detailed versions of this status document.

## Executive summary

Accepted `main` remains **`d796f36b75e730a0bab71bdba564206174393719`**, the merge of #304 (`fix(station): typed fail-closed reviewer findings (#209)`). No newer PR has merged into accepted main during this observation.

Release convergence remains **BLOCKED**. AUD-1 issue #353 remains **OPEN with no milestone**; physical F6-A/F6-B evidence remains **UNKNOWN / not established**; the independent Mason/LEGION re-audit is outstanding; the R4.1 seal-cardinality defect still prevents the erroneous seal from serving as authorization evidence; no corrected seal exists; the v1 deployment profile remains owner/operations-undecided; and no canary, release candidate, deployment, or production acceptance has been authorized.

Meaningful movement since the previous observation is concentrated in PR-G27 release supply-chain work and its master ledger:

- **#427** advanced from `9f959bc0021ec7f127978eb5cb50b020ceff05ce` to **`70f9140d2528ec7583a6a5131815c33279c72488`**, four commits ahead, adding append-only PR-G27 deltas plus a normalized exact-head evidence record.
- **#440** is now the concrete immutable-GitHub-Actions remediation candidate at exact head **`72fd1b5eeef6204db52cafc43ff1f6b48bbde5ce`**. The dedicated `GitHub Action Pin Gate` is **PASS** on run **36002441103** and retained artifact **10809311094** is bound to that head with digest `sha256:aae9486453c8747b58b488ebc1860d03b7419a708158015bd0d6e6f58b3cf612`.
- On the same #440 head, Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, Pages, and the dedicated pin gate are **PASS**. The retained WebVM discriminator/diagnostic workflows remain **FAIL** as a separate runtime investigation; they are not reclassified as PR-G27 failures or erased. PR-Agent advisory is **FAIL**, maintainer approval is **FAIL / no exact-head human attestation**, and Vercel is **FAIL** because of the external deployment rate limit.
- #440 therefore advances only the immutable-action sub-requirement to **READY_FOR_REVIEW**. Parent gate PR-G27 remains **IN_PROGRESS** because independent review, guarded integration, resulting-main requalification, and broader SBOM/provenance/tamper-verification work remain incomplete.
- Exact-head #427 repository technical CI at `70f9140...` is **PASS** for Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, and Control Plane. PR-Agent advisory is **FAIL**; maintainer approval is **FAIL / no exact-head human attestation**; Vercel is **PASS**.

A separate governance/funding lane also moved: draft #441 hardens Open Core export source selection without changing accepted licensing authority, and draft #442 proposes a smaller dependency-closed Open Core boundary. #442's `Open Core Boundary` workflow and the observed repository technical workflows are **PASS** at exact head `c12817e82d065861735e132f16fd0e887d349ff7`; maintainer approval is **FAIL**, PR-Agent advisory is **FAIL**, and Vercel is externally rate-limited. Neither PR changes `main`, establishes legal approval, or authorizes a license-boundary change.

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

Draft **#427** (`docs(v1): add master release-readiness convergence ledger`) is **OPEN / DRAFT / UNMERGED / UNACCEPTED** at exact head **`70f9140d2528ec7583a6a5131815c33279c72488`**.

Compared with the preceding observed head `9f959bc0021ec7f127978eb5cb50b020ceff05ce`, the branch is four commits ahead and adds four documentation/evidence files for PR-G27: two timestamped readiness deltas, a PR-440 delta, and `docs/v1/evidence/PR_G27_EXACT_HEAD_72fd1b5e.md`. Earlier append-only head notes are historical snapshots; the exact-head evidence appendix and current PR metadata govern the current #440 identity.

The current normalized PR-G27 record binds the immutable-action remediation to exact #440 head **`72fd1b5eeef6204db52cafc43ff1f6b48bbde5ce`**, dedicated pin-gate run **36002441103**, artifact **10809311094**, and digest `sha256:aae9486453c8747b58b488ebc1860d03b7419a708158015bd0d6e6f58b3cf612`. It classifies the focused immutable-action remediation as **READY_FOR_REVIEW / UNMERGED**, while keeping the parent PR-G27 production gate incomplete.

Exact-head #427 workflow evidence at `70f9140...` is **PASS** for Qualification v1 run **36009550221**, Controller/provider contracts run **36009550281**, Command Station run **36009550538**, clean install run **36009550358**, Factory ownership run **36009550212**, measured-evaluation binding run **36009550190**, and Control Plane run **36009550322**. PR-Agent advisory run **36009550290** is **FAIL**. Maintainer approval is **FAIL** because no exact-head write-capable human attestation exists. Vercel is **PASS**.

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

Draft audit **#437** (`feat(release): add immutable GitHub Actions pin audit`) remains **OPEN / DRAFT / UNMERGED / UNACCEPTED** at repaired exact head **`46bdfd51c7ea1ff31ab7e3701b894b329010ff50`**. It established the fail-closed audit contract without bulk-rewriting active workflows.

Successor **#440** (`fix(release): pin GitHub Actions dependencies`) is **OPEN / UNMERGED / UNACCEPTED** at exact head **`72fd1b5eeef6204db52cafc43ff1f6b48bbde5ce`**. It applies the reviewed immutable commit identities across the candidate workflow tree, records the selected pin set, preserves checkout credential-hardening assertions, requires an immutable `deploy-pages` ref, and adds the dedicated fully pinned acceptance workflow.

The dedicated `GitHub Action Pin Gate` is **PASS** on run **36002441103**. Retained artifact **10809311094** is bound to the exact head with digest `sha256:aae9486453c8747b58b488ebc1860d03b7419a708158015bd0d6e6f58b3cf612`. Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and Pages are also **PASS** on the same exact head.

The branch preserved an earlier dedicated-gate failure that found a remaining mutable `actions/attest-build-provenance@v2` reference, then resolved the repository's existing v2 choice to immutable commit `e8998f949152b193b063cb0ec769d69d929409be` without weakening the audit rule. Retained WebVM discriminator/diagnostic failures remain separate and are not converted to PASS.

PR-Agent advisory remains **FAIL** and is not independent review evidence. Maintainer approval is **FAIL / no exact-head human attestation**. Vercel is **FAIL** because of the external deployment rate limit.

The focused immutable-action remediation is therefore **READY_FOR_REVIEW**, not production-verified. Parent PR-G27 remains **IN_PROGRESS** pending independent review, broader SBOM/signature/provenance/dependency-and-artifact tamper verification, guarded merge, and authoritative resulting-main requalification. Accepted `main` still contains the pre-remediation workflow bytes until an authorized merge occurs.

## Open Core funding / governance candidates

Draft **#441** (`fix: harden funding open-core exports without expanding license scope`) is stacked on the earlier open-core proposal and remains **UNMERGED / UNACCEPTED**. It hardens export source selection to one immutable Git commit, rejects unsafe/noncanonical paths and symlinks/submodules, and produces a reproducible archive receipt. It explicitly does not change either licensing manifest, the license text, protected Factory bytes, runtime implementation, or accepted `main`.

Draft **#442** (`governance: candidate minimal RESIDUAL Open Core boundary`) is **OPEN / DRAFT / UNMERGED / UNACCEPTED** at exact head **`c12817e82d065861735e132f16fd0e887d349ff7`**. It proposes a narrower Apache-2.0 candidate scope centered on provider abstraction, observation, verifier tooling, and a dependency-closed verification/evidence kernel while keeping Factory, runtime orchestration, sandbox execution, lifecycle/product integration, Studio, control-plane/cluster, licensing, and enterprise implementation reserved.

At exact #442 head, `Open Core Boundary`, Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, and Control Plane are **PASS**. PR-Agent advisory is **FAIL**. Maintainer approval is **FAIL / no exact-head human attestation**. Vercel is **FAIL** because of the external deployment rate limit.

These results establish only candidate technical consistency. They do **not** establish legal review, ownership/provenance clearance, maintainer acceptance, a license grant on accepted `main`, grant eligibility, funding acceptance, or release authority.

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
- immutable reviewed external GitHub Action pins on accepted integrated main plus the broader PR-G27 SBOM/provenance/tamper-verification evidence;
- an exact post-convergence v1 release candidate with required recovery/soak/provenance evidence;
- blanket production readiness.

The accepted Factory/M4 ownership baseline and protected-byte set remain whatever the committed ownership baseline on main records. This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, evidence schemas, provider authority, security implementation, licensing authority, or acceptance authority.

`implementation-status.yaml` remains an implementation-presence manifest, not a release-qualification manifest.

## Documentation scope

This reconciliation changes only `docs/CURRENT_STATUS.md` on the existing dedicated documentation branch. Accepted main has not changed since the previous observation. No new accepted-main claim requires an edit to `README.md`, `HARNESS.md`, `START-HERE.md`, or `implementation-status.yaml`; those files are intentionally unchanged in this observation.

Because this status document records qualification anchors, corrected evidence-authority interpretation, ownership-baseline context, active security successors, retained failures/unknowns, release/canary trust-boundary state, and an unaccepted licensing-boundary candidate, the documentation PR must **not** be merged automatically. Exact-head human review/attestation remains required.
