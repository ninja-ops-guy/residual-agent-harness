# RESIDUAL current status

_Observation: 2026-09-24 22:06 UTC. Exact revisions below are snapshots; changed heads require fresh evidence._

This is a status record, not acceptance authority. Historical PASS/FAIL/UNKNOWN/BLOCKED remains bound to the exact revision, run attempt, and environment that produced it.

## Executive summary

Accepted `main` remains **`d796f36b75e730a0bab71bdba564206174393719`**. No newer PR has merged.

Release convergence remains **BLOCKED**. The most meaningful new evidence is the #448 Station-ownership/exposure successor advancing from retained failing head `a873123f0e97441bf8aad30acbe9c223d18089b3` to **`7001bdf68355b7e5288a8cea3f4c827061aca37d`** after reconciling legacy restart/recovery fixtures with the one-live-owner invariant.

The original #446 audit findings remain authoritative for the audited sources: CV-06 process exclusivity **FAIL** on both audited sources; claims-source non-loopback CLI default **FAIL**; AUD-1-source CLI default **PASS**; direct Server-constructor enforcement **FAIL** on both audited sources; and CV-09 Shared Comms recovery/exclusion **BLOCKED**. Those retained FAIL/BLOCKED observations are not erased by later candidate work.

At the new #448 head, the four commits after `a873123f...` modify only test/qualification fixtures: restart paths now explicitly close the prior Station owner before reopen, observation concurrency remains concurrent within one admitted owner before close/reopen, active-workload recovery uses explicit owner handoff, and persistence fault probes close the prior owner before reopen. No ownership/exposure production implementation was weakened.

Fresh exact-head #448 repository workflows are now **PASS** for Qualification v1 **36055071092**, Controller/provider **36055071013**, Command Station **36055070941**, clean install **36055070983**, Factory ownership **36055071115**, measured-evaluation **36055070939**, Control Plane **36055070914**, and Pages **36055071006**. Qualification-v1 macOS lifecycle, Windows lifecycle, deterministic, active-workload, persistence fault-injection, M4, browser, concurrency, red-team, and aggregate jobs also completed successfully. Final qualification artifact **10832271898** has GitHub-reported digest `sha256:f64a9d3b6b8d59a6e2b5e0428830a360232f60c0b426f54943e1c7f36ccd11e9`; workflow metadata reports head SHA `7001bdf...`. PR-Agent is **FAIL**; maintainer approval is **FAIL**; Vercel is **FAIL** from the external deployment-rate limit; submitted human reviews remain **0**.

This is exact-head candidate qualification only. It does not select #448 as AUD-1 authority, close #446's historical findings on accepted sources, retarget #403, establish physical F6-A/F6-B, satisfy Mason/LEGION re-audit, merge the repair, or establish production acceptance.

Since the preceding observation, **#447 changed review posture without changing code**: GitHub draft → ready-for-review completed at 2026-09-24 21:40:32 UTC on unchanged head `ad524c461aa60426695f226f541e172c557b8e98`. Submitted human reviews remain **0**. Review routing is explicitly **BLOCKED** until a named independent human reviewer or authorized human-review team is designated; the coordination comment is not itself a review, approval, verifier selection, or attestation.

## #447 — seal JSON-boundary successor

#447 is **OPEN / READY FOR REVIEW / UNMERGED / UNACCEPTED / NOT HUMAN-REVIEWED** at **`ad524c461aa60426695f226f541e172c557b8e98`**, stacked on #443 exact head `d2c8bb907da0c51f0bd56c9f5cb0114816b93205`. GitHub moved the unchanged head from draft to ready-for-review at **2026-09-24 21:40:32 UTC**.

It rejects duplicate JSON keys, NaN/Infinity constants, non-object roots, malformed legacy parents, and fallback from a present invalid primary metadata block. Local exact-file replay recorded **39 methods PASS, zero skips**. Exact-head hosted workflows remain **PASS** for Qualification v1 **36049403636**, Controller/provider **36049403872**, Command Station **36049404018**, clean install **36049404011**, Factory ownership **36049403837**, measured-evaluation binding **36049403869**, and Control Plane **36049404090**. The original PR-Agent advisory **36049403994** is **FAIL** and a later same-head advisory run **36062969333** is also **FAIL**; no failure cause is inferred here. Current combined status shows maintainer approval **FAIL** at run **36063099352** and Vercel **PASS**. Submitted human reviews remain **0**.

A 21:41 UTC coordination comment requests independent human review but explicitly records that no named independent human recipient is assigned. Therefore **review routing is BLOCKED**, and the request comment must not be counted as a formal review or approval. These results are candidate-scoped only. Full **PR-G26 remains BLOCKED / NOT VERIFIED** pending a named independent human review path, private direct-source semantic/provenance verification, verifier selection/freeze as a separate owner decision, and explicit package-closure policy.

## #448 — Station ownership / exposure successor

#448 is **OPEN / DRAFT / UNMERGED / UNACCEPTED / NOT HUMAN-REVIEWED** at **`7001bdf68355b7e5288a8cea3f4c827061aca37d`**, stacked on #438 exact head `e815f33484352f100e11b8d075bb954a815244cc`.

Its production candidate still proposes exclusive Station data-directory ownership and routes direct Server construction through the existing AUD-1 exposure validator. Predecessor head **`a873123f0e97441bf8aad30acbe9c223d18089b3`** is retained as the first hosted integration failure: Command Station **36050962794 FAIL**, Controller/provider **36050962818 FAIL**, and Qualification v1 **36050962822 FAIL**, with final qualification artifact **10830043598** / `sha256:b54ef839c8541a1559a8b13da2c06a6845f70c9fca61f3db1d7b98a524a5847d`.

Those predecessor failures traced to legacy restart/recovery fixtures constructing a second live `Station` over the same data directory while the prior owner remained alive. The successor does **not** weaken exclusivity. The four commits from `a873123f...` to current head change only:

- `tests/station/test_station.py`
- `tests/modular/test_observations.py`
- `scripts/qualification_active_workload.py`
- `tests/qualification/test_fault_injection.py`

The reconciled fixtures explicitly close the prior owner before reopen while preserving stale-lease, recovery, concurrency, fail/repair/review/integrate/export, and corruption assertions.

Fresh current-head repository evidence is:

- Qualification v1 **36055071092 — PASS**
- Controller/provider **36055071013 — PASS**
- Command Station **36055070941 — PASS**
- clean install **36055070983 — PASS**
- Factory ownership **36055071115 — PASS**
- measured-evaluation **36055070939 — PASS**
- Control Plane **36055070914 — PASS**
- Pages **36055071006 — PASS**
- PR-Agent **36055070906 — FAIL**
- maintainer approval — **FAIL**
- Vercel — **FAIL**, external deployment-rate limit
- submitted human reviews — **0**

Qualification-v1's macOS lifecycle, Windows lifecycle, deterministic, active-workload, fault-injection, M4, browser, concurrency, red-team and aggregate jobs all completed **PASS**. Final qualification artifact **10832271898** has GitHub-reported digest `sha256:f64a9d3b6b8d59a6e2b5e0428830a360232f60c0b426f54943e1c7f36ccd11e9`; workflow metadata reports head SHA **`7001bdf...`**. Artifact metadata was inspected; this observation does not claim an independent archive redownload/re-hash.

Candidate-level software qualification therefore advanced materially from retained **FAIL** at `a873123f...` to exact-head technical **PASS** at `7001bdf...`. The original #446 audited-source findings remain retained history and accepted `main` still lacks this repair. #448 remains unselected and not human-reviewed; it does not establish AUD-1 acceptance, physical F6 evidence, Mason/LEGION closure, or production readiness.

## #446 — exclusions audit

#446 is **OPEN / DRAFT / UNMERGED / UNACCEPTED** at **`c2b124419b5c5a36f96262c742d4ababeccd15a1`**.

The claims-source retained artifact is **10823649834**, GitHub-reported digest `sha256:47b217bba8f8a1fdeba72d54ee7c15c2d4498110b8034812c5de0edb0b753891`. The AUD-1-source artifact is **10824660381**, GitHub-reported digest `sha256:cd1893d8537a17249f90eb8e54431458f5c9850afface94acf25ff6627d7b7da`.

Normal repository workflows on the audit head are **PASS** for Qualification v1 **36034984717**, Controller/provider **36034984606**, Command Station **36034984706**, clean install **36034984593**, Factory ownership **36034984659**, measured-evaluation binding **36034984631**, and Control Plane **36034984705**. PR-Agent is **FAIL**; maintainer approval is **FAIL**; Vercel is externally rate-limited.

Those repository PASS results do not override the custom audit's FAIL/BLOCKED findings.

## #445 — claims contract

#445 advanced from initial proposal `b91f574c...` to exact head **`9eba077817720021174671ba1652b59fb801b670`**.

The changed bytes remove circular RC/release dependencies and define the proposed lifecycle:

`RC_SELECTED -> RC_QUALIFIED -> SOAK_VERIFIED -> RELEASE_AUTHORIZED`.

Exact-head Qualification v1 **36031593391**, Controller/provider **36031593150**, Command Station **36031592973**, clean install **36031593258**, Factory ownership **36031593219**, measured-evaluation **36031593096**, and Control Plane **36031593091** are **PASS**. PR-Agent and maintainer approval are **FAIL**; Vercel is externally rate-limited.

The claims remain **PROPOSED / OWNER-OPERATIONS APPROVAL REQUIRED**. The #446 audit means CV-06 is currently **FAIL**, the claims-source non-loopback CLI default is **FAIL**, direct constructor enforcement is **FAIL**, and CV-09 is **BLOCKED**. No claims approval or RC selection follows.

## #443 — PR-G26 exact-head CI

#443 is **OPEN / READY FOR REVIEW / UNMERGED / UNACCEPTED** at **`d2c8bb907da0c51f0bd56c9f5cb0114816b93205`**. Relative to prior green head `4d70ddc7...`, it adds strict seal-counter integer typing and focused tests. Prior full-green evidence does not transfer.

Current exact-head results:

- Controller/provider **PASS**
- clean install **PASS**
- Factory ownership **PASS**
- measured-evaluation binding **PASS**
- Control Plane **PASS**
- Qualification v1 **FAIL**
- Command Station **FAIL**
- PR-Agent **FAIL**
- maintainer approval **FAIL**
- Vercel **FAIL** from the external rate limit

Qualification v1 run **36032203299** failed in container-smoke after the Ubuntu package service returned a 404 for a required package, so required container evidence was absent. Command Station run **36032203395** failed at the same external Docker package-fetch boundary; its Python 3.11/3.12/3.13 and browser jobs passed. The workflow conclusions remain **FAIL** and are not relabeled PASS.

Full **PR-G26 remains BLOCKED / NOT VERIFIED** pending exact-head qualification closure, independent human review, and private direct-source semantic/provenance verification of the authoritative runtime package and final Seal v2.

## #427 — readiness ledger

#427 is **OPEN / DRAFT / UNMERGED / UNACCEPTED** at **`676cd6af84934762d130ed3f0998bdd2cde3cdda`**, adding the PR443 schema-typing delta.

Controller/provider, clean install, Factory ownership, measured-evaluation binding, and Control Plane are **PASS**. Qualification v1 **36032252908** and Command Station **36032252960** are **FAIL** at the same external Ubuntu package-fetch boundary. PR-Agent and maintainer approval are **FAIL**; Vercel is externally rate-limited.

The ledger is coordination evidence only and does not override newer exact-head findings.

## Unresolved blockers

Release remains **BLOCKED** on human review/selection and accepted-main integration of the now technically green #448 Station ownership/exposure successor; preservation of the retained #446 audited-source FAIL/BLOCKED record; Shared Comms inclusion/exclusion; **#447 / PR-G26 independent-review routing to a named human reviewer**, private semantic/provenance verification, verifier selection/freeze and package-closure policy; full PR-G28 lock/offline-build evidence; owner/operations approval of claims and deployment profile; AUD-1 independent review, exact successor selection, physical F6-A/F6-B and Mason/LEGION re-audit; corrected/private seal verification and canary authorization; exact-RC recovery, incident, elapsed-soak, provenance, and final release authorization.

## Documentation scope

This reconciliation changes only **`docs/CURRENT_STATUS.md`** on the dedicated documentation branch. Accepted main has not changed, so no new accepted-main fact requires an edit to `README.md`, `HARNESS.md`, `START-HERE.md`, or `implementation-status.yaml`.

No protected Factory/M4 implementation, ownership baseline, qualification anchor, protected byte, evidence schema, frozen artifact, seal, canary, deployment, merge, approval, or human attestation is changed or authorized. This documentation must not be auto-merged.
