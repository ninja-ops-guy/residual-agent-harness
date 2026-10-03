# V1 master delta — #469 owner selection and release-surface reconciliation

Status: review-only, append-only convergence evidence. This file does not authorize merge, physical F6, canary, deployment, RC selection, soak, tag, or release.

## Exact identities

- accepted main: `d796f36b75e730a0bab71bdba564206174393719`
- master parent before this write: `f5b5940c0d4d88c46e65dc6b0f51fb44e8164a6c`
- owner-approved Docker/AUD-1 successor direction: #469 `935498ecd42982bc682d7ed69b562c642b74a8fe`
- frozen predecessor: #448 `943c77a28ada1bc3931408c5f9b40d40c25eb2dc`
- historical F6 helper: #455 `a2567103c7e634310d696e421692fa1f86624e3b`
- version-surface successor: #466 `edc3e47ea14de77ce3ca7140bd34e729f4cea9bd`

## PRE-CANARY — AUD1-CONTAINER-CHOICE-01

**Classification:** scope decision / exact-candidate selection input  
**Status:** VERIFIED for owner direction; downstream helper/F6 work remains BLOCKED.

Owner comment on #469 approves exact head `935498ecd42982bc682d7ed69b562c642b74a8fe` as the bounded v1 Docker/AUD-1 successor direction. The accepted container contract is a single trusted local Docker host / Docker Compose, loopback host publication at `127.0.0.1:8765`, bounded `RESIDUAL_CONTAINER_LOCAL_ONLY=1`, no combination with remote exposure, and no claim for public ingress, Kubernetes, hostile-local-container isolation, multi-tenant container networking, or distributed/HA container topology.

Acceptance evidence currently recorded on that exact head: Qualification-v1 `36212304442`, Command Station `36212304370`, controller/provider `36212304449`, clean install `36212304372`, Factory ownership `36212304427`, Control Plane `36212304361`, measured binding `36212304399`, and Pages `36212304413` all PASS. PR-Agent `36212304501` remains a separate advisory failure. Submitted human PR reviews remain absent.

**Dependency consequence:** #455 remains valid only for historical #448 bytes and MUST NOT be used for physical F6. The AUD-1 single-writer lane must now: record #469 tree identity; explicitly freeze/select the immutable SHA+tree; create/reconcile a helper from frozen #403 bound atomically to #469; freshly qualify that helper; then obtain a new separate physical F6 authorization.

**Owner:** RESIDUAL v1 Closure / AUD-1 lane. This master task does not retarget or edit that lane.

## PRE-PRODUCTION — V1-VERSION-SURFACE-01

**Classification:** release metadata consistency  
**Implementation:** #466 `edc3e47ea14de77ce3ca7140bd34e729f4cea9bd`  
**Status:** READY_FOR_REVIEW technically; UNMERGED / no human review.

#466 derives Station HTTP/banner/bootstrap/diagnostics version reporting from `residual.__version__`, aligns `package.json` to 0.5.0, and extends version-surface tests. Exact-head Qualification-v1 `36211357854`, Command Station `36211357861`, controller/provider `36211357837`, clean install `36211357915`, Factory ownership `36211357833`, Control Plane `36211357936`, measured binding `36211357838`, and Pages `36211357894` PASS. Maintainer policy tests pass but explicit exact-head approval is absent; PR-Agent advisory execution fails after build/secret preflight; Vercel reports its account deployment-rate limit.

Acceptance criterion remains independent review plus integration into the selected convergence tree followed by resulting-main requalification. No prior-head CI transfers after any source change.

## Remaining blocking order

1. AUD-1 lane freeze/select #469 exact SHA+tree, create/requalify its new frozen-#403-derived F6 helper, and obtain fresh physical-F6 authorization.
2. Execute separately authorized F6-A/F6-B and retain distinct evidence; obtain independent Mason/LEGION re-audit.
3. Resolve remaining owner/product decisions: supported release matrix, distribution terms, Shared Comms v1 inclusion/exclusion, and exact-RC operations profile including SLO/RPO/RTO/backup/retention/soak.
4. Close applicable PR-G26 direct-source/private provenance evidence and PR-G28 complete lock/offline reproducibility evidence.
5. Preserve #426 receipt-binding, recovery-digest and concurrent-recoverer findings until explicit scope disposition or accepted repair evidence exists.
6. Assemble the accepted successor set into one convergence tree; run fresh resulting-main qualification.
7. Select exact RC, then perform separately authorized exact-RC install/recovery/rollback/incident/elapsed-soak evidence and final human release authorization.

Historical R4.1 READY_FOR_CANARY remains scoped qualification only and is not canary authorization.
