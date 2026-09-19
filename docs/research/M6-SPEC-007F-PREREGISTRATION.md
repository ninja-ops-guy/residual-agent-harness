# M6-SPEC-007F Preregistration — Evidence-Aware Typed Discovery

M6-SPEC-007E showed that free-text repair could not correct a mechanically known fact: the Scientist repeatedly proposed a MeasurementGap for `provider_timeout_rate` even after being told that the EvidenceSnapshot already measured it at 0.2.

## Question

Can RESIDUAL originate a mechanically admissible improvement proposal when facts derivable directly from trusted evidence are encoded into the typed response schema itself?

## Preserved

- same aggregate EvidenceSnapshot and source-evidence hashes;
- no supplied improvement question, target metric, intervention, or hypothesis;
- same deterministic post-generation verifier;
- same independent semantic reviewer;
- same human approval boundary;
- no implementation or promotion authority.

## Evidence-aware schema

Before the Scientist call, RESIDUAL derives response constraints from the trusted snapshot:

- observation metric IDs: enum of measured metrics;
- target/preserve metric IDs: enum of measured metrics;
- acceptance metric IDs: enum of measured metrics;
- protected invariant IDs: enum of registered invariants;
- MeasurementGap preserve invariants: enum of registered invariants;
- MeasurementGap missing_metric: constrained not to equal an already-measured metric.

These constraints do not choose an improvement objective. They only remove claims that are mechanically impossible given the evidence.

## Success

A single typed Scientist proposal must:
1. satisfy the evidence-aware response schema;
2. pass the unchanged deterministic verifier;
3. receive independent semantic reviewer approval;
4. receive a cryptographic admission receipt.

The proposal remains ineligible for implementation or promotion until human authorization.
