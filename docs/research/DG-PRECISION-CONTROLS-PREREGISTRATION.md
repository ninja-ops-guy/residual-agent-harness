# Derivation Graph Precision Controls — Preregistration

This campaign tests the precision requirements added after the initial DG architecture review.

## CH-001 — mandatory semantic challengeability

Semantic node types must require a challenge policy. Explicit challengeable=false must fail construction.

## HR-001 — durable opaque-handle resolution

A model-authored node cites invocation handle ev_3. The Host persists a resolution node/edge to EvidenceFact A.

Replay must resolve through the stored graph relation, not through a live capability table. A different invocation namespace must fail.

## CA-001 — challenge-aware admission

A complete synthetic ImprovementSpec admission subgraph is the positive control.

Adding an unresolved Challenge to its required MetricDecision must make admission false.

A separately governed supersession of a Challenge must stop active invalidation without deleting historical nodes.

## MX-001 — composite metric refinement

A conjunction of p99 latency, throughput, and error-rate constraints is refined.

Expected:
- compatible stricter child constraints -> STRICT_REFINEMENT;
- any child coarsening -> UNKNOWN;
- incompatible topology -> UNKNOWN;
- incompatible unit dimension -> not mechanically admitted.

## AU-001 — authorization-root execution

HumanDecision COSIGN authorizes an ExecutionAction implementing an ImprovementSpec.

Challenge/revocation of the HumanDecision must invalidate/challenge the ExecutionAction while preserving history.

## ENV-001/002 — environment drift and roots

REQUIRED_EXACT drift must FAIL environment qualification.
REQUIRED_COMPATIBLE drift must require an explicit compatibility verdict.
OBSERVATIONAL queue-latency drift must be retained but not automatically change PASS.

The same semantic DAG root remains unchanged while execution roots differ when observed-environment commitments differ.

## Claim boundary

These are deterministic architecture controls. PASS establishes only the encoded graph/capability/refinement/environment predicates. It does not establish scientific truth or model reliability.
