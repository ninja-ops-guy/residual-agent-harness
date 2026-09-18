# M6-SPEC-007Q Preregistration — Registry-Aware Autonomous Discovery

## Motivation

007O showed that role decomposition can complete the discovery-admission path, but a free-string metric request produced an ambiguous/possibly redundant metric and a semantically unjustified PASS.

007Q repeats split-role autonomous discovery with the versioned Metric Registry from #270.

## Preserved

- same five retained M6 source runs and source-evidence hashes;
- same 007J-derived `context_bytes_non_success_max` value;
- qwen2.5:7b for Evidence Scout, Hypothesis Scientist, Measurement Planner, and independent reviewers;
- no supplied improvement question, target metric, intervention, or hypothesis;
- active evidence selection;
- host authority over evidence truth;
- human approval required;
- no implementation, registry mutation, or promotion authority.

## New independent variable

Metric identity is semantic and registry-bound.

The Measurement Planner may return only:

1. `existing_metric_request` with an exact registered metric ID; or
2. `new_metric_proposal` with a complete MetricDefinition.

The host then:

- resolves existing metrics exactly;
- rejects exact duplicates;
- classifies ambiguous semantics UNKNOWN;
- sends likely semantic overlaps to independent metric review;
- sends mechanically clean new axes to independent metric review;
- never mutates the registry during the run.

The EvidenceSnapshot hash includes registry revision/hash. Any admission receipt cryptographically binds the same registry context through the existing StationReceipt v2 cache/verifier identities.

## Success outcomes

Any of the following is scientifically valid:

- admitted ImprovementSpec -> M6-008 becomes eligible for a separate preregistered candidate experiment;
- admitted, semantically validated MetricDefinitionProposal/MeasurementGap -> evidence acquisition only;
- UNKNOWN/REJECT on ambiguous, duplicate, or ungrounded metric semantics -> fail-closed success of the trust boundary.

A workflow exit code of zero is reserved for an admitted proposal. Rejected/UNKNOWN discovery remains retained research evidence rather than being rerun for green.
