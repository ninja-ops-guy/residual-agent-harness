# RESIDUAL

**Build reliable AI systems from unreliable computation.**

RESIDUAL is an evidence-first reliability and control plane for AI-assisted engineering. Workers propose bounded work; the harness owns acceptance. Execution is observed, evidence is retained, candidate outputs are independently checked, and only accepted state is allowed across controlled integration boundaries.

> **AI reliability does not necessarily require making each individual model reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.**

For exact current claims, start with [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md).

## What is implemented

RESIDUAL now spans a connected platform rather than a single agent loop:

- **Core harness:** obligation DAGs, verifier-defined acceptance, residual delegation, evidence negotiation, receipts, bounded budgets, cache revalidation and tamper-evident traces.
- **Command Station:** self-hosted mission/run control, provider/model management, observations, HITL hooks, evidence export and operational UI.
- **Mission Control / WebVM:** browser-facing real-guest workflows, artifact conversations, provider transport, persistent guest-worker execution and fail-closed browser/runtime handling.
- **Factory M2/M3/M4:** bounded worker contracts/runtime, Station-issued evidence/receipts, trusted handoff, deterministic integration/scheduling and capable-runner qualification machinery.
- **Evaluation/research:** frozen workloads, ablations, statistics, fault injection, reproducible evidence bundles, observability/economics tooling and bounded self-maintenance research.

`FAIL`, `UNKNOWN`, malformed output, verifier exceptions, provider failures and abstention do not silently become `PASS`.

## Current main — technically qualified, review-provisional

Current `main` is **`0580c1e53ddb9163d2423d82c0bca846a6d68ba2`**, tree **`0bfc9f70b86f58a75fa58a7a95a2e3b027886a0b`**. Its observed automated/browser qualification is **PASS**, but independent technical acceptance remains review-provisional because merged PRs #145 and #147 have no submitted reviews in the retained GitHub review record. The revision includes the WebVM/runtime and real-provider sequence through those merges.

PR #145 integrated the current browser polling mitigation: long-lived browser paths use a bounded libc relative wait instead of Python positive-duration timeout APIs that retained WebVM diagnostics showed failing at a process-local call-count boundary. PR #147 then hardened real Puter response conformance, made `residual_submit` the explicitly requested transport while retaining exact raw JSON as a compatibility fallback, and changed the visible default Mission Control model to `openai/gpt-5.4-nano` without hidden substitution.

Exact PR heads for #145 (`6dfc537a...`) and #147 (`694ad005...`) each completed their eight observed applicable pull-request workflows **PASS**, including Browser VM Demo CI and Pages generated desktop+narrow browser proof. Exact merged `main@0580c1e5...` also passed its observed push qualification set; Pages run **`35138502311`** passed generated desktop+narrow proof, deployment, published real-guest execution and published narrow Chromium acceptance on that revision.

These are exact-revision CI/browser **PASS** results. They do **not** establish independent review, live Puter inference quality, long-run WebVM reliability, the historical guest-corruption root cause, blank-environment release qualification, actual host-loss recovery or elapsed soak.

## Live-provider boundary

The latest retained real-account evidence before #147 is still negative: after #145 stabilized the WebVM polling path, the real Puter provider returned responses that failed the RESIDUAL worker envelope as `provider_protocol_invalid`; no obligation or artifact was accepted. PR #147 was designed to tighten that transport/conformance boundary, but a fresh successful post-#147 real-account run is not yet retained.

Therefore:

- current automated provider/browser qualification is **PASS** for its test-double/contract scope;
- the retained pre-#147 real-account attempt is **FAIL** for provider protocol conformance;
- post-#147 real-account provider acceptance remains **UNKNOWN / NOT YET ESTABLISHED**.

## WebVM reliability boundary

Issues #120 and #126 remain open. Diagnostic PR #133 retained a reproducible WebVM-specific, process-local CPython positive-duration timed-wait failure affecting at least `time.sleep()` and `select.select()` at call 273, while tested direct libc waits continued beyond that boundary. The exact CPython/glibc/WebVM mechanism and any relationship to earlier `_sha512`, impossible-constructor and allocator-corruption symptoms remain **UNKNOWN**.

The merged libc-wait mitigation avoids the known Python timed-wait surface in the long-lived browser polling paths. Avoidance of that narrow trigger is not proof that the broader historical corruption family has been root-caused or that its production recurrence rate is acceptable.

## Factory / M4 boundary

M2/M3/M4 are implemented. Issues #63 and #48 are closed, and `implementation-status.yaml` is the machine-readable implementation-presence manifest. Current M4 claims remain environment- and evidence-bound: capable-runner qualification is not every-host qualification, and namespace-unavailable execution remains `BLOCKED`/`UNKNOWN`, not `PASS`.

PR #139 is still a protected-test repair candidate. Its capable-runner M4 workflow passed, while ownership-dependent checks intentionally fail closed because the protected ownership baseline still pins the prior protected byte. Do not advance that baseline merely to make CI green. The required order remains independent exact-head review, deliberate baseline decision, then fresh qualification. PR #134 remains downstream of that protected sequence and now also needs refresh against current `main` before any integration claim.

## Governance boundary

The repository has explicit independent-review expectations, but platform enforcement is not yet complete. Issue #144 tracks the gap and PR #146 implements a repository-side independent current-head review check/policy candidate. On #146's current exact head, the independent-review check **FAILS closed** without qualifying approval, and controller/provider CI is also **FAIL**; it is not integration-ready.

PRs #145 and #147 have no submitted reviews in the retained GitHub review record even though they were merged. Do not rewrite green CI as independent technical acceptance. Treat that as governance debt until independent post-merge review is retained, and complete the #144/#146 platform-enforcement work for future merges.

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

1. Retain an independent post-merge technical review for the current WebVM/provider integration and complete issue #144 / PR #146 enforcement for future merges.
2. Run and retain a fresh real-account provider acceptance test on the exact deployed #147 revision; do not infer live-provider success from test-double CI.
3. Keep #120/#126 open until a defined repeated-run reliability campaign or a proven regression-tested root cause supports closure.
4. Resolve #139 through independent protected-byte review, deliberate ownership-baseline handling and fresh qualification before refreshing #134.
5. Refresh/requalify older open integration candidates against current `main`; prior exact-head green evidence remains historical to those heads.
6. Complete release/recovery qualification without converting rehearsal or simulation into `PASS`.
7. Freeze the confirmatory live-evaluation protocol before observing outcome data, then run R0–R5, degradation, heterogeneous-routing and staged 24h → 72h → 30-day soak studies.

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier establishes only the conditions encoded by its contract and evidence. Receipts are evidence of checked acceptance under stated identities and revisions, not certificates of arbitrary truth.

The project does not currently claim universal correctness, a universal verifier, universally optimal scheduling, guaranteed token/cost savings, blanket production readiness, every-host M4 qualification, completed release/recovery qualification, acceptable long-run WebVM reliability, successful post-#147 real-provider inference, autonomous merge authority, completed long-duration soak, or live proof of the central research hypothesis.
