# INT-005: Ray Execution-Substrate Integration Spec

## Metadata
- **ID**: INT-005
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-003 (pressure), IE-005 (compute ladder), IE-006 (capability routing)
- **Protected boundaries**: Scheduling/admission authority, verifier authority, M4 evidence, disclosure policy, budget authority

## Problem

Distributed execution benefits from mature GPU/CPU placement, actor lifecycle and cluster resource accounting. A compute framework can provide those mechanics, but letting it own retries, route eligibility or acceptance would duplicate RESIDUAL's control plane.

## Goal

Use Ray as an optional **execution and placement substrate** for host-authorized worker/verifier-compute jobs while RESIDUAL retains admission, route eligibility, retry authorization, verification semantics and deterministic integration.

## Non-Goals

- Replacing RESIDUAL's ready-frontier scheduler/admission controller
- Letting Ray decide privacy/capability/budget eligibility
- Letting Ray actor restart/resubmission silently create a new authoritative attempt
- Letting remote verifier actors issue canonical PASS/receipts

## Design

### Authorized execution envelope

```python
@dataclass(frozen=True)
class RayExecutionEnvelope:
    run_id: str
    obligation_id: str
    attempt_id: str
    authorization_hash: str
    retry_token: str | None
    allowed_resources: dict[str, float]
    disclosure_class: str
    input_hash: str
```

Ray receives this envelope only after RESIDUAL has selected an eligible engine/topology and reserved required budget.

### Actors

```python
@ray.remote(max_restarts=0)
class ResidualWorkerActor:
    def execute(self, envelope: RayExecutionEnvelope, task: WorkerTask) -> WorkerComputationResult:
        ...

@ray.remote(max_restarts=0)
class ResidualVerifierComputeActor:
    def compute(self, envelope: RayExecutionEnvelope, evidence: Evidence) -> VerifierComputationResult:
        ...
```

`VerifierComputationResult` is returned to the host verifier boundary. It is **not** an authoritative acceptance decision by itself.

### Placement

Ray may satisfy already-authorized resource placement such as CPU/GPU/custom node labels. Privacy/locality constraints are first converted by RESIDUAL into an allowed placement set; Ray cannot widen that set.

### Retries

- read-only Ray control-plane queries may retry internally;
- worker execution is not auto-resubmitted unless RESIDUAL issues a new attempt/retry authorization;
- ambiguous actor/network failure remains UNKNOWN until host reconciliation;
- side-effectful job replay is prohibited without an idempotency contract.

## Interfaces

```python
class RayAdapter:
    def submit_authorized(self, envelope: RayExecutionEnvelope, task: WorkerTask) -> ExternalExecutionHandle: ...
    def poll(self, handle: ExternalExecutionHandle) -> ExternalExecutionStatus: ...
    def collect(self, handle: ExternalExecutionHandle) -> WorkerComputationResult: ...
    def cluster_capacity(self) -> CapacityObservation: ...
```

## Test Plan

| Test | Description |
|---|---|
| T1 | Authorized dispatch: valid host envelope executes |
| T2 | Unauthorized dispatch: missing/invalid authorization hash is rejected |
| T3 | Hard constraints: Ray cannot place work outside host-authorized resource/locality set |
| T4 | Retry: actor loss does not duplicate execution without a new host retry token |
| T5 | Pressure: capacity observations feed IE-003 but do not bypass admission |
| T6 | Verifier compute: remote computation requires host verifier interpretation before acceptance |
| T7 | Non-interference/replay: authoritative outcomes match direct execution for the same retained inputs |

## Failure Modes

| Failure | Behavior |
|---|---|
| Ray cluster unavailable | no dispatch; host may choose another eligible substrate |
| Actor death/partition with unknown completion | UNKNOWN; no blind replay |
| Resource exhaustion | IE-003 delays/redirects authorized work |
| Result identity mismatch | reject result as protocol violation |

## Exit Criteria

- [ ] Ray is an execution substrate, not a second scheduler/authority
- [ ] Host-authorized retry tokens prevent duplicate execution
- [ ] Privacy/capability/budget eligibility stays host-owned
- [ ] Verifier compute cannot issue accepted state directly
- [ ] Tests T1-T7 pass
- [ ] Q11: exact-head maintainer attestation per #168
