# INT-014: Apache Arrow / Parquet Analytical Projection Spec

## Metadata
- **ID**: INT-014
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-001 (event stream), IE-002 (telemetry)
- **Protected boundaries**: Canonical evidence authority, receipt semantics, verifier authority, disclosure policy

## Problem

Columnar projections can make cross-run analysis cheaper and faster, but an analytical file must not silently become the canonical evidence source or discard UNKNOWN/provenance fields.

## Goal

Create Arrow/Parquet **derived projections** of canonical event/economics evidence for query and archival efficiency, with explicit source hashes and round-trip/integrity checks.

## Non-Goals

- Replacing the canonical evidence/event stream
- Guaranteeing a universal compression ratio or speedup
- Dropping null/UNKNOWN values to simplify analytics
- Changing event/verifier semantics

## Design

Each projection carries a sidecar manifest:

```json
{
  "schema": "residual.parquet-projection.v1",
  "source_evidence_sha256": "...",
  "source_schema_revision": "...",
  "projection_schema_revision": "...",
  "parquet_sha256": "...",
  "row_count": 1234,
  "writer_identity": {"pyarrow": "pinned"}
}
```

The Arrow schema preserves nullable fields explicitly. Queries/results derived from Parquet cite the canonical source digest and are not themselves accepted evidence unless separately admitted by RESIDUAL.

## Interfaces

```python
class ArrowProjectionWriter:
    def write(self, stream: EventStream, path: Path) -> ProjectionManifest: ...
    def validate(self, path: Path, manifest: ProjectionManifest) -> bool: ...
```

## Test Plan

| Test | Description |
|---|---|
| T1 | Serialize: canonical event stream projects to Arrow table |
| T2 | Integrity: Parquet and source digests are manifest-bound |
| T3 | Nulls: UNKNOWN/null fields survive projection |
| T4 | Round-trip: fields required by the projection contract reconstruct exactly |
| T5 | Predicate: filtered query can avoid reading irrelevant row groups/columns where supported |
| T6 | Baseline: size/read-cost comparison is measured on frozen datasets with no universal minimum ratio |
| T7 | Authority: corrupted/modified projection cannot change canonical evidence or accepted state |

## Failure Modes

| Failure | Behavior |
|---|---|
| Schema mismatch/corruption | projection invalid; canonical source remains authoritative |
| Source digest unavailable | projection is unqualified/UNKNOWN |
| Memory pressure | bounded batch/row-group writing; no semantic field dropping |

## Exit Criteria

- [ ] Projection manifest binds source + Parquet bytes
- [ ] UNKNOWN/null semantics preserved
- [ ] Comparative storage/query evidence measured rather than assumed
- [ ] Canonical source remains authoritative
- [ ] Tests T1-T7 pass
- [ ] Q11: exact-head maintainer attestation per #168
