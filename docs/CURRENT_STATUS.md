# RESIDUAL current status

_Current-state check: 2026-09-24 10:03 UTC against `main@d796f36b75e730a0bab71bdba564206174393719`._

This document is a human-readable current-state summary, not a replacement for exact repository bytes, retained artifacts, workflow logs, issue/PR history, or maintainer/protected-byte governance. Historical PASS/FAIL/BLOCKED evidence remains bound to the exact revision, run attempt, and environment that produced it. Git history retains earlier detailed versions of this status document.

## Executive summary

Accepted `main` remains **`d796f36b75e730a0bab71bdba564206174393719`**, the merge of #304 (`fix(station): typed fail-closed reviewer findings (#209)`). No newer PR has merged into accepted main during this observation.

Release convergence remains **BLOCKED**. AUD-1 issue #353 remains **OPEN with no milestone**; physical F6-A/F6-B evidence remains **UNKNOWN / not established**; the independent Mason/LEGION re-audit is outstanding; the R4.1 seal-cardinality defect still prevents the erroneous seal from serving as authorization evidence; no corrected seal exists; and no canary, release candidate, deployment, or production acceptance has been authorized.

Meaningful review-only movement since the previous observation is concentrated in two new candidates:

- **#433** adds AUD1-C5, reproducing and repairing a stale-task-lease authority-loss path on top of #431. Its current exact head is green across the named repository technical workflows and Pages, but it remains draft/unaccepted and lacks exact-head human maintainer attestation.
- **#434** adds the repository-side incident-response qualification plan for PR-G30. Its plan and validator are present and hosted technical CI is green, but **no incident drill has executed** and PR-G30 remains **IN_PROGRESS**, not VERIFIED.

Neither candidate changes accepted-main release state.

## R4.1 evidence authority and canary boundary

The prior external R4.1 qualification record remains bounded to its authoritative candidate, evidence bytes, hashes, and gate results. The previously propagated ready-for-canary seal statement `44/44` is **invalid derived seal metadata** and must not be used as an authority claim.

**#415** (`fix(r4): derive seal cardinality from authoritative manifest`) remains **OPEN / UNMERGED / UNACCEPTED** at `3da0d8ec45adf8934b88906462706617aa22831f`. Its retained forensic result is that the literal `44` was manually embedded after `sha256sum -c` verified hashes without deriving cardinality; authoritative immutable `SHA256SUMS` contains **50** valid non-empty entries. The defect affects derived seal metadata and semantic seal validity, not the candidate identity, authoritative evidence bytes, authoritative hashes, qualification gate results, or the manifest itself.

No corrected seal / Seal v3 exists. The current erroneous seal must not authorize canary execution. Canary execution remains **NOT AUTHORIZED / NOT EXECUTED**.

**#422** remains **DRAFT / UNMERGED / UNACCEPTED** at `31dc9c1bf88ee69f417f53c0f4ff5558fc48f645`. Its exact-head named technical workflows are PASS, while extra-file closure, semantic binding, and provenance-DAG verification remain unresolved requirements. It does not repair an existing seal and does not authorize a canary.

Any open candidate documentation that still states `44/44` as authoritative seal cardinality is superseded on that point by #415 and must not be merged unchanged.

## AUD-1 security convergence

Owner issue **#353 remains OPEN with no milestone** and remains the pre-release security convergence boundary. Original candidate **#399** remains unchanged at `8df77b832b3839ccd2a6944a65760ce3ab10dc9c`; physical-evidence helper **#403** remains unchanged at `118ec3c795ae11c88b68278717fb781f4b059559`. The two required real-host F6 cases remain **UNKNOWN / not established**; no software fixture or hosted CI run substitutes for them.

Draft **#431** remains the qualified C1-C4 predecessor at `a9c00474606b2bd5733ae5eef00a52d59b0aa89b`. Its exact-head Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, PR-Agent, and Pages are PASS. Vercel is PASS on the latest observed status for that exact head; maintainer approval remains **FAIL / no exact-head human attestation**. #431 is still unmerged and unaccepted.

New draft **#433** (`fix(aud1): surrender on stale result lease`) is **DRAFT / OPEN / UNMERGED / UNACCEPTED**, stacked directly on #431. It adds **AUD1-C5**.

Retained test-only head `9caaebe06214a7f8c280732eddbfdd18aeecd42c` reproduced the defect against #431-derived bytes: Station returned HTTP 400 with exact structured error `{"error":"Stale task lease"}` after the authoritative server lease was expired while the same owner still held the task. The worker treated that `HTTPError` as generic transport failure, made three result attempts including the empty-proposal fallback, and did not raise `WorkerAuthorityLost`. Command Station run `35979195361` retains that first hosted failure; the unchanged failing head was not rerun for green.

Current #433 repair head **`9b4f32ce71ba2f4520dc1d7c2d8826fa329bdf60`** treats only HTTP 400 responses parsing as the exact bounded Station error `{"error":"Stale task lease"}` as authoritative lease loss, revokes the local continuity proof, and raises `WorkerAuthorityLost` before generic transport retry. Other HTTP 400 contract/proposal failures retain their prior repair/fallback behavior.

Exact-head #433 evidence is **PASS** for Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, PR-Agent, and Pages. Vercel is **PASS**. Maintainer approval is **FAIL / no exact-head human attestation**. The qualification manifest is reported as 25/25 required gates PASS, zero skips, zero UNKNOWN for this exact head.

That PASS does **not** establish production acceptance. #433 does not select the release successor, retarget #403, establish either physical F6 case, supply Mason/LEGION independent review, authorize merge, or authorize deployment/release. Genuine independent human technical review must now include C1-C5 plus the admitted-operation drain/completion-barrier tradeoff before successor selection.

Required AUD-1 sequence remains: independent review -> deliberate successor selection -> helper reconciliation for that exact target -> separately retained F6-A and F6-B physical evidence -> Mason/LEGION independent read-only re-audit -> exact-head qualification and owner attestation -> guarded merge -> authoritative new-main qualification -> final RC recovery/elapsed-soak evidence.

## Release-readiness convergence ledger

Draft **#427** (`docs(v1): add master release-readiness convergence ledger`) remains **DRAFT / OPEN / UNMERGED / UNACCEPTED** at `b556b3e63ac16d5c5e6ec4c086db4c682cd04530`.

Its canary-scope and deployment-scope worksheets remain fail-closed and **UNAPPROVED / UNDECIDED**. On that exact head, Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent are PASS; Vercel is PASS; maintainer approval is FAIL for lack of exact-head human attestation. Those PASS results qualify only the ledger bytes and do not establish physical, canary, deployment, or production claims.

The ledger continues to leave canary execution blocked on scope/authority prerequisites, production v1 blocked on AUD-1 physical/independent closure plus an approved deployment profile, and final release blocked on exact-RC recovery/soak/provenance plus explicit human release authorization.

## Release-operations and qualification candidates

These candidates are review-only; none is accepted-main state and none authorizes canary, RC, tag, deployment, or production acceptance.

- **#428** remains at `1bf6097f9c528f8bce7d15947bafbc2d5b58cf43`, separating frozen R4.1 canary provenance from the eventual post-convergence RC. No RC is selected.
- **#429** remains at `9d38d87df9bfa5004d3eb5d7144e60ef1ced56f7`. Accepted main still has `pyproject.toml=0.5.0` versus `residual.__version__=0.4.0`; #429 proposes to align those declarations but does not set `1.0.0`.
- **#430** remains at `756e540ca64fa953ca389e2d3441f9229d7969de`, adding ENV-G01 environment/capability preflight without reinterpreting restricted-environment failures as product failures or PASS.
- **#432** remains at `f6487c8430f03e930c3ae22c99f41117d310372e`, adding a typed deployment-profile schema and fail-closed validator. It does not choose topology, tenancy, SLO, RPO, RTO, backup, soak, or HA policy; those remain **BLOCKED / UNDECIDED** until explicit owner/operations approval.

### PR-G30 incident-response qualification

New draft **#434** (`feat(v1): add incident-response qualification plan`) is **DRAFT / OPEN / UNMERGED / UNACCEPTED** at exact head **`76a2a69fa6c7c2959108de2369796a755d59ea84`**, based on accepted `main@d796f36...`.

It adds exactly four files: `docs/v1/V1_INCIDENT_RESPONSE_PLAN.json`, `docs/v1/V1_INCIDENT_RESPONSE_RUNBOOK.md`, `scripts/validate_v1_incident_response_plan.py`, and `tests/test_v1_incident_response_plan.py`. The plan covers five required scenarios: credential leak, database corruption, runaway work/resource exhaustion, host compromise, and evidence-integrity/confidentiality breach. It requires human authority for containment/recovery, first-failure/forensic preservation, redacted evidence, exact source identity, explicit PASS/FAIL/UNKNOWN/BLOCKED semantics, and rejects secret-bearing fields. Its validator explicitly emits `execution_claim: NONE`.

Observed exact-head #434 hosted technical workflows are **PASS** for Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent. Maintainer approval is **FAIL / no exact-head human attestation**. Vercel is **FAIL** because the deployment was rate-limited for 24 hours; this is an external deployment-service limit, not a demonstrated RESIDUAL product-test failure. No Pages PASS claim is made for #434 because a Pages workflow was not present in the observed exact-head PR-triggered run set.

Most importantly, **PR-G30 remains IN_PROGRESS, not VERIFIED**. No incident drill has executed. Verification still requires all five drills against the future owner-approved v1 deployment profile and the exact selected RC, with independently retained evidence bundles and release-authority disposition.

## Additional review-only findings

**#423** records a production-readiness matrix and explicitly lacks authoritative production topology, SLO, RPO, and RTO inputs; its receipt-binding item remains a `BLOCKING_CANDIDATE_FINDING pending scope review`, not an accepted-main defect classification. **#426** records offline fault-space exploration and labels malformed/cross-bound receipt false ACK, recovery digest mismatch, and unfenced simultaneous recovery as candidate-scoped blocking findings requiring human scope disposition. Real fsync/power-loss, ENOSPC, and process-level fencing fixtures remain absent. Neither candidate executed a canary.

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
- executed and independently retained PR-G30 incident-response drill evidence;
- an exact post-convergence v1 release candidate with required recovery/soak/provenance evidence;
- blanket production readiness.

The accepted Factory/M4 ownership baseline and protected-byte set remain whatever the committed ownership baseline on main records. This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, evidence schemas, provider authority, security implementation, licensing authority, or acceptance authority.

`implementation-status.yaml` remains an implementation-presence manifest, not a release-qualification manifest.

## Documentation scope

This reconciliation changes only `docs/CURRENT_STATUS.md` on the existing dedicated documentation branch. Accepted main has not changed since the previous observation. The newly observed work is review-only AUD-1 successor movement and incident-response qualification preparation; no new accepted-main claim requires an edit to `README.md`, `HARNESS.md`, `START-HERE.md`, or `implementation-status.yaml`. Those files are intentionally unchanged in this observation.

Because this status document records qualification anchors, corrected evidence-authority interpretation, ownership-baseline context, active security successors, retained failures/unknowns, and release/canary trust-boundary state, the documentation PR must **not** be merged automatically. Exact-head human review/attestation remains required.
