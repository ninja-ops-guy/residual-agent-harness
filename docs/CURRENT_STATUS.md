# RESIDUAL current status

_Observation: 2026-09-25 13:48 UTC. Exact revisions and run IDs below are snapshots; changed heads require fresh evidence._

This document is a status record, not acceptance authority. PASS/FAIL/UNKNOWN/BLOCKED remains bound to the exact revision, run attempt, environment, and retained evidence that produced it.

## Executive summary

Accepted `main` remains **`d796f36b75e730a0bab71bdba564206174393719`**. No newer PR has merged. AUD-1 issue #353 remains **OPEN with no milestone**.

Release convergence remains **BLOCKED**. The current AUD-1 Station/F6 state is:

- #448 remains the selected candidate at exact head **`943c77a28ada1bc3931408c5f9b40d40c25eb2dc`**, tree **`d8112fe34954ae6ed46544d81eeb951f94f9d95c`**.
- #448 exact-head technical qualification remains **PASS** for the named workflows below. PR-Agent is **FAIL**. Maintainer approval and Vercel are **PASS**.
- #453 at **`e8e1a6702ff3f6a67ef92dd1dce2be4bcc1cf1a2`** remains historical qualified-helper evidence with an exact-identity F6 authorization record.
- #455 is the current F6 evidence-hardening successor at exact head **`72e934c96d9d34373cb6f4a012ee1a4c9df4ad5f`**, tree **`287e89442085a3d347ebf5a2ae0662b685031e9b`**, based on #453. Relative to the previously observed `3bef25d...` head, six additional commits modify only F6 helper/test files; selected #448 product bytes are unchanged.
- #455 exact-head Qualification v1 is now **PASS** at run **36142877196**, including deterministic and aggregate jobs. Controller/provider, Command Station, clean install, Factory ownership, measured-evaluation binding, and Control Plane are also **PASS** on this exact head.
- #455 maintainer approval is **FAIL** at **36142906854**, PR-Agent is **FAIL** at **36142880790**, Vercel is **PASS**, and submitted GitHub review objects are **0**.
- #455 explicitly does **not** inherit #453 physical execution authority. Physical F6-A/F6-B therefore remain **BLOCKED / NOT EXECUTED** pending exact-head human review/disposition and successor-bound authorization, followed by real-host execution and separately retained evidence.

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

#455 remains **OPEN / DRAFT / UNMERGED** at exact head **`72e934c96d9d34373cb6f4a012ee1a4c9df4ad5f`**, tree **`287e89442085a3d347ebf5a2ae0662b685031e9b`**, based on historical helper #453.

The six commits after previously observed head `3bef25d544011f2283da80d1939bda843fe1a3f1` change only:

- `tools/aud1/f6_stale_result_probe.py`
- `tools/aud1/f6_case_guard.py`
- `tests/tools/test_aud1_f6_stale_probe.py`
- `tests/tools/test_aud1_f6_guard.py`

The changes separate the live raw-lease request from retained evidence, redact request secrets from retained response excerpts, add scope/lease-deadline bindings, add negative regression coverage, and correct the lease-expiry negative fixture. This is helper/evidence-hardening scope; it does not modify selected #448 product bytes.

Observed exact-head workflow evidence:

- Qualification v1 **36142877196 — PASS**
  - `deterministic` job **108096720744 — PASS**
  - `aggregate` job **108097740100 — PASS**
- Controller/provider **36142877246 — PASS**
- Command Station **36142880398 — PASS**
- clean install **36142877322 — PASS**
- Factory ownership **36142877148 — PASS**
- measured-evaluation binding **36142892605 — PASS**
- Control Plane **36142877230 — PASS**
- PR-Agent **36142880790 — FAIL**
- maintainer approval **36142906854 — FAIL**
- Vercel — **PASS**
- submitted GitHub review objects — **0**

Qualification-v1 final artifact **10867363132** has GitHub-reported digest **`sha256:96b57aa786de6a891531376ab26dfc3ef1600c5b5cb8e1ecb4248ec601dd81bf`**. The deterministic artifact **10868341286** has GitHub-reported digest **`sha256:3beafca84be5615d7d03ad5217ea6f3716b5b563d94d1b916be9a05d944699ca`**. Artifact metadata was inspected; these statements do not claim an independent redownload/re-hash.

The earlier failing #455 heads remain retained evidence rather than being overwritten by this PASS. The master readiness ledger records a technically requalified predecessor head `ea6f37eb...`; the later exact head above has its own fresh PASS evidence and must not inherit human authorization from that predecessor.

#455 explicitly does **not** inherit #453 physical F6 authorization. Until this exact head obtains human review/disposition and exact-successor authorization, physical F6-A/F6-B remain **BLOCKED / NOT EXECUTED**.

#453 remains historical qualified-helper evidence at **`e8e1a6702ff3f6a67ef92dd1dce2be4bcc1cf1a2`**. Its prior authorization record remains bound to those exact helper bytes and does not transfer to #455. #452 is a historical predecessor; #449 remains stale because it is bound to superseded candidate bytes.

## Other release lanes

#447 remains **OPEN / READY FOR REVIEW / UNMERGED** at `ad524c461aa60426695f226f541e172c557b8e98`. Its named technical workflows remain PASS while PR-Agent and maintainer approval remain FAIL. Full PR-G26 remains **BLOCKED / NOT VERIFIED** pending its retained private-verification and closure decisions.

#427 remains **OPEN / DRAFT / UNMERGED** at exact head **`d9985f16e887ec160f019ac17f3e2c27ef196ab3`** and remains coordination evidence rather than release authority. On that exact head, Qualification v1 **36142124490**, Controller/provider **36142124433**, Command Station **36142124387**, clean install **36142124509**, Factory ownership **36142124364**, measured-evaluation binding **36142124854**, and Control Plane **36142124357** are **PASS**; maintainer approval **36142124461** and PR-Agent **36142124503** are **FAIL**.

Its newest append-only delta records #455 predecessor `ea6f37eb...` as technically requalified and keeps physical F6 **BLOCKED** pending human authorization. Because #455 has since advanced to `72e934c...`, that delta is historical evidence, not current-head authorization.

#450 and #451 are research/post-v1 work and do not advance v1 release authority.

## Unresolved blockers

Release remains **BLOCKED** on:

- exact-head human review/disposition and successor-bound physical-F6 authorization for #455 `72e934c...`;
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

This reconciliation changes only documentation on the existing dedicated documentation branch:

- **`docs/CURRENT_STATUS.md`** — current #455/#427 identities, exact-head qualification evidence, and blocker state;
- **`README.md`** — removes a materially stale `main@4608afa...` snapshot and delegates volatile release evidence to this status record;
- **`HARNESS.md`** — removes the same stale repository-boundary snapshot and preserves exact-head claim discipline.

`START-HERE.md` and `implementation-status.yaml` remain unchanged. The latter remains an implementation-presence manifest, not release qualification evidence.

No protected Factory/M4 implementation, ownership baseline, qualification anchor, protected byte, or evidence schema is changed. This documentation PR must not be auto-merged.
