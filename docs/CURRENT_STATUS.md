# RESIDUAL current status

_Observation: 2026-09-25 01:02 UTC. Exact revisions below are snapshots; changed heads require fresh evidence._

This is a status record, not acceptance authority. Historical PASS/FAIL/UNKNOWN/BLOCKED remains bound to the exact revision, run attempt, and environment that produced it.

## Executive summary

Accepted `main` remains **`d796f36b75e730a0bab71bdba564206174393719`**. No newer PR has merged. AUD-1 issue #353 remains **OPEN with no milestone**.

Release convergence remains **BLOCKED**. The most meaningful change since the preceding observation is another #448 head advance that corrects how native Windows evidence is bound to the pull-request head.

**#448:** GitHub now reports live head **`e9f5ba7eaba80a461c0676035a37c578e073f925`**, one commit ahead of previously observed `6a69b1d5bf5fe3c8a89d92b8ae99bc3ebfc05d63`. The new commit changes only `.github/workflows/station.yml`, adding an explicit checkout ref of `${{ github.event.pull_request.head.sha || github.sha }}` to the native Windows ownership job. This closes an evidence-binding ambiguity: the Windows job now checks out the exact PR head instead of relying on GitHub's default pull-request checkout behavior. No Station production implementation, protected Factory/M4 surface, ownership baseline, qualification anchor, or evidence schema changed in this commit.

All named PR-associated workflows on the new head are **PASS**: Qualification v1 **36076825445**, Controller/provider **36076825515**, Command Station **36076825542**, clean install **36076825405**, Factory ownership **36076825544**, measured-evaluation **36076825634**, Control Plane **36076825593**, and Pages **36076825519**. Command Station's native **windows-ownership** job is **PASS** on the explicit PR-head checkout. Qualification-v1's **windows-lifecycle** and **macos-lifecycle** jobs are **PASS**, along with aggregate, concurrency, deterministic, active-workload, fault-injection, M4, browser, and red-team jobs.

Qualification-v1 retained final artifact **10840244051**, GitHub-reported digest **`sha256:89548201f3ead4514b7020ab257efe0e97ef2f40311862d92fb95bd58b5bc16f`**. The qualification artifact names synthetic PR test-merge commit **`8c8908fabdd9da6780d5486ec184ec9036ef3427`**; repository comparison between that commit and exact #448 head `e9f5ba7...` reports **zero file differences**, so the tested merge tree is byte-equivalent to the current candidate tree. This is not an accepted-main merge.

PR-Agent **36076825550 is FAIL**. Current combined status reports Vercel **FAIL** because of the external deployment-rate limit. A current-head maintainer-approval result was **not observed** in the returned workflow/status evidence and remains **UNKNOWN / not established** here. Submitted GitHub human reviews remain **0**.

The prior owner-selected SHA `7001bdf...` remains withdrawn. No renewed owner review/selection bound to `e9f5ba7...` was observed after the latest head change. #448 therefore remains **OPEN / DRAFT / UNMERGED / UNACCEPTED / NOT SELECTED**. Green technical evidence does not authorize helper retargeting, F6, merge, deployment, canary, production use, tag, or release.

**#449:** helper head **`a30212c463ee317ed110600f3d29f319930ca560`** remains unchanged and still binds to withdrawn target `7001bdf...`. Its historical PASS evidence remains valid only for those helper bytes and that obsolete binding. #449 is therefore still **BLOCKED for physical F6 use** until a current #448 SHA is explicitly selected, every helper target pin is reconciled to that exact SHA, and the changed helper receives fresh qualification. F6-A/F6-B remain **PENDING / NOT EXECUTED**.

The original #446 audit findings remain retained evidence for the audited sources. Later candidate PASS results do not rewrite those historical FAIL/BLOCKED observations.
## #447 — seal JSON-boundary successor

#447 is **OPEN / READY FOR REVIEW / UNMERGED / UNACCEPTED / NOT HUMAN-REVIEWED** at **`ad524c461aa60426695f226f541e172c557b8e98`**, stacked on #443 exact head `d2c8bb907da0c51f0bd56c9f5cb0114816b93205`. GitHub moved the unchanged head from draft to ready-for-review at **2026-09-24 21:40:32 UTC**.

It rejects duplicate JSON keys, NaN/Infinity constants, non-object roots, malformed legacy parents, and fallback from a present invalid primary metadata block. Local exact-file replay recorded **39 methods PASS, zero skips**. Exact-head hosted workflows remain **PASS** for Qualification v1 **36049403636**, Controller/provider **36049403872**, Command Station **36049404018**, clean install **36049404011**, Factory ownership **36049403837**, measured-evaluation binding **36049403869**, and Control Plane **36049404090**. The original PR-Agent advisory **36049403994** is **FAIL** and a later same-head advisory run **36062969333** is also **FAIL**; no failure cause is inferred here. Current combined status shows maintainer approval **FAIL** at run **36063099352** and Vercel **PASS**. Submitted human reviews remain **0**.

A 21:41 UTC coordination comment requests independent human review but explicitly records that no named independent human recipient is assigned. Therefore **review routing is BLOCKED**, and the request comment must not be counted as a formal review or approval. These results are candidate-scoped only. Full **PR-G26 remains BLOCKED / NOT VERIFIED** pending a named independent human review path, private direct-source semantic/provenance verification, verifier selection/freeze as a separate owner decision, and explicit package-closure policy.

## #448 — Station ownership / exposure successor

#448 is **OPEN / DRAFT / UNMERGED / UNACCEPTED / NOT SELECTED** at current GitHub head **`e9f5ba7eaba80a461c0676035a37c578e073f925`**, stacked on #438 exact head `e815f33484352f100e11b8d075bb954a815244cc`.

The earlier owner-selected SHA **`7001bdf68355b7e5288a8cea3f4c827061aca37d`** remains **WITHDRAWN from final approval consideration**. The 23:29 UTC security supersession remains controlling over the older selection comments.

Relative to previously observed repaired head `6a69b1d5bf5fe3c8a89d92b8ae99bc3ebfc05d63`, the current head is one commit ahead. Commit `ci(station): bind Windows evidence to PR head` changes only `.github/workflows/station.yml` and adds:

`ref: ${{ github.event.pull_request.head.sha || github.sha }}`

to the native Windows ownership checkout. This is an evidence-binding repair only; no Station production implementation changed in this latest commit.

Current PR-associated technical evidence:

- Qualification v1 **36076825445 — PASS**
- Controller/provider **36076825515 — PASS**
- Command Station **36076825542 — PASS**
- clean install **36076825405 — PASS**
- Factory ownership **36076825544 — PASS**
- measured-evaluation **36076825634 — PASS**
- Control Plane **36076825593 — PASS**
- Pages **36076825519 — PASS**
- PR-Agent **36076825550 — FAIL**
- Vercel — **FAIL**, external deployment-rate limit
- exact-head maintainer-approval result — **UNKNOWN / not observed**
- submitted GitHub human reviews — **0**

Command Station's **windows-ownership** job is **PASS** and, because of the new explicit checkout ref, is bound to exact PR head `e9f5ba7...`. Qualification-v1's **windows-lifecycle** and **macos-lifecycle** jobs are also **PASS**, as are aggregate, concurrency, deterministic, active-workload, fault-injection, M4, browser, and red-team jobs.

Qualification-v1 final artifact **10840244051** has GitHub-reported digest **`sha256:89548201f3ead4514b7020ab257efe0e97ef2f40311862d92fb95bd58b5bc16f`**. Its artifact name uses synthetic PR test-merge commit **`8c8908fabdd9da6780d5486ec184ec9036ef3427`**. A repository compare from exact head `e9f5ba7...` to that test-merge reports **zero changed files**, establishing tree equivalence for this qualification run without implying any merge into accepted main.

This establishes current candidate technical evidence only. It does **not** renew the withdrawn owner selection, establish independent human review, make #449 current, authorize physical F6, merge the successor, or establish production acceptance. A new exact-SHA owner disposition remains required before helper/F6 authority can advance.
## #449 — F6 helper successor bound to withdrawn target

#449 is **OPEN / DRAFT / UNMERGED / UNACCEPTED** at exact head **`a30212c463ee317ed110600f3d29f319930ca560`**, derived from frozen helper #403 exact head `118ec3c795ae11c88b68278717fb781f4b059559`.

Its declared target is:

- selected candidate: **`7001bdf68355b7e5288a8cea3f4c827061aca37d`**
- selected tree: **`6d60dd39d8c3af8d900843eb5661ca974d9a91b5`**

The helper adds fail-closed exact-head/tree/ancestry and closed-world literal validation. Local focused helper tests and reconciliation preflight are recorded PASS, while its broad local suite is explicitly **NOT PASS** because required environment capabilities were unavailable; that unavailable evidence is not converted to PASS.

Exact-head repository workflows are **PASS** for Qualification v1 **36070369120**, Controller/provider **36070369079**, Command Station **36070369156**, clean install **36070369215**, Factory ownership **36070369070**, measured-evaluation **36070369221**, and Control Plane **36070369194**. PR-Agent **36070369181 is FAIL**; maintainer approval is **FAIL**; Vercel is **PASS**; submitted human reviews remain **0**.

However, #448's later security supersession withdrew `7001bdf...` from final approval consideration. Therefore #449's target binding is now **BLOCKED / stale for downstream physical execution**. Its CI PASS proves only the helper bytes bound to that withdrawn target. Before F6-A/F6-B can be authorized, a current #448 exact SHA must be newly selected, the helper must be reconciled to that exact target, and the changed helper must receive fresh exact-head qualification.

Physical F6 execution remains **NO**; F6-A and F6-B remain **PENDING**.

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

#427 is **OPEN / DRAFT / UNMERGED / UNACCEPTED** at **`8df60000b8b148af125114acc6eb25be98d715c5`**.

Relative to the older status snapshot at `676cd6af...`, the ledger is three commits ahead and adds append-only deltas for review routing, the former AUD-1 candidate selection, and the 17:32 readiness reconciliation. Exact-head Qualification v1 **36069611066**, Controller/provider **36069610996**, Command Station **36069611098**, clean install **36069610995**, Factory ownership **36069611107**, measured-evaluation **36069611156**, and Control Plane **36069611080** are **PASS**. PR-Agent **36069611016 is FAIL**; maintainer approval **36069611119 is FAIL**; Vercel is **PASS**.

The ledger's AUD-1 selection delta naming `7001bdf...` is now **historical/superseded** by #448's later security-review withdrawal and current head `6a69b1d...`. The append-only ledger must not be read as current authorization for #449 or physical F6. Later exact-head security evidence controls over the older planning snapshot.

The ledger remains coordination evidence only and does not override newer exact-head findings or authorization boundaries.

## Unresolved blockers

Release remains **BLOCKED** on a renewed exact-SHA owner review/selection of current #448 `e9f5ba7...` after the prior `7001bdf...` selection was withdrawn; replacement/reconciliation of #449's helper binding to that future selected SHA plus fresh helper qualification; physical F6-A/F6-B; Mason/LEGION re-audit; preservation of #446's retained audited-source FAIL/BLOCKED record; Shared Comms inclusion/exclusion; #447 / PR-G26 independent-review routing to a named human reviewer, private semantic/provenance verification, verifier selection/freeze and package-closure policy; full PR-G27 transitive-input/SBOM/provenance closure; full PR-G28 lock/offline-build evidence; owner/operations approval of claims and deployment profile; corrected/private seal verification and canary authorization; accepted-main integration/requalification; exact-RC recovery, incident, elapsed-soak, provenance, and final release authorization.

## Documentation scope

This reconciliation changes only **`docs/CURRENT_STATUS.md`** on the dedicated documentation branch. Accepted main has not changed, so no new accepted-main fact requires an edit to `README.md`, `HARNESS.md`, `START-HERE.md`, or `implementation-status.yaml`.

No protected Factory/M4 implementation, ownership baseline, qualification anchor, protected byte, evidence schema, frozen artifact, seal, canary, deployment, merge, approval, or human attestation is changed or authorized. This documentation must not be auto-merged.
