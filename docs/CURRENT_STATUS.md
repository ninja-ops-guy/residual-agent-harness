# RESIDUAL current status

_Current-state check: 2026-09-24 16:09 UTC against `main@d796f36b75e730a0bab71bdba564206174393719`._

This document is a human-readable current-state summary, not a replacement for exact repository bytes, retained artifacts, workflow logs, issue/PR history, or maintainer/protected-byte governance. Historical PASS/FAIL/UNKNOWN/BLOCKED evidence remains bound to the exact revision, run attempt, and environment that produced it. Git history retains earlier detailed versions of this status document.

## Executive summary

Accepted `main` remains **`d796f36b75e730a0bab71bdba564206174393719`**, the merge of #304 (`fix(station): typed fail-closed reviewer findings (#209)`). No newer PR has merged into accepted main during this observation.

Release convergence remains **BLOCKED**. AUD-1 issue #353 remains **OPEN with no milestone**; physical F6-A/F6-B evidence remains **UNKNOWN / not established**; the independent Mason/LEGION re-audit is outstanding; the R4.1 seal-cardinality defect still prevents the erroneous seal from serving as authorization evidence; no corrected seal exists; the v1 deployment profile remains owner/operations-undecided; and no canary, release candidate, deployment, or production acceptance has been authorized.

Meaningful movement since the previous observation is concentrated in PR-G26 direct-source verification preparation and the master readiness ledger:

- New **#443** is **OPEN / READY FOR REVIEW / UNMERGED / UNACCEPTED** at exact head **`d4af45bd07abf96d60c834c060395e5619731583`**, based directly on accepted main. It integrates the repository-side seal-manifest/cardinality verifier and adversarial evidence-authority tests without modifying the frozen R4.1 candidate or authoritative evidence.
- Exact-head #443 technical CI is **PASS** for Qualification v1 (`36021594859`), Controller/provider contracts (`36021595165`), Command Station (`36021596338`), clean install (`36021595076`), Factory ownership (`36021594991`), measured-evaluation binding (`36021595110`), and Control Plane (`36021594837`). PR-Agent advisory is **FAIL / unavailable as substantive review**; maintainer approval is **FAIL / no exact-head human attestation**; Vercel is externally deployment-rate-limited.
- #443 advances only the repository-side direct-manifest/cardinality sub-requirement to **READY_FOR_REVIEW**. Full **PR-G26 remains BLOCKED / NOT VERIFIED** pending semantic source binding and independently retained read-only verification of the final authoritative package and Seal v2.
- **#427** advanced from `485e9d797dbef0f9120f014f06fcd3d6fb905fda` to **`ace6968d156fa174639db6a738e9caee0a08cbf4`**, three commits ahead, adding append-only #443/PR-G26 deltas. Its final delta keeps PR-G26 **BLOCKED / NOT VERIFIED** while recording #443 repository tooling as **READY_FOR_REVIEW**.
- Exact-head #427 technical CI is **PASS** for Qualification v1 (`36022546083`), Controller/provider contracts (`36022545976`), Command Station (`36022546174`), clean install (`36022545908`), Factory ownership (`36022546157`), measured-evaluation binding (`36022545966`), and Control Plane (`36022546011`). PR-Agent advisory is **FAIL** and maintainer approval is **FAIL / no exact-head human attestation**.

Accepted `main` remains unchanged. None of this closes #353, creates a corrected R4.1 seal, authorizes canary execution, or establishes production acceptance.
## R4.1 evidence authority and canary boundary

The prior external R4.1 qualification record remains bounded to its authoritative candidate, evidence bytes, hashes, and gate results. The previously propagated ready-for-canary seal statement `44/44` is **invalid derived seal metadata** and must not be used as an authority claim.

Open PR **#415** established that the literal `44` was manually embedded after `sha256sum -c` verified hashes without deriving cardinality; authoritative immutable `SHA256SUMS` contains **50** valid non-empty entries. The defect affects derived seal metadata and semantic seal validity, not the candidate identity, authoritative evidence bytes, authoritative hashes, qualification gate results, or the manifest itself.

No corrected seal / Seal v3 exists. The current erroneous seal must not authorize canary execution. Canary execution remains **NOT AUTHORIZED / NOT EXECUTED**.


## PR-G26 — direct-source seal verification

**#443** is **OPEN / READY FOR REVIEW / UNMERGED / UNACCEPTED** at exact head **`d4af45bd07abf96d60c834c060395e5619731583`**. The proposed verifier directly parses and hashes the authoritative manifest, derives cardinality from that manifest, rejects unsafe or duplicate entries, and rejects stale/mismatched seal cardinality.

The parent PR-G26 gate remains **BLOCKED / NOT VERIFIED**. The repository CI does not establish closed-world package semantics, candidate HEAD/tree and gate/status/safety-counter binding, provenance termination, or independently retained verification of the final Seal v2 against its authoritative source package. Those remain required before the seal can participate in canary authorization.

No corrected seal is created by #443, and no canary authority follows from its PASS workflows.

## AUD-1 security convergence

Owner issue **#353 remains OPEN with no milestone** and remains the pre-release security convergence boundary. Original candidate **#399** and physical-evidence helper **#403** remain frozen to their original bytes/evidence boundaries. The two required real-host F6 cases remain **UNKNOWN / not established**; no software fixture or hosted CI run substitutes for them.

**#438** (`fix(aud1): bound worker control-plane drain`) is **OPEN / READY FOR REVIEW / UNMERGED / UNACCEPTED** at exact head **`e815f33484352f100e11b8d075bb954a815244cc`**, stacked on #433 exact head `9b4f32ce71ba2f4520dc1d7c2d8826fa329bdf60`. Its code head is unchanged; only the PR review posture advanced from draft to ready-for-review.

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

PR-Agent advisory run **35993248511** is **FAIL** and is not security evidence or human approval. The owner handoff records that the configured OpenAI account had no credits remaining and that no substantive advisory review was produced. Vercel status is **PASS**. Maintainer approval is **FAIL** because there is no exact-head write-capable human attestation. The 15:33 UTC gate-order clarification re-verified **0 submitted human reviews**; the current maintainer-gate failure is therefore expected and must not be mistaken for a code defect or an approval.

#438 remains **OPEN / READY FOR REVIEW / UNMERGED / UNACCEPTED**. It does not select the release successor, retarget #403, establish either physical F6 case, provide Mason/LEGION independent review, authorize merge/deployment/release, or change the frozen #399/#403 evidence boundary.

Required AUD-1 sequence remains: genuine independent human review of exact #438 C1-C6 and the completion-barrier/bounded-failure tradeoff -> deliberate successor selection -> helper reconciliation for that exact target -> separately retained F6-A and F6-B physical evidence -> Mason/LEGION independent read-only re-audit -> exact-head qualification and owner attestation -> guarded merge -> authoritative new-main qualification -> final RC recovery/elapsed-soak evidence.

## Release-readiness convergence ledger

Draft **#427** (`docs(v1): add master release-readiness convergence ledger`) is **OPEN / DRAFT / UNMERGED / UNACCEPTED** at exact head **`ace6968d156fa174639db6a738e9caee0a08cbf4`**.

Compared with the preceding observed head `485e9d797dbef0f9120f014f06fcd3d6fb905fda`, the branch is three commits ahead and adds append-only PR-G26 deltas for the initial #443 integration state, its review-ready transition, and the 15:45 UTC evidence correction/refinement. The current ledger advances only #443 repository tooling to **READY_FOR_REVIEW**; full PR-G26 remains **BLOCKED / NOT VERIFIED**.

The current normalized PR-G27 record still binds the immutable-action remediation to exact #440 head **`72fd1b5eeef6204db52cafc43ff1f6b48bbde5ce`**, dedicated pin-gate run **36002441103**, artifact **10809311094**, and digest `sha256:aae9486453c8747b58b488ebc1860d03b7419a708158015bd0d6e6f58b3cf612`. It classifies the focused immutable-action remediation as **READY_FOR_REVIEW / UNMERGED**, while keeping the parent PR-G27 production gate incomplete.

Exact-head #427 workflow evidence at `ace6968...` is **PASS** for Qualification v1 run **36022546083**, Controller/provider contracts run **36022545976**, Command Station run **36022546174**, clean install run **36022545908**, Factory ownership run **36022546157**, measured-evaluation binding run **36022545966**, and Control Plane run **36022546011**. PR-Agent advisory run **36022546103** is **FAIL**. Maintainer approval run **36022546046** is **FAIL** because no exact-head write-capable human attestation exists.

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

## PR-G29 / ENV-G01 — capability preflight

Draft **#430** (`feat(qualification): add ENV-G01 capability preflight`) is **OPEN / DRAFT / UNMERGED / UNACCEPTED** at exact head **`2dd7f5c04b3fff51ecb2646443d6f5120b12043b`**, based directly on accepted main.

The candidate adds a machine-readable fail-closed preflight for broad-suite runner capabilities. Relative to prior exact head `756e540ca64fa953ca389e2d3441f9229d7969de`, the successor contains the cleanup-time exception repair identified by advisory review: `OSError` from process kill/wait cleanup is contained so a cleanup failure cannot replace the intended fail-closed result, and focused regression coverage injects those failure paths. This is a tooling correction; it does not prove that every broad-suite failure was environmental.

Exact-head repository technical workflows are **PASS** for Qualification v1 run **36013067379**, Controller/provider contracts run **36013067276**, Command Station run **36013067586**, clean install run **36013067364**, Factory ownership run **36013067362**, measured-evaluation binding run **36013067520**, and Control Plane run **36013067544**.

PR-Agent advisory is **FAIL**. The retained readiness delta binds run **36013067603** to external OpenAI credit exhaustion for both configured advisory models and no substantive published review; a later same-head run **36013968097** also failed during the advisory-review step and did not publish a substantive review. These failures are retained as unavailable advisory evidence, not converted to product PASS and not treated as independent human review. Maintainer approval remains **FAIL / no exact-head human attestation**. Vercel is **FAIL** with the explicit external status `Deployment rate limited — retry in 24 hours.`

The exact-head repository contract checks are now green, but **PR-G29 remains IN_PROGRESS**. The ENV-G01 proposal has not been merged or integrated into accepted-main Qualification-v1/broad-suite execution, no resulting-main qualification exists, and no independent human acceptance is implied.

## PR-G27 — immutable GitHub Actions dependency identity

Draft audit **#437** (`feat(release): add immutable GitHub Actions pin audit`) remains **OPEN / DRAFT / UNMERGED / UNACCEPTED** at repaired exact head **`46bdfd51c7ea1ff31ab7e3701b894b329010ff50`**. It established the fail-closed audit contract without bulk-rewriting active workflows.

Successor **#440** (`fix(release): pin GitHub Actions dependencies`) is **OPEN / UNMERGED / UNACCEPTED** at exact head **`72fd1b5eeef6204db52cafc43ff1f6b48bbde5ce`**. It applies the reviewed immutable commit identities across the candidate workflow tree, records the selected pin set, preserves checkout credential-hardening assertions, requires an immutable `deploy-pages` ref, and adds the dedicated fully pinned acceptance workflow.

The dedicated `GitHub Action Pin Gate` is **PASS** on run **36002441103**. Retained artifact **10809311094** is bound to the exact head with digest `sha256:aae9486453c8747b58b488ebc1860d03b7419a708158015bd0d6e6f58b3cf612`. Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and Pages are also **PASS** on the same exact head.

The branch preserved an earlier dedicated-gate failure that found a remaining mutable `actions/attest-build-provenance@v2` reference, then resolved the repository's existing v2 choice to immutable commit `e8998f949152b193b063cb0ec769d69d929409be` without weakening the audit rule. Retained WebVM discriminator/diagnostic failures remain separate and are not converted to PASS.

PR-Agent advisory remains **FAIL** and is not independent review evidence. Maintainer approval is **FAIL / no exact-head human attestation**. Vercel is **FAIL** because of the external deployment rate limit.

The focused immutable-action remediation is therefore **READY_FOR_REVIEW**, not production-verified. Parent PR-G27 remains **IN_PROGRESS** pending independent review, broader SBOM/signature/provenance/dependency-and-artifact tamper verification, guarded merge, and authoritative resulting-main requalification. Accepted `main` still contains the pre-remediation workflow bytes until an authorized merge occurs.

## Open Core funding / governance candidates

Draft **#441** (`fix: harden funding open-core exports without expanding license scope`) is stacked on the earlier open-core proposal and remains **UNMERGED / UNACCEPTED**. It hardens export source selection to one immutable Git commit, rejects unsafe/noncanonical paths and symlinks/submodules, and produces a reproducible archive receipt. It explicitly does not change either licensing manifest, the license text, protected Factory bytes, runtime implementation, or accepted `main`.

Draft **#442** (`governance: candidate minimal RESIDUAL Open Core boundary`) is **OPEN / DRAFT / UNMERGED / UNACCEPTED** at exact head **`f7281bcf37ae1f7b2da4bd27b0bc91238659079e`**. It still proposes the same narrower Apache-2.0 candidate scope centered on provider abstraction, observation, verifier tooling, and a dependency-closed verification/evidence kernel while keeping Factory, runtime orchestration, sandbox execution, lifecycle/product integration, Studio, control-plane/cluster, licensing, and enterprise implementation reserved.

Since prior observed head `c12817e82d065861735e132f16fd0e887d349ff7`, #442 is ten commits ahead. The current head is the reconciliation commit **`Merge current main into minimal open-core funding candidate`**, explicitly binding the candidate to accepted `main@d796f36b...` without changing the proposed licensing boundary. The compare against the prior observed head adds accepted-main reviewer-contract and workbench-durability changes plus their focused tests; those inherited runtime bytes are not evidence that their reserved/open-core classification changed.

At exact #442 head, Open Core Boundary run **36020814834**, Qualification v1 **36020814851**, Controller/provider contracts **36020814661**, Command Station **36020814660**, clean install **36020814325**, Factory ownership **36020814750**, measured-evaluation binding **36020814329**, and Control Plane **36020814406** are **PASS**. PR-Agent advisory **36020814280** is **FAIL**. Maintainer approval is **FAIL / no exact-head human attestation**. Vercel is **PASS**.

These results establish only candidate technical consistency on the reconciled exact head. They do **not** establish legal review, ownership/provenance clearance, maintainer acceptance, a license grant on accepted `main`, grant eligibility, funding acceptance, or release authority.

## Other release-preparation candidates

These remain review-only/unaccepted and do not authorize canary, RC, tag, deployment, or production acceptance:

- **#428** separates frozen R4.1 canary provenance from the eventual post-convergence RC; no RC is selected.
- **#429** proposes to align `residual.__version__` with current project metadata; final `1.0.0` normalization remains an RC-creation action.
- **#430** adds ENV-G01 capability preflight; its exact-head repository contract checks are green, but it is still unmerged and does not retroactively convert restricted-environment failures into product failures or PASS.
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
