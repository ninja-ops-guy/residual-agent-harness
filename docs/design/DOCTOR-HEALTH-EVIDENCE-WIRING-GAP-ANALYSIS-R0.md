# RESIDUAL Doctor / Telemetry / Evidence Fabric — Wiring Gap Analysis R0

Baseline: `main@8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`

## Conclusion

The repository already contains most hard infrastructure required for an evidence-driven Health Coordination Doctor. The primary gap is **wiring and semantic unification**, not another observability subsystem.

Existing primitives found on baseline:

- `residual/runtime/telemetry.py`: clock-injectable freshness guard that suppresses stale values and returns UNKNOWN.
- `residual/async_io/telemetry.py`: asynchronous refresh with synchronous verification boundary and UNKNOWN-on-stale/error semantics.
- `residual/telemetry/*`: SPEC-SWARM-OBS-006 raw observation validation, bounded labels, metric families, deterministic reliability reports, evidence artifacts, fixture generation and Prometheus export.
- `residual/station/observability.py`: durable SQLite-backed, hash-chained Station observations with trace IDs, integrity verification, cursor reads and exports.
- Station event storage: durable workflow/event evidence already exists separately from observations.
- PR #481: DF-CLI-002 introduces a read-only `residual doctor` for installation/source/runtime/Station-path diagnostics.
- Research Workbench PR #323: versioned experiment catalog, immutable definition identity, evidence bundles and staged/non-runnable experiment semantics.

## Genuinely missing product capabilities

### GAP-HC-01 — No canonical operational health observation envelope

OBS-006 is optimized for research/reliability metrics. Station observations are durable but generic. Neither provides one canonical fleet-health envelope carrying the coordination hierarchy needed to correlate runner, seat, Station, assignment, provider and projection observations.

**Add:** `HealthObservation` contract with correlation identity, freshness, evidence class and non-authority semantics.

### GAP-HC-02 — No qualified failure-detector registry

Observed failure classes currently live in receipts/docs/chat. Doctor has no versioned registry mapping predicates to HC classifications, evidence requirements, first-divergence priority, safe-continuation semantics and remediation metadata.

**Add:** append-only detector registry; detector maturity states; adapter ownership.

### GAP-HC-03 — Doctor is installation-focused, not evidence-fabric-aware

PR #481 Doctor reports package/source/update/Station-path state but does not consume Station observations, runtime telemetry, runner/provider/comms evidence or failure detectors.

**Add:** Doctor aggregation pipeline: collectors -> normalized health observations -> causal detector engine -> health report.

### GAP-HC-04 — No first-divergence causal engine

Current telemetry can measure observations but does not encode prerequisite/causal edges needed to distinguish:
`timer missing` from `timer fired but no consumer`, or `runner unenrolled` from `runner enrolled but exec contract missing`.

**Add:** detector prerequisites + causal-chain reducer. Earliest evidenced divergence is primary; downstream impacts remain visible but subordinate.

### GAP-HC-05 — Missing agent-runtime adapter boundary

OpenClaw-specific facts (gateway/profile/config-root/runtime/exec capabilities/context state) should not be hard-coded into Doctor core, and future agent systems will differ.

**Add:** health adapter SPI. First adapter target: OpenClaw. Generic core understands enrollment, leases, generations, deadlines, checkpoints, provider readiness and authority; adapter supplies runtime-specific observations.

### GAP-HC-06 — Telemetry streams lack the full coordination correlation block

Existing research telemetry intentionally forbids high-cardinality IDs as metric labels, which is correct. Those IDs are still required in raw evidence/traces.

**Add to raw health observations, not Prometheus labels:** cluster_id, station_id/epoch, runner_id, coordinator_id, seat_id/generation, mission/task/assignment/dispatch, decomposition/subtask/attempt, provider route/invocation, source event, trace/span.

### GAP-HC-07 — No temporal/absence detector substrate

Several real failures are absence-over-time conditions: missing ACK, no progress, wake fired without consumption, projection lag.

**Add:** health evaluator that joins durable observations with policy deadlines. Absence claims require a declared window and clock/freshness evidence.

### GAP-HC-08 — No lifecycle bridge from unknown failure to qualified detector

Research Workbench can preregister experiments, but Doctor has no explicit promotion path from unknown pattern -> candidate HC class -> reproduced -> implemented detector -> independently qualified production diagnostic.

**Add:** detector maturity and Workbench linkage.

### GAP-HC-09 — No health-to-scheduler evidence contract

Scheduler should consume qualified health facts without Doctor becoming scheduling authority.

**Add:** stable `HealthFact` projection with subject, state, classification, evidence digest, freshness and applicability. Scheduler must cite consumed health fact when eligibility changes.

### GAP-HC-10 — No fleet/cluster health composition

Local primitives exist, but there is no composition contract for Station registry/epochs, cross-Station leases, checkpoint portability, replication lag or split-brain indicators.

**Add:** v2-facing Cluster Doctor composition contract. Do not implement authority transfer in Doctor.

### GAP-HC-11 — No mission trace surface spanning layers

Station observations can be queried by trace, but there is no normalized mission trace joining Station events, runner observations, provider invocation evidence, coordinator subtask evidence and Shared Comms projection attempts.

**Add:** read-only `residual trace <mission|assignment|trace>` projection over admitted evidence.

### GAP-HC-12 — No explicit UNKNOWN-pattern retention

When no qualified detector matches, current systems can only surface generic errors/logs.

**Add:** `UNKNOWN_FAILURE_PATTERN` artifact retaining normalized causal shape and evidence refs. It must not mint a new HC class automatically.

## Existing infrastructure that should NOT be rebuilt

- Do not replace OBS-006 metric/report pipeline.
- Do not replace Station's durable observation chain.
- Do not make Prometheus metrics authoritative.
- Do not create another event log.
- Do not make Shared Comms authoritative.
- Do not let Doctor schedule/reassign/repair by default.
- Do not copy secret values into health evidence.
- Do not use LLM classification as the sole evidence for a health state.

## Recommended implementation order

1. HealthObservation + HealthFact schemas.
2. Adapter SPI and Station/OpenClaw collectors.
3. Detector registry + first-divergence reducer.
4. Doctor integration with PR #481 surface.
5. Temporal/absence evaluation.
6. Mission trace projection.
7. Workbench detector qualification bridge.
8. Scheduler consumption contract.
9. Cluster composition after multi-Station primitives qualify.

This ordering reuses the existing telemetry, observation, Station and Research Workbench infrastructure rather than creating a parallel subsystem.
