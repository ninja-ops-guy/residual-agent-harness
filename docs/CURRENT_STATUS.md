# RESIDUAL current status

_Current-state check: 2026-09-15 against merged `main` at `9d88195a6329151197b53c05c6cbb5a74167f08f` and the active qualification candidate where explicitly named._

This page is the human-readable current-state summary for RESIDUAL. Exact code, exact-tree tests and retained machine-readable evidence remain more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The platform spans requirement compilation, bounded worker execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability and operator-facing surfaces.

The central systems hypothesis remains:

> AI reliability does not necessarily require making individual models reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.

The repository contains substantial implementation and development evidence for the mechanisms required to test that hypothesis. It does **not** yet claim that the hypothesis has been proven on live heterogeneous model workloads, that PR #109's protected-byte candidate has been accepted into `main`, that the current Pages/WebVM hardening has established an acceptable long-run failure rate, or that production soak targets have been met.

## What changed on 2026-09-15

Five changes materially advanced or narrowed the integrated qualification state:

1. **PR #108 landed on `main` as `0430f2fa2d107fe48d26ae84a3c1550af029cb52`.** It carries the deterministic sandbox-timing and termination repair: lease tri-state semantics, a single wall-clock deadline owner, bounded lease-read contention, pending-reap ownership/recovery, typed timeout outcomes and receipt-v2 compatibility preservation. The merge explicitly retained namespace-dependent skips as **non-qualification** rather than treating them as passes.
2. **PR #122 advanced `main` to `bc8b783d8d01b343f870cae704fe7b63c6ea6c0d`.** It hardens the Mission Control real-provider experience with truthful failure categories, selected-model validation, a bounded browser/guest mailbox path, guided authorization state, blocked-build conversation behavior and real-browser acceptance coverage. These product/demo changes do not grant generated artifacts M4 authority.
3. **PR #121 advanced `main` to `1a52e9a2dfc9ea9a9d24579bb9b44548c483f0b9`.** It changes only the protected ownership manifest's provenance metadata: `pinned_at` names the accepted #108 squash commit `0430f2fa...`; all 38 protected path-to-blob pins are unchanged. This records accepted source identity and does not add namespace, production, soak or research qualification.
4. **PR #124 advanced `main` to `9d88195a6329151197b53c05c6cbb5a74167f08f`.** It addresses the retained production WebVM delivery failure in which one immutable ext2 chunk returned HTTP 503 and the guest subsequently aborted. The merged change adds a narrowly scoped service-worker retry for same-origin `GET` requests matching only immutable `residual-demo-<sha>.ext2.c<chunk>.txt` resources, with bounded retry/backoff and no retry expansion to provider calls, cross-origin traffic, ordinary assets or 4xx responses. This is delivery hardening, not evidence that WebVM reliability is solved.
5. **PR #109 is refreshed onto current main and has a new exact-candidate PASS, but remains intentionally blocked.** Head `fb99d5896b23b91e3903965a8c56813412533d48`, synthetic merge `d43db468ee1075bb0f2612ef75575afa0ac01d5f`, tree `ed2d089f21273ec1e305d5ab432d554092267343`, includes accepted main `9d88195a...`. Its Ubuntu 22.04 M4 job passed all 12 capability probes, actual `linux-userns-isolated-v1` execution, and 142 cases plus 84 subtests with **zero skips**. It also repairs the artifact exporter to require exactly six unique members and cap declared uncompressed size. The same candidate changes one protected lifecycle test; ownership correctly fails closed until genuinely independent authorization and deliberate baseline advancement.

Issue #63 is closed: the accepted-tree, filesystem/link, verifier-isolation and Git-evidence defects that it tracked are no longer the active M4 implementation blocker. Issue #48 is also closed: the implementation-status manifest has been reconciled with the merged Factory/evaluation tree.

## Current implementation map

| Area | Current state | Evidence / qualification boundary |
| --- | --- | --- |
| Core harness | Implemented | Goal contracts, verifier-defined acceptance, brakes, residual delegation, receipts, cache binding, trace/audit surfaces and provider routing are covered by the repository test corpus. |
| Command Station | Implemented research/operations surface | Self-hosted run control, model/provider management, observations, HITL hooks, evidence download and operational UI are present. Deployment-specific production readiness remains environment-dependent. |
| Mission Control / WebVM | Implemented product/demo surface | Multi-turn artifact conversations, verified parent lineage, isolated preview, browser-local restoration and optional-provider transport exist. PR #122 adds typed provider failures and real-browser acceptance; PR #124 adds bounded recovery for transient same-origin immutable disk-chunk failures. Issue #120 remains the operational reliability tracker. |
| Factory M2 — worker contract/runtime | Implemented | Real `WorkerContract`, bounded worker runtime, isolated worktrees, journaled observations, host-owned termination and sandbox enforcement exist under `residual/factory/`. |
| Factory M3 — evidence bus/receipts | Implemented | Station-issued receipts, artifact binding, evidence-bus handoff and signature/integrity checks exist. Trust is enforced at the trusted consumption/admission boundary, not merely because bytes were stored. |
| Factory M4 — deterministic integration/scheduler | Implemented trust-boundary mechanisms; **capable-runner PASS exists for PR #109 candidate, protected acceptance blocked** | #63 implementation gaps and #108 timing/termination repair are merged. PR #109's exact candidate passed real namespace probes, actual isolated execution and the zero-skip M4 suite, but one protected lifecycle-test blob changed and remains deliberately rejected by ownership until independently reviewed and pinned. Main has since advanced, so a later combined candidate requires fresh qualification. |
| Evaluation | Implemented development/research apparatus | Hash-locked workloads, repeated runs, ablations, reporting, statistics, fault injection and measured Factory hooks exist. The measured-evaluation acceptance-binding workflow is a CI mechanism; it is not live research evidence. |
| Sandbox / red team | Implemented development surface | Namespace/rlimit/bubblewrap paths and adversarial tests exist. Host capability determines whether specific kernel isolation paths can actually be qualified. |
| Cluster / distributed execution | Implemented development surface | Versioned wire schema, authenticated join/leave, heartbeats, task reassignment, local-first routing and cluster CLI exist. Distributed/host-loss guarantees remain narrower than single-process fixture behavior. |
| Lifecycle / gateway | Implemented | Deny-by-default side-effect gateway, lifecycle glue and deterministic resume/recovery mechanisms exist. Release/recovery qualification remains downstream of the active trust gate. |
| Hardening / observability | Implemented development surface | KMS abstraction, backup/rotation, connector conformance, SLO/alert plumbing, trace↔receipt correlation, metrics and async I/O are present. |
| Research / reproducibility | Active | The working paper, controlled-evaluation framework, claim/evidence discipline and fault-containment tooling are in place. Live R0–R5 measurements and soak remain future evidence gates. |

## Exact-tree CI status at this refresh

### Accepted `main`

Current `main` is `9d88195a6329151197b53c05c6cbb5a74167f08f`, the merge of PR #124.

The exact-main push workflows on this revision are green. Pages/WebVM run `35016468585` completed successfully: its artifact build/browser proof passed, deployment passed, and the published WebVM completed both desktop and narrow-Chromium live acceptance. This clears the post-#124 deployment gate for that exact revision; it does not establish an empirical production failure rate.

The failure that motivated #124 remains retained evidence. On deployed revision `bc8b783...`, Pages/WebVM run `35003867644` failed its first narrow-Chromium live attempt after an immutable WebVM disk chunk returned HTTP 503 and the guest aborted/stalled; the unchanged rerun later passed. Failed-attempt artifact `10410904479` has ZIP SHA-256 `57ab059987126acbc4baf3b0b4b10bc7f3412fa8c38322c756fbd1b4b13564a5`; successful-attempt artifact `10411624041` has ZIP SHA-256 `0cbfe28cc0cd1e94d4cde603ad4452b9834a6a6f6f14e41c4ec32565ffc25386`.

PR #124 changes the product path instead of merely relying on reruns: only matching same-origin immutable disk-chunk fetches receive bounded retries. The exact-main deployment confirms the hardened path can complete the required acceptance flow, but it does not establish a recurrence rate or production soak result.

Issue #120 remains open because repeated intermittent failures on the live WebVM surface are a production-reliability concern. The separate Vercel commit status may still be red from external account/deployment-capacity limits; that is not a repository-test pass or failure. None of these outcomes constitutes namespace qualification of merged main, production soak, live-provider research evidence or blanket production readiness.

### Active PR #109 qualification candidate

Current PR #109 head is `fb99d5896b23b91e3903965a8c56813412533d48`; GitHub tested synthetic merge `d43db468ee1075bb0f2612ef75575afa0ac01d5f` with tree `ed2d089f21273ec1e305d5ab432d554092267343` against current base `9d88195a6329151197b53c05c6cbb5a74167f08f`. The head and synthetic merge have the same tree.

The dedicated capable-runner qualification, run `35017167706`, is **PASS** for that exact candidate:

- Ubuntu 22.04 / kernel `6.8.0-1064-azure` / Python 3.12.14;
- all 12 prerequisite namespace/security capability probes passed;
- actual isolated execution passed with boundary `linux-userns-isolated-v1`;
- 142 selected cases plus 84 subtests passed;
- zero skipped test cases were permitted or observed;
- retained artifact `10416235755`, ZIP SHA-256 `49fa75e9c39e13a102bb16b20346e2875f42eac0b83f539ed137f78bc527db6a`.

The artifact contains exactly the six expected members, and its source/environment identities agree with the current candidate. PR #107 permanently retains the archive, extracted evidence and review handoff at commit `27225f9f366ac6472a91cc03d28c01c3aa53a3a0`.

This candidate also repairs the evidence exporter: it now requires exactly six unique expected archive names, rejects more than 16 MiB of declared uncompressed data, and preserves the existing 1 MiB ZIP and digest checks. Seven real-ZIP tests plus six subtests pass, with mutation checks catching removal of the subset, duplicate-name and expansion bounds. This is metadata-level expansion control, not a claim that every member is decompressed during export.

The #109 head deliberately remains blocked at the ownership boundary. `tests/test_factory_runtime_lifecycle.py` changed from protected blob `d4e00bd290351fa2ccd302ac578ac5dc463eda84` to proposed blob `85c6bf10a675ea3a74d775906d0bbaa79e411100`; the other 37 protected blobs and baseline remain unchanged. A COMMENTED review recorded on the preceding head was submitted by the implementer and explicitly defers independent authorization. It is not an independent approval and cannot be recycled for this refreshed head.

Fresh ordinary CI correctly remains red at the single protected ownership mismatch. Ownership, clean-install, measured binding, Factory runtime/OS, Controller/provider and Command Station all terminate on that trust gate; completed full unittest jobs report 1,017 cases with one ownership failure and 22 namespace skips. Those are repository/trust-review blockers, not host-policy failures. Control Plane and Pages are green. No inspected failure justifies weakening the checker or automatically advancing the baseline.

Required sequence: genuinely independent review of the exact current protected test and candidate changes; deliberate one-file pin advancement if accepted; then fresh exact-head ownership, clean-install, measured-binding, full CI and capable-runner zero-skip qualification before merge. The current M4 result qualifies only the named candidate tree and does not complete release, recovery, soak, live-model or research gates.

## M4 claim boundary

### Closed implementation work

The implementation defects formerly tracked by issue #63 are closed. The merged M4 path contains the reviewed mechanisms for:

- verified-tree/accepted-tree binding;
- descriptor-relative/non-following filesystem handling and link/race defenses;
- bounded verifier execution with explicit isolation semantics;
- fail-closed Git evidence semantics where unavailable/incomparable evidence is not silently treated as absence;
- deterministic timeout typing and preserved receipt-v2 signed serialization;
- lease uncertainty distinct from revocation;
- host-owned termination provenance and pending-reap recovery.

PR #108's retained contention work supports its named timing/termination tests under the measured conditions used by that PR. It does not prove arbitrary workloads, elapsed soak or every supported host.

### Qualification candidate and remaining acceptance gate

Namespace-dependent M4 tests that skip because a host cannot provide the required isolation capability remain **UNKNOWN/BLOCKED for qualification**, not PASS. Earlier Ubuntu 24.04 hosted attempts remain retained BLOCKED evidence.

PR #109 has produced multiple Ubuntu 22.04 capable-runner passes. The immediately preceding diagnostic head `1e4c02c5a967ca286cb60cbf23c893cf14a83c3b` passed run `35009804287` with 135 tests plus 78 subtests and zero skips; artifact `10413341869` has ZIP SHA-256 `073a3b4934d5f46153996258402613a1a426ac361efca152267cc62e53a21b3f`. That result is historical evidence for that exact earlier tree.

The current #109 head `fb99d589...` includes accepted main through #124, preserves the protected lifecycle CLI subprocess repair, and adds the hardened evidence exporter. Fresh M4 run `35017167706` passed all 12 probes, actual isolated execution and the 142-case/84-subtest zero-skip gate. The successful namespace run qualifies that named candidate tree only; it does not authorize the protected test-byte change or waive the ownership mismatch.

The original Python 3.13 failures remain retained. A later full instrumented run passed 1,005 tests with 22 namespace skips, so the historical exception's exact origin is not proven. The current repair demonstrates parent-warning contamination and a separate direct-module warning path, but those reproductions should not be expanded into a claim that every historical intermittent failure has been fully explained.

Ubuntu 22.04 is a temporary compatibility target and needs a migration path. A capable-runner PASS does not complete release, recovery, soak or research gates.

## Traceability status

Issue #48 is closed. `implementation-status.yaml` is the machine-readable implementation manifest and includes implemented M2/M3/M4/EVAL families rather than the previous stale `not_started` rows. Its generated status document is derived from that manifest.

This reconciliation fixes implementation traceability; it does **not** promote implementation into live qualification. Read status values together with their closure/non-claim notes and exact-tree evidence.

## Mission Control / WebVM reliability boundary

PR #122 improves the real-provider path without converting provider success into an acceptance proof. The browser surface distinguishes authorization/setup and provider failure classes, keeps conversation history truthful when builds are blocked, and routes browser missions through a bounded guest mailbox contract.

PR #124 is now merged. Its service-worker recovery is intentionally narrow: retries apply only to transient network exceptions/HTTP 5xx for same-origin immutable WebVM disk chunks, with bounded attempts and backoff. Provider calls, cross-origin requests, non-GETs, ordinary assets and 4xx responses remain outside that retry path. This reduces a known failure mode without redefining application correctness or masking terminal failures after retries are exhausted.

Issue #120 remains open for retained intermittent failures on the Pages/WebVM surface, including the earlier guest Python `_sha512` import failure and the later disk-chunk HTTP 503/WebVM abort. The fact that exact revisions later passed unchanged reruns supports an **intermittent delivery/guest-runtime** classification for those observations; it does not prove the reliability risk is solved. Recurrences must be retained and measured rather than hidden behind silent retries.

The exact-current-main Pages run `35016468585` completed successfully, including deployment and desktop plus narrow-Chromium live acceptance. This is one exact-revision result, not an empirical recurrence-rate or production-soak claim.

## Research status

### What is supported today

- The architecture separates generation authority from acceptance authority.
- Bounded worker execution, evidence capture, independent verification and deterministic integration are implemented mechanisms rather than paper-only abstractions.
- The protected M4 implementation gaps tracked by #63 are closed, and the timing/termination repair from #108 is merged.
- PR #109 produced a refreshed exact-current-main capable-runner zero-skip M4 PASS; acceptance of its new protected test bytes is still pending genuinely independent review and deliberate one-file baseline advancement.
- The repository contains evaluation machinery capable of preserving raw observations and recomputing paper-facing metrics.
- Mission Control can exercise real guest workflows and optional provider transport while retaining explicit non-claims around semantic correctness and authority.
- WebVM now contains a narrowly scoped recovery path for the specific retained immutable disk-chunk transient-failure class.

### What is not yet supported

The project does not yet claim, for live heterogeneous models, that:

- `P(correct | accepted)` is materially greater than raw worker correctness under matched model capability;
- the gain remains useful at nontrivial acceptance coverage;
- the reliability gain is worth the orchestration tax in cost/latency/throughput;
- lower-cost or weaker workers can be substituted without unacceptable verifier false-acceptance risk;
- PR #109's current protected lifecycle-test change has been independently authorized, baseline-advanced and integrated into accepted `main`;
- PR #124's recovery path has established an acceptable empirical WebVM recurrence rate;
- 24-hour, 72-hour or 30-day production soak targets have been satisfied.

## Current blockers and next gates

The recommended order is:

1. **Independently authorize the exact #109 protected lifecycle-test repair.** Review proposed blob `85c6bf10...` on current head `fb99d589...`; do not reuse the implementer's COMMENTED review or advance the pin merely to make CI green.
2. **Deliberately advance only the accepted protected pin and rerun the complete gate.** Require ownership, clean-install, measured binding, full CI and a fresh capable-runner zero-skip M4 run on the resulting exact head before merge.
3. **Quantify WebVM reliability.** Keep issue #120 open, retain every failed attempt, and run a defined repeated-run campaign; the green #124 exact-main deployment proves one acceptance run, not an acceptable production recurrence rate.
4. **Run release/recovery qualification.** Exercise blank-environment setup, recovery and retained-evidence procedures on the accepted candidate without broadening claims from fixture evidence.
5. **Freeze the live evaluation protocol.** Lock workload, evidence path, metrics, model/configuration and analysis choices before observing confirmatory model results.
6. **Run one fixed live model across R0–R5.** Measure `P(X)`, `P(A)`, `P(X|A)`, AER/ASSR, verifier false acceptance/rejection/`UNKNOWN`, latency, throughput and cost.
7. **Run model-degradation and heterogeneous-routing studies.** Preserve negative results and denominator discipline.
8. **Progress through 24-hour → 72-hour → 30-day soak** only after shorter qualification gates are clean.
9. **Update the paper from retained artifacts only.** No simulated, historical or synthetic evidence should be presented as live current-tree evidence.

## Documentation authority

Use the following order when determining current truth:

1. exact code at the commit being discussed;
2. tests, verifier output and retained machine-readable artifacts for that exact commit;
3. open qualification/security/reliability issues that narrow claims;
4. this current-status document;
5. `implementation-status.yaml` and its generated implementation summary for implementation traceability;
6. historical specs and snapshots for design intent, not current implementation claims.

RESIDUAL's strongest claim remains architectural until live evaluation is complete: unreliable computation may be useful if its authority is constrained, its behavior is observable, its outputs are independently checked, and only evidence-backed results are allowed to become accepted state.