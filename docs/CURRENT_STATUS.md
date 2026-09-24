# RESIDUAL current status

_Observation: 2026-09-24 20:15 UTC. Exact revisions below are snapshots; changed heads require fresh evidence._

This is a status record, not acceptance authority. Historical PASS/FAIL/UNKNOWN/BLOCKED remains bound to the exact revision, run attempt, and environment that produced it.

## Executive summary

Accepted `main` remains **`d796f36b75e730a0bab71bdba564206174393719`**. No newer PR has merged.

Release convergence remains **BLOCKED**. The most meaningful new evidence is draft **#446**, which executed the proposed v1 enforceable-exclusion audit against exact claims source `9eba077817720021174671ba1652b59fb801b670` and exact AUD-1 source `e815f33484352f100e11b8d075bb954a815244cc`.

Custom audit run **36034977554** retained these claim states:

- CV-06 one-authoritative-Station-per-data-directory: **FAIL** on both audited sources. Two Station processes using the same directory remained live concurrently, so process exclusivity is not established on those entry paths.
- Non-loopback CLI default: claims source **FAIL**; AUD-1 source **PASS**.
- Non-loopback direct Server-constructor default: **FAIL** on both sources at the intercepted bind-policy boundary. The audit did not create a live non-loopback listener.
- CV-09 Shared Comms recovery/exclusion: **BLOCKED** because approved inclusion/exclusion and the selected source are not established.
- Separate-directory and loopback positive controls: **PASS**.

These are bounded audit findings, not release qualification.

## #447 — seal JSON-boundary successor

#447 is **OPEN / DRAFT / UNMERGED / UNACCEPTED / NOT HUMAN-REVIEWED** at **`ad524c461aa60426695f226f541e172c557b8e98`**, stacked on #443 exact head `d2c8bb907da0c51f0bd56c9f5cb0114816b93205`.

It rejects duplicate JSON keys, NaN/Infinity constants, non-object roots, malformed legacy parents, and fallback from a present invalid primary metadata block. Local exact-file replay recorded **39 methods PASS, zero skips**. Fresh exact-head hosted workflows are **PASS** for Qualification v1 **36049403636**, Controller/provider **36049403872**, Command Station **36049404018**, clean install **36049404011**, Factory ownership **36049403837**, measured-evaluation binding **36049403869**, and Control Plane **36049404090**. PR-Agent advisory **36049403994** is **FAIL**; maintainer approval is **FAIL**; Vercel is **PASS**; submitted human reviews remain **0**.

These results are candidate-scoped only. Full **PR-G26 remains BLOCKED / NOT VERIFIED** pending human review, private direct-source semantic/provenance verification, and explicit package-closure policy.

## #448 — Station ownership / exposure successor

#448 is **OPEN / DRAFT / UNMERGED / UNACCEPTED / NOT HUMAN-REVIEWED** at **`a873123f0e97441bf8aad30acbe9c223d18089b3`**, stacked on #438 exact head `e815f33484352f100e11b8d075bb954a815244cc`.

It proposes exclusive Station data-directory ownership and routes direct Server construction through the existing AUD-1 exposure validator. Local focused evidence reports **39 methods PASS, zero skips**, but hosted exact-head CI is mixed: clean install **PASS** **36050962782**, Factory ownership **PASS** **36050962781**, Control Plane **PASS** **36050962770**, measured-evaluation **PASS** **36050962808**, Pages **PASS** **36050962799**; Command Station **FAIL** **36050962794**, Controller/provider **FAIL** **36050962818**, Qualification v1 **FAIL** **36050962822**, and PR-Agent **FAIL** **36050962802**. Maintainer approval is **FAIL**; Vercel is **PASS**; submitted human reviews remain **0**.

The observed Python 3.11 Command Station and Controller/provider failures include existing same-directory restart/concurrency fixtures creating a second live `Station`; the candidate raises `StationOwnershipError: Station data directory is already owned`. Qualification v1 also has multiple failed subjobs. Their workflow conclusions remain **FAIL** and no broader root-cause claim is inferred.

#448 therefore does **not** establish qualified CV-06 closure, supported-platform ownership behavior, or constructor exposure-policy closure. Fresh qualification is required after test/recovery reconciliation that preserves the one-owner invariant.

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

Release remains **BLOCKED** on qualification-clean Station process exclusivity and supported Server exposure enforcement; reconciliation of restart/recovery fixtures without weakening the one-owner invariant; Shared Comms inclusion/exclusion; PR-G26 human review plus private semantic/provenance verification and package-closure policy; full PR-G28 lock/offline-build evidence; owner/operations approval of claims and deployment profile; AUD-1 independent review, exact successor selection, physical F6-A/F6-B and Mason/LEGION re-audit; corrected/private seal verification and canary authorization; exact-RC recovery, incident, elapsed-soak, provenance, and final release authorization.

## Documentation scope

This reconciliation changes only **`docs/CURRENT_STATUS.md`** on the dedicated documentation branch. Accepted main has not changed, so no new accepted-main fact requires an edit to `README.md`, `HARNESS.md`, `START-HERE.md`, or `implementation-status.yaml`.

No protected Factory/M4 implementation, ownership baseline, qualification anchor, protected byte, evidence schema, frozen artifact, seal, canary, deployment, merge, approval, or human attestation is changed or authorized. This documentation must not be auto-merged.
