# RESIDUAL current status

_Current-state check: 2026-09-24 03:45 UTC against `main@d796f36b75e730a0bab71bdba564206174393719`._

This document is a human-readable current-state summary, not a replacement for exact repository bytes, retained artifacts, workflow logs, issue/PR history, or maintainer/protected-byte governance. Historical PASS/FAIL/BLOCKED evidence remains bound to the exact revision, run attempt, and environment that produced it. Git history retains earlier detailed versions of this status document.

## Executive summary

Accepted `main` advanced from `91d32fd8b713c68c1cd2e473013c9e1c33b93572` to **`d796f36b75e730a0bab71bdba564206174393719`** when **#304** (`fix(station): typed fail-closed reviewer findings (#209)`) merged. The accepted change makes reviewer findings typed (`note|warning|blocking`), rejects contradictory approval with blocking findings, requires a blocking finding for rejection, rejects legacy string-only verdicts, and records blocking-finding count. It does not weaken mechanical verification, M4, integration, or release authority.

The exact #304 head `c3fde7b7db3e3dd1cc38fb08789e19e7d84cab90` completed the named repository technical workflows **PASS**, including RESIDUAL Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, PR-Agent, Pages, and the exact-head maintainer approval gate. Fresh push-triggered observations on accepted `main@d796f36...` also show **PASS** for Qualification v1, Controller/provider contracts, Command Station, measured-evaluation binding, and Pages. These observations are exact-revision evidence only.

Release convergence is still **BLOCKED**. AUD-1 issue #353 remains open; the required physical F6-A/F6-B evidence is not established; the independent Mason/LEGION re-audit is outstanding; and the R4.1 ready-for-canary seal has a confirmed semantic cardinality defect that prevents it from serving as canary authorization evidence in its current form.

## R4.1 evidence authority and canary boundary

The prior external R4.1 qualification record remains bounded to its authoritative candidate, evidence bytes, hashes, and gate results. However, the previously propagated statement that the ready-for-canary seal verified `44/44` evidence entries is **invalid seal metadata** and must not be used as an authority claim.

**#415** (`fix(r4): derive seal cardinality from authoritative manifest`) is **OPEN / UNMERGED / UNACCEPTED** at exact head `3da0d8ec45adf8934b88906462706617aa22831f`. Its retained forensic result is:

- the literal value `44` was manually embedded in the first seal-creation patch after `sha256sum -c` verified hashes but did not derive cardinality;
- the authoritative immutable `SHA256SUMS` contains **50** valid non-empty entries;
- there is no demonstrated filter or traversal defect producing an authentic excluded-six set;
- the defect affects derived count metadata and the seal's semantic validity, not the qualified candidate HEAD/tree, authoritative evidence bytes, authoritative SHA-256 values, qualification gate results, or the authoritative manifest itself.

The proposed #415 tooling derives cardinality directly from `SHA256SUMS`, accepts no expected-count argument, rejects malformed/duplicate/unsafe paths, verifies every referenced hash, independently recomputes cardinality during seal verification, and rejects the existing `recorded=44 authoritative=50` mismatch. Exact-head Qualification v1, Controller/provider, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent are **PASS**; Vercel is **PASS**; exact-head maintainer approval is **FAIL / no matching human attestation**.

No corrected seal / Seal v3 exists. The current erroneous seal must not authorize canary execution. Before any new seal or canary authorization review, the direct-source generator/verifier path requires human review and the final seal must pass an independently frozen verifier. Canary execution remains **NOT AUTHORIZED / NOT EXECUTED**.

**#422** (`test(r4): adversarially qualify seal evidence authority`) is a **DRAFT / UNMERGED / UNACCEPTED** stacked candidate at `31dc9c1bf88ee69f417f53c0f4ff5558fc48f645`. Its 11 local manifest/adversarial tests are reported **PASS**, but it explicitly leaves extra-file closure, semantic binding, and provenance-DAG verification as requirements beyond the current cardinality verifier. At this observation, some exact-head hosted workflows are **PASS** while Qualification v1, Command Station, and Controller/provider are still **UNKNOWN/PENDING**. #422 does not repair an existing seal and does not authorize a canary.

Any open candidate documentation that still states `44/44` as authoritative seal cardinality, including the earlier #411 record, is superseded on that point by the #415 root-cause evidence and must not be merged unchanged.

## AUD-1 security convergence

Owner issue **#353 remains OPEN with no milestone** and remains the pre-release security convergence boundary. The original candidate **#399** remains unchanged at `8df77b832b3839ccd2a6944a65760ce3ab10dc9c`, and physical-evidence helper **#403** remains unchanged at `118ec3c795ae11c88b68278717fb781f4b059559`. The two required real-host F6 cases remain **UNKNOWN / not established**; no software fixture or hosted CI run substitutes for them.

A new draft successor exists: **#416** (`fix(station): fence credential revocation and stalled heartbeat authority`) is **DRAFT / OPEN / UNMERGED / UNACCEPTED** at exact head `30c8c640e80a6d59a6db9e3199bf4cba81fb0296`, based on accepted `main@d796f36...`. It preserves #399/#403 rather than silently retargeting them and adds repairs for two newly reproduced schedules:

- **AUD1-C1**: a delayed worker request could authenticate before body read and still be admitted after credential rotation/worker disable;
- **AUD1-C2**: a blocked heartbeat request could prevent the local worker from observing authority loss within the intended grace window.

The #416 PR reports parent probes of **3 FAIL + 1 ERROR** and a repaired focused suite of **12 PASS**; a prior repair head `d291688b...` had 25/25 Qualification-v1 gates PASS, but that result remains bound to those prior bytes. Fresh exact-head `30c8c640...` Qualification v1, Controller/provider, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent are **PASS**. Vercel is **PASS**; exact-head maintainer approval is **FAIL / no matching human attestation**; Pages was **UNKNOWN/PENDING** at this observation.

#416 is not yet the selected release successor. Required sequence remains: independent review and exact-head CI -> deliberate successor selection -> requalify the physical helper for that exact selected target -> separately retain F6-A and F6-B physical evidence -> Mason/LEGION independent read-only re-audit -> exact-head owner attestation -> guarded merge -> authoritative new-main qualification -> final RC recovery/elapsed-soak evidence. No physical execution or helper retarget is claimed here.

## Additional review-only findings

Several new candidate lanes add useful evidence without changing accepted release state. **#423** records a production-readiness matrix and explicitly lacks authoritative production topology, SLO, RPO, and RTO inputs; its receipt-binding item is a **BLOCKING_CANDIDATE_FINDING pending scope review**, not an accepted-main defect classification. **#426** records offline fault-space exploration and labels malformed/cross-bound receipt false ACK, recovery digest mismatch, and unfenced simultaneous recovery as **BLOCKING_CANDIDATE_FINDING** items requiring human scope disposition; real fsync/power-loss, ENOSPC, and process-level fencing fixtures remain absent. Neither candidate executed a canary.

Other R4/R5/research/canary planning PRs remain unmerged and unaccepted. Their local or hosted PASS results do not authorize promotion, deployment, canary execution, or broad production-readiness claims.

## Qualification and trust-boundary discipline

`PASS`, `FAIL`, `UNKNOWN`, and `BLOCKED` remain exact-claim states. A PASS on one revision does not transfer to changed bytes. A candidate finding does not become an accepted defect until its scope and evidence are reviewed. A documented external result does not override contradictory or missing repository-local evidence. Missing physical evidence remains `UNKNOWN / not established` rather than inferred from software tests.

Still **UNKNOWN / not established** by accepted-main hosted PASS results:

- universal/every-host M4 qualification;
- true 24h/72h/30d elapsed soak evidence;
- physical F6-A/F6-B authority-loss reliability;
- Mason/LEGION closure of AUD-1;
- a valid corrected R4.1 seal suitable for authorization review;
- live R4.1 canary success;
- accepted R4.1/R5 Shared Comms implementation on main;
- blanket production readiness.

The accepted Factory/M4 ownership baseline and protected-byte set remain whatever the committed ownership baseline on main records. This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, evidence schemas, provider authority, security implementation, licensing authority, or acceptance authority.

`implementation-status.yaml` remains an implementation-presence manifest, not a release-qualification manifest.

## Documentation scope

This reconciliation changes only `docs/CURRENT_STATUS.md` on the existing dedicated documentation branch. Searches of accepted main found no `44/44` or prior-main-hash claim requiring a new edit in `README.md`, `HARNESS.md`, `START-HERE.md`, or `implementation-status.yaml`, and the accepted #304 reviewer-contract change does not create a contradictory claim in those documents. They are intentionally unchanged in this observation.

Because this status document records qualification anchors, corrected evidence-authority interpretation, ownership-baseline context, active security successors, and other trust-boundary state, the documentation PR must **not** be merged automatically. Exact-head human review/attestation remains required.
