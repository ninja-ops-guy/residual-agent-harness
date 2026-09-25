# RESIDUAL current status

_Observation: 2026-09-25 04:04 UTC. Exact revisions and run IDs below are snapshots; changed heads require fresh evidence._

This document is a status record, not acceptance authority. PASS/FAIL/UNKNOWN/BLOCKED remains bound to the exact revision, run attempt, environment, and retained evidence that produced it.

## Executive summary

Accepted `main` remains **`d796f36b75e730a0bab71bdba564206174393719`**. No newer PR has merged. AUD-1 issue #353 remains **OPEN with no milestone**.

Release convergence remains **BLOCKED**, but the AUD-1 Station/F6 lane advanced:

- #448 is the selected candidate at exact head **`943c77a28ada1bc3931408c5f9b40d40c25eb2dc`**, tree **`d8112fe34954ae6ed46544d81eeb951f94f9d95c`**.
- #448 exact-head technical qualification is **PASS** for the named workflows below. PR-Agent is **FAIL**. Maintainer approval and Vercel are **PASS**.
- #453 is the current qualified F6 helper successor at exact head **`e8e1a6702ff3f6a67ef92dd1dce2be4bcc1cf1a2`**.
- The owner posted a new exact-identity authorization on #453 at **2026-09-25 02:49:57 UTC** permitting physical F6-A/F6-B evidence collection for selected #448 using exact #453 helper bytes.
- That authorization changes the previous blocker classification: **authorization is now PASS / established for the exact identities named above**.
- Physical F6-A/F6-B themselves remain **BLOCKED / NOT EXECUTED** because the required real-host execution context and retained evidence are still absent.

## #448 — selected AUD-1 Station candidate

#448 remains **OPEN / DRAFT / UNMERGED** at exact head **`943c77a28ada1bc3931408c5f9b40d40c25eb2dc`**.

Exact-head evidence:

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

The current owner record does not claim independent third-party human review. This candidate is selected for the bounded AUD-1 closure path only; it is not merged and does not establish release authority.

## #453 — current F6 helper successor

#453 remains **OPEN / DRAFT / UNMERGED** at exact head **`e8e1a6702ff3f6a67ef92dd1dce2be4bcc1cf1a2`**, parented on historical helper #452.

Its exact-head technical evidence:

- Qualification v1 **36085661604 — PASS**
- Controller/provider **36085661501 — PASS**
- Command Station **36085661508 — PASS**
- clean install **36085661574 — PASS**
- Factory ownership **36085661581 — PASS**
- measured-evaluation binding **36085661671 — PASS**
- Control Plane **36085661546 — PASS**
- PR-Agent **36085661475 — FAIL**
- latest observed maintainer approval **36087876973 — PASS**
- Vercel — **PASS**
- submitted GitHub review objects — **0**

Qualification-v1 final artifact **10843910701** has GitHub-reported digest **`sha256:d8e8e6d454722f09614b33b42b037cb1c09f3d04c9a20802208a83e9d6970ce7`**.

The owner authorization on #453 explicitly binds selected candidate **`943c77a...`** to helper **`e8e1a67...`** for F6-A/F6-B evidence collection. This is **PASS as an authorization record**, but it is not execution evidence and does not change F6-A/F6-B from **BLOCKED / NOT EXECUTED**.

#452 remains historical predecessor evidence. #449 remains stale because it is bound to superseded candidate bytes.

## Other release lanes

#447 remains **OPEN / READY FOR REVIEW / UNMERGED** at `ad524c461aa60426695f226f541e172c557b8e98`. Its named technical workflows remain PASS while PR-Agent and maintainer approval remain FAIL. Full PR-G26 remains **BLOCKED / NOT VERIFIED** pending its retained private-verification and closure decisions.

#427 remains **OPEN / DRAFT / UNMERGED** at exact head **`8df60000b8b148af125114acc6eb25be98d715c5`** and remains coordination evidence rather than release authority.

#450 and #451 are research/post-v1 work and do not advance v1 release authority.

## Unresolved blockers

Release remains **BLOCKED** on:

- real-host F6-A/F6-B execution and separately retained PASS evidence;
- post-F6 read-only independent re-audit / Mason-LEGION closure;
- Shared Comms inclusion/exclusion disposition;
- PR-G26 private semantic/provenance verification and package-closure/verifier decisions;
- PR-G27 transitive-input / SBOM / provenance closure;
- PR-G28 complete lock, offline install/build, and reproducibility evidence;
- owner/operations approval of final claims and deployment profile;
- corrected/private seal verification and any canary authorization;
- accepted-main integration followed by fresh resulting-main qualification;
- exact-RC recovery, incident-response, provenance, and real elapsed-soak evidence;
- explicit final release authorization.

## Documentation scope

This reconciliation changes only **`docs/CURRENT_STATUS.md`** on a dedicated documentation branch created from accepted main.

`README.md`, `HARNESS.md`, `START-HERE.md`, and `implementation-status.yaml` remain unchanged because accepted main has not advanced and the new facts are candidate/helper governance state rather than accepted implementation state.

No protected Factory/M4 implementation, ownership baseline, qualification anchor, protected byte, or evidence schema is changed. This documentation PR must not be auto-merged.
