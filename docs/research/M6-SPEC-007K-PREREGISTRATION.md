# M6-SPEC-007K Preregistration — Close the Admitted MeasurementGap

## Starting point

M6-SPEC-007J formally admitted MeasurementGap proposal SHA-256
`3876881dc9dd662197217337c0b5ae7fd20f626e4221e82cfc24154437779d23`
with admission receipt
`09f3bbc0dba17ca7344b485cf4a8757dc11382e0ac2f6b46ece8fb7f74bd80c9`.

The requested missing metric was:

`context_bytes_non_success_max`

## Evidence acquisition

The underlying retained source records already contain the per-run `first_request_bytes` values from which `context_bytes_non_success_mean` was derived.

007K closes the gap deterministically:

```text
context_bytes_non_success_max =
    max(first_request_bytes for retained runs where outcome != success)
```

For the bound retained runs this evaluates to **32,652 bytes**.

The enriched EvidenceSnapshot records:
- the new metric/value;
- derivation method;
- contributing run IDs;
- contributing evidence artifact hashes;
- originating 007J admission receipt.

The full enriched snapshot is rehashed before the Scientist sees it.

## Discovery question

No improvement question, target metric, intervention, or hypothesis is supplied.

The Scientist receives the enriched EvidenceSnapshot and must again choose either:
- an ImprovementSpec-like proposal supported by the now-richer evidence; or
- another legitimate MeasurementGap.

## Gates

Same as 007J:
- typed structured output;
- deterministic evidence admission;
- branch-aware independent semantic review;
- cryptographic admission receipt;
- human approval required;
- no implementation or promotion authority.

## Interpretation

An admitted ImprovementSpec makes M6-008 eligible for a separate preregistered candidate-generation experiment.

An admitted MeasurementGap does not. It triggers another evidence-acquisition step instead.
