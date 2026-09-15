# RESIDUAL current status

_Current-state check: 2026-09-15 against merged `main` at `bc8b783d8d01b343f870cae704fe7b63c6ea6c0d`._

This page is the human-readable current-state summary for RESIDUAL. Exact code, exact-tree tests and retained machine-readable evidence remain more authoritative than prose. Historical results apply only to the revisions they name.

## Executive summary

RESIDUAL is an evidence-first reliability and control plane for heterogeneous AI computation. The platform spans requirement compilation, bounded worker execution, evidence/receipt handling, deterministic integration, lifecycle recovery, evaluation, observability and operator-facing surfaces.

The central systems hypothesis remains:

> AI reliability does not necessarily require making individual models reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.

The repository contains substantial implementation and development evidence for the mechanisms required to test that hypothesis. It does **not** yet claim that the hypothesis has been proven on live heterogeneous model workloads, that the current M4 boundary has completed capable-runner namespace qualification, or that production soak targets have been met.

## What changed on 2026-09-15

Two changes materially advanced the integrated tree:

1. **PR #108 landed on `main` as `0430f2fa2d107fe48d26ae84a3c1550af029cb52`.** It carries the deterministic sandbox-timing and termination repair: lease tri-state semantics, a single wall-clock deadline owner, bounded lease-read contention, pending-reap ownership/recovery, typed timeout outcomes and receipt-v2 compatibility preservation. The merge explicitly retained namespace-dependent skips as **non-qualification** rather than treating them as passes.
2. **PR #122 advanced `main` to `bc8b783d8d01b343f870cae704fe7b63c6ea6c0d`.** It hardens the Mission Control real-provider experience with truthful failure categories, selected-model validation, a bounded browser/guest mailbox path, guided authorization state, blocked-build conversation behavior and real-browser acceptance coverage. These product/demo changes do not grant generated artifacts M4 authority.

Issue #63 is closed: the accepted-tree, filesystem/link, verifier-isolation and Git-evidence defects that it tracked are no longer the active M4 implementation blocker. Issue #48 is also closed: the implementation-status manifest has been reconciled with the merged Factory/evaluation tree.

## Current implementation map

| Area | Current state | Evidence / qualification boundary |
| --- | --- | --- |
| Core harness | Implemented | Goal contracts, verifier-defined acceptance, brakes, residual delegation, receipts, cache binding, trace/audit surfaces and provider routing are covered by the repository test corpus. |
| Command Station | Implemented research/operations surface | Self-hosted run control, model/provider management, observations, HITL hooks, evidence download and operational UI are present. Deployment-specific production readiness remains environment-dependent. |
| Mission Control / WebVM | Implemented product/demo surface | Multi-turn artifact conversations, verified parent lineage, isolated preview, browser-local restoration and optional-provider transport exist. PR #122 adds typed provider failures and real-browser acceptance. Issue #120 retains an earlier intermittent guest-runtime import failure; one unchanged rerun passed, so the event is tracked as an operational reliability concern rather than erased. |
| Factory M2 — worker contract/runtime | Implemented | Real `WorkerContract`, bounded worker runtime, isolated worktrees, journaled observations, host-owned termination and sandbox enforcement exist under `residual/factory/`. |
| Factory M3 — evidence bus/receipts | Implemented | Station-issued receipts, artifact binding, evidence-bus handoff and signature/integrity checks exist. Trust is enforced at the trusted consumption/admission boundary, not merely because bytes were stored. |
| Factory M4 — deterministic integration/scheduler | Implemented trust-boundary mechanisms; **capable-runner qualification still pending** | The original #63 implementation gaps are closed and #108's timing/termination repair is merged. Current hosted CI still cannot convert namespace-dependent skips into qualification. PR #109 records hosted-runner namespace capability as `BLOCKED`, with actual isolated execution `UNKNOWN / isolation_unavailable:namespace_probe_failed`. |
| Evaluation | Implemented development/research apparatus | Hash-locked workloads, repeated runs, ablations, reporting, statistics, fault injection and measured Factory hooks exist. The measured-evaluation acceptance-binding workflow is a CI mechanism; it is not live research evidence. |
| Sandbox / red team | Implemented development surface | Namespace/rlimit/bubblewrap paths and adversarial tests exist. Host capability determines whether specific kernel isolation paths can actually be qualified. |
| Cluster / distributed execution | Implemented development surface | Versioned wire schema, authenticated join/leave, heartbeats, task reassignment, local-first routing and cluster CLI exist. Distributed/host-loss guarantees remain narrower than single-process fixture behavior. |
| Lifecycle / gateway | Implemented | Deny-by-default side-effect gateway, lifecycle glue and deterministic resume/recovery mechanisms exist. Release/recovery qualification remains downstream of the active trust gate. |
| Hardening / observability | Implemented development surface | KMS abstraction, backup/rotation, connector conformance, SLO/alert plumbing, trace↔receipt correlation, metrics and async I/O are present. |
| Research / reproducibility | Active | The working paper, controlled-evaluation framework, claim/evidence discipline and fault-containment tooling are in place. Live R0–R5 measurements and soak remain future evidence gates. |

## Exact-tree CI status at this refresh

For `main` at `bc8b783d8d01b343f870cae704fe7b63c6ea6c0d`, the following push workflows had completed successfully when this document was prepared:

- Clean install qualification;
- Measured evaluation acceptance binding;
- Factory ownership gate;
- Command Station checks;
- Controller and provider contracts.

The GitHub Pages/WebVM deployment workflow for this exact SHA was still **in progress** at the time of the refresh. Therefore this document does **not** claim that every exact-current-main workflow is green. A later successful Pages completion may clear that deployment check, but it still would not constitute namespace qualification, production soak, live-provider research evidence or blanket production readiness.

## M4 claim boundary

### Closed implementation work

The implementation defects formerly tracked by issue #63 are closed. The merged M4 path now contains the reviewed mechanisms for:

- verified-tree/accepted-tree binding;
- descriptor-relative/non-following filesystem handling and link/race defenses;
- bounded verifier execution with explicit isolation semantics;
- fail-closed Git evidence semantics where unavailable/incomparable evidence is not silently treated as absence;
- deterministic timeout typing and preserved receipt-v2 signed serialization;
- lease uncertainty distinct from revocation;
- host-owned termination provenance and pending-reap recovery.

PR #108's retained contention work supports its named timing/termination tests under the measured conditions used by that PR. It does not prove arbitrary workloads, elapsed soak or every supported host.

### Still not qualified

Namespace-dependent M4 tests that skip because the host cannot provide the required isolation capability remain **UNKNOWN/BLOCKED for qualification**, not PASS. PR #109 is the active runner-prerequisite lane and currently records the hosted runner as blocked by namespace capability. Final qualification requires a genuinely capable environment, successful prerequisite probing and actual isolated M4 execution with zero namespace skips.

## Traceability status

Issue #48 is closed. `implementation-status.yaml` is now the machine-readable implementation manifest and includes implemented M2/M3/M4/EVAL families rather than the previous stale `not_started` rows. Its generated status document is derived from that manifest.

This reconciliation fixes implementation traceability; it does **not** promote implementation into live qualification. Read status values together with their closure/non-claim notes and exact-tree evidence.

## Mission Control / WebVM reliability boundary

PR #122 improves the real-provider path without converting provider success into an acceptance proof. The browser surface now distinguishes authorization/setup and provider failure classes, keeps conversation history truthful when builds are blocked, and routes browser missions through a bounded guest mailbox contract.

Issue #120 remains open for the earlier intermittent guest Python `_sha512` import failure observed during Pages acceptance on `afb9a191...`. The exact same revision and acceptance step passed on rerun without code or test changes. That supports an **intermittent guest-runtime** classification, not a claim that the reliability risk is solved. Recurrences should be retained and measured rather than hidden behind silent retries.

## Research status

### What is supported today

- The architecture separates generation authority from acceptance authority.
- Bounded worker execution, evidence capture, independent verification and deterministic integration are implemented mechanisms rather than paper-only abstractions.
- The protected M4 implementation gaps tracked by #63 are closed, and the timing/termination repair from #108 is merged.
- The repository contains evaluation machinery capable of preserving raw observations and recomputing paper-facing metrics.
- Mission Control can exercise real guest workflows and optional provider transport while retaining explicit non-claims around semantic correctness and authority.

### What is not yet supported

The project does not yet claim, for live heterogeneous models, that:

- `P(correct | accepted)` is materially greater than raw worker correctness under matched model capability;
- the gain remains useful at nontrivial acceptance coverage;
- the reliability gain is worth the orchestration tax in cost/latency/throughput;
- lower-cost or weaker workers can be substituted without unacceptable verifier false-acceptance risk;
- M4 has been requalified with zero namespace skips on a current capable runner;
- 24-hour, 72-hour or 30-day production soak targets have been satisfied.

## Current blockers and next gates

The recommended order is:

1. **Finish exact-current-main deployment qualification.** Require the Pages/WebVM workflow for the exact release candidate to complete successfully; retain failures and do not weaken acceptance assertions to get green CI.
2. **Qualify M4 on a capable runner.** Refresh the PR #109 runner-prerequisite path onto the accepted current trust boundary, independently review it, and require all namespace prerequisites plus actual isolated execution with zero namespace-dependent skips.
3. **Run release/recovery qualification.** Exercise blank-environment setup, recovery and retained-evidence procedures on the accepted candidate without broadening claims from fixture evidence.
4. **Freeze the live evaluation protocol.** Lock workload, evidence path, metrics, model/configuration and analysis choices before observing confirmatory model results.
5. **Run one fixed live model across R0–R5.** Measure `P(X)`, `P(A)`, `P(X|A)`, AER/ASSR, verifier false acceptance/rejection/`UNKNOWN`, latency, throughput and cost.
6. **Run model-degradation and heterogeneous-routing studies.** Preserve negative results and denominator discipline.
7. **Run fault campaigns under live execution.** Do not infer live containment from development fixtures.
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
