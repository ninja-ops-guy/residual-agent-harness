# RESIDUAL current status

_Current-state check: 2026-09-15 against merged `main` at `7cf45ea8eab675b870502fb76db1b6e63b562e9f` and the active PR #109 qualification candidate where explicitly named._

This is the human-readable current-state summary for RESIDUAL. Exact code, exact-tree tests and retained machine-readable evidence remain more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The platform spans requirement compilation, bounded worker execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability and operator-facing surfaces.

The central systems hypothesis remains:

> AI reliability does not necessarily require making individual models reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.

The repository contains substantial implementation and development evidence for the mechanisms required to test that hypothesis. It does **not** yet claim that the hypothesis has been proven on live heterogeneous model workloads, that PR #109 has been merged into accepted `main`, that WebVM hardening has established an acceptable long-run failure rate, or that production soak targets have been met.

## Accepted main

Current accepted `main` is **`7cf45ea8eab675b870502fb76db1b6e63b562e9f`**, the merge of PR #127.

Important accepted milestones on the current tree:

- **PR #108 / `0430f2fa...`** — deterministic sandbox-timing and termination repair: lease tri-state semantics, one wall-clock deadline owner, bounded lease-read contention, pending-reap ownership/recovery, typed timeout outcomes and receipt-v2 compatibility preservation. Namespace-dependent skips were retained as non-qualification rather than treated as passes.
- **PR #122 / `bc8b783d...`** — Mission Control real-provider reliability/UX hardening, including truthful provider failure classes, model validation, bounded browser/guest mailbox behavior and real-browser acceptance coverage. These product/demo mechanisms do not grant generated artifacts M4 authority.
- **PR #121 / `1a52e9a2...`** — provenance-only finalization of the Factory ownership anchor after #108. All 38 accepted protected blob pins remained unchanged.
- **PR #124 / `9d88195a...`** — narrowly scoped WebVM recovery for transient same-origin immutable disk-chunk failures. Retries apply only to matching immutable ext2 chunk `GET`s and do not expand to provider calls, cross-origin traffic, ordinary assets or 4xx responses.
- **PR #125 / `70e701d5...`** — publishes a completion marker for WebVM provider replies. It is confined to the WebVM/workbench surface and does not change Factory/M4 or shared evidence schemas.
- **PR #127 / `7cf45ea8...`** — launches WebVM workbench missions through the guest shell. It is likewise disjoint from the protected Factory/M4 surface.

Issue #63 is closed: its accepted-tree, filesystem/link, verifier-isolation and Git-evidence implementation defects are no longer the active M4 blocker. Issue #48 is closed: `implementation-status.yaml` has been reconciled with the merged Factory/evaluation implementation.

## Accepted-main Pages/WebVM status

Pages/WebVM run **`35031823399`** on exact main `7cf45ea8...` completed successfully: artifact build/browser proof passed, deployment passed, and the published WebVM completed both desktop and narrow-Chromium live acceptance. The other push-triggered main workflows are also green.

That clears the exact-revision deployment gate through #127. It does **not** establish an empirical production failure rate or soak result.

The failure that motivated #124 remains retained evidence. On deployed revision `bc8b783...`, run `35003867644` failed its first narrow-Chromium live attempt after an immutable WebVM disk chunk returned HTTP 503 and the guest aborted/stalled; the unchanged rerun later passed. Issue #120 remains open because repeated intermittent delivery/guest-runtime failures are an operational reliability concern and must be measured rather than erased by retries.

## PR #109 — current M4 qualification candidate

PR #109 has materially advanced beyond its preceding candidate.

### Protected-byte review and ownership advancement

The lifecycle CLI test repair changed protected `tests/test_factory_runtime_lifecycle.py` from accepted blob:

- `d4e00bd290351fa2ccd302ac578ac5dc463eda84`

to reviewed blob:

- `85c6bf10a675ea3a74d775906d0bbaa79e411100`.

The repair preserves the original substantive assertions while moving observation to the real CLI subprocess boundary: both CLI aliases, exit code, empty stdout, exact sanitized blocked JSON, path-disclosure guard and empty-journal assertions remain enforced.

The recorded owner-supplied independent technical acceptance authorized **only that protected test-byte change**. Current PR head **`4c44fe07f7e214c2c25ab8ff48f06e81ff5c86b9`** advances only that one ownership pin. Its refresh onto current main added only the disjoint WebVM/workbench files from PRs #125 and #127; the reviewed lifecycle-test blob remains `85c6bf10...`. The other 37 protected pins, the accepted provenance anchor and protected executable blobs are unchanged. This is not represented as an independent-account GitHub approval event.

### Fresh exact-head qualification

GitHub tested synthetic merge **`fea9429b2d111851fa074d6e72eb1892e3797d60`**, tree **`39599b2296fa8865ab1e0dabae333b9b6f933da8`**, combining PR #109 head `4c44fe07...` with current main `7cf45ea8...`.

The dedicated capable-runner M4 workflow, run **`35032478689`**, completed **PASS** on Ubuntu 22.04 / Python 3.12:

- all 12 prerequisite capability probes passed;
- `blocked_capabilities` was empty;
- actual isolated execution passed with boundary `linux-userns-isolated-v1`;
- **142 test cases passed**;
- **84 subtests passed**;
- the zero-skip gate passed;
- retained artifact **`10421733816`** is 10,760 bytes and has ZIP SHA-256 **`2fdafde41243964fd2ed8964dfd52d6c2a2e77b4ffb3f6910b94e80db6de4f89`**.

At the latest exact-head snapshot, the current GitHub check set is terminal with no failures or still-running/queued jobs. Factory ownership and measured-evaluation binding are green after the one-pin advancement; Python qualification jobs, Factory/runtime/OS paths, browser checks and the capable-runner M4 gate also complete without a failing check. PR-triggered deployment skips are not represented as live deployment evidence.

This means the previous ownership blocker has been resolved **for the named PR candidate** without weakening the checker. It does not make merged `main` namespace-qualified because PR #109 remains unmerged.

### Historical candidate evidence

The preceding #109 candidate `fb99d5896b23b91e3903965a8c56813412533d48` remains useful historical evidence. Its run `35017167706` passed all 12 probes, actual isolated execution and 142 cases plus 84 subtests with zero skips. That earlier PASS is not being reused as evidence for the current head; the current head has its own fresh run `35032478689`.

## Current implementation map

| Area | Current state | Evidence / qualification boundary |
| --- | --- | --- |
| Core harness | Implemented | Goal contracts, verifier-defined acceptance, brakes, residual delegation, receipts, cache binding, trace/audit surfaces and provider routing are covered by the repository test corpus. |
| Command Station | Implemented research/operations surface | Self-hosted run control, model/provider management, observations, HITL hooks, evidence download and operational UI exist. Deployment-specific production readiness remains environment-dependent. |
| Mission Control / WebVM | Implemented product/demo surface | Multi-turn artifact conversations, verified parent lineage, isolated preview, browser-local restoration, optional-provider transport, typed provider failures and bounded disk-chunk recovery exist. Issue #120 remains the reliability tracker. |
| Factory M2 — worker contract/runtime | Implemented | Real `WorkerContract`, bounded worker runtime, isolated worktrees, journaled observations, host-owned termination and sandbox enforcement exist. |
| Factory M3 — evidence bus/receipts | Implemented | Station-issued receipts, artifact binding, evidence-bus handoff and signature/integrity checks exist. |
| Factory M4 — deterministic integration/scheduler | Implemented; **current PR candidate zero-skip qualified, not yet merged** | #63 implementation gaps and #108 timing repair are merged. Current PR #109 exact candidate passed real namespace probes, actual isolated execution and the zero-skip M4 suite after the reviewed one-pin ownership advancement. Accepted `main` does not inherit that qualification until the PR is merged and any required accepted-main confirmation is complete. |
| Evaluation | Implemented development/research apparatus | Hash-locked workloads, repeated runs, ablations, reporting, statistics, fault injection and measured Factory hooks exist. CI binding is not live research evidence. |
| Sandbox / red team | Implemented development surface | Namespace/rlimit/bubblewrap paths and adversarial tests exist. Host capability still determines whether specific kernel isolation paths can be qualified. |
| Cluster / distributed execution | Implemented development surface | Versioned wire schema, authenticated membership, heartbeats, task reassignment, local-first routing and cluster CLI exist. Distributed guarantees remain narrower than fixture behavior. |
| Lifecycle / gateway | Implemented | Deny-by-default side-effect gateway, lifecycle glue and deterministic resume/recovery mechanisms exist. Release/recovery qualification remains downstream. |
| Hardening / observability | Implemented development surface | KMS abstraction, backup/rotation, connector conformance, SLO/alert plumbing, trace↔receipt correlation, metrics and async I/O are present. |
| Research / reproducibility | Active | Working paper, controlled-evaluation framework, claim/evidence discipline and fault-containment tooling exist. Live R0–R5 and soak remain future evidence gates. |

## M4 claim boundary

### Closed implementation work

The merged M4 path contains reviewed mechanisms for:

- verified-tree/accepted-tree binding;
- descriptor-relative/non-following filesystem handling and link/race defenses;
- bounded verifier execution with explicit isolation semantics;
- fail-closed Git evidence semantics where unavailable/incomparable evidence is not silently treated as absence;
- deterministic timeout typing and preserved receipt-v2 signed serialization;
- lease uncertainty distinct from revocation;
- host-owned termination provenance and pending-reap recovery.

PR #108's retained contention evidence supports its named timing/termination tests under its measured conditions. It does not prove arbitrary workloads, every host or elapsed soak.

### Qualification state

Namespace-dependent M4 tests that skip because a host cannot provide the required isolation capability remain **UNKNOWN/BLOCKED**, not PASS. Earlier Ubuntu 24.04 hosted attempts remain retained BLOCKED evidence.

PR #109 now has fresh exact-current-main candidate evidence after the protected test-byte review and one-pin advancement. Run `35032478689` is the authoritative current capable-runner result for head `4c44fe07...` / synthetic merge `fea9429b...` / tree `39599b22...`: all 12 probes PASS, isolated execution PASS, 142 tests + 84 subtests PASS, zero skips.

The remaining boundary is integration authority: this PASS qualifies that named candidate tree only. It does not authorize a claim that accepted `main` is namespace-qualified before merge and any required post-merge exact-tree confirmation.

Ubuntu 22.04 is a temporary compatibility target and needs a migration path. A capable-runner PASS does not complete release, recovery, soak or research gates.

## Traceability status

Issue #48 is closed. `implementation-status.yaml` is the machine-readable implementation manifest and includes implemented M2/M3/M4/EVAL families rather than the previous stale `not_started` rows. Its generated status document is derived from that manifest.

This reconciliation fixes implementation traceability; it does **not** promote implementation into live qualification. Read status values together with exact-tree evidence and explicit non-claims.

## Research status

### Supported today

- Generation authority is separated from acceptance authority.
- Bounded worker execution, evidence capture, independent verification and deterministic integration are implemented mechanisms.
- The protected M4 implementation gaps tracked by #63 are closed, and #108's timing/termination repair is merged.
- PR #109's reviewed current-main candidate has a fresh capable-runner zero-skip M4 PASS after the deliberate one-pin ownership advancement.
- The repository contains evaluation machinery capable of preserving raw observations and recomputing paper-facing metrics.
- Mission Control exercises real guest workflows and optional provider transport while retaining explicit non-claims around semantic correctness and authority.
- WebVM contains a narrowly scoped recovery path for the retained immutable disk-chunk transient-failure class.

### Not yet supported

The project does not yet claim, for live heterogeneous models, that:

- `P(correct | accepted)` is materially greater than raw worker correctness under matched model capability;
- the gain remains useful at nontrivial acceptance coverage;
- the reliability gain is worth the orchestration tax in cost/latency/throughput;
- lower-cost or weaker workers can be substituted without unacceptable verifier false-acceptance risk;
- PR #109's qualified candidate has been integrated into accepted `main`;
- PR #124's recovery path has established an acceptable empirical WebVM recurrence rate;
- 24-hour, 72-hour or 30-day production soak targets have been satisfied.

## Current blockers and next gates

The recommended order is:

1. **Complete PR #109 merge review without broadening the trust change.** The reviewed one-pin advancement and fresh exact-head CI/M4 gates are green; do not add unrelated protected changes before integration.
2. **If #109 merges, verify the accepted-main exact tree as required by policy.** Do not recycle the PR synthetic-merge result if the accepted tree differs or new commits land first.
3. **Quantify WebVM reliability.** Keep issue #120 open, retain every failed attempt, and run a defined repeated-run campaign; the green #124 exact-main deployment proves one exact acceptance run, not a production recurrence rate.
4. **Run release/recovery qualification.** Exercise blank-environment setup, recovery and retained-evidence procedures on the accepted candidate without broadening fixture claims.
5. **Freeze the live evaluation protocol.** Lock workload, evidence path, metrics, model/configuration and analysis choices before confirmatory model results.
6. **Run one fixed live model across R0–R5.** Measure `P(X)`, `P(A)`, `P(X|A)`, AER/ASSR, verifier false acceptance/rejection/`UNKNOWN`, latency, throughput and cost.
7. **Run model-degradation and heterogeneous-routing studies.** Preserve negative results and denominator discipline.
8. **Progress through 24-hour → 72-hour → 30-day soak** only after shorter gates are clean.
9. **Update the paper from retained artifacts only.** Do not present synthetic, historical or fixture evidence as live current-tree evidence.

## Documentation authority

Use this order when determining current truth:

1. exact code at the commit being discussed;
2. tests, verifier output and retained machine-readable artifacts for that exact commit;
3. open qualification/security/reliability issues that narrow claims;
4. this current-status document;
5. `implementation-status.yaml` and generated implementation summary for traceability;
6. historical specs/snapshots for design intent, not current implementation claims.

RESIDUAL's strongest claim remains architectural until live evaluation is complete: unreliable computation may be useful if its authority is constrained, its behavior is observable, its outputs are independently checked, and only evidence-backed results are allowed to become accepted state.