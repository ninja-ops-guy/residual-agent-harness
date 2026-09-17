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

## Live-provider and WebVM production boundary

Earlier retained real-account evidence before #156 is **FAIL** at the provider-envelope boundary: two real Puter calls returned `provider_protocol_invalid`, zero obligations were accepted, and no candidate reached verification. That evidence remains authoritative history.

Fresh post-#156 iPhone/WebKit public-demo evidence advanced the failure boundary but did **not** produce a successful end-to-end live mission. The browser reported **`Provider connected`**, while the Linux guest exposed **`RESIDUAL_WORKER_POISONED`** and Mission Control remained at **`GUEST STARTING`** with no supported recovery path. The observed public-demo attempt is therefore an end-to-end **FAIL** at the guest-recovery/product boundary. Because no valid live candidate completed the normal RESIDUAL verifier path, successful paid/live Puter candidate execution on exact current main remains **UNKNOWN**, not `PASS`.

The poison fence itself remains intentional fail-closed behavior. The lower-level cause of the production guest poison remains **UNKNOWN**.

PR #158 explored clearing a proven-recovered generation's poison tombstone, but its exact head `ac637711...` is **FAIL**: Controller/provider contracts, Command Station and Pages are red, and Python 3.11 retained two regressions requiring the durable timeout poison to remain present. Do not treat #158 as qualified.

PR #159 instead preserves the old poison fence and adds whole-guest recovery by rotating to a fresh browser-session WebVM writable overlay. Exact head **`5c33f31d234e3be315a052109fe270d3b70276c5`** has all eight observed applicable workflows **PASS**, including Browser VM Demo CI and generated desktop+narrow Pages proof. The browser acceptance deliberately reproduces the poisoned state, requires `GUEST FAILED · RESTART REQUIRED`, rotates the overlay, proves poison/PID/control/busy/active-lock state does not carry into the replacement guest, then completes a real local repository audit. Cloud inference remains test-double coverage. The only submitted review is an owner `COMMENTED` handoff explicitly marked **not independent acceptance**, so #159 remains **BLOCKED on genuinely independent technical review** before integration. After any accepted merge, production Pages and a fresh real-account iPhone/WebKit mission are still required before claiming the public provider demo fixed.

## WebVM reliability boundary

Issues #120 and #126 remain open. Retained diagnostics isolate a WebVM-specific, process-local CPython positive-duration timed-wait failure affecting at least `time.sleep()` and `select.select()` around call 273, while tested direct libc waits continue beyond that boundary. Merged #145 routes long-lived browser polling below the known Python timed-wait surface, but avoidance of that trigger is not proof that the historical corruption family is root-caused or that its recurrence rate is acceptable.

The fresh poisoned-guest production evidence is additional reliability evidence, not proof that the timed-wait defect and poison event share one cause. Their relationship remains **UNKNOWN**.

## Factory / M4 boundary

M2/M3/M4 are implemented. Issues #63 and #48 are closed. Current M4 claims remain evidence- and environment-bound: capable-runner qualification is not every-host qualification, and unavailable namespace/capability execution remains `BLOCKED`/`UNKNOWN`, not `PASS`.

PR #139 still changes a protected M4 qualification test. Required order remains: genuinely independent exact-head review → deliberate ownership-baseline decision if accepted → fresh qualification after any protected pin change → refresh/requalify downstream #134. This repository documentation does not advance protected bytes, ownership baselines, qualification anchors or evidence schemas.

## Current candidate boundary after #156

- **#159** — fresh-overlay poisoned-guest recovery, exact head `5c33f31d...`: all eight observed applicable workflows **PASS**; owner COMMENT is not independent acceptance; **BLOCKED** on genuinely independent review, then post-merge production Pages + fresh real-account iPhone/WebKit validation.
- **#158** — alternative in-console provider/recovery approach, exact head `ac637711...`: **FAIL** on Controller/provider contracts, Command Station and Pages; retained Python 3.11 regressions show durable poison was removed where existing tests require it to remain. Not qualified.
- **#153** — consolidated WebVM acceptance-harness repairs at `35cbf2ba...`: all eight observed applicable exact-head workflows **PASS**, but no qualifying independent current-head approval; blocked before integration, then #89 must be refreshed/requalified.
- **#152** — Qualification v1 evidence-first testing framework; its prior exact-head evidence is historical after #156 and no aggregate release `PASS` is inherited.
- **#146** — independent-current-head review gate at `c416d408...`: ordinary workflows and policy regressions pass, while the live independent-review gate correctly remains **BLOCKED** without a qualifying current-head human approval. Platform ruleset enforcement is a separate maintainer action.
- **#118** `ee81051220c616f8a605c948820d972177e19801`, **#115** `27e6e3b790d950ad1e8dd3603569f2eb5090ada4`, and **#131** `0094dd4c27231f8c4f71161b9a82770a27c7aa7b` are refreshed onto current main with applicable exact-head workflows green, but each remains blocked on genuine independent acceptance. #115's simulator is not elapsed soak; #131 remains the separate core persistence lane. **#93** remains unqualified on its retained failure/protected dependency.

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

1. Obtain genuinely independent exact-head review for technically green #159; if accepted, integrate without weakening poison semantics, then require first-attempt production Pages and a fresh real-account iPhone/WebKit mission before claiming the public demo recovered.
2. Preserve #158 as exact-head **FAIL** evidence unless it is materially revised and requalified; do not waive the durable-poison regressions.
3. Retain genuinely independent post-merge technical review for the #156 current-main surface and finish #144/#146 enforcement for future merges.
4. Obtain genuinely independent acceptance for #153 before integration, then refresh/requalify #89 while retaining its historical Pages failure.
5. Refresh/requalify #152. Do not inherit stale-head qualification.
6. Keep #120/#126 open until a predefined reliability campaign or proven regression-tested root cause supports closure.
7. Resolve #139 through independent protected-byte review, deliberate baseline handling and fresh qualification before refreshing #134.
8. Complete release/recovery qualification without converting rehearsal or simulation into `PASS`.
9. Freeze the confirmatory live-evaluation protocol before observing outcome data, then run R0–R5, degradation, heterogeneous routing and staged 24h → 72h → 30-day soak studies.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, a universal verifier, universally optimal scheduling, guaranteed token/cost savings, blanket production readiness, every-host M4 qualification, completed release/recovery qualification, acceptable long-run WebVM reliability, successful post-#156 end-to-end real-provider execution, root cause of the poisoned-guest production failure, autonomous merge authority, completed long-duration soak, or live proof of the central research hypothesis.
