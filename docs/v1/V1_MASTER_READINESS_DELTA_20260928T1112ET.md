# RESIDUAL v1 master readiness delta — 2026-09-28 11:12 ET

Status: **review-only additive delta to PR #427**. This records newly source-corroborated scope evidence for V1-PC-002..004 and does not authorize Shared Comms admission, canary, physical F6, production, tag, or release.

## Live identities

- Accepted main: `8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`.
- Master predecessor read immediately before this write: #427 `1eb142be519154ecd6ffecddc9d21dbd25aaf0ae`, base `main@d796f36b75e730a0bab71bdba564206174393719`.
- QD-2 product candidate: #476 `05e01731208957e85cf72cf02a925b0660fca144`.
- Shared Comms implementation lineage under review: #404 `7783081c858ad9ddf98b2e64e740e1104ae5d08b`.
- Retained offline-fault report: #426 `494dac7c0702a285c33ceddd3f0237f63ceea425`.
- Station local-ownership candidate: #448 `943c77a28ada1bc3931408c5f9b40d40c25eb2dc`.

## PRE-CANARY — V1-PC-002 / V1-PC-003 / V1-PC-004 applicability refinement

### Source corroboration on #404

Exact #404 source now directly supports the mechanisms behind the retained #426 observations:

1. **Receipt semantic binding:** `MeshOutbox.ack(operation_id, receipt)` persists the first receipt for an operation and only compares later receipts against the already-stored value. The function does not validate receipt type, project, operation, actor, or payload binding before first ACK persistence.
2. **Recovery payload integrity:** `MeshOutbox.enqueue()` stores a digest, but `MeshOutbox.due()` returns the persisted JSON value without recomputing/comparing that stored digest. `MeshWorkerClient.recover_outbox()` then hands the value to `_deliver_envelope()`, which can perform the network request before any stored-payload digest check.
3. **Concurrent recovery ownership:** `recover_outbox()` enumerates due rows and attempts delivery without a durable claim/lease/fencing transition around each row before network delivery. That source shape is consistent with the retained #426 simultaneous-recoverer/double-POST observation.

This is **source corroboration of mechanism**, not an independent dynamic reproduction of the #426 probes.

### Exact current-source applicability

Direct reads at accepted `main@8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2` and QD-2 `05e01731208957e85cf72cf02a925b0660fca144` returned **404 / absent** for both:

- `residual/station/mesh_outbox.py`
- `residual/station/mesh_worker.py`

Therefore these Shared Comms worker/outbox surfaces are not present in the currently observed main/QD-2 source trees. That absence narrows applicability; it does **not** itself constitute an owner scope decision or final release exclusion proof.

### Deduplication with #448

#448 explicitly scopes its ownership claim to one **local Station data directory / process lifetime** and disclaims distributed filesystems and HA fencing. Its local ownership mechanism must not be credited as closing worker-side concurrent recovery authority in #404.

### Gate disposition

**Classification:** retained reported findings + exact-source corroboration + release-scope decision.

**Verification status:** **BLOCKED** until one of two explicit paths is satisfied.

**EXCLUDE path acceptance:**
- owner explicitly excludes Shared Comms from v1; and
- the exact selected RC/release artifact has an enforceable negative source/release guard proving the Shared Comms runtime/API/capability cannot enter the shipped surface.

**INCLUDE path acceptance:**
- reviewed successor validates receipt type/project/operation/actor/payload binding before ACK;
- stored payload digest is recomputed and compared before any recovery POST;
- one durable/fenced recovery owner is enforced under concurrent recovery;
- isolated negative/concurrency tests demonstrate those properties on the exact admitted source;
- resulting exact RC is freshly qualified.

**Required human action:** explicit D4 INCLUDE or EXCLUDE disposition bound to the selected RC. Source absence today is evidence toward EXCLUDE, not authorization to silently clear the gate.

## RELEASE / master qualification state

Predecessor master head `1eb142be519154ecd6ffecddc9d21dbd25aaf0ae` had exact-head PASS for Qualification-v1, Command Station, controller/provider, clean install, Factory ownership, Control Plane, and measured-evaluation binding. Its maintainer gate remained red for missing exact-head human attestation and it had zero submitted human reviews.

This new documentation commit is a new exact head. **No predecessor CI result transfers.** Inspect the fresh exact-head workflows before any status transition.

No merge, auto-merge, approval, human attestation by this task, candidate/helper mutation, physical F6, canary, private Seal execution, real provider workload, live host/service change, soak, production deployment, tag, or release is performed by this delta.
