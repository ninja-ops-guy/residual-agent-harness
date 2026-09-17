# IE-003 — Pressure-Aware Admission, Logical Pools and Backpressure

Status: proposed implementation contract  
Planning base: `main@f6f9bad84caccf68c7ab35e5788e756d12c55fb7`  
Prerequisites: qualified IE-001 prototype / #160; accepted IE-002 telemetry contract / #161

## 1. Objective

Add bounded admission control around the existing ready-frontier scheduler so RESIDUAL can avoid producing work faster than downstream verification/integration can safely consume it.

Current RESIDUAL already has ready-frontier semantics. IE-003 MUST NOT replace that scheduler. It adds pressure-aware admission and capacity accounting around existing eligibility/order rules.

## 2. Logical execution pools

The implementation SHALL model at least three independently observable logical pools:

- worker execution;
- verification;
- integration.

Planning/context packaging MAY be exposed as separate capacity domains if the accepted implementation naturally supports them.

A logical pool does not require a separate process or machine. The purpose is independent capacity, queue and pressure accounting.

## 3. Admission semantics

An obligation may be eligible in the DAG yet not admitted to worker execution because downstream pressure exceeds policy.

The system MUST distinguish:

- `ready` — dependencies accepted;
- `admission_wait` — ready but held by bounded pressure policy;
- `running`;
- `verification_wait`;
- `integration_wait`;
- terminal states.

Admission delay MUST NOT be represented as task failure.

## 4. Backpressure inputs

Minimum policy inputs:

- ready-frontier depth;
- active workers / configured worker capacity;
- pending verification depth;
- active verifier / verifier capacity when known;
- integration queue depth;
- active integration capacity;
- configured max in-flight attempts;
- cancellation/deadline state;
- optional provider throttle/rate-limit signal when authoritative.

The policy MUST NOT infer missing capacity as zero or infinity. Unknown capacity requires an explicit conservative/default policy.

## 5. Policy contract

The first production policy SHALL be deterministic and configuration-driven.

At minimum it SHALL support:

- hard max in-flight worker attempts;
- verifier queue high/low watermarks;
- integration queue high/low watermarks;
- hysteresis so admission does not oscillate at one threshold;
- bounded per-mission concurrency;
- bounded global concurrency;
- deterministic tie breaking among equally eligible obligations.

A later adaptive policy may change thresholds, but IE-003 itself MUST first qualify the deterministic policy.

## 6. No-drop invariant

Backpressure MAY delay dispatch.

It MUST NOT silently drop:

- accepted artifacts;
- retained evidence;
- verifier outcomes;
- receipts;
- terminal failure/UNKNOWN information.

If queues reach an explicit hard storage/resource bound, the system MUST emit a typed overload/resource result and preserve enough evidence to explain why work could not continue.

## 7. Fairness and starvation

The admission controller MUST define deterministic fairness across independent ready obligations/missions.

Required properties:

- no permanently admissible obligation can be starved solely by later arrivals;
- a high-volume mission cannot consume unbounded global slots when other missions have ready work, unless an explicit priority policy says so;
- priorities, if supported, must be explicit configuration/contract data rather than inferred from model content.

A simple weighted/fair FIFO policy is acceptable for v1 if deterministic and tested.

## 8. Deadlines and cancellation

Backpressure MUST preserve existing host-owned cancellation/deadline authority.

A task held in `admission_wait` MUST still respond to:

- mission cancellation;
- obligation cancellation;
- deadline expiry;
- dependency invalidation if such a transition is legal in the current runtime.

Cancellation MUST NOT require first admitting the task.

## 9. Pool separation and scaling semantics

IE-003 SHALL expose independent capacity knobs so a later operator/controller can increase verifier capacity without necessarily increasing worker capacity, and vice versa.

This PR does not need to introduce multi-host pool deployment. It needs clean logical separation and pressure semantics that can later map to local threads/processes/remote workers.

## 10. Relationship to deterministic integration

Integration ordering/eligibility remains authoritative and deterministic.

Backpressure can delay when eligible accepted work enters/executes integration, but MUST NOT reorder work in a way that violates existing deterministic integration contracts.

## 11. Required tests

### T1 — existing scheduler preservation

With pressure control disabled or capacities effectively unbounded, a deterministic fixture MUST produce the same ready-frontier dispatch/order/outcomes as the accepted baseline.

### T2 — verifier-bound fixture

Workers complete faster than verifiers. Queue depth reaches the high watermark; new worker admission pauses; verification drains below the low watermark; admission resumes. No evidence/work is lost.

### T3 — integration-bound fixture

Accepted work accumulates at integration. Worker admission is reduced according to policy before unbounded growth occurs.

### T4 — hysteresis

A queue oscillating around one boundary MUST NOT cause pathological pause/resume thrashing.

### T5 — max in-flight

Configured per-mission/global in-flight bounds are never exceeded, including simultaneous readiness transitions.

### T6 — cancellation while waiting

A task in `admission_wait` cancels/deadlines cleanly without worker dispatch.

### T7 — fairness

A sustained large mission plus a small independent mission demonstrates the declared fairness policy and no indefinite starvation.

### T8 — overload

A deliberately tiny hard resource bound produces a typed overload/UNKNOWN/error condition with retained evidence, not silent drop or fabricated PASS.

### T9 — deterministic replay

Given identical lifecycle/pressure inputs, every admission/pause/resume decision is reproduced exactly.

### T10 — telemetry consistency

IE-002 queue/utilization projections agree with actual admission state at every transition in a frozen fixture.

### T11 — concurrency race

Concurrent completion/readiness events cannot exceed capacity due to a check-then-act race. Admission reservation must be atomic within the relevant runtime authority.

### T12 — repository qualification

All applicable exact-head CI remains green. No protected M4 trust-boundary file/test/pin/shared schema is modified without stopping for dependency review.

## 12. Rollout

Initial rollout SHOULD be opt-in/configurable until exact-head qualification and controlled workload comparison are complete.

A release candidate SHOULD compare the same frozen workload with:

- pressure policy disabled;
- pressure policy enabled.

Required comparison outputs:

- accepted/integrated goodput;
- queue depth peaks;
- latency distributions;
- rejection/rework;
- orchestration tax;
- no-drop/overload events.

The comparison is engineering evidence, not a universal performance claim.

## 13. Exit criteria

IE-003 exits when:

- IE-001 prototype is qualified;
- IE-002 telemetry needed for pressure evidence is accepted;
- deterministic backpressure passes T1–T12;
- disabled-mode equivalence is demonstrated;
- bounded-queue behavior is demonstrated under verifier/integration pressure;
- independent review accepts the exact head.

## 14. Non-goals

This PR does not:

- choose which model/engine should run an obligation;
- alter verifier truth semantics;
- implement context caching;
- introduce speculative expensive-model dispatch;
- claim optimal queueing/control theory;
- require multi-host orchestration.
