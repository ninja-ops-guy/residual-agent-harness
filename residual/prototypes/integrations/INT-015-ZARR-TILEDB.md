# INT-015: Zarr / TileDB Derived Tensor-Storage Spec

## Metadata
- **ID**: INT-015
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-001 (evidence/artifact identity)
- **Protected boundaries**: Canonical evidence authority, receipt semantics, verifier authority, disclosure policy

## Problem

Large tensor/array artifacts can be expensive to persist and slice as monolithic blobs. Chunked array stores can improve local analysis while creating a risk that a mutable analytical store is mistaken for canonical evidence.

## Goal

Support Zarr and/or TileDB as optional **derived tensor stores** whose arrays/chunks are hash-bound to canonical source artifacts and never become acceptance authority implicitly.

## Non-Goals

- Making Zarr/TileDB canonical evidence stores
- Replacing canonical artifact retention or receipt hashes
- Requiring both backends in every deployment
- Treating storage-level compression/chunk identity as verifier proof

## Design

A stored tensor projection retains:

- canonical source artifact/receipt hash;
- array dtype/shape/order;
- chunking/compression configuration;
- backend/version identity;
- projection manifest hash;
- per-object or manifest-level digest sufficient to detect mutation.

Implement one backend first when there is a concrete workload need; the second backend is optional and must pass the same conformance tests.

```python
class TensorProjectionStore(Protocol):
    def store(self, source: CanonicalArtifactRef, array: ndarray) -> TensorProjectionRef: ...
    def slice(self, ref: TensorProjectionRef, key: tuple[slice, ...]) -> ndarray: ...
    def validate(self, ref: TensorProjectionRef) -> bool: ...
```

## Test Plan

| Test | Description |
|---|---|
| T1 | Store: array projection binds canonical source hash |
| T2 | Slice: bounded slice loads without requiring full materialization where backend supports it |
| T3 | Round-trip: dtype/shape/value semantics preserved for frozen fixtures |
| T4 | Tamper: modified chunks/metadata fail projection validation |
| T5 | Missingness/privacy: storage does not broaden disclosure or coerce absent data |
| T6 | Optional backend: selected Zarr or TileDB adapter passes common conformance; second backend is not mandatory |
| T7 | Authority: projection mutation/deletion cannot change canonical accepted state |

## Failure Modes

| Failure | Behavior |
|---|---|
| Projection corruption | discard/rebuild from canonical source where available |
| Slice out of bounds | typed failure |
| Memory pressure | use smaller bounded chunks; do not change semantic array contents |
| Source hash unavailable | projection is unqualified/UNKNOWN |

## Exit Criteria

- [ ] Tensor projections bind canonical source evidence
- [ ] At least one selected backend passes conformance when needed
- [ ] Tamper detection and round-trip tests pass
- [ ] Backend remains derived/non-authoritative
- [ ] Tests T1-T7 pass
- [ ] Q11: exact-head maintainer attestation per #168
