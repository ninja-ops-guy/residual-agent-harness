# M6-SPEC-007 Preregistration — Autonomous Improvement Discovery

## Research question

Can RESIDUAL originate a defensible improvement objective from its own retained measurements when no question, target metric, or hypothesis is supplied?

## Evidence

The experiment uses five retained model-driven M6 development/shipping runs:

- M6-SPEC-006
- M6-ROADMAP-001B
- M6-SHIP-001
- M6-SHIP-003
- M6-SHIP-004

The EvidenceSnapshot records their artifact hashes, outcomes, runner attempts, first-request bytes, first-call latency, model-call counts, reported tokens, wall time, provider timeouts, and identical-failure repeats. Aggregate metrics are computed mechanically by the experiment script.

The Scientist receives the snapshot and immutable proposal verifier as read-only context.

## No supplied improvement target

The prompt does NOT provide:
- an improvement question;
- a target metric;
- a desired intervention;
- a hypothesis;
- a preferred finding.

It only instructs the Scientist to choose the single most defensible evidence-grounded improvement opportunity, or emit a MeasurementGap if the measured dimensions cannot support one.

## Mechanical admissibility

An ImprovementSpec-like proposal is rejected unless:
- its observation metric exists in the snapshot;
- the numeric observation value exactly matches the snapshot;
- any comparison metric/value also exactly matches;
- target and preservation metrics are measured metric IDs;
- target and preserve sets are non-empty and disjoint;
- protected invariants use the closed registered vocabulary;
- acceptance is a structured list of metric/operator/numeric-threshold criteria;
- every target and preserve metric has an acceptance criterion;
- the exact EvidenceSnapshot hash is bound;
- human approval remains true.

A MeasurementGap is rejected unless:
- the requested metric is actually absent;
- question/why/proposed measurement are substantive;
- preserve invariants are non-empty registered invariant IDs;
- the exact EvidenceSnapshot hash is bound;
- no extra ImprovementSpec fields are present.

## Authority boundary

The Scientist writes only `proposal.json` in an isolated fixture repo. It cannot modify evidence, checker, production source, Git history, verifier, M4, integration rules, or promotion authority.

## Success

The task must pass JSON validation and the deterministic proposal checker, receive independent review approval, integrate with a station receipt, and export the accepted proposal.

## Interpretation

A valid proposal demonstrates bounded evidence-driven improvement discovery for this retained evidence scope. It does not establish novelty, general autonomous research ability, or authority to implement/promote the proposal without external authorization.

A valid MeasurementGap is also a legitimate epistemic result, but it would indicate the current snapshot was insufficient to support a defensible improvement hypothesis.
