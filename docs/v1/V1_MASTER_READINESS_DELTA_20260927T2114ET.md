# RESIDUAL v1 master readiness delta — 2026-09-27 21:14 ET

Status: **review-only additive delta to PR #427**. This file changes planning/read-model state only. It does not authorize merge, candidate selection, helper mutation, physical F6, canary, provider execution, private Seal verification, soak, deployment, tag, or release.

## Live baseline

- Accepted main: `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`.
- Existing master branch/PR: #427, branch `docs/v1-master-readiness`, predecessor head read immediately before this write: `560e296aae465d98fcd7ef10c9896bf26ae92a48`.
- QD-2 convergence candidate remains #476 exact `05e01731208957e85cf72cf02a925b0660fca144`; no evidence from later main is inherited onto it.
- QD-2 F6 helper remains #483 exact `558b37c2d552e20f18192c73a642b31038ee7b83`; physical F6 remains separately gated and unauthorized by this delta.
- Frozen R4.1 candidate remains reference-only: `8701367db6d3202f24b3eb9f4696b0cadf657985` / tree `79bfe6ed1743907065ed44aeb9c460c47527e0c6`.

## PRE-CANARY

### V1-PC-001 — direct-source Seal/package verification
**Acceptance:** reviewed/frozen verifier independently recomputes authoritative semantic/package/provenance claims from the private direct sources.

**Source/evidence:** #423 PR-G26; #443/#447 tooling lineage.

**Classification:** missing evidence.

**Dependencies:** trusted private runtime/Seal sources; reviewed verifier.

**Owner:** release/evidence reviewer.

**Implementation PR:** tooling successors only; no private authoritative execution claimed here.

**Verification status:** **BLOCKED**.

**Required human action:** select exact verifier bytes and separately authorize private read-only verification. Public PRs must retain sanitized hashes/descriptions only.

### V1-PC-002 / V1-PC-003 / V1-PC-004 — receipt/recovery safety
**Acceptance:** either (a) receipt project/operation/actor/payload/type binding, pre-network stored-payload digest verification, and one durable recovery owner are proven with isolated negative/concurrency fixtures, or (b) the affected capability is explicitly excluded and that exclusion is enforced and tested.

**Source/evidence:** #426 exact `494dac7c0702a285c33ceddd3f0237f63ceea425`; #423 PR-G32.

**Classification:** retained reported findings / scope decision.

**Dependencies:** D4 feature-scope disposition and exact selected release source.

**Owner:** Shared Comms / recovery owner plus release owner.

**Implementation PR:** none selected by this lane.

**Test/evidence:** retained disposable probes report malformed/wrong-project/wrong-operation receipts becoming ACKED, tampered stored payload POSTed before digest revalidation, and synchronized recoverers issuing two POSTs. This delta does not claim independent reproduction.

**Verification status:** **BLOCKED**.

**Required human action:** explicitly INCLUDE and repair/qualify, or EXCLUDE with enforced negative tests. Do not relabel observed risk optional merely to clear a gate.

## CANARY

### V1-CAN-001 — canary authorization
Historical R4.1 17/17 READY_FOR_CANARY remains historical exact-scope evidence only.

**Status:** **BLOCKED** on applicable pre-canary dispositions, reviewed procedure/evaluator, and separate owner GO.

No canary is authorized by this delta.

## POST-CANARY

### V1-POST-001 — independent post-canary evaluation
**Status:** **NOT_STARTED** for the current v1 path.

Tooling proposals do not substitute for execution against an authorized retained canary bundle.

## PRE-PRODUCTION

### V1-PP-001 — authoritative deployment profile
**Acceptance:** owner-approved topology, trust boundary, supported environment, SLO/availability, RPO/RTO, backup/retention, storage/durability, evidence/log/disk budgets, host/region-loss claims, soak environment/workload/cadence/reset, and named operational owners are bound to an exact profile.

**Source/evidence:** #423 production audit; #472 deployment-profile tooling.

**Classification:** scope decision / missing evidence.

**Dependencies:** owner/operations decisions.

**Owner:** owner + operations.

**Verification status:** **BLOCKED**. Tooling qualification is not profile acceptance.

**Required human action:** supply and approve exact values; do not infer Internet-facing enterprise scope or narrow the product solely to ship.

### V1-SRC-001 — immutable RC source composition
**Acceptance:** exact RC source/tree explicitly includes or excludes post-QD-2 changes before RC qualification.

**Source/evidence:** accepted main now includes merged #485 at `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`; QD-2 #476 remains `05e01731208957e85cf72cf02a925b0660fca144`.

**Classification:** scope/source decision.

**Dependencies:** Closure/F6 disposition and owner release composition.

**Owner:** release owner.

**Verification status:** **BLOCKED**.

**Required human action:** explicitly include or exclude #485 and any other admitted post-QD-2 bytes. Inclusion changes RC identity and requires fresh exact-RC qualification; exclusion means the Puter referrer repair cannot be credited to that RC.

### V1-HOSTED-001 — real hosted-provider success
**Acceptance:** one named admitted hosted provider/model succeeds on the exact selected RC under the approved bounded workload and evidence policy.

**Source/evidence:** #485 fixes the Puter popup-origin referrer path, but no exact-RC real hosted-provider success is established by this lane.

**Classification:** missing evidence.

**Dependencies:** D3 provider/model selection, exact RC, separately authorized credential/provider use.

**Owner:** release/provider owner.

**Verification status:** **BLOCKED**.

**Required human action:** name provider/model, authorize bounded execution, and retain exact-RC evidence without publishing secrets.

## RELEASE

### V1-REL-003 — fail-closed RC/release receipt
**Source:** PR #478 exact head `a91d89d9e0b7767e174646324afb38fb0cd90c61`, base `1bf6097f9c528f8bce7d15947bafbc2d5b58cf43`.

**Acceptance:** structural/cross-field release closure fails closed on RC/source/tree/artifact-set/gate/tag/deployment/rollback mismatches and requires caller-supplied trusted expected identities. Cryptographic signature verification and external artifact hashing remain separate evidence producers.

**Classification:** implementation / release-preparation control.

**Dependencies:** independent human review, accepted integration, exact RC identity, trusted external evidence producers.

**Owner:** release owner/reviewer.

**Implementation PR:** #478.

**Test/evidence:** exact-head Qualification-v1, Command Station, controller/provider, clean install, Factory ownership, Control Plane, and measured-binding workflows are PASS. The exact-head human maintainer attestation `RESIDUAL-MAINTAINER-APPROVAL: a91d89d9e0b7767e174646324afb38fb0cd90c61` was posted by the owner at 2026-09-28T01:02:12Z. Because that gate input changed, only the previously failed maintainer job was rerun. Workflow run `36326836065`, rerun job `108750259341`, is now PASS: policy tests and exact-head approval publication both succeeded. Combined status reports `maintainer-approval: success` for this exact head.

**Verification status:** **READY_FOR_REVIEW** as an implementation; PR remains DRAFT/UNMERGED and submitted human reviews remain zero.

**Required human action:** independent review, then accepted integration and resulting-source/exact-RC requalification. The maintainer attestation is not an independent review and does not authorize merge or release.

**Repository-side action in this run:** attempted draft -> ready-for-review metadata transition only after re-reading unchanged exact head/base. The platform safety layer blocked that mutation before execution; no state changed and no bypass was attempted.

### V1-CLOSURE-001 — AUD-1 / F6 security closure
**Source:** issue #353; #476/#483.

**Classification:** missing physical/independent evidence; Closure-owned single-writer lane.

**Dependencies:** owner review/helper freeze, separate F6 authorization, distinct F6-A/F6-B retained evidence, Mason/LEGION read-only falsification re-audit, unchanged-head qualification.

**Owner:** existing RESIDUAL v1 Closure task.

**Verification status:** **BLOCKED**.

**Required human action:** follow the existing Closure sequence. This master lane must not edit, rebase, retarget, supersede, duplicate, merge, attest, or physically execute that work.

## R5 / POST-V1

### V1-R5-PC-001 — Program Control
PR #484 remains post-v1 unless separately admitted. Its current exact head is not inherited into v1 readiness. Any failing/incomplete exact-head qualification remains an R5 concern unless an owner scope decision explicitly admits it.

**Status:** **BLOCKED / POST-V1**, no v1 critical-path effect.

## RESEARCH

R5 corpus, AX-21/AX22 and other frozen research evidence remain research inputs, not prerequisites to finishing every v1 gate. Original evidence and frozen experiments are not rewritten by this delta.

## Current shortest dependency path

1. Preserve QD-2/#483 exact identities and complete Closure-owned independent review/helper freeze.
2. Separate physical F6 authorization.
3. Execute and retain distinct F6-A/F6-B evidence.
4. Mason/LEGION read-only re-audit; then unchanged-head qualification/disposition.
5. Explicitly select immutable RC composition, including/excluding #485 and other admitted successors.
6. Fresh exact-RC qualification.
7. Close applicable PR-G26 / receipt-recovery / hosted-provider / provenance-reproducibility / operational-profile gates.
8. Complete exact-RC recovery/rollback/soak evidence where applicable.
9. Independent release review and final human release authorization.

No readiness percentage is assigned. Readiness is represented by satisfied applicable gates, unresolved blockers, and missing evidence.

## Actions explicitly not performed

No merge, auto-merge, self-approval, human attestation by this task, candidate/helper mutation, protected-pin change, physical F6, canary, private Seal verification, real paid-provider workload, live service/host/credential action, recovery or incident exercise, elapsed soak, production deployment, tag, or release was performed.
