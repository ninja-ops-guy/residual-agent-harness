# V1 closure delta — F6 evidence-helper hardening, 2026-09-25

Status: append-only review/coordination evidence. No physical F6, merge, canary, deployment, soak, tag, or release authorization is granted by this file.

## Baseline

- accepted main: `d796f36b75e730a0bab71bdba564206174393719`
- master-ledger parent observed immediately before this write: `cb0b8364b58a402f02ea68fd07c98c872e32e02d`
- selected AUD-1 candidate remains #448 `943c77a28ada1bc3931408c5f9b40d40c25eb2dc`
- previously qualified helper #453 remains `e8e1a6702ff3f6a67ef92dd1dce2be4bcc1cf1a2`
- new successor #455 is `98819b48decfc52b95d24b455d9d990402d8da13`, tree `a01b2b59bcf24183c2836bb0ae9a3c1e9fecf011`, based on #453
- issue #353 remains the controlling AUD-1 gate order.

## PRE-PRODUCTION / AUD-1 F6 helper

| Stable ID | Requirement / acceptance criterion | Classification | Source / implementation | Dependencies | Test / evidence | Status | Required human action |
|---|---|---|---|---|---|---|---|
| V1-PP-002-F6-HARDEN | Physical F6 evidence helper must bind candidate/tree/module identity, complete runner identity, event-chain/history ordering, natural Case-B expiry/reclaim ordering, and stale-result rejection without retaining raw authority material. Exact successor must pass normal qualification before use. | observed implementation successor + missing acceptance evidence | #455 `98819b48decfc52b95d24b455d9d990402d8da13`; 9 helper/test files only; #448 product bytes unchanged | #448 selected candidate; #453 helper baseline; issue #353 | Qualification-v1 `36106514544`: deterministic-regression FAIL; aggregate FAIL because deterministic-regression=FAIL. Command Station `36106514511`, clean install `36106514538`, Factory ownership `36106514486`, Control Plane `36106514539`, controller/provider `36106514497`, measured binding `36106514508` PASS. | **BLOCKED** | Existing AUD-1 single writer must repair/replace #455, retain the failure, obtain fresh exact-head qualification, then obtain owner approval and successor-bound F6 authorization. |
| V1-PP-002-F6-PROBE-CONTRACT | Stale-result probe must send the original raw lease in the one bounded worker-result request while retained evidence contains only a SHA-256 lease fingerprint plus original attempt/owner binding; retained artifact must not contain raw lease or worker credential. | observed source/test contradiction on #455 exact head | exact source blob `tools/aud1/f6_stale_result_probe.py@577b270ca8638aaa003cd1b02ab12c2768bb9bc8`; exact test blob `tests/tools/test_aud1_f6_stale_probe.py@3b91aad6a86118d277eb565e9b2d3310820a11cb` | V1-PP-002-F6-HARDEN | Source currently places `lease_fingerprint`, `attempt`, and `owner` in the HTTP request body while omitting raw `lease`; retained record still writes raw `lease` and omits the new fingerprint/attempt/owner fields. The exact-head regression test requires the opposite contract. This is consistent with the exact-head deterministic-regression failure but is not claimed as the only failing test without the retained pytest artifact. | **BLOCKED** | Existing AUD-1 owner repairs the contract without weakening the test; changed bytes require fresh qualification. |
| V1-PP-002-F6-AUTH | F6-A/F6-B may execute only on an exact helper head explicitly authorized after that head qualifies. | authority boundary | #455 PR body explicitly states it does not inherit #453 physical execution authority | V1-PP-002-F6-HARDEN | No submitted PR reviews on #455; Qualification-v1 is red at the current head. | **BLOCKED** | Do not execute F6 using #455. If #455 or a successor becomes green, record a new exact-head owner authorization before physical manipulation. |

## Exact #455 failure evidence

Qualification-v1 run `36106514544` on exact head `98819b48decfc52b95d24b455d9d990402d8da13` produced:

- `deterministic` job `107980166861`: **FAIL** at `Full deterministic regression gate`; evidence result records `deterministic-regression=FAIL`, zero skips, source commit `98819b48...`, tree `a01b2b59...`;
- `aggregate` job `107980946583`: **FAIL** because `deterministic-regression=FAIL`;
- all other Qualification-v1 jobs returned PASS in the inspected run.

The run is therefore a real exact-head regression failure. It is not reclassified as environment-only and predecessor #453 qualification is not inherited.

The published #455 source and test also expose a concrete contract mismatch:

- the probe request currently sends `lease_fingerprint`, `attempt`, and `owner` instead of the original raw `lease`;
- the retained record still stores `lease` directly and does not populate the new fingerprint/attempt/owner fields;
- the new exact-head unit test requires raw lease only in the request and requires retained evidence to omit that raw lease while storing its fingerprint plus attempt/owner.

This finding is evidence for a focused repair in the existing AUD-1 lane. It does not authorize this master-ledger task to edit #455.

## Readiness movement

The previous #453 F6 helper remains historical qualified evidence, but #455 exists specifically to correct evidence-binding defects discovered before physical execution and explicitly does not inherit #453 execution authority. Therefore the physical-F6 gate returns to **BLOCKED on helper qualification + exact-head authorization** until the successor chain is green and authorized.

Historical R4.1 17/17 READY_FOR_CANARY remains scoped historical qualification only. No #426 Shared Comms finding, PR-G26/27/28 requirement, claims/profile decision, canary, post-canary, RC, soak, or release gate is waived by this delta.
