# RESIDUAL current status

_Observation: 2026-09-25 02:40 UTC. Exact revisions and run IDs below are snapshots; changed heads require fresh evidence._

This document is a status record, not acceptance authority. PASS/FAIL/UNKNOWN/BLOCKED remains bound to the exact revision, run attempt, environment, and retained evidence that produced it.

## Executive summary

Accepted `main` remains **`d796f36b75e730a0bab71bdba564206174393719`**. No newer PR has merged. AUD-1 issue #353 remains **OPEN with no milestone**.

Release convergence remains **BLOCKED**, but the Station-ownership/F6 lane advanced materially:

- #448 is now explicitly selected at exact head **`943c77a28ada1bc3931408c5f9b40d40c25eb2dc`**, tree **`d8112fe34954ae6ed46544d81eeb951f94f9d95c`**.
- The owner posted an exact-head security attestation and immutable-candidate selection for that head. Combined status reports **maintainer-approval PASS** at run **36084522045** and Vercel **PASS**.
- #452 rebound the frozen F6 helper lineage to the selected #448 candidate and qualified successfully, but physical execution stopped at a pre-execution HOLD before transport manipulation.
- #453 is a one-file documentation-only successor to #452 that corrects the stale checkout example in `tools/aud1/README.md`. Its exact-head technical qualification and maintainer gate are PASS, but #452's physical-F6 authorization was bound to #452 helper bytes and does not automatically transfer to #453.

Physical F6-A/F6-B remain **BLOCKED / NOT EXECUTED**.

## #448 — selected AUD-1 Station candidate

#448 remains **OPEN / DRAFT / UNMERGED** at exact head **`943c77a28ada1bc3931408c5f9b40d40c25eb2dc`**, stacked on #438 exact head `e815f33484352f100e11b8d075bb954a815244cc`.

Current exact-head evidence:

- Qualification v1 **36080373837 — PASS**
- Controller/provider **36080373816 — PASS**
- Command Station **36080373820 — PASS**
- clean install **36080373792 — PASS**
- Factory ownership **36080373769 — PASS**
- measured-evaluation binding **36080373856 — PASS**
- Control Plane **36080373844 — PASS**
- Pages **36080373846 — PASS**
- PR-Agent **36080373790 — FAIL**
- maintainer approval **36084522045 — PASS**
- Vercel — **PASS**
- submitted GitHub review objects — **0**

Qualification-v1 final artifact **10841817512** has GitHub-reported digest **`sha256:277d856b605cdea5a6ec5fe6a54a6d5c6512b3cb21e73375bc45f330bb85be4f`**.

The previous `7001bdf...` selection is historical and superseded. The current owner record explicitly states independent third-party human review was **NOT PERFORMED / NOT CLAIMED**; the solo-maintainer compensating-review governance controls this bounded v1 AUD-1 gate. That does not establish physical qualification, integration acceptance, RC qualification, canary authorization, deployment, or release authority.

## #452 / #453 — F6 helper state

### #452

#452 remains **OPEN / DRAFT / UNMERGED** at helper head **`6a4518ebf37ec6f089ec28093d65b0caabc6c619`**, tree **`ca7dbd3ebfb0a8762ae724c8774041652f1faf99`**, derived from frozen #403 head `118ec3c795ae11c88b68278717fb781f4b059559`.

Its named technical workflows are PASS: Qualification v1 **36084678954**, Controller/provider **36084679030**, Command Station **36084679106**, clean install **36084679031**, Factory ownership **36084679049**, measured evaluation **36084678936**, and Control Plane **36084679027**. PR-Agent **36084678886 is FAIL**. Combined status reports **maintainer-approval PASS** at **36085443200** and Vercel **PASS**.

The owner authorized physical F6-A/F6-B evidence collection against exact selected candidate `943c77a...` using exact helper `6a4518e...`. A subsequent pre-execution check recorded **HOLD BEFORE TRANSPORT MANIPULATION** because no live exact-candidate Station, real remote-runner workload, or authenticated tunnel/probe context was identified, and the helper README still contained a stale checkout example. No physical attempt was started.

### #453

#453 is **OPEN / DRAFT / UNMERGED** at exact head **`e8e1a6702ff3f6a67ef92dd1dce2be4bcc1cf1a2`**, parented on #452. Its only changed path is **`tools/aud1/README.md`**, correcting the stale checkout example. No executable helper-semantic file changed.

Fresh exact-head evidence:

- Qualification v1 **36085661604 — PASS**
- Controller/provider **36085661501 — PASS**
- Command Station **36085661508 — PASS**
- clean install **36085661574 — PASS**
- Factory ownership **36085661581 — PASS**
- measured-evaluation binding **36085661671 — PASS**
- Control Plane **36085661546 — PASS**
- PR-Agent **36085661475 — FAIL**
- maintainer approval **36086068695 — PASS**
- Vercel — **PASS**
- submitted GitHub review objects — **0**

Qualification-v1 final artifact **10843910701** has GitHub-reported digest **`sha256:d8e8e6d454722f09614b33b42b037cb1c09f3d04c9a20802208a83e9d6970ce7`**.

Because #453 changes the helper identity named in #452's physical-F6 authorization, that authorization does **not** automatically transfer. A new explicit authorization must bind selected #448 to exact #453 helper bytes, and the real-host preconditions still need to exist. Until then F6-A/F6-B remain **BLOCKED / NOT EXECUTED**.

#449 remains historical/stale because it is bound to withdrawn candidate `7001bdf...`.

## Other release lanes

#447 remains **OPEN / READY FOR REVIEW / UNMERGED** at `ad524c461aa60426695f226f541e172c557b8e98`. Its exact-head technical workflows remain PASS while PR-Agent and the maintainer gate on that head remain FAIL. Full PR-G26 remains **BLOCKED / NOT VERIFIED** pending private semantic/provenance verification and package-closure/verifier decisions.

#427 remains **OPEN / DRAFT / UNMERGED** at exact head **`8df60000b8b148af125114acc6eb25be98d715c5`**. It is coordination evidence only; older append-only deltas naming superseded candidates are historical rather than current F6 authority.

New #450 and #451 are research/post-v1 work and do not change v1 release authority.

## Unresolved blockers

Release remains **BLOCKED** on:

- fresh physical-F6 authorization bound to selected #448 plus exact #453 helper;
- availability of a live exact-candidate Station, real remote-runner workload, and authenticated tunnel/probe context;
- separate retained F6-A and F6-B PASS evidence;
- post-F6 read-only adversarial re-audit / Mason-LEGION closure;
- Shared Comms inclusion/exclusion disposition;
- PR-G26 private semantic/provenance verification and package-closure/verifier decisions;
- PR-G27 transitive-input / SBOM / provenance closure;
- PR-G28 complete lock, offline install/build, and reproducibility evidence;
- owner/operations approval of final claims and deployment profile;
- corrected/private seal verification and any canary authorization;
- accepted-main integration followed by fresh resulting-main qualification;
- exact-RC recovery, incident-response, provenance and real elapsed-soak evidence;
- explicit final release authorization.

## Documentation scope

This reconciliation changes only **`docs/CURRENT_STATUS.md`** on a dedicated documentation branch created from accepted main.

`README.md`, `HARNESS.md`, `START-HERE.md`, and `implementation-status.yaml` are intentionally unchanged because accepted main has not advanced and the new facts are candidate/helper governance state rather than accepted implementation state.

No protected Factory/M4 implementation, ownership baseline, qualification anchor, protected byte, or evidence schema is changed. This documentation PR must not be auto-merged.
