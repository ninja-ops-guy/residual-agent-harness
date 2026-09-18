# INT-004: vLLM Integration Spec

## Metadata
- **ID**: INT-004
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-004 (context economics), IE-005 (compute ladder), IE-006 (capability routing)
- **Protected boundaries**: Verifier authority, receipt semantics, disclosure policy, provider boundaries

## Problem

The local-model path may leave throughput and repeated-prefix efficiency on the table when it uses a basic inference loop. The magnitude of the opportunity depends on model, hardware, prompt shape, concurrency and runtime version and must be measured rather than assumed.

## Goal

Offer vLLM as an optional local inference engine with continuous batching and runtime-native prefix caching while preserving RESIDUAL routing, disclosure, budget, verification and acceptance authority.

## Non-Goals

- Claiming a universal speedup or latency target
- Replacing local solvers or RESIDUAL semantic context caching
- Allowing vLLM cache identity to substitute for RESIDUAL provenance
- Supporting every architecture/runtime combination

## Design

### Adapter boundary

```python
class VLLMAdapter:
    def execute(self, request: AuthorizedInferenceRequest) -> EngineResult: ...
    def batch_execute(self, requests: list[AuthorizedInferenceRequest]) -> list[EngineResult]: ...
    def runtime_identity(self) -> RuntimeIdentity: ...
```

Every request is already authorized by IE-005/IE-006. The adapter records model digest/revision, tokenizer revision, vLLM version, relevant serving configuration and request hash.

### Context reuse

- IE-004 semantic fragments remain provider/runtime-independent.
- vLLM prefix caching is a runtime optimization only.
- A cache hit does not prove semantic equivalence or acceptance.
- If RESIDUAL adds an explicit wire-cache layer for vLLM, the key must bind exact serialized prompt bytes plus model/tokenizer/framing/runtime identity. Otherwise use vLLM's native cache and report hit/miss telemetry as non-authoritative runtime evidence.

### Measured performance gate

Performance qualification compares a frozen baseline and vLLM on the same:

- model digest and tokenizer;
- hardware/driver/runtime environment;
- prompt corpus and concurrency schedule;
- sampling parameters;
- warmup protocol and repetitions.

Report throughput, TTFT/latency percentiles, memory pressure, prefix-cache hit rate and accepted/integrated goodput. **No minimum universal multiplier is preregistered.** Deployment is justified only if the measured tradeoff meets the environment's declared SLO/budget policy.

## Test Plan

| Test | Description |
|---|---|
| T1 | Single: authorized request produces an engine result |
| T2 | Batch: compatible requests are batched without cross-request disclosure |
| T3 | Prefix cache: repeated exact prefix can report a runtime cache hit |
| T4 | Baseline comparison: frozen comparative benchmark emits confidence intervals/evidence, not a hardcoded speedup |
| T5 | Identity: model/tokenizer/runtime/config revisions are bound to observations |
| T6 | Ladder: IE-005 can dispatch the local-model tier through the adapter |
| T7 | Non-interference: engine change cannot alter host verifier semantics or accepted-state authority |

## Failure Modes

| Failure | Behavior |
|---|---|
| OOM/resource exhaustion | return typed resource failure; IE-003/host decides whether to reduce batch/retry |
| Model/runtime unavailable | mark engine ineligible/failed; router may choose another already-authorized engine |
| Prefix cache miss | normal execution; no semantic penalty |
| Runtime identity unavailable | engine is not eligible for qualified measured claims |

## Exit Criteria

- [ ] vLLM is an optional authorized engine, not a routing authority
- [ ] Context/prefix reuse cannot bypass provenance or disclosure controls
- [ ] Frozen baseline comparison completed on declared hardware/model/workload
- [ ] Tests T1-T7 pass
- [ ] Q11: exact-head maintainer attestation per #168
