# M6-SPEC-007I Preregistration — Branch-Aware Semantic Review

## Motivation

M6-SPEC-007H produced the first mechanically admissible autonomous discovery proposal, but the semantic reviewer applied ImprovementSpec criteria to a MeasurementGap.

007I changes only semantic review semantics.

## Preserved

- same observed-anomaly MeasurementGap contract as 007H;
- same aggregate EvidenceSnapshot and source-evidence hashes;
- same general `qwen2.5:7b` Scientist/reviewer;
- no supplied improvement question, target metric, intervention, or hypothesis;
- same deterministic mechanical verifier;
- exact evidence binding;
- human approval required;
- no implementation or promotion authority.

## Branch-aware review

For ImprovementSpec:
- reject causal overclaim;
- require falsifiable acceptance;
- require coherent target/preserve metrics and invariants.

For MeasurementGap:
- do not require causal proof or intervention thresholds;
- require a meaningful evidence-bound observed anomaly;
- require a genuinely absent, nonredundant missing measurement;
- require a mechanically collectible measurement;
- require that collecting it could materially resolve the stated uncertainty;
- require appropriate authority/integrity invariants.

## Success

The proposal must pass unchanged mechanical verification and its branch-specific independent semantic review. Only then may RESIDUAL issue the admission receipt.

A successful MeasurementGap does not authorize M6-008 implementation. It authorizes the next measurement/instrumentation experiment needed to close the evidence gap.
