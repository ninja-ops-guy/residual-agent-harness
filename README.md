# RESIDUAL

**Build reliable AI systems from unreliable computation.**

RESIDUAL is an evidence-first reliability and control plane for AI-assisted engineering. Workers propose bounded work; the harness owns acceptance. Execution is observed, evidence is retained, candidate outputs are independently checked, and only accepted state is allowed across controlled integration boundaries.

> **AI reliability does not necessarily require making each individual model reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.**

For exact current claims, start with [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

## What is implemented

RESIDUAL spans a connected platform rather than a single agent loop:

- **Core harness:** obligation DAGs, verifier-defined acceptance, residual delegation, evidence negotiation, receipts, bounded budgets, cache revalidation and tamper-evident traces.
- **Command Station:** self-hosted mission/run control, provider/model management, observations, HITL hooks, evidence export and operational UI.
- **Mission Control / WebVM:** browser-facing real-guest workflows, artifact conversations, provider transport, persistent guest-worker execution and fail-closed browser/runtime handling.
- **Factory M2/M3/M4:** bounded worker contracts/runtime, Station-issued evidence/receipts, trusted handoff, deterministic integration/scheduling and capable-runner qualification machinery.
- **Evaluation/research:** frozen workloads, ablations, statistics, fault injection, reproducible evidence bundles, observability/economics tooling and bounded self-maintenance research.

`FAIL`, `UNKNOWN`, malformed output, verifier exceptions, provider failures and abstention do not silently become `PASS`.

## Current main — technically qualified, review-provisional

Current `main` is **`f2d58e779ad589fe1d08842c9efc40ec5214a213`**, tree **`c62cf2a5d8c4234edcd7e53e0faa8edeb94a1571`**, the merge of PR #151.

PR #151 adds an event-backed `LIVE PIPELINE` projection to Mission Control, tighter provider-stage telemetry, stricter Puter response transport and exact-model handling while preserving fail-closed worker-envelope acceptance. It changes no Factory/M4 trust-boundary implementation or shared evidence schema.

The exact #151 candidate head completed all eight observed applicable pull-request workflows **PASS**. Exact merged main then completed all seven observed main-push qualification workflows **PASS**. M4 run **`35149837820`** executed the real `linux-userns-isolated-v1` path with `blocked_capabilities: []`, **142 tests + 84 subtests, zero skips**. Pages run **`35149837756`** passed its first-attempt generated and published desktop+narrow WebVM acceptance; retained live-proof artifact **`10468668615`** has SHA-256 **`5105cdda5d63eae0b97ed5953989cf8ce1616af6a28fa103940b0e4e28be2a1f`**.

Those are exact-revision automated/browser `PASS` results. They do **not** establish independent technical acceptance, paid/live Puter quality, long-run WebVM reliability, blank-environment release qualification, actual host-loss recovery or elapsed soak.

GitHub records **zero submitted reviews** for PR #151. The merge is therefore technically qualified but **review-provisional**. Green CI does not substitute for independent acceptance. Earlier merged #145/#147 carry the same governance debt.

## Live-provider boundary

The latest retained real-account provider evidence remains negative: after the WebVM polling path was stabilized, real Puter responses failed closed as `provider_protocol_invalid`; no obligation or artifact was accepted.

PR #151 strengthens the transport and visible pipeline, but its post-merge browser proof records `cloud_inference: NOT_RUN` and uses the explicit SDK test double. A fresh successful paid/live Puter acceptance on exact `main@f2d58e77...` is therefore **UNKNOWN / NOT YET ESTABLISHED**.

PR #149 retains additional nested `updates.build = {summary, files}` guidance, but it is based on the pre-#151 main and must be refreshed/requalified before it can support a current-main integration claim.

## WebVM reliability boundary

Issues #120 and #126 remain open. Retained diagnostics isolate a WebVM-specific, process-local CPython positive-duration timed-wait failure affecting at least `time.sleep()` and `select.select()` at call 273, while tested direct libc waits continue beyond that boundary. The exact CPython/glibc/WebVM mechanism and any relationship to earlier `_sha512`, impossible-constructor and allocator-corruption symptoms remain **UNKNOWN**.

Merged #145 avoids the known Python timed-wait surface in long-lived browser polling. Avoidance of that trigger is not proof that the broader historical corruption family is root-caused or that its recurrence rate is acceptable.

## Browser acceptance / onboarding boundary

PR #89 retains a first-attempt narrow-browser **FAIL** caused by an acceptance-observation defect: whitespace normalization plus an unterminated greedy exit-marker parse could turn a real `:0` into synthetic `:03`. The failed run remains authoritative and #89 is not qualified.

Closed-unmerged PRs #140 and #150 carried separate synchronization/parser repairs. Their work is now consolidated on current-main PR **#153**, which changes only the four acceptance-harness files needed for those repairs. Its current exact head is still qualifying; some workflows are green while Browser VM Demo/Pages remain in progress and other checks are queued. No submitted independent review is recorded. Do not inherit stale-branch green evidence into #153.

## Factory / M4 boundary

M2/M3/M4 are implemented. Issues #63 and #48 are closed, and `implementation-status.yaml` is the machine-readable implementation-presence manifest. Current M4 claims remain evidence- and environment-bound: capable-runner qualification is not every-host qualification, and unavailable namespace/capability execution remains `BLOCKED`/`UNKNOWN`, not `PASS`.

PR #139 still changes a protected M4 qualification test. Its capable-runner evidence is not permission to advance the protected ownership baseline automatically. Required order remains: independent exact-head review → deliberate baseline decision → fresh qualification. Downstream #134 must then be refreshed and requalified against the resulting current main.

## Governance boundary

Issue #144 remains open. PR #146 is refreshed directly onto `main@f2d58e77...` and implements a fail-closed independent-current-head review check. It passes only a human, non-author, current-head approval from a reviewer with write/admin authority. Platform ruleset enforcement still needs a maintainer change after the PR itself is independently accepted.

The policy does not rewrite history: missing pre-merge independent acceptance on #136/#145/#147/#151 remains governance debt.

## Qualification-v1 candidate

Draft PR #152 proposes a unified evidence-first qualification layer, generated lifecycle/state exploration, DSM fault-matrix binding, mutation canaries, branch coverage, exact-wheel qualification, multi-browser journeys and bounded process-soak tooling. It does **not** manufacture elapsed 24h/72h/30d evidence or replace existing M4/Pages gates. Its current CI is still partial/in progress, so no release-qualification `PASS` is claimed from #152.

## Design principles

1. **Workers propose; acceptance is independent.**
2. **`UNKNOWN` is not `PASS`.** Missing or incomparable evidence stays visible.
3. **Contracts precede execution.** Scope, authority, evidence and checks are explicit.
4. **Evidence survives handoffs.** Receipts bind accepted work to artifacts and relevant identities.
5. **Escalate the residual, not the whole problem.**
6. **Integration is deterministic.** Stochastic workers do not get unilateral durable-state authority.
7. **Parallelism must earn its coordination cost.**
8. **Verifier reliability is measured, not assumed.**
9. **Local and cloud compute are policy-governed resources.**
10. **Claims require exact-tree evidence.** Historical green runs do not automatically qualify later code.

## Quick start

### Command Station

Windows: **Start-Station.cmd**  
macOS: **Start-Station.command**  
Linux: `bash Start-Station.sh`

With Docker running, the launcher serves the Station UI at `http://localhost:8765`. Native mode requires Python 3.11+ and Git:

```bash
python3 -m residual.station.server --open
# or
python3 -m residual serve --open
```

See [`START-HERE.md`](START-HERE.md) for installation and operator setup.

### Core harness

```bash
python3 -m residual demo
python3 -m residual verify-trace runs/latest/trace.jsonl --result runs/latest/result.json
python3 -m residual benchmark --output runs/benchmark.json
```

### Factory / research

Start with:

- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)
- [`docs/roadmap/README.md`](docs/roadmap/README.md)
- [`docs/factory/PLAN-CONTRACT.md`](docs/factory/PLAN-CONTRACT.md)
- [`docs/evaluation.md`](docs/evaluation.md)
- [`docs/research.md`](docs/research.md)

## Research boundary

The working paper, **“Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems,”** treats the architecture as a falsifiable systems hypothesis. The repository does **not** yet claim that live heterogeneous-model evaluation proves the hypothesis.

Paper-facing evaluation must preserve raw worker correctness `P(X)`, acceptance coverage `P(A)`, accepted correctness `P(X|A)`, AER/ASSR, verifier false acceptance/rejection/`UNKNOWN`, cost, latency, throughput and orchestration overhead. A system that rejects nearly everything cannot be called reliable merely because accepted error is low.

## Current priority gates

1. Retain genuinely independent post-merge technical review for the #151 current-main surface and finish #144/#146 enforcement for future merges.
2. Run and retain a fresh real-account Puter acceptance test on exact deployed `f2d58e77...`; do not infer live-provider success from SDK-test-double CI.
3. Complete exact-head CI plus independent review for current-main PR #153 before using its consolidated WebVM harness repairs; then refresh/requalify #89.
4. Keep #120/#126 open until a predefined retained reliability campaign or proven regression-tested root cause supports closure.
5. Resolve #139 through independent protected-byte review, deliberate baseline handling and fresh qualification before refreshing #134.
6. Refresh older open integration candidates after #151 before merging; their pre-#151 exact-head results remain historical to those heads.
7. Complete release/recovery qualification without converting rehearsal or simulation into `PASS`.
8. Freeze the confirmatory live-evaluation protocol before observing outcome data, then run R0–R5, degradation, heterogeneous-routing and staged 24h → 72h → 30-day soak studies.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, a universal verifier, universally optimal scheduling, guaranteed token/cost savings, blanket production readiness, every-host M4 qualification, completed release/recovery qualification, acceptable long-run WebVM reliability, successful post-#151 real-provider inference, autonomous merge authority, completed long-duration soak, or live proof of the central research hypothesis.
