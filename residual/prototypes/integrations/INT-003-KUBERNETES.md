# INT-003: Kubernetes Integration Spec

## Metadata
- **ID**: INT-003
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-003 (pressure/backpressure), IE-002 (telemetry)
- **Protected boundaries**: Scheduling authority, verifier authority, M4 evidence, disclosure policy

## Problem

RESIDUAL's worker/verifier/integration pools are manually managed. There's no elastic scaling, no self-healing, and no cloud-native deployment model. The system cannot scale dynamically with load.

## Goal

Deploy RESIDUAL on Kubernetes with HPA (Horizontal Pod Autoscaler) consuming IE-003 pressure metrics for intelligent scaling.

## Non-Goals

- Letting Kubernetes/HPA decide mission admission, route eligibility, verification, or integration
- Replacing RESIDUAL's scheduler with K8s scheduling
- Changing verifier authority or receipt semantics
- Supporting multiple cloud providers (generic K8s only)

## Design

Kubernetes owns deployment placement and replica capacity. RESIDUAL owns mission admission, route eligibility, retry authorization, verification and integration. HPA may scale capacity in response to IE-003 metrics but scaling never authorizes work by itself.

### HPA Metrics

Custom metrics from IE-003 can include worker/verifier utilization and queue pressure. Metric absence does not become zero pressure; the adapter retains the last qualified/default capacity policy or reports scaling evidence UNKNOWN according to deployment policy.

### KubernetesAdapter

```python
class KubernetesAdapter:
    def scale_worker_pool(self, replicas: int) -> None: ...
    def scale_verifier_pool(self, replicas: int) -> None: ...
    def get_pool_status(self, pool: str) -> PoolStatus: ...
    def expose_pressure_metrics(self, metrics: PressureSnapshot) -> None: ...
```

## Test Plan

| Test | Description |
|---|---|
| T1 | Deploy: declared RESIDUAL components deploy successfully |
| T2 | Scale up: HPA increases eligible pool capacity on frozen high-pressure fixture |
| T3 | Scale down: HPA reduces capacity with hysteresis on frozen low-pressure fixture |
| T4 | Self-heal: failed pod is replaced without duplicating authoritative attempts |
| T5 | Config revision: deployment/config changes are version-bound and require explicit rollout |
| T6 | Metrics: IE-003 pressure is exported to autoscaling without becoming admission authority |
| T7 | Non-interference: replica changes do not alter verifier/receipt/integration semantics |

## Failure Modes

| Failure | Behavior |
|---|---|
| Kubernetes API unavailable | no scaling mutation; existing authoritative execution continues/fails according to host policy |
| HPA metrics unavailable | no fabricated zero; retain bounded/default replica policy and expose UNKNOWN |
| Pod eviction with ambiguous execution | host reconciles attempt identity; no blind replay |
| Invalid deployment/config | rollout fails closed |

## Exit Criteria

- [ ] Kubernetes is deployment/capacity substrate only
- [ ] HPA consumes IE-003 metrics without owning admission
- [ ] attempt identity prevents duplicate acceptance after pod replacement
- [ ] Tests T1-T7 pass
- [ ] Q11: exact-head maintainer attestation per #168
