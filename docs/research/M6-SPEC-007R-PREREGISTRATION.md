# M6-SPEC-007R Preregistration — Corrected Registry-Aware Autonomous Discovery

M6-SPEC-007Q failed before model execution because its generated import edit contained literal newline escape characters. 007R corrects only that apparatus serialization defect.

## Scientific variable

Unchanged from 007Q:

- versioned Metric Registry governs metric identity;
- Evidence Scout actively selects registered metrics;
- Hypothesis Scientist returns ImprovementSpec or InsufficientEvidence;
- Measurement Planner returns either an exact registered metric request or a complete new MetricDefinitionProposal;
- host owns evidence availability and deterministic registry checks;
- ambiguous semantics remain UNKNOWN;
- exact semantic duplicates are rejected;
- likely overlaps/new axes require independent metric review;
- EvidenceSnapshot and receipt identity bind registry revision/hash;
- no registry mutation, implementation, or promotion authority.

## Preserved evidence/model conditions

Same five retained M6 runs, same 007J-derived metric, same qwen2.5:7b roles, no supplied question/target/intervention/hypothesis, same two-cycle bound.

## Apparatus preflight

Before Ollama installation or model execution, CI MUST:

1. compile the experiment script;
2. run all Metric Registry unit tests;
3. load the registry and verify the expected registered metric count/hashable identity.

Failure before model execution is apparatus evidence only.

## Interpretation

- admitted ImprovementSpec -> M6-008 becomes eligible for a separate preregistered experiment;
- admitted semantically valid new MetricDefinitionProposal/MeasurementGap -> evidence acquisition only;
- duplicate/ambiguous/ungrounded metric -> fail closed, no receipt.
