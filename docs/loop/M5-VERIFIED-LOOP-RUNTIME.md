# M5 — Verified Loop Runtime (v0.9-loop-preview)

M5 adds host-owned iteration around the existing Factory. It does not create a second execution system.

## Authority boundaries

| Existing component | M5 interaction |
| --- | --- |
| Factory plan/compiler | Produces canonical obligations and plans; M5 never redefines obligation semantics. |
| WorkerContract | Immutable execution input; M5 may request another attempt but cannot widen worker authority. |
| Factory residual obligations | Canonical unresolved work; M5 resubmits only these objects by reference. |
| Evidence Bus | Sole evidence authority; M5 references accepted/rejected evidence roots. |
| Verifiers | Produce PASS/FAIL/UNKNOWN; M5 never converts worker claims into verifier outcomes. |
| M4 Integrator | Sole accepted-state authority; M5 consumes the exact accepted tree hash. |
| Router / orchestration tax | Resolve provider/model/topology from M5 intent; M5 never forces swarm width or provider. |
| Observability | Owns exported metrics; M5 contributes low-cardinality loop metrics. |
| Evaluation | Owns frozen workloads; M5 adds loop modes, not a parallel runner. |
| M5 | Owns continuation, progress/stagnation state, escalation intent, and mission termination. |

## Completion binding

A mission can be COMPLETE only when every required verification result is PASS and each result is bound to both the exact `accepted_tree_hash` and the `accepted_evidence_root` returned by the Factory/M4 boundary. `rejected_evidence_root` is diagnostic only and cannot satisfy mission completion.

Worker prose is never parsed for `done`, `continue`, or any other lifecycle signal in host-owned mode.

## Progress

M5 tracks three signals:

1. residual mass (FAIL + UNKNOWN + unresolved Factory obligation states),
2. exact accepted-tree transitions,
3. obligation resolution (`UNRESOLVED/SUBMITTED -> ACCEPTED|REJECTED|UNKNOWN`).

A tree change without obligation resolution or residual reduction is classified as **churn**, not progress.

## Escalation

M5 emits `ExecutionIntent` only. The Router remains authoritative for the concrete provider, model, worker count, and topology. Escalation intents are cooldown-limited to prevent capability thrashing.

## Deduplication

Each obligation attempt carries a stable key over:

- canonical obligation id,
- input artifact hashes,
- WorkerContract hash.

Factory adapters may use this key to reuse receipt-bound results instead of paying for an equivalent execution again.

## Abort semantics

Human/operator abort is always authoritative. Contract abort conditions may also terminate after a budget/time threshold. Abort stops new dispatch, invokes the existing Factory cancellation boundary, preserves completed evidence, and does not integrate new work after abort.

## Evaluation modes

- `single`: existing one-pass Factory behavior,
- `naive`: re-run the full original obligation set and trust worker self-reported completion (evaluation-only baseline),
- `host-owned`: M5 continuation/completion with fixed routing policy,
- `adaptive`: host-owned plus escalation intents to the existing Router.

The primary research question is whether removing continuation/completion authority from stochastic workers reduces false completion and improves verified completion efficiency.

## Implementation invariant

> Obligations are born in Factory. Evidence is owned by the Evidence Bus. Acceptance is owned by verifiers and M4. Routing is owned by the Router. M5 owns only continuation.
