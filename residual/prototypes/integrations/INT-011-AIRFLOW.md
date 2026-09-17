# INT-011: Apache Airflow Outer-Orchestration Integration Spec

## Metadata
- **ID**: INT-011
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-001 (mission lifecycle)
- **Protected boundaries**: Internal scheduling authority, verifier authority, receipt authority, deterministic integration, M4 evidence

## Problem

Organizations may want RESIDUAL missions triggered from an existing workflow platform with scheduling, UI, alerts and upstream/downstream data dependencies. Mapping Airflow tasks directly onto internal verification/integration stages would create duplicate retry and authority semantics.

## Goal

Provide Airflow as an **outer mission orchestrator**: Airflow can submit an idempotent RESIDUAL mission, monitor it, collect its terminal evidence reference, and then trigger downstream non-authoritative workflow steps. Internal planning, worker scheduling, verification, retries and integration remain inside RESIDUAL.

## Non-Goals

- Turning internal RESIDUAL stages into independently retryable Airflow tasks
- Calling private verifier/integrator APIs from Airflow
- Letting Airflow retry provider/worker execution
- Requiring Airflow for normal RESIDUAL operation

## Design

```python
with DAG("residual_outer_mission", schedule=None, catchup=False) as dag:
    submit = PythonOperator(
        task_id="submit",
        python_callable=submit_residual_mission,  # idempotency key + request hash
    )
    wait = PythonOperator(
        task_id="wait_for_terminal",
        python_callable=wait_for_residual_terminal_state,  # read-only polling
    )
    collect = PythonOperator(
        task_id="collect_evidence_reference",
        python_callable=collect_terminal_evidence_reference,
    )
    submit >> wait >> collect
```

Airflow receives opaque mission/evidence references rather than raw authority-bearing internal objects wherever possible.

### Retry policy

- `submit`: may retry only with the same idempotency key/request hash;
- `wait/status`: read-only retries allowed;
- `collect`: read-only retrieval retries allowed;
- internal worker/verifier/integration retries are invisible to and not controlled by Airflow.

## Interfaces

```python
class AirflowAdapter:
    def submit_mission(self, request: MissionRequest, idempotency_key: str) -> MissionHandle: ...
    def get_status(self, handle: MissionHandle) -> MissionStatus: ...
    def get_terminal_evidence_ref(self, handle: MissionHandle) -> EvidenceReference: ...
```

## Test Plan

| Test | Description |
|---|---|
| T1 | Submit: Airflow submits one mission with stable idempotency key |
| T2 | Duplicate submit: retry does not create duplicate mission |
| T3 | Monitor: status polling observes terminal state without mutating execution |
| T4 | Authority: adapter exposes no direct verifier/integrator authority |
| T5 | Failure: ambiguous submit is reconciled by idempotency lookup, not blind resubmission |
| T6 | Downstream: terminal evidence reference can feed later workflow tasks |
| T7 | Non-interference: mission outcome matches direct RESIDUAL submission |

## Failure Modes

| Failure | Behavior |
|---|---|
| Airflow unavailable | RESIDUAL remains directly operable |
| Submit response lost | reconcile using idempotency key/request hash |
| Polling unavailable | Airflow task retries read-only status check |
| Mission fails/UNKNOWN | propagate terminal state truthfully; no Airflow override |

## Exit Criteria

- [ ] Airflow is an optional outer orchestrator only
- [ ] Internal verifier/integration/retry authority remains in RESIDUAL
- [ ] Idempotent mission submission is qualified
- [ ] Tests T1-T7 pass
- [ ] Q11: exact-head maintainer attestation per #168
