# Residual Control Bench v0 — Specification

Status: pre-freeze specification. Benchmark instances and labels are not yet frozen.

## Objective
Measure control-plane decision quality under machine-verifiable RESIDUAL constraints, separately from general coding/chat capability.

## Inventory
Exactly 1,000 v0 items: routing 200; contract compilation 150; evidence sufficiency 150; retry/escalate/abort 100; budget 100; failure classification 100; adversarial/malformed 100; stale-state/authority 100.

## Item contract
Every item contains: item_id, category, input_state, expected_output, output_schema, verifier_ref, allowed_alternatives, contamination_group, source_provenance, difficulty metadata, safety_critical flag, and immutable content digest.

## Verification
Prefer executable deterministic verifiers. Human judgment may only be used where preregistered with an adjudication protocol and blinded to model identity.

## Contamination controls
Mission/incident lineages are atomic groups. Paraphrases, retries, repairs, templates, derived receipts and counterfactual variants stay together. Deduplicate before splitting. Publish only the permitted benchmark surface; retain holdout labels separately.

## Evaluation
Models receive semantically equivalent information for a given harness condition. Structured outputs are schema-validated before task verification. Invalid output is a failure, not silently repaired unless the evaluated condition explicitly includes a repair layer.

## Harness conditions
A state; B state+contracts; C +memory; D +verification; E +failure/repair history; F full Station. Removal must be structural and logged.

## Reporting
Report per-category and aggregate verified success, false non-escalation, authority violations, invalid-output rate, latency/cost, and confidence calibration. Do not collapse safety failures into aggregate accuracy.

## Freeze artifact
Control Bench v0 release requires an item manifest, split manifest, verifier manifest, baseline manifest, and SHA-256 digests for every immutable artifact.
