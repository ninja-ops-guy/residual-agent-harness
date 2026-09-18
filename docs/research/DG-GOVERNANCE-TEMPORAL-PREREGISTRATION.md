# DG Governance/Temporal Controls — Preregistration

This campaign tests the next formal layer of the canonical derivation graph.

## CP-001 ChallengePolicy
Validate eligible challenger roles, allowed grounds, filing-window bounds, resolution authority, withdrawal policy, and governed terminal disposition.

## TA-001 Temporal admission
Create a complete synthetic ImprovementSpec and record an AdmissionDecision at event T. Append a challenge at T+1. Historical AdmissionDecision must retain its original evaluated graph root/verdict while current admission recomputation becomes false.

## EB-001 Execution binding
Create a DerivationSnapshot and EnvironmentContext, then a challengeable ExecutionBinding over declared input artifacts. Challenge the binding. The binding must become CHALLENGED without changing the semantic snapshot.

## RV-002 Revocation
Human COSIGN authorizes an ExecutionAction. Append a Revocation node. HumanDecision and dependent execution authorization must become AUTHORIZATION_REVOKED while history remains present.

## AC-001 Authorship context
A complete admission subgraph must bind each required semantic node to exactly one EnvironmentContext through AUTHORED_UNDER. Missing authorship context must block admission.

## QC-001 Relative quiescence
A QuiescenceCertificate may exist only after exhaustive completion of the declared search policy with zero admissible candidates. It is explicitly relative to evidence root, metric-theory root, search policy, scope, and budget.

## MX soundness regression
Composite MetricExpr tests must distinguish non-strict REFINEMENT from STRICT_REFINEMENT and must remain conservative for disjunction, negation, incompatible topology, and units.

## Claim boundary
PASS establishes only these formalized protocol properties. It does not establish semantic truth, global convergence, or completeness of the refinement logic.
