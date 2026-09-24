# RESIDUAL current status

_Current-state check: 2026-09-24 08:08 UTC against `main@d796f36b75e730a0bab71bdba564206174393719`._

This document is a human-readable current-state summary, not a replacement for exact repository bytes, retained artifacts, workflow logs, issue/PR history, or maintainer/protected-byte governance. Historical PASS/FAIL/BLOCKED evidence remains bound to the exact revision, run attempt, and environment that produced it. Git history retains earlier detailed versions of this status document.

## Executive summary

Accepted `main` remains **`d796f36b75e730a0bab71bdba564206174393719`**, the merge of **#304** (`fix(station): typed fail-closed reviewer findings (#209)`). No newer PR has merged into accepted main during this observation. The accepted reviewer contract uses typed findings (`note|warning|blocking`), rejects contradictory approval with blocking findings, requires a blocking finding for rejection, rejects legacy string-only verdicts, and records blocking-finding count. It does not weaken mechanical verification, M4, integration, or release authority.

Release convergence remains **BLOCKED**. AUD-1 issue #353 remains open with no milestone; physical F6-A/F6-B evidence is still **UNKNOWN / not established**; the independent Mason/LEGION re-audit is outstanding; the R4.1 seal-cardinality defect still prevents the erroneous seal from serving as authorization evidence; no corrected seal exists; and no canary, release candidate, deployment, or production acceptance has been authorized.

Repository-side preparation did advance. #431's repair head now has Pages PASS in addition to its previously green technical qualification; #427 advanced three commits with explicit fail-closed canary-scope and deployment-scope decision worksheets plus a readiness delta; and new draft #432 converts the unresolved v1 deployment/trust/SLO/RPO/RTO decision into a typed machine-checkable profile contract. None of those changes supplies the missing human decisions or trust-boundary evidence, so they do not change the release disposition.

## R4.1 evidence authority and canary boundary

The prior external R4.1 qualification record remains bounded to its authoritative candidate, evidence bytes, hashes, and gate results. However, the previously propagated statement that the ready-for-canary seal verified `44/44` evidence entries is **invalid seal metadata** and must not be used as an authority claim.

**#415** (`fix(r4): derive seal cardinality from authoritative manifest`) is **OPEN / UNMERGED / UNACCEPTED** at exact head `3da0d8ec45adf8934b88906462706617aa22831f`. Its retained forensic result remains that the literal `44` was manually embedded after `sha256sum -c` verified hashes without deriving cardinality; the authoritative immutable `SHA256SUMS` contains **50** valid non-empty entries; and the defect affects derived seal metadata and semantic seal validity, not the qualified candidate identity, authoritative evidence bytes, authoritative hashes, qualification gate results, or the manifest itself.

The proposed #415 tooling derives cardinality directly from `SHA256SUMS`, accepts no expected-count argument, rejects malformed/duplicate/unsafe paths, verifies every referenced hash, independently recomputes cardinality during seal verification, and rejects the existing `recorded=44 authoritative=50` mismatch. Its named exact-head technical workflows remain **PASS**; exact-head maintainer approval remains **FAIL / no matching human attestation**.

No corrected seal / Seal v3 exists. The current erroneous seal must not authorize canary execution. Canary execution remains **NOT AUTHORIZED / NOT EXECUTED**.

**#422** (`test(r4): adversarially qualify seal evidence authority`) remains **DRAFT / UNMERGED / UNACCEPTED** at `31dc9c1bf88ee69f417f53c0f4ff5558fc48f645`. Its exact-head named technical workflows are **PASS**, while extra-file closure, semantic binding, and provenance-DAG verification remain unresolved requirements. It does not repair an existing seal and does not authorize a canary.

Any open candidate documentation that still states `44/44` as authoritative seal cardinality, including the earlier #411 record, is superseded on that point by #415 and must not be merged unchanged.

## AUD-1 security convergence

Owner issue **#353 remains OPEN with no milestone** and remains the pre-release security convergence boundary. The original candidate **#399** remains unchanged at `8df77b832b3839ccd2a6944a65760ce3ab10dc9c`, and physical-evidence helper **#403** remains unchanged at `118ec3c795ae11c88b68278717fb781f4b059559`. The two required real-host F6 cases remain **UNKNOWN / not established**; no software fixture or hosted CI run substitutes for them.

Draft successor **#416** remains at `d41a9428e8667963f85526f44a9616be19ca9d7f`. It is **DRAFT / OPEN / UNMERGED / UNACCEPTED** and preserves #399/#403 rather than silently retargeting them. Its C1/C2/C3 exact-head hosted technical workflows are **PASS**, but that head is not the selected release successor and its evidence does not transfer to later changed bytes.

Draft **#431** (`fix(aud1): surrender on explicit result authority denial`) remains **DRAFT / OPEN / UNMERGED / UNACCEPTED**, stacked directly on #416. Retained test-only head `a980274c6a3d5b3b479a18466a7877d1207476ab` preserves **AUD1-C4** before repair: explicit `/api/worker/result` HTTP 403 entered the generic transport retry path, allowing a second denied result attempt and generic empty-proposal fallback rather than immediate authority surrender. On those exact failing bytes, Qualification v1, Controller/provider contracts, and Command Station remain **FAIL** evidence and were not rerun unchanged for green.

Current #431 repair head **`a9c00474606b2bd5733ae5eef00a52d59b0aa89b`** classifies result HTTP 401/403 as authority loss before generic transport retry, revokes the local continuity proof, raises `WorkerAuthorityLost`, and uses the same guarded path for the empty-proposal fallback. Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, PR-Agent, and **Pages are now PASS** on this exact head. Vercel remains **FAIL** because of the external account build-rate limit, not a demonstrated RESIDUAL product-test failure. Maintainer approval remains **FAIL / no matching human attestation**.

#431 does not select a release successor, retarget #403, establish either physical F6 case, or authorize merge/release activity. Genuine independent human review of C1/C2/C3/C4 plus the admitted-operation drain/completion-barrier tradeoff remains mandatory before successor selection.

Required sequence remains: independent review -> deliberate successor selection -> helper reconciliation for that exact target -> separately retained F6-A and F6-B physical evidence -> Mason/LEGION independent read-only re-audit -> exact-head qualification/owner attestation -> guarded merge -> authoritative new-main qualification -> final RC recovery/elapsed-soak evidence.

## Release-readiness convergence ledger

Draft **#427** (`docs(v1): add master release-readiness convergence ledger`) advanced from `570b82f05042725f01ab4dc1916a9c13b5d60ea0` to exact head **`b556b3e63ac16d5c5e6ec4c086db4c682cd04530`**. It is still **DRAFT / OPEN / UNMERGED / UNACCEPTED** and review-only.

Relative to its original head, #427 added three documentation artifacts:

- `docs/v1/R4_1_CANARY_SCOPE_DECISION.md`, which keeps the #426 receipt-binding, stored-payload-digest, and concurrent-recovery findings **UNDECIDED** and fail-closed until an explicit scope disposition is approved;
- `docs/v1/V1_DEPLOYMENT_SCOPE_DECISION.md`, which leaves topology, tenancy, runtime envelope, SLO, RPO, RTO, backup, retention, HA, soak, and related owner/operations decisions **UNAPPROVED / UNDECIDED**;
- `docs/v1/V1_MASTER_READINESS_DELTA.md`, which records #431/C4, #428, #429, and #430 as review-ready repository-side progress without converting them into acceptance authority.

On #427 exact head `b556b3e...`, Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent are **PASS**. Vercel is **PASS**. Maintainer approval is **FAIL / no matching human attestation**. These PASS results qualify only #427's exact bytes; they do not establish the underlying physical, canary, deployment, or production claims tracked by the ledger.

The ledger still leaves canary execution blocked on scope/authority prerequisites, production v1 blocked on AUD-1 physical/independent closure plus an approved deployment profile, and final release blocked on exact-RC recovery/soak/provenance and explicit human release authorization.

## Release-operations candidates

The following review-only candidates are active; none is accepted-main state and none authorizes a canary, RC, tag, deployment, or production acceptance.

**#428** (`fix(release): bind v1 receipt to post-convergence RC`) remains **DRAFT / OPEN / UNMERGED / UNACCEPTED** at `1bf6097f9c528f8bce7d15947bafbc2d5b58cf43`. It separates frozen R4.1 `canary_provenance` from the eventual post-convergence release candidate and validates RC/final-tag binding. Its named technical workflows remain **PASS**; Vercel is **PASS**; maintainer approval is **FAIL / no matching human attestation**. No RC has been selected.

**#429** (`fix(release): align package version metadata`) remains **DRAFT / OPEN / UNMERGED / UNACCEPTED** at `9d38d87df9bfa5004d3eb5d7144e60ef1ced56f7`. Accepted main still has the metadata mismatch `pyproject.toml=0.5.0` versus `residual.__version__=0.4.0`; #429 proposes only to align the declarations and pin them with a regression. Its named technical workflows and Pages are **PASS**; maintainer approval is **FAIL / no matching human attestation**. It does not set `1.0.0`.

**#430** (`feat(qualification): add ENV-G01 capability preflight`) remains **DRAFT / OPEN / UNMERGED / UNACCEPTED** at `756e540ca64fa953ca389e2d3441f9229d7969de`. It adds a machine-readable `PASS | BLOCKED` environment/capability preflight and does not reinterpret prior restricted-environment failures as product failures or PASS. Its named technical workflows are **PASS**; maintainer approval is **FAIL / no matching human attestation**. Active Qualification-v1 wiring remains a later review decision.

New draft **#432** (`feat(release): validate v1 deployment qualification profile`) is **DRAFT / OPEN / UNMERGED / UNACCEPTED** at exact head **`f6487c8430f03e930c3ae22c99f41117d310372e`**, based on accepted `main@d796f36...`. It maps to master-ledger `V1-PP-001` and turns an eventual owner-approved deployment profile into a typed, fail-closed qualification input by adding `docs/v1/V1_DEPLOYMENT_PROFILE.schema.json`, a stdlib-only validator, and focused regressions.

#432 rejects unresolved `UNDECIDED` state, malformed source identity, secret-bearing fields, contradictory loopback/non-loopback TLS or proxy claims, undeclared multi-user authorization, unsupported multi-host/process combinations, and failover claims without multi-host support. It emits a deterministic profile SHA-256 and applicability decisions for `PR-G05`, `PR-G09`, `PR-G17`, and `PR-G31`.

#432 does **not** choose the v1 topology, tenancy model, SLO, RPO, RTO, backup policy, soak duration, or HA claim. Those remain owner/operations decisions and therefore remain **BLOCKED / UNDECIDED** until explicitly approved. On exact head `f6487c8...`, Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent are **PASS**. Maintainer approval is **FAIL / no matching human attestation**. Vercel is **FAIL** because of the external account build-rate limit, not a demonstrated product-test failure.

## Additional review-only findings

**#423** records a production-readiness matrix and explicitly lacks authoritative production topology, SLO, RPO, and RTO inputs; its receipt-binding item remains a **BLOCKING_CANDIDATE_FINDING pending scope review**, not an accepted-main defect classification. **#426** records offline fault-space exploration and labels malformed/cross-bound receipt false ACK, recovery digest mismatch, and unfenced simultaneous recovery as **BLOCKING_CANDIDATE_FINDING** items requiring human scope disposition; real fsync/power-loss, ENOSPC, and process-level fencing fixtures remain absent. Neither candidate executed a canary.

Other R4/R5/research/canary planning PRs remain unmerged and unaccepted. Their local or hosted PASS results do not authorize promotion, deployment, canary execution, or broad production-readiness claims.

## Qualification and trust-boundary discipline

`PASS`, `FAIL`, `UNKNOWN`, and `BLOCKED` remain exact-claim states. A PASS on one revision does not transfer to changed bytes. A candidate finding does not become an accepted defect until its scope and evidence are reviewed. A documented external result does not override contradictory or missing repository-local evidence. Missing physical evidence remains `UNKNOWN / not established` rather than inferred from software tests.

Still **UNKNOWN / not established** by accepted-main hosted PASS results:

- universal/every-host M4 qualification;
- true 24h/72h/30d elapsed soak evidence;
- physical F6-A/F6-B authority-loss reliability on the selected AUD-1 successor;
- Mason/LEGION closure of AUD-1;
- a valid corrected R4.1 seal suitable for authorization review;
- live R4.1 canary success;
- accepted R4.1/R5 Shared Comms implementation on main;
- an approved v1 deployment/trust/SLO/RPO/RTO profile;
- an exact post-convergence v1 release candidate with required recovery/soak/provenance evidence;
- blanket production readiness.

The accepted Factory/M4 ownership baseline and protected-byte set remain whatever the committed ownership baseline on main records. This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, evidence schemas, provider authority, security implementation, licensing authority, or acceptance authority.

`implementation-status.yaml` remains an implementation-presence manifest, not a release-qualification manifest.

## Documentation scope

This reconciliation changes only `docs/CURRENT_STATUS.md` on the existing dedicated documentation branch. Accepted main has not changed since the previous observation, and the newly observed work is review-only release/security planning plus exact-head CI completion; no new accepted-main claim requires an edit to `README.md`, `HARNESS.md`, `START-HERE.md`, or `implementation-status.yaml`. Those files are intentionally unchanged in this observation.

Because this status document records qualification anchors, corrected evidence-authority interpretation, ownership-baseline context, active security successors, retained failures/unknowns, and release/canary trust-boundary state, the documentation PR must **not** be merged automatically. Exact-head human review/attestation remains required.