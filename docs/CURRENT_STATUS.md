# RESIDUAL current status

_Observation: 2026-09-25 11:29 UTC. Exact revisions and run IDs below are snapshots; changed heads require fresh evidence._

This document is a status record, not acceptance authority. PASS/FAIL/UNKNOWN/BLOCKED remains bound to the exact revision, run attempt, environment, and retained evidence that produced it.

## Executive summary

Accepted `main` remains **`d796f36b75e730a0bab71bdba564206174393719`**. No newer PR has merged. AUD-1 issue #353 remains **OPEN with no milestone**.

Release convergence remains **BLOCKED**. The current AUD-1 Station/F6 state is:

- #448 remains the selected candidate at exact head **`943c77a28ada1bc3931408c5f9b40d40c25eb2dc`**, tree **`d8112fe34954ae6ed46544d81eeb951f94f9d95c`**.
- #448 exact-head technical qualification remains **PASS** for the named workflows below. PR-Agent is **FAIL**. Maintainer approval and Vercel are **PASS**.
- #453 at **`e8e1a6702ff3f6a67ef92dd1dce2be4bcc1cf1a2`** remains historical qualified-helper evidence with an exact-identity F6 authorization record.
- #455 is the current F6 evidence-hardening successor at exact head **`98819b48decfc52b95d24b455d9d990402d8da13`**, tree **`a01b2b59bcf24183c2836bb0ae9a3c1e9fecf011`**, based on #453. It changes helper/test bytes only; selected #448 product bytes are unchanged.
- #455 Qualification v1 is **FAIL** at run **36106514544** because the `deterministic` job **107980166861** failed at **Full deterministic regression gate**; aggregate **107980946583** also failed. The other inspected Qualification-v1 jobs passed.
- #455 does **not** inherit #453 physical execution authority. Its maintainer-approval status is **FAIL**, PR-Agent is **FAIL**, Vercel is **PASS**, and submitted GitHub review objects are **0**.
- Physical F6-A/F6-B therefore remain **BLOCKED / NOT EXECUTED** pending repair/replacement of #455, fresh exact-head qualification, owner approval, successor-bound authorization, real-host execution, and separately retained evidence.

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

## #455 — current F6 evidence-hardening successor

#455 remains **OPEN / DRAFT / UNMERGED** at exact head **`98819b48decfc52b95d24b455d9d990402d8da13`**, tree **`a01b2b59bcf24183c2836bb0ae9a3c1e9fecf011`**, based on historical helper #453.

Observed exact-head workflow evidence:

- Qualification v1 **36106514544 — FAIL**
  - `deterministic` job **107980166861 — FAIL** at **Full deterministic regression gate**
  - `aggregate` job **107980946583 — FAIL**
  - all other inspected Qualification-v1 jobs — **PASS**
- Controller/provider **36106514497 — PASS**
- Command Station **36106514511 — PASS**
- clean install **36106514538 — PASS**
- Factory ownership **36106514486 — PASS**
- measured-evaluation binding **36106514508 — PASS**
- Control Plane **36106514539 — PASS**
- PR-Agent **36106514499 — FAIL**
- maintainer approval **36106542851 — FAIL**
- Vercel — **PASS**
- submitted GitHub review objects — **0**

The retained master-ledger delta identifies a concrete source/test contract mismatch in the stale-result probe on this exact head, consistent with the deterministic-regression failure, but does not claim that mismatch is the only failing test without the retained pytest artifact.

#455 explicitly does **not** inherit #453 physical F6 authorization. Until a repaired/replacement successor obtains fresh exact-head qualification, owner approval, and exact-successor authorization, physical F6-A/F6-B remain **BLOCKED / NOT EXECUTED**.

#453 remains historical qualified-helper evidence at **`e8e1a6702ff3f6a67ef92dd1dce2be4bcc1cf1a2`**. Its prior authorization record remains bound to those exact helper bytes and does not transfer to #455. #452 is a historical predecessor; #449 remains stale because it is bound to superseded candidate bytes.

## Other release lanes

#447 remains **OPEN / READY FOR REVIEW / UNMERGED** at `ad524c461aa60426695f226f541e172c557b8e98`. Its named technical workflows remain PASS while PR-Agent and maintainer approval remain FAIL. Full PR-G26 remains **BLOCKED / NOT VERIFIED** pending its retained private-verification and closure decisions.

#427 remains **OPEN / DRAFT / UNMERGED** at exact head **`6e54c5047e2b563cfdf3387baef72abde3309483`** and remains coordination evidence rather than release authority. On that exact head, Qualification v1 **36108398001**, Controller/provider **36108397894**, Command Station **36108397924**, clean install **36108397973**, Factory ownership **36108397940**, measured-evaluation binding **36108397931**, and Control Plane **36108397930** are **PASS**; maintainer approval **36108422941** and PR-Agent **36108397974** are **FAIL**. Its retained F6 delta classifies #455 and physical F6 as **BLOCKED**.

#450 and #451 are research/post-v1 work and do not advance v1 release authority.

## Unresolved blockers

Release remains **BLOCKED** on:

- repair/replacement of #455, fresh exact-head qualification, owner approval, and successor-bound F6 authorization;
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

This reconciliation changes only **`docs/CURRENT_STATUS.md`** on the existing dedicated documentation branch created from accepted main.

`README.md`, `HARNESS.md`, `START-HERE.md`, and `implementation-status.yaml` remain unchanged because accepted main has not advanced and the new facts are candidate/helper governance state rather than accepted implementation state.

No protected Factory/M4 implementation, ownership baseline, qualification anchor, protected byte, or evidence schema is changed. This documentation PR must not be auto-merged.
