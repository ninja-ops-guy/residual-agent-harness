# INT-016: Prefect / Dagster Outer-Orchestration Adapter Spec

## Metadata
- **ID**: INT-016
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-001 (mission lifecycle)
- **Protected boundaries**: Internal scheduling authority, verifier authority, receipt authority, deterministic integration, M4 evidence

## Problem

Some deployments prefer Python-native workflow products rather than Airflow. Supporting every orchestrator as a required core component would increase dependency and authority complexity.

## Goal

Define a common **outer-orchestrator adapter contract** and allow Prefect *or* Dagster implementations when a deployment needs them. They submit/monitor whole RESIDUAL missions; they do not own internal plan/worker/verifier/integration stages.

## Non-Goals

- Requiring Airflow + Prefect + Dagster simultaneously
- Exposing internal acceptance/integration methods as workflow tasks
- Letting orchestrator retry policies duplicate provider/worker execution
- Selecting one product as universally preferred

## Design

```python
class OuterOrchestratorAdapter(Protocol):
    def submit(self, request: MissionRequest, idempotency_key: str) -> MissionHandle: ...
    def status(self, handle: MissionHandle) -> MissionStatus: ...
    def evidence_ref(self, handle: MissionHandle) -> EvidenceReference: ...
```

### Prefect example

```python
@flow
def residual_outer_flow(request: MissionRequest):
    handle = submit_residual(request)        # idempotent
    terminal = wait_for_terminal(handle)     # read-only polling
    return collect_evidence_ref(terminal)    # opaque reference
```

Dagster follows the same three-step outer contract. Product-specific features such as assets/data-versioning may annotate downstream workflow data but cannot redefine RESIDUAL evidence or receipt authority.

### Adapter selection

Implement **one** adapter only when a concrete deployment use case requires it. Additional adapters must pass the same conformance suite and are optional plugins.

## Test Plan

| Test | Description |
|---|---|
| T1 | Conformance: selected adapter implements submit/status/evidence-ref contract |
| T2 | Idempotency: workflow retry does not duplicate mission execution |
| T3 | Authority: no direct verifier/integrator methods exposed to orchestrator |
| T4 | Failure: mission FAIL/UNKNOWN is propagated, not retried into PASS by workflow policy |
| T5 | Optionality: RESIDUAL runs with no external orchestrator installed |
| T6 | Product adapter: Prefect or Dagster implementation passes common contract tests |
| T7 | Non-interference: direct and orchestrated submissions produce equivalent authoritative outcomes |

## Failure Modes

| Failure | Behavior |
|---|---|
| Orchestrator unavailable | direct RESIDUAL operation remains available |
| Ambiguous submit | reconcile via idempotency key/request hash |
| Workflow retry | repeats only idempotent outer operation, not internal execution |

## Exit Criteria

- [ ] Common outer-orchestrator contract implemented
- [ ] At least one product adapter passes conformance only when deployment need exists
- [ ] No internal authority exported to workflow system
- [ ] Tests T1-T7 pass
- [ ] Q11: exact-head maintainer attestation per #168
