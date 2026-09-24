# RESIDUAL current status

_Current-state check: 2026-09-24 03:17 UTC against `main@91d32fd8b713c68c1cd2e473013c9e1c33b93572`._

This document is a human-readable current-state summary, not a replacement for exact repository bytes, retained artifacts, workflow logs, issue/PR history, or maintainer/protected-byte governance. Historical PASS/FAIL/BLOCKED evidence remains bound to the exact revision, run attempt, and environment that produced it. Git history retains earlier detailed versions of this status document.

## Executive summary

Accepted `main` remains **`91d32fd8b713c68c1cd2e473013c9e1c33b93572`**. No new commit or merged PR has entered accepted repository state in this observation.

Three new Shared Comms continuity candidates are material:

- **#410** (`spec(r5): extract Shared Comms continuity backlog`) is **OPEN / UNMERGED / UNACCEPTED** at exact head `1c0f6015ca6be160efcf3a4f530f148e015403aa`. It adds one planning-only R5 backlog document and explicitly states that its 14 requirements are `POST_CANARY/R5`, not pre-canary blockers. Hosted exact-head Controller/provider, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent are **PASS**, and Vercel is **PASS**. RESIDUAL Qualification v1 is **FAIL** on that exact head; retained workflow metadata shows multiple qualification-job failures including deterministic, M4-host-capability, Windows lifecycle, and artifact qualification steps, while the lower-level root cause remains **UNKNOWN** from retained metadata. Maintainer approval is **FAIL / no exact-head human attestation**.
- **#411** (`research(r4): document R4 to R4.1 qualification findings`) is **OPEN / UNMERGED / UNACCEPTED** at exact head `1e2592bfc81dfe94d0f39332ebd451862680cab4`. It adds one secondary research record describing an external sealed R4 → R4.1 qualification sequence. The document records R4 as `BLOCKED` at 15/17 gates and records external R4.1 candidate `8701367db6d3202f24b3eb9f4696b0cadf657985` / tree `79bfe6ed1743907065ed44aeb9c460c47527e0c6` as 17/17 with disposition `READY_FOR_CANARY`. Those source artifacts are explicitly external to this repository and are referenced by SHA-256; GitHub does not resolve `8701367d...` as a commit in this repository. Therefore `READY_FOR_CANARY` is a recorded external qualification disposition, not accepted-main state and not an independently re-derived repository claim. Hosted exact-head Controller/provider, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent are **PASS**, Vercel is **PASS**, RESIDUAL Qualification v1 is **FAIL**, and maintainer approval is **FAIL**. The hosted qualification failure does not erase the external R4.1 record, and the external record does not override the hosted PR-head failure; they are separate evidence domains.
- **#412** (`spec(canary): prepare bounded R4.1 continuity canary`) is **OPEN / UNMERGED / UNACCEPTED** at exact head `2bcfc010c48c8d5d8d8b130ea10b3fb1e67583ef`. It adds an inert canary specification/package for the same externally referenced R4.1 candidate. Its specification says **prepared only; execution is not authorized** and requires an independent authorization receipt plus explicit operator GO before one bounded canary operation. Exact-head Qualification v1, Controller/provider, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent are **PASS**; Vercel is **PASS**; maintainer approval is **FAIL / no exact-head human attestation**. No canary execution, deployment, merge, promotion, or production success is established.

AUD-1 release state is unchanged. **#399** remains the exact software candidate at `8df77b832b3839ccd2a6944a65760ce3ab10dc9c`; **#403** remains the exact qualified physical-evidence helper at `118ec3c795ae11c88b68278717fb781f4b059559`. Physical F6-A and F6-B remain **UNKNOWN / not established**, Mason/LEGION's independent read-only re-audit remains outstanding, and **#353 remains OPEN / P0 / BLOCKED at the release level**.

No evidence in this observation authorizes merging #399, #403, #404, #405, #406, #407, #409, #410, #411, #412, or this documentation PR.

## Accepted repository state

**#397** (`fix(webvm): sync standalone workbench before reload`) remains the latest accepted merge. Its exact PR head was `ed60fb135fea32baf603ff45ecb2d0a82b44828e`; GitHub merged it as `main@91d32fd8b713c68c1cd2e473013c9e1c33b93572`.

Retained exact-main observations remain bounded to those bytes: RESIDUAL Qualification v1, repaired-main Pages/browser proof, Controller/provider contracts, Command Station, clean install, M4 qualification prerequisites, and Vercel have retained **PASS** observations. They do not establish every-host M4 qualification, true elapsed soak, physical-device reliability, successful live-provider semantics, closure of AUD-1, or blanket production readiness.

## AUD-1 security convergence

Owner issue **#353 remains OPEN / P0 / BLOCKED at the release level**. Focused candidate **#399** remains open and unmerged at exact head `8df77b832b3839ccd2a6944a65760ce3ab10dc9c`.

Current software evidence for #399 remains hosted **PASS** for the named software gates, but the required physical authority-loss stage is not complete. Physical execution is permitted only with exact helper **#403@118ec3c795ae11c88b68278717fb781f4b059559** against unchanged #399 bytes.

Required physical outputs remain separate:

1. `F6-A-inside-window` — prove the same runner process/owner/lease resumes when transport is restored inside the 180-second worker grace without duplicate authority or invalid transition.
2. `F6-B-outside-window` — after natural surrender/expiry/reassignment, prove the old process remains dead and an exact old project/task/lease result is rejected with the expected bounded denial after host reachability returns.

Until both independently frozen bundles exist and machine-validate, both claims remain **UNKNOWN / not established**. Mason/LEGION's independent read-only F1/F2/F3/F4/F6 re-audit still follows those physical observations. No current status changes #399 candidate bytes, #403 helper bytes, or that sequence.

## Shared Comms / continuity candidates

### #400 — OpenClaw Shared Comms bridge

**#400** remains **DRAFT / UNMERGED / UNACCEPTED** at exact head `c0c1f2cbd4677e0bc8fd2f710b40f3608db9cda7`. Its own PR boundary remains controlling: accepted main does not yet contain the server-side Shared Comms contract it expects, so that dependency remains **BLOCKED** for accepted-main use.

### #404 — SPEC-SC-MESH-001 durable mesh foundation

**#404** remains **DRAFT / UNMERGED / UNACCEPTED / NOT MERGE-READY** at exact head `cae9ab31e0ca3acfd948af32726db388c589aeb2`. Its retained exact-head state remains mixed: Control Plane, Factory ownership, measured-evaluation binding, clean install, PR-Agent, Pages/browser proof, and Vercel are retained **PASS**; Factory runtime evidence, Qualification v1, Controller/provider contracts, and Command Station have retained **FAIL** observations. Lower-level causes not established by retained metadata remain **UNKNOWN**. No `MESH_QUALIFIED` or multi-host production claim exists.

### #410 — R5 Shared Comms continuity backlog

**#410** is planning-only. It adds `docs/research/R5_SHARED_COMMS_CONTINUITY_BACKLOG.md`, references the externally supplied R4.1 disposition, and defines 14 post-canary requirements covering fenced recovery ownership, authenticated/request-bound receipts, durable reconciliation states, malformed-receipt handling, crash-safe ACK persistence, corruption and storage failures, stale-operation policy, multi-process/multi-host recovery, observability, protocol negotiation, distributed lookup, receipt retention/GC, and formal at-most-once claim boundaries.

Its own stated disposition is that there are **no BLOCKING** or `SHOULD_FIX_BEFORE_CANARY` findings for the already-qualified external R4.1 boundary; all backlog items are `POST_CANARY/R5`. That statement is a candidate planning conclusion, not accepted release authority. Exact-head hosted Qualification v1 is **FAIL** while the other named technical workflows are **PASS**; do not infer merge-readiness from the green subset.

### #411 — R4 → R4.1 qualification findings

**#411** adds `docs/research/R4_R4.1_QUALIFICATION_FINDINGS.md`. It preserves two distinct findings from an external qualification program:

- `R4-F01`: G11 was classified as a qualification-instrumentation defect caused by reading a stale task snapshot rather than authoritative Station state.
- `R4-F02`: G13 was classified as a candidate protocol defect because, after remote commit + ACK loss + sender restart, the sender performed a retransmission before authoritative receipt reconciliation even though receiver idempotency kept the receiver event count at one.

The secondary record says R4.1 changed restart recovery to perform authoritative receipt lookup before retransmission, then recorded 17/17 gates and `READY_FOR_CANARY`. The record also explicitly states that canary execution did **not** occur, the result is bounded to the recorded conditions, and no novelty claim is made without literature review.

The authoritative R4/R4.1 runtime artifacts and ready-for-canary seal are not copied into this repository; #411 references them by run identity and SHA-256. GitHub cannot resolve the cited R4.1 candidate commit in this repository. Treat the record as a documented external evidence handoff, not accepted-main code or a repository-local reproducibility result.

Hosted PR-head state for #411 is mixed: the named non-aggregate technical workflows are **PASS**, Vercel is **PASS**, RESIDUAL Qualification v1 is **FAIL**, and maintainer approval is **FAIL**. Do not rewrite either the external 17/17 record or the hosted failure into the other.

### #412 — bounded R4.1 continuity canary package

**#412** adds `canary/R4.1/` with a specification, manifest, preflight, runner, evidence collection, rollback, verification, helper library, self-test, and README. The package is explicitly inert by default.

The canary specification requires exact candidate/seal identity, a clean candidate worktree with no remotes, expected protected-service state, an independently approved authorization receipt, a safe new evidence destination, a deployment-specific adapter, and explicit `RESIDUAL_R4_CANARY_GO=R4.1-CANARY-8701367D`. Its intended operation is exactly one Shared Comms canary action with induced sender interruption after remote commit and before local ACK, followed by receipt-first reconciliation. It forbids deployment, merge, promotion, push, credential mutation, protected-service restart, and writes outside the designated scope.

Machine-verifiable success would require exactly one initial POST, then a receipt GET after restart with no retransmission POST, durable `PENDING -> SENT_INDETERMINATE -> ACKED`, exactly one receiver event, stable protected services, complete hashed evidence, zero safety counters, and no abort condition. None of those live canary conditions has been executed or established by this PR.

Hosted exact-head evidence for #412 is currently:

- RESIDUAL Qualification v1: **PASS**
- Controller/provider contracts: **PASS**
- Command Station checks: **PASS**
- clean-install qualification: **PASS**
- Factory ownership: **PASS**
- measured-evaluation acceptance binding: **PASS**
- Control Plane: **PASS**
- PR-Agent advisory: **PASS**
- Vercel: **PASS**
- exact-head maintainer approval: **FAIL / no matching human attestation**

These results qualify only the repository package on `2bcfc010...`. They do not authorize or prove the external R4.1 canary.

## Research-maintenance candidates

**#401** remains an append-only AX-21 research-maintenance candidate on the SLM research branch. It does not authorize training, freeze SLM-00, close AUD-1, or advance release status.

**#402** remains **DRAFT / UNMERGED / UNACCEPTED** at `2958ef726cab4deaaa997c0bf4b426a74349213e`. It adds measured R0-R5 apparatus and preregistration only; no confirmatory live H1 result exists.

**#405** remains **DRAFT / UNMERGED / UNACCEPTED** at `2549bb1b81f6bdc6954896eb7ebedadfe82b2722`. It records the 2026-09-22 AX-21 check-in without closing AUD-1, qualifying mesh, claiming measured R0-R5 effects, or finally freezing AX-21.

**#409** remains **DRAFT / UNMERGED / UNACCEPTED** at `9c0f8589b1dc83061ba018207f7bbde88f03ed06`. It records the 2026-09-23 AX-21 check-in while preserving physical-F6, inference, APF, P5, and baseline-freeze boundaries.

## Post-v1 design candidates

**#406** remains **DRAFT / POST-v1 / NO IMPLEMENTATION AUTHORIZED** at `c749e06afa5d86b05f894b9deb45434ce0efefda`. It specifies inference-aware routing/serving capabilities but adds no runtime implementation and establishes no performance benefit.

**#407** remains **DRAFT / POST-v1 / EXECUTION-DEFERRED** at `b15aa2aff58ee31391976e7d4cb89cf0f346a7ec`. It registers RRI-005 / SPEC-APF-001 as a future Agent Privilege Firewall research program. It is not an implemented or demonstrated security result.

## Qualification and trust-boundary discipline

Qualification v1 remains accepted implementation on main, but every PASS/FAIL is exact-revision evidence only. Missing, superseded, externally referenced, or pending evidence does not inherit another revision's status.

Still **UNKNOWN / not established** by accepted-main hosted PASS results:

- universal/every-host M4 qualification;
- true 24h/72h/30d elapsed soak evidence;
- successful live-provider candidate→verifier→receipt semantics;
- physical-device reliability;
- closure of AUD-1 #353;
- live R4.1 canary success;
- accepted R4.1/R5 Shared Comms implementation on main;
- SLM-00 human freeze/training authority;
- #404 mesh qualification or multi-host production readiness.

The accepted Factory/M4 ownership baseline and protected-byte set remain whatever the committed ownership baseline on main records. This documentation does not modify protected Factory/M4 implementation or tests, ownership baselines, qualification anchors, verifier/evidence schemas, provider authority, security implementation, licensing authority, or acceptance authority.

`implementation-status.yaml` remains an implementation-presence manifest, not a release-qualification manifest. It is intentionally unchanged.

## Documentation scope

This reconciliation changes only `docs/CURRENT_STATUS.md` on the existing dedicated docs branch. The open documentation PR continues to carry earlier `README.md` and `HARNESS.md` reconciliation; neither requires another edit because accepted-main product/operator behavior did not change. `START-HERE.md` remains accurate operator guidance. `implementation-status.yaml` remains accurate for its declared implementation-presence purpose.

The immediately preceding docs head `5a4a628fb33fb3399e45fbfbddf0003d1e1b21e6` completed exact-head Qualification v1, Controller/provider, Command Station, clean install, Factory ownership, measured-evaluation binding, Control Plane, and PR-Agent **PASS**; Vercel was **PASS**; maintainer approval was **FAIL / no matching human attestation**. Those results remain bound to `5a4a628f...` and are not inherited by this changed documentation head.

Because this status document records ownership-baseline context, qualification anchors, retained failures, external evidence boundaries, and active security/canary trust-boundary state, this documentation PR must **not** be merged automatically. Exact-head human review/attestation remains required.