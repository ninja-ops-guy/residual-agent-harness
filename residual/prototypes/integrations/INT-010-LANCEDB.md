# INT-010: LanceDB Analytical Index Spec

## Metadata
- **ID**: INT-010
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-001 (evidence bundle)
- **Protected boundaries**: Canonical evidence authority, receipt semantics, verifier authority, disclosure policy

## Problem

Cross-run analysis over many retained evidence bundles is cumbersome when every query scans raw JSON. An analytical index can accelerate exploration but must not become a second evidence source.

## Goal

Use LanceDB as an optional **derived analytical index** whose rows are hash-bound to immutable canonical evidence bundles.

## Non-Goals

- Making LanceDB authoritative evidence or routing authority
- Replacing canonical bundle retention
- Treating a query result as verifier/receipt evidence without re-binding to canonical sources

## Design

Each indexed row includes `bundle_sha256`, source commit/tree, schema revision, metric projections and an immutable reference to canonical evidence. Full canonical bundle bytes remain outside the index unless stored only as a convenience copy whose digest is verified before use.

```python
class LanceDBProjection:
    def index_bundle(self, bundle: EvidenceBundle) -> IndexReceipt: ...
    def query(self, query: AnalyticsQuery) -> list[IndexedEvidenceRef]: ...
    def verify_ref(self, ref: IndexedEvidenceRef) -> bool: ...
    def rebuild(self, canonical_manifest: Iterable[EvidenceReference]) -> RebuildReport: ...
```

UNKNOWN/null fields remain nullable; they are not coerced to zero for aggregation. Aggregates must expose sample counts/missingness.

## Test Plan

| Test | Description |
|---|---|
| T1 | Index: canonical bundle projects with exact source digest |
| T2 | Query: filters return references bound to canonical bundles |
| T3 | Missingness: UNKNOWN/null values remain visible in aggregate counts |
| T4 | Drift: modified/corrupt index row fails source-digest verification |
| T5 | Rebuild: index can be reconstructed from canonical bundle manifest |
| T6 | Performance: frozen dataset benchmark reports latency/scan cost without a universal target |
| T7 | Non-interference: index mutation/deletion cannot change authoritative run outcome |

## Failure Modes

| Failure | Behavior |
|---|---|
| Index corruption | discard/rebuild from canonical evidence |
| Query timeout | return explicit incomplete/timeout result; do not silently present partial set as complete |
| Disk full | stop indexing and alert; canonical evidence retention policy remains separate |

## Exit Criteria

- [ ] LanceDB is a derived index only
- [ ] Every row binds canonical source digest/schema
- [ ] Missingness semantics preserved
- [ ] Rebuild from canonical evidence is qualified
- [ ] Tests T1-T7 pass
- [ ] Q11: exact-head maintainer attestation per #168
