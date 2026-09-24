# RESIDUAL current status

_Current-state check: 2026-09-24 06:31 UTC against `main@d796f36b75e730a0bab71bdba564206174393719`._

This document is a human-readable current-state summary, not a replacement for exact repository bytes, retained artifacts, workflow logs, issue/PR history, or maintainer/protected-byte governance. Historical PASS/FAIL/BLOCKED evidence remains bound to the exact revision, run attempt, and environment that produced it. Git history retains earlier detailed versions of this status document.

## Executive summary

Accepted `main` remains **`d796f36b75e730a0bab71bdba564206174393719`**, the merge of **#304** (`fix(station): typed fail-closed reviewer findings (#209)`). No newer PR has merged into accepted main during this observation. The accepted reviewer contract uses typed findings (`note|warning|blocking`), rejects contradictory approval with blocking findings, requires a blocking finding for rejection, rejects legacy string-only verdicts, and records blocking-finding count. It does not weaken mechanical verification, M4, integration, or release authority.

The exact #304 head `c3fde7b7db3e3dd1cc38fb08789e19e7d84cab90` completed the named repository technical workflows **PASS**, including RESIDUAL Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, PR-Agent, Pages, and the exact-head maintainer approval gate. Fresh push-triggered observations on accepted `main@d796f36...` also show **PASS** for Qualification v1, Controller/provider contracts, Command Station, measured-evaluation binding, and Pages. These observations are exact-revision evidence only.

Release convergence is still **BLOCKED**. AUD-1 issue #353 remains open; the required physical F6-A/F6-B evidence is not established; the independent Mason/LEGION re-audit is outstanding; the R4.1 seal-cardinality defect still prevents the erroneous seal from serving as authorization evidence; and review-only convergence planning has not authorized a canary, release candidate, deployment, or production acceptance. New #431 has retained an additional AUD-1 result-denial failure schedule (C4) on top of #416 and now proposes a narrow repair, but that repair is unaccepted and still under exact-head CI.

## R4.1 evidence authority and canary boundary

The prior external R4.1 qualification record remains bounded to its authoritative candidate, evidence bytes, hashes, and gate results. However, the previously propagated statement that the ready-for-canary seal verified `44/44` evidence entries is **invalid seal metadata** and must not be used as an authority claim.

**#415** (`fix(r4): derive seal cardinality from authoritative manifest`) is **OPEN / UNMERGED / UNACCEPTED** at exact head `3da0d8ec45adf8934b88906462706617aa22831f`. Its retained forensic result is:

- the literal value `44` was manually embedded in the first seal-creation patch after `sha256sum -c` verified hashes but did not derive cardinality;
- the authoritative immutable `SHA256SUMS` contains **50** valid non-empty entries;
- there is no demonstrated filter or traversal defect producing an authentic excluded-six set;
- the defect affects derived count metadata and the seal's semantic validity, not the qualified candidate HEAD/tree, authoritative evidence bytes, authoritative SHA-256 values, qualification gate results, or the authoritative manifest itself.

The proposed #415 tooling derives cardinality directly from `SHA256SUMS`, accepts no expected-count argument, rejects malformed/duplicate/unsafe paths, verifies every referenced hash, independently recomputes cardinality during seal verification, and rejects the existing `recorded=44 authoritative=50` mismatch. Exact-head Qualification v1, Controller/provider, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent are **PASS**; Vercel is **PASS**; exact-head maintainer approval is **FAIL / no matching human attestation**.

No corrected seal / Seal v3 exists. The current erroneous seal must not authorize canary execution. Before any new seal or canary authorization review, the direct-source generator/verifier path requires human review and the final seal must pass an independently frozen verifier. Canary execution remains **NOT AUTHORIZED / NOT EXECUTED**.

**#422** (`test(r4): adversarially qualify seal evidence authority`) is a **DRAFT / UNMERGED / UNACCEPTED** stacked candidate at `31dc9c1bf88ee69f417f53c0f4ff5558fc48f645`. Its 11 local manifest/adversarial tests are reported **PASS**. Exact-head Qualification v1, Controller/provider, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent are now **PASS**; Vercel is **PASS**; exact-head maintainer approval is **FAIL / no matching human attestation**. #422 explicitly leaves extra-file closure, semantic binding, and provenance-DAG verification as requirements beyond the current cardinality verifier. It does not repair an existing seal and does not authorize a canary.

Any open candidate documentation that still states `44/44` as authoritative seal cardinality, including the earlier #411 record, is superseded on that point by the #415 root-cause evidence and must not be merged unchanged.

## AUD-1 security convergence

Owner issue **#353 remains OPEN with no milestone** and remains the pre-release security convergence boundary. The original candidate **#399** remains unchanged at `8df77b832b3839ccd2a6944a65760ce3ab10dc9c`, and physical-evidence helper **#403** remains unchanged at `118ec3c795ae11c88b68278717fb781f4b059559`. The two required real-host F6 cases remain **UNKNOWN / not established**; no software fixture or hosted CI run substitutes for them.

Draft successor **#416** (`fix(station): fence credential revocation and stalled heartbeat authority`) remains at **`d41a9428e8667963f85526f44a9616be19ca9d7f`**. It is **DRAFT / OPEN / UNMERGED / UNACCEPTED**, based on accepted `main@d796f36...`, and preserves #399/#403 rather than silently retargeting them.

#416 covers three separately retained continuity schedules:

- **AUD1-C1**: a delayed worker request could authenticate before body read and still be admitted after credential rotation/worker disable;
- **AUD1-C2**: a blocked heartbeat request could prevent the local worker from observing authority loss within the intended grace window;
- **AUD1-C3**: a result request could begin while authority was fresh, stall beyond local continuity grace, fail at transport, and then begin a retry without rechecking authority.

The C3 regression was first retained on test-only head `e82aca429812be71efd4590921e22fa703268d32`; its hosted Command Station and Controller/provider failures remain **FAIL** evidence for those exact bytes and were not converted into green by rerunning the unchanged failing head. Current #416 head `d41a9428...` adds a shared monotonic continuity proof through proposal submission so a new retry or generic empty-proposal fallback cannot start after local authority grace has expired.

Fresh exact-head `d41a9428...` Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, PR-Agent, and Pages are **PASS**. Vercel is **PASS**. Exact-head maintainer approval is **FAIL / no matching human attestation**. Prior PASS results on `d291688b...` and `30c8c640...`, and the retained FAIL results on `e82aca42...`, remain historical exact-byte evidence only.

New draft **#431** (`fix(aud1): surrender on explicit result authority denial`) is **DRAFT / OPEN / UNMERGED / UNACCEPTED**, stacked directly on #416. Its retained test-only head **`a980274c6a3d5b3b479a18466a7877d1207476ab`** establishes the additional **AUD1-C4** schedule: an explicit HTTP 403 from `/api/worker/result` was caught by the generic transport retry path because `urllib.error.HTTPError` subclasses `OSError`, allowing a second result attempt and generic empty-proposal fallback instead of immediate surrender. The focused invariant requires HTTP 401/403 authority denial to raise `WorkerAuthorityLost`, with exactly one result attempt and no retry/empty fallback. On that exact retained head, **RESIDUAL Qualification v1 = FAIL**, **Controller/provider contracts = FAIL**, and **Command Station = FAIL**; measured-evaluation binding, clean install, Factory ownership, Control Plane, and PR-Agent are **PASS**; Vercel is **PASS**; maintainer approval is **FAIL / no matching human attestation**. The unchanged failing head was not rerun for green.

#431 has now advanced to repair head **`a9c00474606b2bd5733ae5eef00a52d59b0aa89b`**. The narrow code change classifies result HTTP 401/403 as Station authority loss before the broader transport retry handler, revokes the local continuity proof, raises `WorkerAuthorityLost`, and reuses the same guarded result helper for the generic empty-proposal path. Non-authority transport failures retain the existing bounded retry semantics; C1/C2/C3 completion-barrier and monotonic-grace semantics are otherwise unchanged. On this repair head, measured-evaluation binding, clean install, Factory ownership, Control Plane, and PR-Agent are **PASS**; **Qualification v1, Controller/provider contracts, Command Station, and Pages are UNKNOWN / still running** at this observation. **Vercel = FAIL / external deployment rate limit (`retry in 24 hours`)**, not a demonstrated product-test failure. Exact-head maintainer approval is **FAIL / no matching human attestation**.

#431 does not select a release successor, retarget #403, establish either physical F6 case, or authorize merge/release activity. The earlier #416 PASS results do not transfer to `a9c0047...`; fresh exact-head qualification plus genuine independent human review of C1/C2/C3/C4 and the admitted-operation drain tradeoff remain mandatory.

#416 is not yet the selected release successor. Required sequence remains: genuine independent review of C1/C2/C3/C4 and the completion-barrier semantics -> deliberate successor selection -> requalify the physical helper for that exact selected target -> separately retain F6-A and F6-B physical evidence -> Mason/LEGION independent read-only re-audit -> exact-head owner attestation -> guarded merge -> authoritative new-main qualification -> final RC recovery/elapsed-soak evidence. No physical execution or helper retarget is claimed here.

## Release-readiness convergence ledger

Draft **#427** (`docs(v1): add master release-readiness convergence ledger`) is **DRAFT / OPEN / UNMERGED / UNACCEPTED** at exact head `570b82f05042725f01ab4dc1916a9c13b5d60ea0`. It adds only `docs/v1/V1_MASTER_READINESS.md` and is explicitly review-only planning/coordination. It does not authorize a canary, merge, deployment, physical test, tag, attestation, or production mutation.

The ledger consolidates pre-canary, canary, post-canary, AUD-1, production-qualification, RC/release, R5/post-v1, and research dependencies. It keeps #399/#403/#416 under the existing AUD-1 closure lane, records the #415 50-entry cardinality correction, treats #423/#426 findings as scope decisions rather than silently accepted live defects, and keeps optional research/post-v1 work off the v1 critical path unless separately promoted by verified evidence.

Fresh exact-head #427 Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent are **PASS**. Vercel is **PASS**. Exact-head maintainer approval is **FAIL / no matching human attestation**. These PASS results qualify only #427's exact bytes; they do not convert the ledger into release authorization or establish the underlying physical/canary/production claims it tracks.

The ledger itself does not close existing blockers. Its current dependency model still leaves canary authorization blocked on explicit scope/authority prerequisites, production v1 blocked on AUD-1 physical/independent closure and deployment-scope authority, and final release blocked on exact-RC recovery/soak/provenance plus human release authorization.

## Release-operations candidates

Three new review-only release/convergence candidates are present; none is accepted-main state and none authorizes a canary, release candidate, tag, deployment, or production acceptance.

**#428** (`fix(release): bind v1 receipt to post-convergence RC`) is **DRAFT / OPEN / UNMERGED / UNACCEPTED** at exact head `1bf6097f9c528f8bce7d15947bafbc2d5b58cf43`. It is stacked on the #418 release-operations branch rather than directly on `main`. It preserves the frozen R4.1 identity as `canary_provenance`, separates the eventual release `candidate` as an exact post-convergence RC identity, requires RC/final tags to bind to the selected candidate, and adds a cross-field release-receipt validator plus negative regressions. Exact-head Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent are **PASS**; Vercel is **PASS**; maintainer approval is **FAIL / no matching human attestation**. No RC has been selected and #428 does not repair or authorize the R4.1 seal/canary boundary.

**#429** (`fix(release): align package version metadata`) is **DRAFT / OPEN / UNMERGED / UNACCEPTED** at exact head `9d38d87df9bfa5004d3eb5d7144e60ef1ced56f7`, directly based on `main@d796f36...`. Accepted main currently has a release-metadata mismatch: `pyproject.toml` declares `0.5.0` while `residual.__version__` declares `0.4.0`. #429 proposes only to align `residual.__version__` to `0.5.0` and add a regression requiring those declarations to remain equal. Exact-head Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, PR-Agent, and Pages are **PASS**; Vercel is **PASS**; maintainer approval is **FAIL / no matching human attestation**. This does **not** set `1.0.0`; final v1 version normalization remains a later RC gate.

**#430** (`feat(qualification): add ENV-G01 capability preflight`) is **DRAFT / OPEN / UNMERGED / UNACCEPTED** at exact head `756e540ca64fa953ca389e2d3441f9229d7969de`, directly based on `main@d796f36...`. It adds a stdlib-only machine-readable environment/capability preflight that reports per-capability and overall `PASS | BLOCKED`, fails closed on missing reference/runtime capabilities, and records only an allowlisted environment subset. It explicitly does **not** reinterpret #425's restricted-environment broad-suite failures as product failures or PASS and does not yet change existing Qualification-v1 workflow execution. Exact-head Qualification v1, Controller/provider contracts, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent are **PASS**; Vercel is **PASS**; maintainer approval is **FAIL / no matching human attestation**.

## Additional review-only findings

**#423** records a production-readiness matrix and explicitly lacks authoritative production topology, SLO, RPO, and RTO inputs; its receipt-binding item is a **BLOCKING_CANDIDATE_FINDING pending scope review**, not an accepted-main defect classification. **#426** records offline fault-space exploration and labels malformed/cross-bound receipt false ACK, recovery digest mismatch, and unfenced simultaneous recovery as **BLOCKING_CANDIDATE_FINDING** items requiring human scope disposition; real fsync/power-loss, ENOSPC, and process-level fencing fixtures remain absent. Neither candidate executed a canary.

Other R4/R5/research/canary planning PRs remain unmerged and unaccepted. Their local or hosted PASS results do not authorize promotion, deployment, canary execution, or broad production-readiness claims.

## Qualification and trust-boundary discipline

`PASS`, `FAIL`, `UNKNOWN`, and `BLOCKED` remain exact-claim states. A PASS on one revision does not transfer to changed bytes. A candidate finding does not become an accepted defect until its scope and evidence are reviewed. A documented external result does not override contradictory or missing repository-local evidence. Missing physical evidence remains `UNKNOWN / not established` rather than inferred from software tests.

Still **UNKNOWN / not established** by accepted-main hosted PASS results:

- universal/every-host M4 qualification;
- true 24h/72h/30d elapsed soak evidence;
- physical F6-A/F6-B authority-loss reliability on the selected AUD-1 successor;
- Mason/LEGION closure of AUD-1;
- a valid corrected R4.1 seal suitable for authorization review;
- live R4.1 canary success;
- accepted R4.1/R5 Shared Comms implementation on main;
- an exact post-convergence v1 release candidate with required recovery/soak/provenance evidence;
- blanket production readiness.

The accepted Factory/M4 ownership baseline and protected-byte set remain whatever the committed ownership baseline on main records. This documentation does not modify Factory/M4 implementation or tests, ownership baselines, qualification anchors, protected bytes, evidence schemas, provider authority, security implementation, licensing authority, or acceptance authority.

`implementation-status.yaml` remains an implementation-presence manifest, not a release-qualification manifest.

## Documentation scope

This reconciliation changes only `docs/CURRENT_STATUS.md` on the existing dedicated documentation branch. Accepted-main searches found no `44/44`, superseded #416-head/C4, or release-version claim requiring a new edit in `README.md`, `HARNESS.md`, `START-HERE.md`, or `implementation-status.yaml`; historical/versioned `0.4.0` references elsewhere are not silently rewritten as current release metadata. They are intentionally unchanged in this observation.

Because this status document records qualification anchors, corrected evidence-authority interpretation, ownership-baseline context, active security successors, retained failures/unknowns, and release/canary trust-boundary state, the documentation PR must **not** be merged automatically. Exact-head human review/attestation remains required.
