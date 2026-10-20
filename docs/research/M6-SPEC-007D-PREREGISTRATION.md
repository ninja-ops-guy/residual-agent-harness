# M6-SPEC-007D Preregistration — Typed Autonomous Discovery

## Purpose

M6-SPEC-007C reached autonomous objective selection but failed formal admission because the model repeatedly malformed JSON punctuation while expressing a stable evidence-grounded idea.

M6-SPEC-007D removes serialization from the Scientist's scientific task.

## Architecture

```text
EvidenceSnapshot
      ↓
typed structured Scientist response
      ↓
RESIDUAL canonical serializer
      ↓
deterministic mechanical verifier
      ↓
independent semantic reviewer
      ↓
cryptographic admission receipt
```

The Scientist no longer writes `proposal.json` source text.

## Preserved conditions

- same aggregate EvidenceSnapshot values used by 007B/007C;
- same raw evidence hashes;
- no supplied improvement question;
- no supplied target metric;
- no supplied intervention;
- no supplied hypothesis;
- same registered invariant vocabulary;
- same mechanical admissibility semantics;
- human approval remains mandatory;
- no source-write, Git, integration, evaluator, M4, or promotion authority.

## Typed response contract

The model response schema admits exactly one of:
1. an ImprovementSpec-like object with structured observation, hypothesis, target/preserve metrics, registered invariants, structured acceptance criteria, exact evidence hash, and human approval; or
2. a MeasurementGap with a genuinely absent metric, substantive measurement proposal, registered invariants, exact evidence hash, and human approval.

RESIDUAL serializes the typed object canonically after model return.

## Mechanical verifier

A proposal is rejected if:
- any numeric baseline differs from the EvidenceSnapshot;
- any referenced metric is unmeasured;
- target/preserve sets overlap or are empty;
- protected invariant IDs are unregistered;
- acceptance criteria are incomplete/non-numeric/unsupported;
- snapshot hash is wrong;
- human approval is disabled;
- a MeasurementGap requests a metric already present.

## Semantic review

Only mechanically admissible proposals reach an independent reviewer. The reviewer is explicitly instructed to reject causal overclaim, incoherent preservation criteria, or non-falsifiable acceptance.

## Success

M6-SPEC-007D succeeds only if:
- typed Scientist response completes;
- mechanical verifier returns zero errors;
- independent reviewer approves;
- RESIDUAL issues a content-addressed admission receipt.

The admission receipt does not grant implementation or promotion authority.
