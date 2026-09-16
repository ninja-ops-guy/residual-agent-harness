# RESIDUAL

**Build reliable AI systems from unreliable computation.**

RESIDUAL is an evidence-first reliability and control plane for AI-assisted engineering. It treats model output as an untrusted proposal rather than an answer: workers operate inside explicit contracts, execution is observed, outputs are independently checked, and only accepted artifacts are allowed to cross controlled integration boundaries.

> **AI reliability does not necessarily require making each individual model reliable. Reliability can emerge from constraining, observing, verifying, and deterministically integrating unreliable computation.**

RESIDUAL is the applied engineering system used to make that hypothesis testable.

**Current-state documentation:** [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)

## Why this exists

Most agent systems concentrate capability and authority inside the worker. RESIDUAL separates capability from authority.

```text
Requirement / intent
        ↓
Frozen plan + worker contracts
        ↓
Route / schedule bounded workers
        ↓
Observe execution + collect evidence
        ↓
Independent verification
        ↓
PASS ──→ controlled deterministic integration ──→ receipt / audit
  │
  └─ FAIL / UNKNOWN ──→ counterexample / residual ──→ retry / escalate
```

The model is replaceable compute. The harness owns acceptance authority.

## What is implemented

### Core harness

The original harness provides obligation DAGs, immutable evidence snapshots, verifier-defined acceptance, counterexample-directed repair, residual delegation, evidence negotiation, receipt-bound caching, disclosure controls, budgets and tamper-evident traces.

`FAIL`, `UNKNOWN`, malformed output, verifier exceptions, provider errors and abstention never silently become success.

### Command Station and Mission Control

Command Station exposes the harness as a self-hosted operations console with mission/spec import, run control, local/cloud execution, provider routing, observation traces, model management, HITL hooks, security inspection, downloadable evidence and source-release packaging.

The browser Mission Control path supports multi-turn artifact conversations, explicit parent lineage, isolated previews, browser-local restoration, optional provider transport, typed provider failures and real-guest acceptance checks. Generated preview artifacts remain outside repository mutation authority; repository-changing autonomous work belongs behind explicit maintenance/Factory controls.

### Factory / Studio runtime

The Factory runtime extends RESIDUAL into multi-worker execution with frozen execution plans, immutable worker contracts, isolated worktrees, bounded runtime, host-owned termination, Station-issued receipts, evidence-bus handoff, deterministic integration, scheduler machinery, lifecycle recovery, side-effect gateways, cluster/distributed surfaces, observability and adversarial tests.

M2/M3/M4 are implemented under `residual/factory/` and related packages. Issues #63 and #48 are closed. PR #109 established the capable-runner M4 qualification path, and the previously accepted revision `22a5bae54ec12987ffd7a90d881fb4533c9b4b97` received a retained zero-skip qualification in run `35036589940`.

Current accepted `main` is **`f1e62936a7ce72b801c852c1d7428d4c6ed4152c`** (tree **`733b28ab38fec71e8029250e858db486cea22dd8`**), the merge of PR #132. The exact-current-main push workflows are green for Factory ownership, measured-evaluation binding, clean install, Command Station, controller/provider contracts, the capable-runner M4 prerequisite/qualification workflow, and Pages/WebVM (`35046857227`). That is exact-tree evidence for the named workflows and environments; it is not blanket production readiness or every-host qualification.

### Protected self-hosting and research bundles

PR #132 merged a bounded self-maintenance/research experiment and frozen research-bundle tooling. The retained trial used exactly **one live external GPT-5.6 Sol worker** to author a four-file research-bundle candidate against a frozen base. RESIDUAL reconstructed that candidate, applied deterministic acceptance predicates, classified it `PR_READY`, and retained `merge_authorized=false`.

The trial also retained controller/policy stress experiments (100-generation lineage, 1,000 synthetic fault trials, and 200 documentation-policy cases). Those are **not** 100 live model-authored generations, 1,000 autonomous self-modification attempts, independent trust-domain review, or evidence of autonomous merge authority. The merge of PR #132 was an external repository action; the self-maintenance controller itself has no merge-authorized path.

### Evaluation and soak infrastructure

`residual/eval/` provides frozen workloads, repeated runs, ablations, statistics, fault injection, report reconstruction and measured Factory hooks. The repository also contains release/soak preparation, but live-model confirmatory evaluation and elapsed 24h → 72h → 30-day production soak remain future evidence gates.

## Design principles

1. **Workers propose; acceptance is independent.**
2. **UNKNOWN is not PASS.** Missing or incomparable evidence stays visible.
3. **Contracts precede execution.** Scope, tools, resources, evidence and checks are explicit.
4. **Evidence survives handoffs.** Receipts bind accepted results to artifacts and relevant identities.
5. **Escalate the residual, not the whole problem.**
6. **Integration is deterministic.** Stochastic workers do not get unilateral authority over durable state.
7. **Parallelism must earn its cost.**
8. **Verifier reliability is itself measured.**
9. **Local and cloud compute are policy-governed resources.**
10. **Claims require exact-tree evidence.** Historical green results do not automatically qualify later code.

## Current status and qualification boundary

Current accepted `main` is `f1e62936a7ce72b801c852c1d7428d4c6ed4152c`. PR #132 changed research/self-maintenance surfaces, not protected Factory/M4 implementation, and the post-merge exact-main qualification workflows listed above completed successfully.

The main unresolved operational reliability boundary is WebVM guest lifecycle stability. Issue #120 remains open for intermittent Pages/WebVM failures, and issue #126 has been reopened after retained production evidence showed later fresh guest Python processes failing inside the standard library after earlier mission steps had succeeded. PR #136 is the current persistent-worker mitigation candidate on `f1e629...`; its exact head `1eaca5a2...` remains **FAIL / unqualified** after Pages/WebVM run `35088995295` rejected `/data/residual-worker.control` as unsafe and controller/provider run `35088995307` also failed. These are candidate failures, not accepted-main regressions or proof of the historical corruption root cause. PR #134 remains held until the runtime lifecycle boundary is stabilized and requalified.

The other major integration candidates have now been refreshed onto current accepted `main`, but their qualification states differ:

- **PR #118 — runtime/DSM closure:** live head `334527da...` is based on `f1e62936...` and its current exact-head workflow set is green. Historical first-attempt failures remain retained; fresh independent technical acceptance of this exact repaired head is still required before integration.
- **PR #131 — core SoakState persistence:** live head `368f3085...` is based on `f1e62936...` and all seven applicable exact-head workflows are green. Independent technical acceptance is still required, and this hardening does not create elapsed-soak evidence.
- **PR #115 — release preparation:** live head `b1ffbb48...` is also based on `f1e62936...`, but its current exact-head qualification is **incomplete** because controller/provider run `35087653566` is `CANCELLED`. Do not treat the candidate as fully green until the required exact-head workflow set completes successfully and independent review accepts that head.

Before paper-facing live reliability claims, the priority gates are:

1. stabilize and independently qualify the WebVM lifecycle path (#126 / #136), retaining every failure rather than rerunning it away;
2. rebase/requalify #134 only after the runtime release is stable, then obtain fresh real-provider evidence;
3. independently review the current-main-qualified #118 and #131 heads, while preserving their component-level non-claims;
4. complete fresh exact-head qualification and independent review for #115 before using its release/recovery procedures as an integration candidate;
5. complete release/recovery qualification and a defined WebVM reliability campaign;
6. finish the remaining reproducibility/statistical work tracked by #35 and freeze the live evaluation protocol before confirmatory results;
7. run fixed-model R0–R5, degradation and heterogeneous-routing studies;
8. progress through elapsed 24h → 72h → 30-day soak only after shorter gates are clean.

## Traceability

Issue #48 is closed. `implementation-status.yaml` and `docs/status/IMPLEMENTATION_STATUS.md` describe implementation presence; they do **not** convert missing release, recovery, live-provider, soak or research evidence into PASS.

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

See [`START-HERE.md`](START-HERE.md) for installation, GPU options, storage and troubleshooting.

### Core harness

```bash
python3 -m residual demo
python3 -m residual verify-trace runs/latest/trace.jsonl --result runs/latest/result.json
python3 -m residual benchmark --output runs/benchmark.json
```

### Factory planning

- [`docs/factory/PLAN-CONTRACT.md`](docs/factory/PLAN-CONTRACT.md)
- [`docs/factory/M2-EXECUTION.md`](docs/factory/M2-EXECUTION.md)
- [`docs/factory/M3-EVIDENCE-BUS.md`](docs/factory/M3-EVIDENCE-BUS.md)
- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)

## Architecture at a glance

| Layer | Responsibility | Trust boundary |
| --- | --- | --- |
| Requirement / plan | Convert intent into explicit obligations and dependencies | Frozen before execution |
| Router / scheduler | Select execution under policy and observed performance | Policy boundary |
| Worker runtime | Produce candidates under bounded contracts | Untrusted computation |
| Evidence bus | Preserve observations, artifacts, hashes and outcomes | Evidence/admission boundary |
| Verifier layer | Evaluate acceptance and surface counterexamples/`UNKNOWN` | Independent authority |
| Integrator | Apply eligible work and control state transitions | Deterministic authority |
| Receipt / audit | Bind accepted state to evidence and revisions | Reproducibility/audit |
| Evaluation | Measure component correctness vs accepted-state correctness | Independent research boundary |

## Research program

The working paper, **“Reliability from Unreliable Computation: An Evidence-First Architecture for Verifiable Multi-Agent AI Systems,”** develops a system-level hypothesis intended to be falsifiable. The repository does **not** claim the hypothesis is proven.

Key confirmatory measures include raw worker correctness `P(X)`, acceptance coverage `P(A)`, accepted correctness `P(X|A)`, AER/ASSR, verifier false acceptance/rejection/`UNKNOWN`, cost, latency, throughput and orchestration overhead.

Start with:

- [`docs/CURRENT_STATUS.md`](docs/CURRENT_STATUS.md)
- [`docs/research.md`](docs/research.md)
- [`docs/research/PROTECTED_SELF_HOSTING_TRIAL.md`](docs/research/PROTECTED_SELF_HOSTING_TRIAL.md)
- [`docs/research/RESEARCH_BUNDLES.md`](docs/research/RESEARCH_BUNDLES.md)
- [`docs/evaluation.md`](docs/evaluation.md)
- [`docs/papers/reliability-from-unreliable-computation.md`](docs/papers/reliability-from-unreliable-computation.md)

## Scope and non-claims

RESIDUAL is an implemented research and engineering platform, not a universal proof system. A verifier proves only what its contract and evidence allow it to check. Receipts are evidence of checked acceptance under stated conditions, not certificates of arbitrary truth. Plugins and host integrations remain trusted code unless explicitly isolated by another boundary.

The project does not currently claim a universal verifier, universally optimal scheduler, guaranteed token savings, guaranteed quality preservation, blanket production readiness, every-host M4 qualification, completed release/recovery qualification, acceptable long-run WebVM failure rate, autonomous recursive self-improvement, autonomous merge authority, live proof of the central reliability hypothesis, completed long-duration soak, or first-in-literature status.

---

**RESIDUAL’s thesis is architectural:** stochastic workers do not have to become trustworthy before they can be useful. Make their authority small, their behavior observable, their outputs checkable, and their accepted effects controlled and reproducible.
