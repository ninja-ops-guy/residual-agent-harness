# Swarm 5 — Economics and reliability observability

Swarm 5 implements `SPEC-SWARM-OTX-003` and `SPEC-SWARM-OBS-006` as one
observation-first measurement lane. It does not change the Factory M4 trust
boundary or any M4 evidence schema.

## Authority boundary

`ReliabilityObservation` is the retained source. Reports and Prometheus metrics
are projections. Neither aggregate reports nor Prometheus samples are accepted
as authoritative input to verification, integration, or replay.

Each observation binds its schema, observation hash, implementation commit,
tree, task class, topology, engine mix, worker count, verifier family, evidence
size, terminal state, correctness, acceptance, timing, cost, and completeness.
Corrupt hashes and malformed schemas fail closed. An incomplete execution is
different: it remains an explicit `UNKNOWN` denominator with nullable usage and
cost.

## Timing semantics

The critical path is decomposed into exclusive buckets for planning,
scheduling, context packaging, worker execution, verifier execution,
integration, retry/rework, coordination, and host overhead. Their sum must equal
wall-clock time within 0.001 ms. Summed worker and verifier resource time are
separate fields because concurrent resource duration can exceed wall time and
must not be added to the critical path.

## Topology policy

The controller compares direct, single verified worker, fixed swarm, dynamic
swarm, and heterogeneous swarm execution. It learns success, cost, and latency
by task class and candidate profile (engine mix, worker count, verifier family,
and evidence-size bucket). Decisions record all candidate estimates, predicted
quality-adjusted utility, the selected topology, threshold state, and the
eventual result. Stored outcome observations can rebuild the controller and
reproduce a decision.

The deterministic development fixture deliberately learns different policies:

- `small-edit` prefers `direct` because additional orchestration adds no quality;
- `wide-refactor` prefers `dynamic_swarm` because its quality improvement
  exceeds its measured overhead.

This is a mechanism test, not evidence that these preferences generalize to
live models or workloads.

## Reproduction

Run:

```bash
python -m pytest tests/swarm/test_economics_observability.py -q
python scripts/swarm5_evidence.py --output runs/swarm5
```

The generator writes raw timing observations, topology decisions, per-run
predicted-versus-observed orchestration tax, an aggregate reliability report,
its SHA-256, Pareto inputs, and one combined evidence artifact. Generating twice
from the same implementation commit produces byte-identical documents.

## Claim boundary

The committed fixture evidence is labeled `development_fixture`. Live R0–R5
experiments, held-out topology evaluation, confidence intervals, and soak data
remain separate work. No fixture result supports a production reliability,
cost-savings, or latency claim.
