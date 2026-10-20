# INT-006: MLflow Experiment-Tracking Projection Spec

## Metadata
- **ID**: INT-006
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-001 (evidence bundle), IE-002 (telemetry)
- **Protected boundaries**: Canonical evidence authority, receipt semantics, verifier authority, disclosure policy, routing authority

## Problem

RESIDUAL evidence bundles are authoritative retained artifacts, but comparing many runs through raw JSON is cumbersome. A tracking UI can improve analysis without becoming a second source of truth.

## Goal

Project finalized evidence/telemetry into MLflow for experiment comparison and cataloging while keeping canonical RESIDUAL evidence immutable and authoritative.

## Non-Goals

- Making MLflow the canonical evidence store, model authority, router, or acceptance authority
- Mutating a finalized evidence bundle to insert an MLflow run ID
- Auto-promoting a model because MLflow labels one run "best"
- MLflow model deployment

## Design

### Projection flow

1. RESIDUAL finalizes and hashes the canonical evidence bundle.
2. MLflow run is created from a derived projection of config/metrics.
3. The canonical bundle is uploaded as an artifact copy or referenced by immutable URI/digest.
4. A separate `residual.mlflow-link.v1` sidecar binds `canonical_bundle_sha256 -> mlflow_run_id`.

Unknown/null values stay absent/null according to MLflow encoding policy; they are never logged as zero solely to satisfy the backend.

### Engine catalog

A qualified `EngineProfile` MAY be mirrored into the MLflow registry for browsing. Registry state is descriptive only; active IE-006 eligibility still comes from RESIDUAL's qualified profile store and hard constraints.

## Interfaces

```python
class MLflowProjectionAdapter:
    def log_bundle_projection(self, bundle: EvidenceBundle) -> MLflowLink: ...
    def compare_runs(self, run_ids: list[str]) -> ComparisonProjection: ...
    def mirror_engine_profile(self, profile: QualifiedEngineProfile) -> str: ...
```

## Test Plan

| Test | Description |
|---|---|
| T1 | Projection: finalized bundle projects into one MLflow run |
| T2 | Immutability: MLflow link is sidecar; canonical bundle bytes are unchanged |
| T3 | UNKNOWN: missing usage/cost/correctness is not converted to zero |
| T4 | Integrity: sidecar binds canonical bundle digest and MLflow run ID |
| T5 | Catalog: only already-qualified engine profiles may be mirrored |
| T6 | Advisory query: MLflow comparison/ranking cannot change IE-006 active routing |
| T7 | Non-interference: MLflow unavailable/corrupt cannot change authoritative run outcome |

## Failure Modes

| Failure | Behavior |
|---|---|
| MLflow unavailable | buffer/drop projection per telemetry policy; canonical evidence unaffected |
| Artifact upload fails | link/projection remains incomplete and explicitly marked; never claim mirrored artifact exists |
| MLflow data diverges | canonical RESIDUAL evidence wins; flag projection drift |

## Exit Criteria

- [ ] MLflow is a derived projection only
- [ ] Canonical bundle stays immutable
- [ ] Qualified profile mirroring cannot authorize routing
- [ ] UNKNOWN/null semantics preserved
- [ ] Tests T1-T7 pass
- [ ] Q11: exact-head maintainer attestation per #168
