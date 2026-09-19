# SPIKE-A2A-000 v1.0 — A2A ↔ RESIDUAL Semantic Feasibility and Trust-Boundary Validation

**Status:** APPROVED FOR IMPLEMENTATION  
**Scope:** Experimental / isolated  
**Production authority:** NONE  
**M4 authority:** NONE

## Protected invariant

```text
REMOTE PROTOCOL STATE != ACCEPTED STATE
```

Only the authoritative RESIDUAL verification path may cross that boundary.

## Objective
Determine whether A2A 1.0 can serve as an interoperability boundary for RESIDUAL without weakening the acceptance-authority model. Semantic feasibility only: no production code, no M4 modifications, and no commitment to integration. A well-evidenced GO, REVISE, or NO-GO is success.

A2A may remain only the transport/federation envelope. WorkerContract, obligation, evidence, verification, and receipts remain RESIDUAL-native unless the spike proves a stronger mapping safe.

## Questions
1. **Q1 Task/obligation mapping.** A2A taskId/contextId/messageId and RESIDUAL run_id/obligation_id remain distinct and are joined by a BindingRecord.
2. **Q2 Streaming/provisional state.** Received events and assembled artifacts remain non-authoritative until explicit RESIDUAL verification.
3. **Q3 Provenance/evidence.** Protocol provenance is distinct from RESIDUAL evidence provenance and is joined into a unified audit trail.
4. **Q4 Lifecycle/termination.** WORKING, INPUT_REQUIRED, AUTH_REQUIRED, COMPLETED, FAILED, REJECTED, and CANCELED are mapped without allowing COMPLETED to mean PASS.
5. **Q5 Identity/authority.** Agent identity is a claim; authentication != authorization != qualification != acceptance.

The dependency graph (Q1→Q2/Q5→Q3→Q4→E2E) is itself a hypothesis and MUST be revised if execution disproves it.

## BindingRecord
A BindingRecord MUST bind, without conflating, A2A task/context/message identity to RESIDUAL run/obligation identity, creation time, and exact snapshot references.

## Impedance taxonomy
- **Lossless:** source semantic fully preserved.
- **Conservatively representable:** translation cannot grant authority, weaken acceptance, broaden disclosure, erase verification-required provenance, or turn unresolved/UNKNOWN into acceptance.
- **Adapter-specific state:** safe bridge requires local non-standard state.
- **Protocol extension:** required semantic cannot be represented without extending A2A.
- **Fundamentally incompatible:** no translation preserves the protected invariants.

## Mandatory F0 canaries
1. Peer reports COMPLETED with a deliberately incorrect artifact → verifier FAIL, no accepted receipt, failure evidence retained.
2. Valid artifact arrives and transport dies before terminal state → artifact remains provisional; recovery cannot silently promote it.

Additional probes: malformed Agent Card, false capability claim, identity mutation mid-session, wrong provenance, excessive streaming, cancellation race.

## SDK and binding
Implementation MUST target A2A specification 1.0.x and pin the exact official Python SDK version used. The evidence bundle MUST retain spec version, SDK version/release or commit where available, and selected binding. The normative spike does not hard-code unstable SDK APIs.

## Isolation
Implementation lives under `spikes/a2a/`. It MAY consume stable public RESIDUAL interfaces needed to test reality, but MUST NOT modify protected M4/trust-boundary paths or import M4/factory internals merely to make the spike pass.

CI MUST reject changes to protected paths and prohibited imports.

## Evidence bundle
Retain content-addressed manifest/environment, raw protocol requests/responses and Agent Card, BindingRecords, semantic map, impedance report, execution events, verifier results, termination records, adversarial results, receipts, implementer summary, independent reviewer assessment, and final verdict.

The manifest binds the exact implementation commit, RESIDUAL revision, A2A spec/SDK/binding, environment fingerprint, qualification configuration, and evidence root.

## Decision procedure
- **F0 acceptance-authority incompatibility:** immediate NO-GO for proposed architecture.
- **F1 security/trust-boundary incompatibility:** STOP + architecture review.
- **F2 core interoperability incompatibility:** REVISE unless a conservative adapter exists.
- **F3 optional capability incompatibility:** document/defer; does not block GO.

GO requires Q1–Q5 supported by retained evidence, no unresolved F0/F1, every F2 conservatively resolved, and a complete evidence bundle. Implementer and reviewer are logically separate roles and produce separate artifacts even if one human performs both.

## Time box
Nominal 5 engineering days; hard cap 10 engineering days / 1 engineer-FTE. Stop on F0; review on F1. Continue beyond day 5 only for a named falsifiable experiment capable of resolving remaining uncertainty.

## M4 protection
Receipt format, verifier authority, evidence fabric, and protected M4 code remain unchanged. Spike-specific evidence may reference existing receipt-v2/public evidence APIs but cannot redefine their authority semantics.

## Success principle
**GO is not the desired result.** A well-evidenced NO-GO is a successful spike if it demonstrates that A2A cannot preserve a RESIDUAL invariant.
