# M6-EPI-001 Results — Evidence Sufficiency vs Measurement Gap

## Result

M6-EPI-001 completed successfully as a controlled epistemic-fork experiment.

- run: `35347275081`
- model: `qwen2.5-coder:7b`
- integrated tasks: 2 / 2
- passes: 2
- model calls: 6
- reported tokens: 7,417
- mission wall clock: 499.011 s
- evidence artifact: `10548155225`
- artifact SHA-256: `ed9b1f790039629d2d9dd5bd52f0ef37cd505835e1c08f3ff6094e574fa49008`

Both arms failed their first semantic check and succeeded after bounded repair.

## Sufficient-evidence arm

The snapshot included:
- `repair_attempts_mean = 2.4`
- `task_success_rate = 0.72`
- `verification_failures = 14`

The accepted proposal:
- selected `type = improvement_spec`;
- bound to the exact snapshot hash;
- used the measured `repair_attempts_mean` value of 2.4 rather than inventing a baseline;
- targeted repair attempts;
- preserved task success;
- required human approval.

### Observed contract weakness

The model expressed `acceptance` as free-form prose rather than a mechanically evaluable structured criterion.

It also used `task_success_rate` as a member of `protected_invariants`, conflating a preservation metric with an authority/safety invariant.

These outputs passed the narrow experimental checks but should **not** pass the production M6.2 HypothesisVerifier.

## Insufficient-evidence arm

The snapshot deliberately omitted `repair_attempts_mean` while retaining the question that required it.

The accepted proposal:
- selected `type = measurement_gap`;
- identified exactly `repair_attempts_mean` as missing;
- bound to the exact EvidenceSnapshot hash;
- proposed collecting average repair attempts;
- did **not** include `baseline_value`;
- did **not** include a hypothesis;
- did **not** include acceptance criteria;
- retained human approval.

### Observed contract weakness

The model emitted an empty `preserve_invariants` list.

Again, this passed the deliberately narrow experiment check but must fail the production MeasurementGap verifier.

## Main finding

The model demonstrated the desired **epistemic distinction**:

> measured deficiency → improvement hypothesis  
> missing required measurement → measurement gap

It did so without fabricating the deliberately absent numeric baseline.

However, M6-EPI-001 also demonstrates that model output cannot define its own validity. Prompt instructions alone were insufficient to guarantee:
- structured acceptance criteria;
- correct separation of metrics from protected invariants;
- non-empty invariant preservation.

This strengthens the M6.2 architecture rather than weakening it: the Improvement Scientist should propose, while a deterministic HypothesisVerifier decides whether the proposal is admissible.

## Changes derived from the experiment

The M6.2 spec now requires:
1. mechanically evaluable structured acceptance criteria;
2. a versioned closed vocabulary / registered IDs for protected invariants;
3. non-empty MeasurementGap preserve_invariants;
4. exact EvidenceSnapshot hash binding;
5. explicit metric provenance rules.

## What this demonstrates

For these controlled snapshots, a real local model inside RESIDUAL can distinguish evidence sufficiency from missing evidence and can repair initially nonconforming proposals under immutable checks.

## What this does not demonstrate

It does not yet show autonomous discovery from natural production evidence. The question and required metric were deliberately constructed by the experiment. M6-SPEC-007 must operate on retained RESIDUAL evidence without being handed the improvement hypothesis.
