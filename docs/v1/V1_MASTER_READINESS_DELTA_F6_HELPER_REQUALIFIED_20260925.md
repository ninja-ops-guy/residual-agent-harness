# V1 closure delta — F6 helper repair requalified, 2026-09-25

Status: append-only review/coordination evidence. No physical F6, merge, canary, deployment, soak, tag, or release is authorized by this file.

## Baseline
- accepted main: `d796f36b75e730a0bab71bdba564206174393719`
- master-ledger parent immediately before this write: `6e54c5047e2b563cfdf3387baef72abde3309483`
- selected AUD-1 candidate: #448 `943c77a28ada1bc3931408c5f9b40d40c25eb2dc`
- helper-hardening successor: #455 `ea6f37eb1d7ff86c4b71668c847be90f47954b76`
- issue #353 remains the controlling AUD-1 gate order.

## PRE-PRODUCTION / AUD-1 F6 helper

| Stable ID | Acceptance criterion | Classification | Source / evidence | Dependencies | Owner | Implementation | Verification status | Required human action |
|---|---|---|---|---|---|---|---|---|
| V1-PP-002-F6-HARDEN | Evidence helper binds candidate/tree/module identity, runner identity, event/history ordering, natural Case-B expiry/reclaim ordering, and stale-result rejection without retaining raw authority material; exact helper head passes technical qualification. | observed repair + exact-head qualification | #455 `ea6f37eb...`; Qualification-v1 `36140455618` PASS; Command Station `36140455752`, controller/provider `36140455637`, clean install `36140455807`, Factory ownership `36140455488`, Control Plane `36140455672`, measured binding `36140455755` PASS | #448; #453 historical helper; issue #353 | existing AUD-1 single writer | #455 | **READY_FOR_REVIEW** | Human review/disposition is still required before any physical use. |
| V1-PP-002-F6-PROBE-CONTRACT | Raw lease appears only in the bounded worker-result request; retained evidence omits raw lease/credential and stores SHA-256 lease fingerprint plus original attempt/owner. | observed repair with regression coverage | source blob `8ea13109f205513bb3ab3a71ad9ee45ff446681d`; test blob `3b91aad6a86118d277eb565e9b2d3310820a11cb`; deterministic qualification PASS | F6-HARDEN | existing AUD-1 single writer | #455 | **VERIFIED** | Preserve bytes; any change requires fresh exact-head qualification. |
| V1-PP-002-F6-AUTH | Physical F6-A/F6-B requires exact-head helper qualification plus a separate human authorization bound to that exact helper head. | authority boundary / missing human evidence | #455 states it does not inherit #453 physical authority; exact-head maintainer workflow `36140492277` is red because human exact-head disposition is absent; submitted PR reviews were zero when observed. | F6-HARDEN | owner | #455 | **BLOCKED** | Review/disposition and a new exact-head physical-F6 authorization are required. |
| V1-PP-002-F6-PHYSICAL | Execute and retain distinct F6-A and F6-B evidence, then provide it to Mason/LEGION for read-only falsification audit. | missing physical evidence | issue #353; #455 exact head `ea6f37eb...` | F6-AUTH plus live operator prerequisites | operator; Mason/LEGION after execution | none | **BLOCKED** | Do not manipulate transport until the exact-head authority gate above is satisfied. |

## Exact-head repair evidence

Historical failing #455 heads remain retained evidence:
- `98819b48...`: deterministic regression failed.
- `3bef25d...`: comment-only attempted repair; deterministic regression still failed.

Current #455 head `ea6f37eb1d7ff86c4b71668c847be90f47954b76` contains the behavioral correction:
- worker-result request sends the original raw lease;
- request excludes evidence-only fingerprint/attempt/owner fields;
- retained record stores lease fingerprint, attempt and owner instead of the raw lease;
- retained record does not contain the worker credential.

Qualification-v1 `36140455618` is PASS on this exact head, including deterministic and aggregate jobs. This evidence is not inherited from #453 or earlier #455 heads.

## Remaining non-green checks

- Maintainer gate: red because exact-head human disposition is absent. This is a governance gate, not a product-test failure.
- PR-Agent `36140455745`: red during advisory model execution due an authentication error; no substantive advisory review was published. It is not independent review or acceptance evidence.

## Readiness movement

The F6 helper moved from **BLOCKED on technical qualification** to **READY_FOR_REVIEW**. Physical F6 remains **BLOCKED** until the human authorization boundary is satisfied for `ea6f37eb...`.

Historical R4.1 17/17 READY_FOR_CANARY remains scoped historical qualification only. No #426 Shared Comms finding, PR-G26/PR-G27/PR-G28 requirement, claims/profile decision, canary, post-canary, RC, soak, or release gate is waived by this delta.
