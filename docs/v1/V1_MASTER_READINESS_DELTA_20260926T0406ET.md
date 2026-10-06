# V1 master readiness delta — 2026-09-26 04:06 ET

Status: **review-only / append-only / no release authority**.

## Exact live identities

- accepted main: `d796f36b75e730a0bab71bdba564206174393719`
- ledger parent before this append: `bd498a31cb0045dfd5791f729084a5504ccdf760`
- owner-selected Docker/AUD-1 successor: #469 `935498ecd42982bc682d7ed69b562c642b74a8fe`, tree `8d8ecb2970d3dc2cf304ba8c8c6997a05b45370b`
- historical F6 helper #455: `a2567103c7e634310d696e421692fa1f86624e3b`; valid only for historical #448 binding
- PR-G27 digest successor #468: `f30a1e16f14d92b623770b3866b5c249d9dee263`
- deployment-profile first-failure branch: `repair/v1-deployment-profile-boundary-r1@20adc626cf7200afc101d2cb3c9ea0f078e7b27d`
- production-audit source #423: `324a8421205c664cb4cfbfda9582a6e79d43ee64`
- offline-fault source #426: `494dac7c0702a285c33ceddd3f0237f63ceea425`

## PRE-CANARY

| Stable ID | Requirement / acceptance criterion | Source / class | Dependencies | Owner | Implementation | Test / evidence | Verification | Human action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AUD1-CONTAINER-CHOICE-01 | Use the exact owner-selected #469 SHA/tree as the next F6 candidate identity; historical #448/#455 physical authority must not transfer. | #469 owner disposition; **scope decision** | #469 exact head | RESIDUAL v1 Closure | #469 | Qualification-v1 `36212304442` plus Command Station/controller-provider/clean-install/Factory/Control Plane/measured/Pages PASS | VERIFIED for candidate selection only | Closure owner freezes/selects exact SHA/tree and creates a fresh #403-derived helper |
| AUD1-F6-NEWHELPER-01 | A new helper must atomically bind all established candidate identity surfaces to #469, pass fresh exact-head helper qualification, then receive a separate physical F6 authorization. | #469/#455; **missing evidence** | AUD1-CONTAINER-CHOICE-01 | RESIDUAL v1 Closure | not yet observed | no new #469-bound helper found in current open-PR discovery | BLOCKED | Create/review/qualify helper; then separately authorize F6 |
| V1-PC-002 | Client must not ACK malformed/cross-project/cross-operation receipts unless an explicit accepted scope excludes this capability. | #426 retained disposable probes / #423 PR-G32; **observed finding** | v1 Shared Comms scope | owner + implementation owner | none observed | retained #426 probe report only; not independently reproduced this run | BLOCKED | explicit scope disposition or isolated repair + regression successor |
| V1-PC-003 | Recovery must verify stored payload digest before any POST; mismatch must quarantine/fail closed with zero POST. | #426; **observed finding** | Shared Comms included in v1 | owner + implementation owner | none observed | retained digest-mismatch probe only | BLOCKED | explicit scope disposition or isolated repair + regressions |
| V1-PC-004 | Concurrent recoverers must have one enforced recovery authority; synchronized absence must not issue two POSTs. | #426; **observed finding** | Shared Comms included in v1 | owner + implementation owner | none observed | retained synchronized-thread probe only | BLOCKED | explicit scope disposition or isolated fencing repair + regressions |

Historical R4.1 17/17 READY_FOR_CANARY remains historical exact-scope qualification only. This delta does not authorize a canary.

## PRE-PRODUCTION

| Stable ID | Requirement / acceptance criterion | Source / class | Dependencies | Owner | Implementation | Test / evidence | Verification | Human action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V1-PP-001 | Owner-approved deployment topology, trust boundary, supported OS/arch/Python/artifact/filesystem matrix, SLO/RPO/RTO, backup/retention, availability/HA claim and soak policy; no `UNDECIDED` values may enter the approved profile hash. | #423/#432 + first-failure branch; **scope decision + observed validator finding** | owner decisions | owner / operations | branch-only successor | `20adc626...` retains three padded-UNDECIDED negative failures against unchanged validator | IN_PROGRESS / BLOCKED | approve actual values; land the one-line recursive placeholder repair on a reviewable branch and qualify it |
| PR-G27 | All release workflow/action/container inputs must be immutable and provenance-dispositioned; no mutable nested action or Docker image reference. | #440/#464/#467/#468; **observed findings + implementation** | review/integration | release owner | #468 | Action Pin Gate `36211835639` PASS; seven named technical workflows PASS on exact head | READY_FOR_REVIEW technically; PR remains draft, zero human reviews | human review; upstream image provenance/attestation disposition; guarded integration + resulting-main requalification |
| PR-G26 | Independently verify authoritative private Seal/runtime claims directly from trusted immutable source and preserve package-closure/provenance guarantees. | #423/#443/#447; **missing evidence** | private source + independent review | release/security owner | repository prep only | repository verifier candidates exist; private direct-source acceptance absent | BLOCKED | complete private direct-source verification and human acceptance |
| PR-G28 | Produce complete transitive hash lock for approved release matrix; prove network-disabled/hash-enforced install/build and reproducibility against exact RC. | #444; **missing evidence** | V1-PP-001 + selected RC | release owner | #444 tooling | parser/tooling repair exists; authoritative lock/offline build absent | BLOCKED | authorize trusted resolver/build, retain lock/build evidence, independently review |

## RELEASE

| Stable ID | Requirement / acceptance criterion | Source / class | Dependencies | Owner | Implementation | Test / evidence | Verification | Human action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V1-CONVERGENCE-01 | Integrate only accepted review-ready successors, then run authoritative resulting-main qualification; do not inherit PR-head evidence across changed trees. | master ledger / **missing evidence** | all applicable pre-canary/pre-production gates | maintainer | none yet | current accepted main unchanged | NOT_STARTED | guarded merge wave only after reviews/approvals |
| V1-RC-01 | Select exact RC source/tree/artifact/config/lock/profile identities only after resulting-main qualification. | #445 lifecycle / **missing evidence** | V1-CONVERGENCE-01, V1-PP-001, PR-G26, PR-G28 | owner | none | no RC selected | BLOCKED | explicit owner RC selection |
| V1-OPS-01 | Execute separately authorized recovery/rollback, incident-response and approved elapsed-soak evidence against exact RC and approved profile. | #434/#435/#461/#445 / **missing evidence** | V1-RC-01 | operations + qualification lead | tooling only | no operational exercise performed by this task | BLOCKED | separate exercise authorizations + retained evidence + independent acceptance |
| V1-RELEASE-01 | Human release authority accepts all applicable exact-RC evidence; only then tag/publish/deploy. | #445 / **missing evidence** | V1-OPS-01 | owner | none | none | NOT_STARTED | explicit final authorization |

## R5 / POST-V1 and RESEARCH

R5-G01..G08 and AX-21/AX22 remain outside v1 unless owner scope explicitly promotes an observed risk into the v1 contract. No frozen research experiment or research branch is modified by this delta.

## Current ledger-head technical status before append

The parent ledger head `bd498a31...` had terminal PASS on Qualification-v1 `36225715836`, Command Station `36225715851`, controller/provider `36225715833`, clean install `36225715822`, Factory ownership `36225715841`, Control Plane `36225715827`, and measured-evaluation binding `36225715846`. Maintainer approval remained FAIL for missing exact-head human approval and PR-Agent remained an advisory failure. Those results do **not** qualify this new append commit; fresh exact-head CI is required.

No merge, F6, canary, private Seal verification, production exercise, soak, deployment, tag or release is authorized or claimed.
