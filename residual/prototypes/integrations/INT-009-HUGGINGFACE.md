# INT-009: Hugging Face Hub Discovery Integration Spec

## Metadata
- **ID**: INT-009
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-006 (capability routing)
- **Protected boundaries**: Verifier authority, disclosure policy, provider boundaries, routing eligibility

## Problem

Manual model catalogs make discovery cumbersome. Public model metadata can help locate candidate engines, but popularity and pipeline tags are not measured RESIDUAL capability/reliability evidence.

## Goal

Use Hugging Face Hub as a **candidate discovery/catalog source**, then require explicit qualification before a discovered model becomes an active IE-006 engine profile.

## Non-Goals

- Treating downloads/likes/pipeline tags as pass rate, correctness, latency or cost
- Auto-enabling a discovered model for production routing
- Replacing RESIDUAL engine profile or qualification evidence

## Design

### Discovery record

```python
@dataclass(frozen=True)
class DiscoveredModelCandidate:
    model_id: str
    revision: str | None
    pipeline_tag: str | None
    library_name: str | None
    downloads: int | None
    gated: bool | None
    metadata_sha256: str
    source: str = "huggingface-hub"
```

Unknown measured fields are **not** filled with zero.

### Promotion gate

A candidate becomes `EngineProfile` only after a qualified probe/benchmark produces retained observations for the exact model revision and runtime:

```python
class CandidateQualifier:
    def qualify(self, candidate: DiscoveredModelCandidate,
                protocol: QualificationProtocol) -> QualifiedEngineProfile | QualificationFailure:
        ...
```

The promotion record binds candidate metadata, model revision/digest, runtime/tokenizer identity, capability tests, disclosure eligibility and measured latency/cost/acceptance evidence. Ground-truth correctness is included only where an independent grader exists.

## Test Plan

| Test | Description |
|---|---|
| T1 | Discovery: public candidates can be enumerated |
| T2 | UNKNOWN: unmeasured latency/cost/pass fields remain null/UNKNOWN |
| T3 | Metadata: pipeline tag is descriptive only and cannot satisfy hard capability proof by itself |
| T4 | Revision: candidate/profile binds exact model revision or is not production-eligible |
| T5 | Promotion: unqualified candidate cannot enter active IE-006 feasible set |
| T6 | Qualification: measured probe can promote exact revision into a profile |
| T7 | Non-interference: Hub outage/catalog changes do not change already-frozen active profile revisions |

## Failure Modes

| Failure | Behavior |
|---|---|
| Hub unreachable/rate-limited | use retained discovery cache for browsing only; no new qualification claim |
| Revision unavailable | candidate remains non-production/UNKNOWN |
| Missing metadata | retain null/UNKNOWN fields |
| Model disappears after qualification | existing profile remains bound to its retained revision/artifact; new fetch fails closed |

## Exit Criteria

- [ ] Discovery records are separate from qualified engine profiles
- [ ] No popularity metadata is treated as reliability evidence
- [ ] Exact revision qualification required before active routing
- [ ] Tests T1-T7 pass
- [ ] Q11: exact-head maintainer attestation per #168
