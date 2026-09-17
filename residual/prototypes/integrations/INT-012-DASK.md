# INT-012: Dask Local Compute-Substrate Spec

## Metadata
- **ID**: INT-012
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-003 (pressure), IE-005 (compute ladder)
- **Protected boundaries**: Scheduling/admission authority, verifier authority, disclosure policy, retry authority

## Problem

Some local CPU-heavy preprocessing or deterministic subcomputations can benefit from parallel execution without requiring a full distributed GPU framework.

## Goal

Use Dask as an optional local CPU compute substrate for **host-authorized, bounded, preferably pure/idempotent subcomputations** while RESIDUAL retains scheduling eligibility, retry authorization and acceptance authority.

## Non-Goals

- Letting Dask authorize retries, routing, verifier outcomes or durable integration
- Treating Dask scheduler success as RESIDUAL acceptance
- Replacing Ray for distributed/GPU placement
- Blindly replaying side-effectful tasks after worker loss

## Design

```python
class DaskAdapter:
    def parallel_map(self, envelope: AuthorizedLocalCompute,
                     fn: Callable, items: list[Any]) -> list[SubcomputeResult]: ...
    def capacity(self) -> CapacityObservation: ...
```

IE-003 limits how much work may be admitted. Dask may use its local scheduler to place already-admitted subcomputations across workers/threads. The adapter disables or intercepts automatic retries for non-idempotent tasks; a new authoritative attempt requires host approval.

Suitable uses include parsing, feature extraction, deterministic analytics and other explicitly declared local substeps. Candidate-generating or side-effectful work must retain attempt identity and host retry semantics.

## Test Plan

| Test | Description |
|---|---|
| T1 | Parallel: authorized pure tasks execute concurrently and preserve item/result identity |
| T2 | Capacity: Dask capacity observations feed IE-003 without bypassing admission |
| T3 | Retry: worker loss does not duplicate non-idempotent work without host authorization |
| T4 | Memory: resource exhaustion returns typed failure rather than silently changing work |
| T5 | Fallback: optional adapter can fall back to sequential host execution where policy allows |
| T6 | Determinism: frozen pure workload produces equivalent normative results sequential vs Dask |
| T7 | Non-interference: Dask cannot alter verifier/receipt/integration outcomes |

## Failure Modes

| Failure | Behavior |
|---|---|
| Local Dask unavailable | host may run approved sequential fallback |
| Worker death with pure idempotent subtask | adapter may retry only under declared idempotency policy |
| Worker death with ambiguous/non-idempotent subtask | UNKNOWN; require host retry authorization |
| Memory exhaustion | typed resource failure; host controls repartition/retry |

## Exit Criteria

- [ ] Dask restricted to host-authorized local compute
- [ ] automatic retry semantics are bounded by idempotency/host authorization
- [ ] IE-003 remains admission authority
- [ ] sequential equivalence test passes for frozen deterministic fixture
- [ ] Tests T1-T7 pass
- [ ] Q11: exact-head maintainer attestation per #168
