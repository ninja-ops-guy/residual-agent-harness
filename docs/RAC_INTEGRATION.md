# RAC improvement integration

Status: experimental, opt-in

RESIDUAL can verify and orchestrate RAC improvement envelopes through
`residual.modules.rac.RACModule`. The module is intentionally independent of
the RAC Python package: it consumes the hash-addressed JSON envelope exported by
RAC and does not import RAC measurement code.

## Authority model

RAC remains authoritative for:

- experiment manifests and evaluation versions;
- held-out separation and provenance firewall evidence;
- scientific evidence classification;
- physical experiment arming/execution;
- claim promotion.

RESIDUAL may coordinate bounded implementation work and independently verify
the resulting envelope, but it must not acquire any of those authorities.

The module therefore enforces three layers:

| Layer | RESIDUAL check |
| --- | --- |
| Mechanical | `rac:contract_integrity` |
| Structural | `rac:replication_independence` |
| Structural | `rac:authority_boundary` |

It also installs:

- a quarantine policy that denies held-out candidate selection, physical
  experiment execution, and automatic scientific promotion;
- an authority brake that aborts a run if one of those capabilities appears in
  an observation.

## GoalSpec example

```python
from residual import (
    AmendmentRule, CheckType, GoalSpec, StationExtensionRegistry,
    SuccessCriterion,
)
from residual.modules.rac import RACModule

registry = StationExtensionRegistry().register_module(RACModule())

goal = GoalSpec(
    "rac_improvement",
    "Verify a RAC improvement evidence envelope.",
    (
        SuccessCriterion(
            "contract", CheckType.MECHANICAL,
            "Verify hashes and the frozen evaluation binding.",
            "rac:contract_integrity",
        ),
        SuccessCriterion(
            "replication", CheckType.STRUCTURAL,
            "Verify outcome and independent replication coherence.",
            "rac:replication_independence",
        ),
        SuccessCriterion(
            "authority", CheckType.STRUCTURAL,
            "Keep scientific authority external and human-gated.",
            "rac:authority_boundary",
        ),
    ),
    max_passes=1,
    token_budget=1000,
    wall_clock_budget_s=60,
    amendment_rule=AmendmentRule(("operator",)),
)
```

Pass `registry` to the `LoopController` used for the mission.

## Important semantics

A RAC evidence outcome of `FAIL` is not itself a RESIDUAL integration
failure. If the FAIL is correctly bound, retained, and the RAC advisory decision
is `REJECTED`, the RESIDUAL verification mission should pass. That establishes
that the system preserved an unfavorable scientific result instead of repairing
the record into a PASS.

By contrast, any of these conditions fail closed:

- evidence references another ImprovementSpec;
- the RAC evaluation version drifts;
- a producer is also its own independent verifier;
- the decision's evidence hashes do not match the supplied bundles;
- `PROMOTABLE` lacks two replication identities and distinct replication-receipt hashes;
- `PROMOTABLE` lacks two independent verifier labels, verifier-identity hashes, and verifier-receipt hashes;
- the human promotion gate is removed;
- automated scientific promotion is granted;
- mandatory forbidden capabilities disappear from the ImprovementSpec.

## Experiment sequence

Use the RAC integration experiments in this order.

### RRI-001 — contract conformance

Run the deterministic fixture suite and smoke mission. It must demonstrate
positive, retained-negative, drift, self-verification, replication, and
authority cases without model calls.

### RRI-002 — infrastructure optimization

Select a deterministic RAC infrastructure component. Freeze input fixtures and
canonical output hashes. Allow RESIDUAL to propose a bounded implementation
change. Acceptance requires:

1. exact output/hash parity;
2. the RAC test and schema suites remain green;
3. the frozen evaluation version is unchanged;
4. no held-out access;
5. a measured runtime or memory improvement;
6. independent replication.

This is deliberately non-scientific: the first live experiment should test
whether recursive improvement works without giving the loop leverage over an
efficacy metric.

### RRI-003 — negative control

Inject a known regression. The RAC evidence must preserve `FAIL`, the RAC
advisory decision must become `REJECTED`, and RESIDUAL must verify that
negative record successfully.

### RRI-004 — verifier independence

Feed two nominal PASS bundles that merely use different labels while sharing a
verifier-identity hash or replication-receipt hash. The envelope must remain
`INCONCLUSIVE`. Repeat with hash-distinct verifier identities/receipts and
hash-distinct replication receipts; only then may RAC produce the advisory
`PROMOTABLE` state.

## Promotion boundary

`PROMOTABLE` means only that the supplied evidence satisfies the frozen
orchestration contract. It is not a release, merge, physical-test authorization,
or scientific claim. RAC's envelope must continue to state:

```json
{
  "authority": {
    "advisory_only": true,
    "human_gate_required": true,
    "automatic_promotion_forbidden": true
  }
}
```

The RESIDUAL module verifies this mechanically and structurally on every
candidate.
