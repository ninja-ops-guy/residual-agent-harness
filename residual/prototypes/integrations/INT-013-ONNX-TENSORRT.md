# INT-013: ONNX Runtime / TensorRT Integration Spec

## Metadata
- **ID**: INT-013
- **Status**: Draft
- **Spec family**: Integration
- **Governed by**: INT-000 (Integration Authority Contract)
- **Depends on**: IE-005 (compute ladder), IE-006 (capability routing)
- **Protected boundaries**: Verifier authority, receipt semantics, disclosure policy, routing eligibility

## Problem

Some local models can execute more efficiently through ONNX Runtime or TensorRT, but gains and numerical behavior depend on model export, precision, hardware, driver and runtime versions.

## Goal

Offer ONNX Runtime/TensorRT as qualified local engine implementations with exact runtime/model identity, semantic regression checks and measured performance profiles.

## Non-Goals

- Claiming a universal speedup
- Auto-selecting a runtime solely because it is installed
- Treating lower precision as equivalent without task/verifier qualification
- Replacing vLLM for workloads where serving/batching is the better substrate

## Design

`OptimizedInferenceAdapter` reports an exact `RuntimeIdentity` containing model/export digest, tokenizer/preprocessor identity, runtime version, provider/engine build flags, CUDA/driver identity and precision mode.

IE-006 selects only among engine variants that pass hard capability/privacy/budget constraints and have qualified observations for the exact identity.

Precision/export variants (`fp32`, `fp16`, `int8`, etc.) are distinct engine revisions. A faster variant that changes candidate behavior is acceptable only if downstream verifier/quality gates still satisfy the frozen qualification protocol.

## Test Plan

| Test | Description |
|---|---|
| T1 | ONNX: qualified model executes through pinned ONNX Runtime identity |
| T2 | TensorRT: engine build/execution identity is retained and reproducible |
| T3 | Semantic: frozen candidate/output checks detect unacceptable conversion/precision drift |
| T4 | Baseline: performance is measured against a frozen reference on declared hardware; no fixed multiplier is required |
| T5 | Routing: IE-006 sees each runtime/precision variant as a distinct measured engine profile |
| T6 | Fallback: unavailable runtime returns typed ineligibility/failure; host router chooses another eligible engine |
| T7 | Non-interference: runtime cannot alter verifier/receipt/integration authority |

## Failure Modes

| Failure | Behavior |
|---|---|
| Export/engine build invalid | engine variant ineligible; fail closed for that variant |
| CUDA/runtime unavailable | route only to another pre-qualified eligible engine |
| OOM | return typed resource failure; host controls batch/retry |
| Numerical/semantic regression | variant fails qualification regardless of speed |

## Exit Criteria

- [ ] Runtime/model/precision identity fully bound
- [ ] Semantic regression gate passes before performance promotion
- [ ] Frozen comparative benchmark completed
- [ ] Tests T1-T7 pass
- [ ] Q11: exact-head maintainer attestation per #168
