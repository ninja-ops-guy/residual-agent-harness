# SWARM Reliability Research Program

Status: execution-ready coordination specification
Owner: Residual research program
Scope: empirical validation of reliability-from-unreliable-computation hypothesis

## Program objective

Test whether system-level reliability can improve without changing the underlying model by progressively adding: constrained execution, evidence capture, independent verification, deterministic integration, and dynamic orchestration.

The swarm MUST preserve a strict distinction between:

- implemented mechanism;
- software validation;
- controlled experimental result;
- hypothesis;
- unsupported/generalized claim.

No swarm may promote a mechanism to an empirical result without frozen artifacts that reproduce the result.

## Shared rules for every swarm

1. Work from a dedicated branch named `swarm/<spec-id>-<short-name>`.
2. Do not modify another swarm's owned files except through an explicit dependency PR.
3. Every requirement MUST map to one or more tests.
4. Every experiment MUST record exact commit/tree identity, runtime versions, frozen inputs, configuration, raw observations, and machine-readable results.
5. Failures remain in denominators; missing evidence is not free work.
6. `UNKNOWN`, `FAIL`, `REJECTED`, and `PASS` remain distinct states.
7. Any randomized or model-dependent experiment MUST preserve seeds/settings when controllable and record them when not.
8. No benchmark result may be added to the paper unless it is regenerated from retained artifacts.
9. All PRs MUST include a requirements-to-tests traceability table.
10. Integration order follows the dependency graph defined below.

---

# SPEC-SWARM-EVAL-001 — Frozen Reliability Evaluation

## Purpose

Implement the critical-path experiment that compares raw/unconstrained execution against progressively stronger Residual control layers while holding worker/model capability constant.

## Requirements

- EVAL-R1: Define a versioned `FrozenWorkload` schema with immutable workload hash.
- EVAL-R2: Support configurations R0-R5: raw, orchestrated, contracted, constrained+observed+verified, COVD, and dynamic swarm.
- EVAL-R3: Hold model/provider/version, prompting policy, inference settings, task corpus, tool environment, and grader constant across ablations unless the experiment explicitly varies one.
- EVAL-R4: Run each configuration at least 3 times per workload slice.
- EVAL-R5: Preserve independent correctness `X` separately from acceptance `A`.
- EVAL-R6: Emit AER/FAR, ISR, ASSR, acceptance coverage, false rejection, FCR when fault labels exist, throughput, latency, rework, conflicts, verifier rejection, and compute/token cost.
- EVAL-R7: Produce paired run records that enable task-level comparison between configurations.
- EVAL-R8: Preserve all failed and aborted runs in the aggregate report.
- EVAL-R9: Generate paper-ready CSV/JSON plus reproducible plotting inputs; plotting itself may be a downstream research task.
- EVAL-R10: CI MUST run a scripted development fixture; live-model runs remain separately labeled.

## Acceptance

A frozen fixture study runs end-to-end for all R0-R5 modes and produces hash-bound reports from which `P(X)`, `P(A)`, and `P(X|A)` can be independently recomputed.

Dependencies: M2, M3, M4, current reliability metrics.

---

# SPEC-SWARM-VQ-002 — Verifier Quality Framework

## Purpose

Measure and gate the quality of the acceptance boundary instead of assuming verifier correctness.

## Requirements

- VQ-R1: Introduce `VerifierQualityProfile` with precision, recall, coverage, calibration, false-accept, false-reject, and sample count.
- VQ-R2: Version verifier identity, implementation hash, configuration hash, policy hash, and optional proof hash.
- VQ-R3: Update profiles only from independently labeled outcomes, never worker self-report.
- VQ-R4: Safety-critical verifier precision below 0.95 MUST trigger HITL escalation rather than silent acceptance.
- VQ-R5: Support verifier ensembles with deterministic aggregation policy.
- VQ-R6: FrozenWorkload MUST include known-defect cases to measure verifier recall.
- VQ-R7: Add adversarial verifier tests designed to induce false acceptance and false rejection.
- VQ-R8: Receipts MUST include the verifier quality snapshot/revision used at acceptance time.
- VQ-R9: Report uncertainty when sample sizes are insufficient; do not emit misleading point estimates as authoritative.

## Acceptance

A reproducible verifier benchmark demonstrates profile updates and at least one fail-closed HITL escalation caused by degraded precision.

Dependencies: M3, EVAL-001.

---

# SPEC-SWARM-OTX-003 — Orchestration Tax Controller

## Purpose

Learn when swarming helps and when orchestration overhead exceeds its benefit.

## Requirements

- OTX-R1: Measure planning, scheduling, context packaging, worker execution, verification, integration, and coordination overhead separately.
- OTX-R2: Define `orchestration_tax(task, topology)` from observed data rather than a fixed constant.
- OTX-R3: Maintain task-class-conditioned estimates with Bayesian or equivalently uncertainty-aware updating.
- OTX-R4: Compare predicted and observed tax after every experimental task.
- OTX-R5: Support a configurable deployment threshold above which Residual chooses a simpler execution topology.
- OTX-R6: Evaluate at multiple task granularities using FrozenWorkload.
- OTX-R7: Measure quality-adjusted utility so a faster but less reliable mode cannot appear superior solely on latency.
- OTX-R8: Every topology choice MUST emit an observation containing inputs, predicted utility/tax, selected topology, and eventual observed result.

## Acceptance

The controller learns at least two task classes with distinct preferred topologies and reproduces its decision from stored observations.

Dependencies: M4 scheduler, EVAL-001.

---

# SPEC-SWARM-DSM-004 — Distributed State Maturity

## Purpose

Move evidence, scheduling, and recovery semantics from single-host durable state toward explicit distributed guarantees.

## Requirements

- DSM-R1: Define authoritative ownership for task lease, receipt publication, integration intent, and terminal task state.
- DSM-R2: Add durable acknowledgement semantics for state/event delivery.
- DSM-R3: Support reconnect/catch-up from a monotonic sequence or durable cursor.
- DSM-R4: Duplicate delivery MUST be idempotent.
- DSM-R5: Stale lease/fencing tokens MUST fail closed.
- DSM-R6: Concurrent writers MUST have deterministic conflict semantics.
- DSM-R7: Document which properties are guaranteed without consensus and which require a consensus service.
- DSM-R8: Provide crash/restart/replay tests including process death between write and acknowledgement.
- DSM-R9: Preserve audit provenance across recovery.
- DSM-R10: Add a fault matrix for duplicate, delayed, reordered, and lost delivery.

## Acceptance

A deterministic recovery suite demonstrates no duplicate accepted state transition across restart/replay scenarios and clearly states remaining non-consensus guarantees.

Dependencies: M2/M3/M4.

---

# SPEC-SWARM-RUNTIME-005 — Engine + Async Runtime Integration

## Purpose

Unify heterogeneous execution engines behind a capability contract while making telemetry/cancellation robust under async I/O.

## Requirements

- RUN-R1: Define an `ExecutionEngine` protocol and adapters for supported cloud/local engines already targeted by Residual.
- RUN-R2: CapabilityRouter MUST probe declared capability before routing and fail closed on mismatch.
- RUN-R3: Local execution is preferred when capability/policy are equivalent; provider selection remains deterministic for equal scores.
- RUN-R4: Engine name/version/provider metadata MUST enter receipts and evaluation records.
- RUN-R5: Residual HITL and policy remain authoritative over provider-native autonomous/HITL behavior.
- RUN-R6: Telemetry reads MUST expose freshness and return `UNKNOWN` when stale rather than reusing stale values as current truth.
- RUN-R7: Abort/cancel MUST propagate to active async operations within the configured cancellation budget.
- RUN-R8: Observation sinks MUST support buffered async flush with durable terminal flush semantics.
- RUN-R9: Add adapter conformance tests and cancellation/staleness fault tests.

## Acceptance

At least two execution adapters pass the same conformance suite, and stale telemetry plus cancellation faults produce deterministic fail-closed outcomes.

Dependencies: M2, M3.

---

# SPEC-SWARM-OBS-006 — Observability + Reliability Telemetry

## Purpose

Make every paper metric derivable from authoritative events rather than manual interpretation.

## Requirements

- OBS-R1: Export metric families for execution, acceptance, rejection, verification, integration, conflicts, retries, resource consumption, and orchestration timing.
- OBS-R2: Provide Prometheus-compatible export without making Prometheus authoritative state.
- OBS-R3: Metric labels MUST avoid unbounded task/content cardinality by default.
- OBS-R4: Reliability report generation MUST recompute from raw observations and reject incomplete/corrupt evidence.
- OBS-R5: Expose separate timings for planning, dispatch, context packaging, worker runtime, verification, and integration.
- OBS-R6: Report evidence completeness and missing-data counts alongside every aggregate.
- OBS-R7: Add a schema version and hash to exported analysis reports.
- OBS-R8: Add deterministic fixture tests for every metric family and aggregation invariant.

## Acceptance

A fresh fixture run can rebuild all paper-facing metrics from observations alone and produces the same report hash twice from identical inputs.

Dependencies: M2-M4, EVAL-001.

---

# SPEC-SWARM-PROD-007 — Production Control + Recovery Hardening

## Purpose

Close operational gaps required before claiming production-suitable control-plane behavior.

## Requirements

- PROD-R1: Durable HITL decisions with replay prevention and explicit approver identity.
- PROD-R2: Recovery after controller/process restart without losing terminal state or duplicating accepted actions.
- PROD-R3: Explicit secret/provider credential boundary; secrets MUST NOT enter observations or receipts.
- PROD-R4: Deployment health/readiness/liveness semantics separated from task success.
- PROD-R5: Backpressure and bounded queues for verification and integration.
- PROD-R6: Graceful shutdown MUST either complete or durably cancel/hand off in-flight work.
- PROD-R7: Define upgrade/schema migration strategy for journals, Evidence Bus, and receipts.
- PROD-R8: Add disaster/restart tests and document unsupported HA guarantees.
- PROD-R9: Produce operator runbook and production-readiness checklist.

## Acceptance

A restart/recovery test suite proves no lost terminal decisions, no duplicate HITL acceptance, and no leaked secrets in retained evidence.

Dependencies: DSM-004, runtime, M3/M4.

---

# SPEC-SWARM-RESEARCH-008 — Research, Statistics, Reproducibility + Paper Sync

## Purpose

Convert experiment artifacts into defensible claims and keep the manuscript synchronized with evidence.

## Requirements

- RES-R1: Maintain a claim-evidence matrix tagging every manuscript claim as literature, prior result, implemented mechanism, new result, or hypothesis.
- RES-R2: Build a verified IEEE bibliography with DOI/venue/year where available.
- RES-R3: Predefine statistical tests before inspecting final live-model results.
- RES-R4: Report confidence intervals and effect sizes; repeated runs MUST be treated as clustered observations where appropriate.
- RES-R5: Produce reliability-vs-cost and reliability-vs-latency Pareto inputs.
- RES-R6: Publish negative and `UNKNOWN` results.
- RES-R7: Maintain artifact manifests containing commit hashes, workload hashes, verifier revisions, environment metadata, and result hashes.
- RES-R8: Update the paper only from frozen result artifacts, never by hand-copying benchmark numbers.
- RES-R9: Build an independent reproduction command that regenerates tables from retained artifacts.
- RES-R10: Document threats to validity per experiment family.

## Acceptance

A clean checkout plus retained artifact bundle regenerates the paper's numeric tables and validates their source hashes without model credentials.

Dependencies: all experiment-producing specs.

---

## Dependency graph

```text
M2 ─┬──────────────► RUNTIME-005 ─┐
M3 ─┼──────────────► VQ-002 ──────┤
M4 ─┼──────────────► OTX-003 ─────┤
    ├──────────────► DSM-004 ──────┤
    └──────────────► EVAL-001 ─────┼──► OBS-006 ──► RESEARCH-008
                                   │
DSM/RUNTIME/M3/M4 ───────────────► PROD-007
```

EVAL-001 is the critical path for the paper. VQ and OTX should integrate before final live-model claims, but their implementation can proceed in parallel.

## Integration gates

Gate A — Mechanism: requirement-specific unit/integration tests pass.

Gate B — Evidence: machine-readable experiment artifact exists and contains exact source identity.

Gate C — Reproduction: aggregate can be recomputed from raw events/receipts.

Gate D — Claim: only after A-C may RESEARCH-008 promote the result into the manuscript.

## Recommended swarm allocation

- Swarm A: EVAL-001
- Swarm B: VQ-002
- Swarm C: OTX-003
- Swarm D: DSM-004
- Swarm E: RUNTIME-005
- Swarm F: OBS-006
- Swarm G: PROD-007
- Swarm H: RESEARCH-008

Swarm H should not edit production runtime code. Other swarms should not edit the manuscript's numeric Results section directly.
