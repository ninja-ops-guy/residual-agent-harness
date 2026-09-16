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

Current `main` is **`f6f9bad84caccf68c7ab35e5788e756d12c55fb7`**, tree **`9991788c5d59b8ccd3b18b10ad0d4a46098305df`**, the merge of PR #156.

PR #156 repairs the real Puter worker-envelope boundary after fresh real-account evidence showed two `openai/gpt-5.4-nano` calls fail closed as `provider_protocol_invalid`. The merge removes provider-side strict structured-output mode for the dynamic obligation-key envelope and restores explicit `updates.build = {summary, files}` guidance while keeping RESIDUAL's local parser/verifier authoritative. It changes no Factory/M4 trust-boundary implementation or shared evidence schema.

All seven observed post-merge `main` workflows are **PASS** on this exact revision. The capable-runner M4 prerequisite/qualification workflow passed its fail-closed capability and zero-skip gate. Pages run **`35158939226`** passed on attempt 1, including generated desktop+narrow proof, deployment, published real-guest execution and published narrow-Chromium acceptance.

Those are exact-revision automated/browser results. They do **not** establish independent technical acceptance, paid/live Puter success, long-run WebVM reliability, blank-environment release qualification, actual host-loss recovery or elapsed soak.

GitHub records **zero submitted reviews** for PR #156. Current main is therefore technically qualified but **review-provisional**. Missing pre-merge independent acceptance on #136/#145/#147/#151/#156 remains governance debt.

## Live-provider boundary

The latest retained real-account evidence before #156 is **FAIL**: two real Puter calls returned `provider_protocol_invalid`, zero obligations were accepted, and no candidate reached verification. That failure is retained evidence and is not rewritten by the repair.

PR #156's merged revision has green provider-contract and browser/Pages qualification, but those automated paths are not a successful real-account provider run. A fresh successful paid/live Puter build on exact deployed `main@f6f9bad8...` is therefore **UNKNOWN / NOT YET RETAINED**.

Closed PRs #149 and #154 are superseded by #156 and should not be treated as active integration candidates.

## WebVM reliability boundary

Issues #120 and #126 remain open. Retained diagnostics isolate a WebVM-specific, process-local CPython positive-duration timed-wait failure affecting at least `time.sleep()` and `select.select()` around call 273, while tested direct libc waits continue beyond that boundary. Merged #145 routes long-lived browser polling below the known Python timed-wait surface, but avoidance of that trigger is not proof that the historical corruption family is root-caused or that its recurrence rate is acceptable.

## Factory / M4 boundary

M2/M3/M4 are implemented. Issues #63 and #48 are closed. Current M4 claims remain evidence- and environment-bound: capable-runner qualification is not every-host qualification, and unavailable namespace/capability execution remains `BLOCKED`/`UNKNOWN`, not `PASS`.

PR #139 still changes a protected M4 qualification test. Required order remains: genuinely independent exact-head review → deliberate ownership-baseline decision if accepted → fresh qualification after any protected pin change → refresh/requalify downstream #134. This repository documentation does not advance protected bytes, ownership baselines, qualification anchors or evidence schemas.

## Current candidate boundary after #156

Several open candidates were built on `main@f2d58e77...` and became stale when #156 merged:

- **#153** — consolidated WebVM acceptance-harness repairs refreshed onto current main at `35cbf2ba060bc04aabb6cfd10fbf90dc8dbccb77`; fresh exact-head qualification and genuinely independent review are required before integration, then #89 must be refreshed/requalified.
- **#152** — Qualification v1 evidence-first testing framework; its prior exact-head evidence is historical after #156 and no aggregate release `PASS` is inherited.
- **#146** — independent-current-head review gate refreshed onto current main at `c416d408149408ff8668a48d6e73eb1f3bf6347e`; fresh exact-head qualification and genuinely independent write-authorized acceptance remain required. Platform ruleset enforcement is a separate maintainer action.
- **#118** `ee81051220c616f8a605c948820d972177e19801`, **#115** `27e6e3b790d950ad1e8dd3603569f2eb5090ada4`, and **#131** `0094dd4c27231f8c4f71161b9a82770a27c7aa7b` are refreshed onto current main with all applicable exact-head workflows green, but each has zero reviews and remains blocked on genuine independent acceptance. #115's simulator is not elapsed soak; #131 remains the separate core persistence lane. **#93** remains unqualified on its retained failure/protected dependency.

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

1. Retain genuinely independent post-merge technical review for the #156 current-main surface and finish #144/#146 enforcement for future merges.
2. Run and retain a fresh real-account Puter acceptance test on exact deployed `f6f9bad8...`; do not infer live-provider success from green contract/browser CI.
3. Complete fresh qualification of refreshed #153 head `35cbf2ba060bc04aabb6cfd10fbf90dc8dbccb77`, preserve first-attempt evidence, require independent review before integration, then refresh/requalify #89.
4. Refresh/requalify #152; complete fresh qualification and independent acceptance of refreshed #146 head `c416d408149408ff8668a48d6e73eb1f3bf6347e`. Do not inherit stale-head qualification.
5. Keep #120/#126 open until a predefined reliability campaign or proven regression-tested root cause supports closure.
6. Resolve #139 through independent protected-byte review, deliberate baseline handling and fresh qualification before refreshing #134.
7. Complete release/recovery qualification without converting rehearsal or simulation into `PASS`.
8. Freeze the confirmatory live-evaluation protocol before observing outcome data, then run R0–R5, degradation, heterogeneous routing and staged 24h → 72h → 30-day soak studies.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, a universal verifier, universally optimal scheduling, guaranteed token/cost savings, blanket production readiness, every-host M4 qualification, completed release/recovery qualification, acceptable long-run WebVM reliability, successful post-#156 real-provider inference, autonomous merge authority, completed long-duration soak, or live proof of the central research hypothesis.
