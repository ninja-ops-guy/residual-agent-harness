# SPEC-INFERENCE-AWARE-ROUTING-001 — Post-v1 Inference-Aware Scheduling

**Status:** DRAFT / POST-v1 / NO IMPLEMENTATION AUTHORIZED  
**Target:** first review after RESIDUAL v1 release  
**Scope:** provider capability discovery, inference telemetry, deterministic routing, and evaluation  
**Non-scope:** custom CUDA kernels, implementing an inference server, modifying model semantics, or weakening existing verification/authority boundaries

## 1. Objective

RESIDUAL already treats heterogeneous intelligence as a schedulable resource. After v1, extend that model so the scheduler can reason about inference-serving characteristics that materially affect latency, throughput, and cost without reimplementing the serving layer.

The first post-v1 optimization set is intentionally narrow:

1. **prefix-cache awareness**;
2. **continuous-batching awareness**;
3. **chunked-prefill awareness**.

These three are prioritized because they directly match RESIDUAL workloads: repeated shared contracts/context across sibling workers, concurrent swarm requests that start and finish at different times, and long evidence/repository prompts that can otherwise delay active decode work.

The following are explicitly lower priority:

- **paged KV / PagedAttention:** expose only as an opaque backend capability/capacity signal;
- **speculative decoding:** experimental, opt-in, and not required for the initial implementation;
- **prefill/decode disaggregation:** deferred until cluster-scale demand justifies separate worker pools and KV transfer.

RESIDUAL MUST remain the control/assurance layer above inference. Provider-native optimization MUST NOT gain authority over mission policy, verification, HITL, budgets, receipts, or integration.

---

## 2. Activation gate

This specification MUST NOT become a v1 release dependency.

Implementation may begin only after:

1. RESIDUAL v1 is released or the maintainer explicitly opens the post-v1 development window;
2. the v1 scheduler/runtime behavior used as the comparison baseline is frozen;
3. representative baseline measurements exist for latency, cost, throughput, and accepted useful work;
4. implementation occurs on a dedicated branch/PR and passes the ordinary review and qualification path.

A documentation-only draft may exist before v1. Its presence does not authorize code changes or broaden current product claims.

---

## 3. Design principle

Inference optimization is a provider/backend responsibility. RESIDUAL consumes **capabilities, fresh telemetry, and execution evidence** and uses them only to choose among already-authorized placements.

The layering is:

```text
Mission / WorkerContract
        |
        v
RESIDUAL policy + capability eligibility
        |
        v
M4 / Runtime routing
        |
        v
Inference-aware scoring
        |
        v
Provider / local inference server
        |
        +-- prefix cache
        +-- continuous batching
        +-- paged KV
        +-- chunked prefill
        +-- speculative decode
        +-- prefill/decode disaggregation
```

The provider may optimize execution. RESIDUAL remains authoritative for whether the work is allowed and whether the result is accepted.

---

## 4. New records

### 4.1 `InferenceCapabilityManifest`

Each inference endpoint MAY publish a versioned, hashable manifest.

Minimum fields:

```text
manifest_version
provider_id
engine_id
engine_version
model_id
model_revision
tokenizer_id
locality
observed_at
fresh_until

prefix_cache:
  support: SUPPORTED | UNSUPPORTED | UNKNOWN
  scope: request | process | host | cluster | provider | UNKNOWN
  cache_identity_version
  max_reusable_tokens: int | UNKNOWN

continuous_batching:
  support: SUPPORTED | UNSUPPORTED | UNKNOWN
  max_active_sequences: int | UNKNOWN
  max_batched_tokens: int | UNKNOWN

chunked_prefill:
  support: SUPPORTED | UNSUPPORTED | UNKNOWN
  max_prefill_chunk_tokens: int | UNKNOWN

paged_kv:
  support: SUPPORTED | UNSUPPORTED | UNKNOWN
  capacity_tokens: int | UNKNOWN

speculative_decode:
  support: SUPPORTED | UNSUPPORTED | UNKNOWN
  mode: draft_model | self_speculative | provider_managed | UNKNOWN
  target_distribution_preserved: true | false | UNKNOWN

prefill_decode_disaggregation:
  support: SUPPORTED | UNSUPPORTED | UNKNOWN
  kv_transfer_supported: true | false | UNKNOWN
```

A stale manifest MUST be treated as stale evidence, not current truth.

### 4.2 `InferenceWorkloadProfile`

Before routing, RESIDUAL MAY derive a content-minimized workload profile:

```text
task_id
mission_revision
prompt_tokens_estimate
expected_output_tokens
shared_prefix_digest
shared_prefix_tokens
sibling_group_id
latency_class
max_cost
required_context_window
required_model_capabilities
privacy_class
profile_revision
```

The shared prefix MUST be represented by digest and token count. Raw prompt text MUST NOT be copied into routing telemetry merely to support cache-aware placement.

### 4.3 `InferenceRuntimeTelemetry`

Fresh telemetry MAY include:

```text
endpoint_id
observed_at
fresh_until
queue_depth
active_sequences
batch_occupancy
kv_tokens_used
kv_tokens_capacity
cache_hit_rate
cached_tokens_reused
prefill_tokens
prefill_ms
time_to_first_token_ms
decode_tokens_per_second
estimated_wait_ms
provider_reported_cost
```

Unsupported values remain `UNKNOWN`. Missing values MUST NOT be fabricated or silently coerced to zero.

### 4.4 `InferenceRouteDecision`

Every inference-aware route MUST emit a deterministic observation containing:

- task and mission revision;
- eligible endpoint set;
- exclusions and reasons;
- workload-profile hash;
- capability-manifest hashes;
- telemetry snapshot hashes and freshness;
- scoring inputs;
- selected endpoint;
- deterministic tie-break reason;
- policy/router revision.

This MAY extend the existing `RoutingDecision` evidence model rather than creating an independent authority path.

---

## 5. Normative requirements

### Capability and evidence

**IAR-R1.** Inference-aware routing MUST run only after ordinary policy, capability, authority, locality, privacy, and budget eligibility filters.

**IAR-R2.** Provider optimization capabilities MUST be treated as execution properties, never as authority grants.

**IAR-R3.** Capability manifests and runtime telemetry MUST expose observation time and freshness.

**IAR-R4.** Stale or missing capability/telemetry MUST become `UNKNOWN`; `UNKNOWN` MUST NOT be silently treated as `SUPPORTED`.

**IAR-R5.** Routing decisions MUST be reproducible from retained workload profile, eligible set, capability manifests, telemetry snapshots, policy revision, and router revision.

**IAR-R6.** Raw prompts, secrets, credentials, private artifacts, and provider keys MUST NOT be added to routing telemetry. Shared-prefix identity MUST use a digest.

### Prefix-cache awareness

**IAR-R7.** The scheduler MAY prefer an eligible endpoint with a confirmed reusable prefix when model revision, tokenizer identity, cache-identity version, and shared-prefix digest are compatible.

**IAR-R8.** A claimed cache hit MUST NOT be inferred solely from repeated prompt text. It requires provider/backend evidence or a deterministic local cache identity that the adapter can verify.

**IAR-R9.** Cache affinity MUST NOT override hard budget, privacy, locality, health, context-window, or model-capability requirements.

**IAR-R10.** Cache affinity MUST NOT make prior model output authoritative. Only prefill/KV reuse is in scope.

**IAR-R11.** Measurements SHOULD record cached tokens reused, prefill time avoided when measurable, and cache-hit status separately from total task success.

### Continuous-batching awareness

**IAR-R12.** Endpoints that support continuous batching MAY advertise current queue depth, active sequence count, and batching capacity.

**IAR-R13.** Scheduler scoring MAY account for expected wait time and available batching capacity, but MUST use bounded deterministic scoring.

**IAR-R14.** Queue/capacity telemetry older than its freshness bound MUST NOT be used as current utilization truth.

**IAR-R15.** RESIDUAL MUST NOT assume that batching support implies admission capacity. Health and current capacity remain separate inputs.

### Chunked-prefill awareness

**IAR-R16.** Long-context workloads MAY prefer an eligible endpoint with chunked-prefill support when this is expected to reduce head-of-line blocking.

**IAR-R17.** The scheduler MUST NOT require a specific chunk size unless the provider exposes a compatible, supported control surface.

**IAR-R18.** Chunk-size tuning, when supported, MUST be bounded by adapter-declared limits and captured in execution evidence.

### Paged KV / PagedAttention

**IAR-R19.** Paged-KV support is an optional backend capability. RESIDUAL MUST NOT implement attention approximation or depend on a specific PagedAttention implementation.

**IAR-R20.** KV capacity MAY inform admission/routing only when reported with freshness and endpoint identity.

### Speculative decoding

**IAR-R21.** Speculative decoding MUST be disabled by default in the first implementation phase.

**IAR-R22.** When later enabled, the adapter MUST identify the speculation mode and whether target-distribution preservation is established or `UNKNOWN`.

**IAR-R23.** Speculative decoding MUST NOT change verifier requirements, acceptance policy, model identity claims, or receipt semantics.

### Prefill/decode disaggregation

**IAR-R24.** Prefill/decode disaggregation is deferred until a separate experiment shows that expected transfer/coordination cost is justified by observed workload scale.

**IAR-R25.** Any later disaggregated design MUST preserve exact model/revision identity across prefill and decode and bind KV-transfer provenance to the execution record.

### Failure and fallback

**IAR-R26.** Inference-optimization failure MUST degrade to an ordinary eligible route when policy permits; it MUST NOT convert an execution failure into `PASS`.

**IAR-R27.** Provider-reported success, cache hit, batching admission, or speculative acceptance MUST NOT substitute for RESIDUAL verification.

**IAR-R28.** Routing fallback MUST be explicit evidence with the rejected optimization path and fallback reason.

---

## 6. Deterministic scoring

The first implementation SHOULD use a transparent weighted or lexicographic policy rather than learned routing.

Recommended order after hard eligibility:

1. healthy/fresh endpoint;
2. confirmed model/context compatibility;
3. confirmed reusable shared prefix, when meaningful;
4. estimated queue/wait cost;
5. total estimated monetary cost;
6. expected time-to-first-token for latency-sensitive work;
7. local preference when capability/policy remain equivalent;
8. stable engine/node identifier tie-break.

A learned policy MAY be evaluated later, but historical performance MUST NOT silently become authorization or bypass verification.

---

## 7. Phased implementation

### Phase A — post-v1 core

Implement only:

- `InferenceCapabilityManifest`;
- `InferenceWorkloadProfile`;
- `InferenceRuntimeTelemetry`;
- deterministic inference-aware routing;
- prefix-cache awareness;
- continuous-batching awareness;
- chunked-prefill awareness;
- evidence and metrics.

No custom inference kernels are required.

### Phase B — qualification and economics

Run frozen comparisons of:

- baseline routing;
- cache-aware routing;
- batching-aware routing;
- chunked-prefill-aware routing;
- combined inference-aware routing.

Hold model, model revision, prompt policy, task corpus, verifier policy, and acceptance criteria constant.

### Phase C — optional backend features

Evaluate, but do not require:

- paged-KV capacity signals;
- speculative decoding.

### Phase D — cluster-scale experiment

Only after observed demand justifies it, preregister an experiment for:

- prefill/decode disaggregation;
- KV transfer overhead;
- pool sizing;
- cross-node failure/recovery behavior.

---

## 8. Evaluation requirements

**IAR-E1.** The baseline MUST be the frozen post-v1 ordinary routing behavior.

**IAR-E2.** Comparative experiments MUST hold worker/model capability constant unless the experiment explicitly varies it.

**IAR-E3.** Report at minimum:

- accepted useful work per wall-clock hour;
- accepted useful work per provider dollar;
- time to first token;
- end-to-end task latency;
- prompt/prefill tokens;
- cached tokens reused;
- cache hit rate;
- decode throughput;
- queue wait;
- verifier rejection rate;
- fallback count;
- evidence completeness.

**IAR-E4.** Raw throughput improvement without accepted-result quality MUST NOT be described as system improvement.

**IAR-E5.** Failed, aborted, fallback, stale-telemetry, and `UNKNOWN` cases remain in the retained dataset.

**IAR-E6.** The evaluation SHOULD separately report:
- model inference time;
- orchestration tax;
- verification time;
- integration time.

**IAR-E7.** A claimed optimization win requires retained evidence that can reproduce the route decision and metric aggregate.

---

## 9. Acceptance criteria

Phase A is implementation-complete only when all of the following are true:

1. at least two adapters pass the same capability-manifest conformance tests;
2. one adapter exercises a confirmed prefix-reuse path;
3. one adapter exercises continuous-batching telemetry or returns explicit `UNSUPPORTED/UNKNOWN`;
4. one adapter exercises chunked-prefill capability or returns explicit `UNSUPPORTED/UNKNOWN`;
5. stale telemetry deterministically fails closed to `UNKNOWN` and does not masquerade as live capacity;
6. routing remains deterministic under identical retained inputs;
7. existing authority, verification, receipt, budget, and HITL tests remain unchanged or stronger;
8. a frozen fixture reconstructs each `InferenceRouteDecision` from retained evidence;
9. no raw prompt, secret, credential, or private artifact appears in the new telemetry records.

Production-performance claims require Phase B live measurements and are not implied by Phase A software tests.

---

## 10. Dependency and ownership

Dependencies:

- M4 deterministic scheduler;
- Runtime/ExecutionEngine capability routing;
- OBS-006-style authoritative telemetry;
- EVAL-001 frozen comparative evaluation;
- post-v1 baseline freeze.

Likely ownership:

```text
residual/runtime/*        capability/adapters
residual/factory/*        deterministic scheduling integration
residual/observability/*  telemetry projections
residual/eval/*           frozen comparative evaluation
docs/specs/*              normative post-v1 contract
```

Exact implementation paths are intentionally non-binding until post-v1 design review.

---

## 11. Non-goals

This specification does **not** authorize RESIDUAL to:

- become a replacement for vLLM, SGLang, TensorRT-LLM, Ollama, or another inference server;
- implement PagedAttention/CUDA kernels;
- assume provider-internal optimizations are trustworthy without evidence;
- alter model output to improve benchmark scores;
- bypass verification because an endpoint is faster or cheaper;
- change v1 release scope;
- claim production performance before comparative evidence exists.

---

## 12. Research questions

The post-v1 experiment should answer:

1. How much repeated RESIDUAL context is actually reusable as a stable prefix across sibling workers?
2. Does prefix-aware placement improve accepted useful work per dollar and wall-clock hour?
3. At what swarm concurrency does continuous batching materially reduce idle inference capacity?
4. Does chunked prefill reduce head-of-line blocking for long-context research/engineering tasks?
5. How often do cache affinity and queue pressure disagree, and which signal better predicts end-to-end accepted-task latency?
6. Do inference-serving gains remain meaningful after orchestration, verification, and integration costs are included?
7. At what scale, if any, do speculative decoding or prefill/decode disaggregation justify their added complexity?

---

## 13. Summary

The post-v1 priority is **not** to build another inference engine. It is to make RESIDUAL capable of observing and exploiting inference-engine capabilities while preserving its existing control model.

The highest-value initial path is:

```text
capability manifest
      +
fresh telemetry
      +
shared-prefix identity
      |
      v
deterministic inference-aware routing
      |
      +--> prefix-cache affinity
      +--> continuous-batch capacity
      +--> chunked-prefill suitability
      |
      v
existing verifier / receipt / integration boundary
```

Paged KV remains a backend detail, speculative decoding remains experimental, and prefill/decode disaggregation remains deferred until scale demonstrates a need.
