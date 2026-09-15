# RESIDUAL current status

_Current-state check: 2026-09-15 against merged `main` at `1a52e9a2dfc9ea9a9d24579bb9b44548c483f0b9` and the active qualification candidate where explicitly named._

This page is the human-readable current-state summary for RESIDUAL. Exact code, exact-tree tests and retained machine-readable evidence remain more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The platform spans requirement compilation, bounded worker execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability and operator-facing surfaces.

The central systems hypothesis remains:

> AI reliability does not necessarily require making individual models reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.

The repository contains substantial implementation and development evidence for the mechanisms required to test that hypothesis. It does **not** yet claim that the hypothesis has been proven on live heterogeneous model workloads, that the current M4 qualification candidate has been accepted into `main`, or that production soak targets have been met.

## What changed on 2026-09-15

Four changes materially advanced or narrowed the integrated qualification state:

1. **PR #108 landed on `main` as `0430f2fa2d107fe48d26ae84a3c1550af029cb52`.** It carries the deterministic sandbox-timing and termination repair: lease tri-state semantics, a single wall-clock deadline owner, bounded lease-read contention, pending-reap ownership/recovery, typed timeout outcomes and receipt-v2 compatibility preservation. The merge explicitly retained namespace-dependent skips as **non-qualification** rather than treating them as passes.
2. **PR #122 advanced `main` to `bc8b783d8d01b343f870cae704fe7b63c6ea6c0d`.** It hardens the Mission Control real-provider experience with truthful failure categories, selected-model validation, a bounded browser/guest mailbox path, guided authorization state, blocked-build conversation behavior and real-browser acceptance coverage. These product/demo changes do not grant generated artifacts M4 authority.
3. **PR #121 advanced `main` to `1a52e9a2dfc9ea9a9d24579bb9b44548c483f0b9`.** It changes only the protected ownership manifest's provenance metadata: `pinned_at` names the accepted #108 squash commit `0430f2fa...`; all 38 protected path-to-blob pins are unchanged. This records accepted source identity and does not add namespace, production, soak or research qualification.
4. **PR #109 has now reached a stronger but still intentionally blocked qualification candidate.** Current head `2551585f8951d242db92cd4c3e680409b0e4c572`, synthetic merge `6c62e64f2b1251f7ac8e43883207fa2a3240554e`, tree `0299afd8e0caef5cc247317b5ed2d41423f86a14`, is based on current `main`. Its Ubuntu 22.04 M4 qualification job passed all capability probes, actual `linux-userns-isolated-v1` execution, and 135 M4 tests plus 78 subtests with **zero skips**. The same head also changes one protected lifecycle test to repair the Python 3.13 CLI/stderr contamination path. Because that protected blob changed, the ownership gate correctly fails closed until independent review accepts the bytes and a deliberate baseline advancement is made.

Issue #63 is closed: the accepted-tree, filesystem/link, verifier-isolation and Git-evidence defects that it tracked are no longer the active M4 implementation blocker. Issue #48 is also closed: the implementation-status manifest has been reconciled with the merged Factory/evaluation tree.

## Current implementation map

| Area | Current state | Evidence / qualification boundary |
| --- | --- | --- |
| Core harness | Implemented | Goal contracts, verifier-defined acceptance, brakes, residual delegation, receipts, cache binding, trace/audit surfaces and provider routing are covered by the repository test corpus. |
| Command Station | Implemented research/operations surface | Self-hosted run control, model/provider management, observations, HITL hooks, evidence download and operational UI are present. Deployment-specific production readiness remains environment-dependent. |
| Mission Control / WebVM | Implemented product/demo surface | Multi-turn artifact conversations, verified parent lineage, isolated preview, browser-local restoration and optional-provider transport exist. PR #122 adds typed provider failures and real-browser acceptance. Issue #120 retains intermittent guest/delivery failures as an operational reliability concern rather than erasing them after successful reruns. |
| Factory M2 — worker contract/runtime | Implemented | Real `WorkerContract`, bounded worker runtime, isolated worktrees, journaled observations, host-owned termination and sandbox enforcement exist under `residual/factory/`. |
| Factory M3 — evidence bus/receipts | Implemented | Station-issued receipts, artifact binding, evidence-bus handoff and signature/integrity checks exist. Trust is enforced at the trusted consumption/admission boundary, not merely because bytes were stored. |
| Factory M4 — deterministic integration/scheduler | Implemented trust-boundary mechanisms; **current capable-runner PASS, protected acceptance blocked** | #63 implementation gaps and #108 timing/termination repair are merged. PR #109's current-main synthetic candidate passes real namespace probes, actual isolated execution and the zero-skip M4 suite, but one protected lifecycle-test blob changed and is deliberately rejected by ownership until independently reviewed and pinned. |
| Evaluation | Implemented development/research apparatus | Hash-locked workloads, repeated runs, ablations, reporting, statistics, fault injection and measured Factory hooks exist. The measured-evaluation acceptance-binding workflow is a CI mechanism; it is not live research evidence. |
| Sandbox / red team | Implemented development surface | Namespace/rlimit/bubblewrap paths and adversarial tests exist. Host capability determines whether specific kernel isolation paths can actually be qualified. |
| Cluster / distributed execution | Implemented development surface | Versioned wire schema, authenticated join/leave, heartbeats, task reassignment, local-first routing and cluster CLI exist. Distributed/host-loss guarantees remain narrower than single-process fixture behavior. |
| Lifecycle / gateway | Implemented | Deny-by-default side-effect gateway, lifecycle glue and deterministic resume/recovery mechanisms exist. Release/recovery qualification remains downstream of the active trust gate. |
| Hardening / observability | Implemented development surface | KMS abstraction, backup/rotation, connector conformance, SLO/alert plumbing, trace↔receipt correlation, metrics and async I/O are present. |
| Research / reproducibility | Active | The working paper, controlled-evaluation framework, claim/evidence discipline and fault-containment tooling are in place. Live R0–R5 measurements and soak remain future evidence gates. |

## Exact-tree CI status at this refresh

### Accepted `main`

Current `main` remains `1a52e9a2dfc9ea9a9d24579bb9b44548c483f0b9`. PR #121 was a provenance-only ownership-manifest update; its applicable exact-main metadata checks were green. It did not change the deployed browser surface, so the latest deployed application revision remains `bc8b783d8d01b343f870cae704fe7b63c6ea6c0d`.

The latest deployed application revision's Pages/WebVM run `35003867644` failed its first live attempt in narrow Chromium after the deployed disk chunk returned HTTP 503 and the guest stalled after attachment. The unchanged rerun then completed successfully on desktop and narrow Chromium. Failed-attempt artifact `10410904479` has ZIP SHA-256 `57ab059987126acbc4baf3b0b4b10bc7f3412fa8c38322c756fbd1b4b13564a5`; successful-attempt artifact `10411624041` has ZIP SHA-256 `0cbfe28cc0cd1e94d4cde603ad4452b9834a6a6f6f14e41c4ec32565ffc25386`.

Issue #120 remains open because repeated intermittent failures on the live WebVM surface are a production-reliability concern. The separate Vercel commit status has also been observed red from external account/deployment-capacity limits; that is not a repository-test pass or failure. None of these outcomes constitutes namespace qualification, production soak, live-provider research evidence or blanket production readiness.

### Active PR #109 qualification candidate

Current PR #109 head is `2551585f8951d242db92cd4c3e680409b0e4c572`; GitHub tested synthetic merge `6c62e64f2b1251f7ac8e43883207fa2a3240554e` with tree `0299afd8e0caef5cc247317b5ed2d41423f86a14` against base `1a52e9a...`.

The dedicated capable-runner qualification, run `35010813043`, is **PASS**:

- Ubuntu 22.04.5 / kernel `6.8.0-1064-azure` / Python 3.12.14;
- all prerequisite namespace/capability probes passed;
- actual isolated execution passed with boundary `linux-userns-isolated-v1`, return code 0, and retained stdout/stderr hashes;
- 135 selected M4 tests plus 78 subtests passed;
- zero skipped test cases were permitted or observed;
- retained artifact `10413437995`, ZIP SHA-256 `181c57c49e94aaca513f8cf16f83dd2924d1cc0ec12f8105fbb6110047ddc7e1`.

That is genuine exact-candidate namespace/isolation qualification evidence for the tests and environment recorded by the run. It is **not** a production, soak, live-model or research result.

The current head deliberately remains blocked at the ownership boundary. `tests/test_factory_runtime_lifecycle.py` changed from protected blob `d4e00bd290351fa2ccd302ac578ac5dc463eda84` to proposed blob `85c6bf10a675ea3a74d775906d0bbaa79e411100`. The Factory ownership gate therefore fails closed with exactly that one mismatch. Clean-install qualification fails for the same ownership prerequisite on Python 3.11/3.12/3.13, and measured-evaluation binding stops at its ownership prerequisite. These are expected trust-gate failures for an unreviewed protected-byte change, not evidence that the ownership control is defective.

Other current-head workflows were still completing at this snapshot. They must be evaluated on this exact head before merge. The previous head's all-green workflow result is historical and must not be projected onto `2551585f...`.

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

PR #109 has now produced multiple Ubuntu 22.04 capable-runner passes. The immediately preceding diagnostic head `1e4c02c5a967ca286cb60cbf23c893cf14a83c3b` passed run `35009804287` with 135 tests plus 78 subtests and zero skips; artifact `10413341869` has ZIP SHA-256 `073a3b4934d5f46153996258402613a1a426ac361efca152267cc62e53a21b3f`. That result is historical evidence for that exact earlier tree.

The current head `2551585f...` changed the protected lifecycle CLI test to exercise both real subprocess aliases and prevent parent warning contamination from corrupting JSON parsing. Fresh M4 run `35010813043` again passed all probes, actual isolated execution and the 135-test/78-subtest zero-skip gate. Because the protected test bytes changed, that successful namespace run does not authorize the protected change. The next trust action is independent review of the proposed protected blob, followed—only if accepted—by deliberate ownership-baseline advancement and fresh exact-candidate gates.

The original Python 3.13 failures remain retained. A later full instrumented run passed 1,005 tests with 22 namespace skips, so the historical exception's exact origin is not proven. The current repair demonstrates parent-warning contamination and a separate direct-module warning path, but those reproductions should not be expanded into a claim that every historical intermittent failure has been fully explained.

Ubuntu 22.04 is a temporary compatibility target and needs a migration path. A capable-runner PASS does not complete release, recovery, soak or research gates.

## Traceability status

Issue #48 is closed. `implementation-status.yaml` is the machine-readable implementation manifest and includes implemented M2/M3/M4/EVAL families rather than the previous stale `not_started` rows. Its generated status document is derived from that manifest.

This reconciliation fixes implementation traceability; it does **not** promote implementation into live qualification. Read status values together with their closure/non-claim notes and exact-tree evidence.

## Mission Control / WebVM reliability boundary

PR #122 improves the real-provider path without converting provider success into an acceptance proof. The browser surface distinguishes authorization/setup and provider failure classes, keeps conversation history truthful when builds are blocked, and routes browser missions through a bounded guest mailbox contract.

Issue #120 remains open for retained intermittent failures on the Pages/WebVM surface, including the earlier guest Python `_sha512` import failure and the later disk-chunk HTTP 503/WebVM abort. Exact revisions later passed unchanged reruns. That supports an **intermittent delivery/guest-runtime** classification, not a claim that the reliability risk is solved. Recurrences must be retained and measured rather than hidden behind silent retries.

Draft PR #124 adds further WebVM/lineage hardening but remains downstream of current `main` and requires refresh/review before any merge. Its changes do not establish an acceptable recurrence rate by themselves.

## Research status

### What is supported today

- The architecture separates generation authority from acceptance authority.
- Bounded worker execution, evidence capture, independent verification and deterministic integration are implemented mechanisms rather than paper-only abstractions.
- The protected M4 implementation gaps tracked by #63 are closed, and the timing/termination repair from #108 is merged.
- A current-main-based PR #109 candidate has executed the M4 isolation suite on a capable runner with zero skips; acceptance of its new protected test bytes is still pending.
- The repository contains evaluation machinery capable of preserving raw observations and recomputing paper-facing metrics.
- Mission Control can exercise real guest workflows and optional provider transport while retaining explicit non-claims around semantic correctness and authority.

### What is not yet supported

The project does not yet claim, for live heterogeneous models, that:

- `P(correct | accepted)` is materially greater than raw worker correctness under matched model capability;
- the gain remains useful at nontrivial acceptance coverage;
- the reliability gain is worth the orchestration tax in cost/latency/throughput;
- lower-cost or weaker workers can be substituted without unacceptable verifier false-acceptance risk;
- PR #109's current protected lifecycle-test change has been independently reviewed, baseline-authorized and integrated into accepted `main`;
- 24-hour, 72-hour or 30-day production soak targets have been satisfied.

## Current blockers and next gates

The recommended order is:

1. **Review the protected #109 lifecycle-test repair.** Inspect proposed blob `85c6bf10...` independently; do not advance the ownership baseline merely to make CI green. If accepted, deliberately repin the single protected path and rerun ownership, clean-install, measured-evaluation binding and the full exact-candidate suite.
2. **Preserve the capable-runner evidence.** Keep run `35010813043`, its zero-skip M4 result and retained artifact bound to the exact synthetic candidate; do not project it onto later heads without rerunning qualification.
3. **Control live WebVM reliability.** Keep the exact-current-main Pages/WebVM gate green, retain every failed attempt, quantify recurrence under a defined repeated-run campaign, and investigate delivery/runtime failures without weakening acceptance assertions.
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
