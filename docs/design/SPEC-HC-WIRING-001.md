# SPEC-HC-WIRING-001 — Health Evidence Fabric and Doctor Wiring

Status: **DESIGN CANDIDATE / NO REPAIR AUTHORITY**

## 1. Architecture

```
runtime/agent/runner/provider/comms observations
                  |
                  v
       existing telemetry + Station observations
                  |
                  v
        HealthObservation normalization
                  |
          +-------+--------+
          |                |
          v                v
 detector registry    mission trace
          |
          v
 first-divergence reducer
          |
          v
       HealthFact
          |
    +-----+------+
    |            |
 Doctor       scheduler
 report       consumes facts
(read-only)   (authority remains there)
```

Research Workbench consumes failure specimens and qualification definitions; it is not in the runtime authority path.

## 2. Evidence classes

Every input is one of:

- `OBSERVATION`: logs, metrics, heartbeats, process/runtime facts.
- `EVIDENCE`: durable identity-bound observation usable by Doctor/verifier.
- `AUTHORITY_EVENT`: dispatch, acceptance, fencing, delegation, epoch transition.

Doctor may correlate all three but MUST NOT promote OBSERVATION/EVIDENCE into AUTHORITY_EVENT.

## 3. HealthObservation

Required:

```
schema_version
observation_id
observed_at
source
evidence_class
kind
subject
correlation
freshness
payload
evidence_refs
```

Correlation fields are optional individually but typed when present:

```
cluster_id
station_id
station_epoch
runner_id
coordinator_id
seat_id
generation
mission_id
task_id
assignment_id
dispatch_id
decomposition_id
subtask_id
attempt_id
provider_route_id
invocation_id
source_event_id
trace_id
span_id
```

High-cardinality correlation fields MUST NOT automatically become Prometheus labels. OBS-006 bounded-label rules remain controlling for metrics.

## 4. HealthFact

Detector output:

```
fact_id
check_id
subject
stage
state
classification
first_divergence
safe_continuation
mission_impact
observed_window
fresh_until
evidence_refs
causal_predecessors
downstream_impacts
detector_version
detector_maturity
```

HealthFact is evidence, not authority.

## 5. Detector contract

A detector definition contains:

```
check_id
classification
stage
version
maturity
applies_to
required_observations
optional_observations
prerequisites
temporal_window
predicate
first_divergence_priority
safe_continuation
downstream_impacts
remediation_metadata
workbench_experiment_refs
positive_control_refs
negative_control_refs
```

Maturity:

`OBSERVED -> CORRELATED -> REPRODUCED -> DETECTOR_DESIGNED -> DETECTOR_IMPLEMENTED -> INDEPENDENTLY_QUALIFIED -> PRODUCTION_DIAGNOSTIC`

Only IMPLEMENTED+ detectors execute. Only INDEPENDENTLY_QUALIFIED+ detectors may be consumed as production scheduling-health evidence unless an explicit policy permits lower maturity.

## 6. First-divergence reducer

For all matching facts in a causal chain:

1. reject stale evidence as current truth;
2. evaluate prerequisites before dependent predicates;
3. select the earliest failed/unknown prerequisite supported by evidence;
4. mark it `first_divergence=true`;
5. retain later failures as downstream impacts;
6. never replace UNKNOWN with inferred PASS.

Example:

```
deadline_registered PASS
deadline_fired PASS
event_emitted PASS
consumer_action FAIL
scheduler_progress FAIL
```

Primary = `WAKEUP_FIRED_NO_ACTION`; scheduler stall is impact.

## 7. Temporal/absence rules

Absence is evidence only when all are true:

- expected event is defined;
- start/reference event exists;
- deadline/window is explicit;
- clock source is identified;
- evidence source covers the entire window or its gaps are declared;
- no matching event exists in that covered window.

Otherwise classification is UNKNOWN, not timeout/failure.

## 8. Adapter SPI

```
HealthAdapter
  identity()
  capabilities()
  collect(snapshot_context) -> list[HealthObservation]
  explain(check_id) -> adapter-specific metadata
```

Adapters are read-only by default.

Initial adapters:

- `station`: event/observation heads, roots, epochs, queues, deadlines, projections.
- `openclaw`: runtime version, gateway/profile/config-root identity, listener/process health, execution capabilities, context-consumption state where safely observable.
- `provider`: configuration/readiness/auth-presence/invocation journal facts.
- `shared_comms`: projection/outbox/cursor/delivery facts.

Future agent systems implement the same SPI without changing Doctor core.

## 9. Doctor integration

The existing DF-CLI-002 Doctor remains the installation/source layer. Health wiring adds:

```
residual doctor --scope host
residual doctor --scope station
residual doctor --scope runner
residual doctor --scope provider
residual doctor --scope comms
residual doctor --json
residual doctor --explain HC-xxx
```

Default execution remains read-only and bounded. Collection errors become UNKNOWN findings, not crashes where safe.

## 10. Mission trace

`residual trace <id>` is a read-only projection joining evidence by correlation identity.

It must distinguish:

- observed event time;
- ingestion time;
- authoritative event vs evidence vs observation;
- gaps;
- stale/unknown spans.

Trace output cannot create acceptance/authority.

## 11. Unknown-pattern retention

When no qualified detector matches a non-healthy causal chain:

```
UNKNOWN_FAILURE_PATTERN
  normalized_shape
  involved_stages
  evidence_refs
  first_unexplained_edge
  recurrence_key
```

A recurrence key may group similar specimens for research, but it cannot create a production detector. Promotion requires Workbench reproduction and qualification.

## 12. Scheduler boundary

Scheduler may consume HealthFacts only through an explicit policy.

Example:

```
subject=runner-dell-crucible
classification=RUNNER_EXEC_CONTRACT_MISMATCH
state=FAIL
fresh_until=...
evidence_digest=...
```

If scheduler changes eligibility, its durable decision cites the fact/digest. Doctor never issues the reassignment.

## 13. Failure register seed

Initial detector design corpus is HC-001..HC-030 from `HEALTH-COORDINATION-FAILURE-REGISTER-R0.md`, including wakeup, authority, scheduling, transport, provider, runner, restart, projection, context and evidence-integrity classes observed during current dogfood.

## 14. Acceptance

The wiring implementation is qualified only when:

- existing OBS-006 tests remain unchanged/green;
- Station observation chain remains authoritative only for its existing scope;
- Doctor performs zero mutation;
- stale evidence produces UNKNOWN/STALE;
- causal fixtures identify intended first divergence;
- high-cardinality IDs do not leak into metric labels;
- secret values never appear in reports;
- identical normalized evidence + frozen clock produces identical semantic HealthFacts;
- unknown patterns remain unknown until qualified;
- scheduler integration can be disabled without changing Doctor results.
