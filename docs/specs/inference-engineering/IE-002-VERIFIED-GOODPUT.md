# IE-002 — Production Lifecycle Telemetry and Verified Goodput

Status: proposed implementation contract  
Planning base: `main@f6f9bad84caccf68c7ab35e5788e756d12c55fb7`  
Prerequisite: qualified IE-001 prototype contract / PR #160

## 1. Objective

Wire the qualified IE-001 measurement model into production execution as a **passive observation layer**.

This PR SHALL make RESIDUAL capable of explaining where time, queue pressure and useful accepted work are going without changing scheduling, routing, provider selection, verifier authority or integration decisions.

IE-002 is intentionally observational. Active control begins later.

## 2. Required behavior

The implementation SHALL emit lifecycle observations for the existing execution path, using the frozen IE-001 stage vocabulary where a real stage exists:

- mission submitted;
- obligation becomes ready/eligible;
- scheduling/admission begins and ends;
- context packaging begins and ends;
- worker/provider dispatch begins and ends;
- evidence becomes visible;
- verification begins and ends;
- integration eligibility/queue entry;
- integration begins and ends;
- terminal mission/obligation state.

Instrumentation MUST attach to existing authorities rather than wrapping them with new acceptance logic.

## 3. Clock and identity rules

Durations MUST use a monotonic clock.

Wall-clock UTC MAY be retained for operator correlation but MUST NOT be used for normative duration arithmetic.

Every event MUST bind sufficient identity to prevent cross-run mixing:

- run/mission id;
- obligation/task id;
- attempt id where relevant;
- topology;
- engine/provider identity when known;
- source commit/tree when available at run scope;
- event schema revision.

Duplicate normative event identities MUST fail observation validation rather than being silently merged.

## 4. Metric semantics

### 4.1 Throughput

Expose separately:

- worker-attempt throughput;
- verifier-terminal throughput;
- accepted goodput;
- integrated goodput.

Accepted goodput means independently verifier-accepted obligations per unit wall time. It MUST NOT be named or surfaced as ground-truth correctness.

Ground-truth/correct goodput exists only when an independent grade/gold label is bound to the observation set. Without that grade, correctness metrics MUST be UNKNOWN.

### 4.2 Latency

Expose at minimum:

- TTFW;
- TTE;
- TTA;
- TTI;
- stage service time;
- queue wait time;
- end-to-end obligation latency;
- end-to-end mission latency.

Report distributions and sample counts. A percentile with insufficient samples MUST be absent/UNKNOWN rather than fabricated.

### 4.3 Pressure/utilization

Observe, without controlling:

- ready frontier depth;
- admitted/running workers;
- configured worker capacity when known;
- pending verification depth;
- active verifier count/capacity when known;
- integration queue depth;
- active integration work;
- provider throttling/rate-limit observations when explicitly reported;
- cancellation, retry, rework and rejection counts.

## 5. Context and usage accounting

When existing provider adapters report authoritative usage, telemetry SHALL preserve separately:

- request bytes;
- prompt/input tokens;
- completion/output tokens;
- provider-reported cached input tokens;
- reasoning tokens when separately reported;
- calculated cost only when both authoritative usage and configured price data exist.

Missing usage MUST remain missing. Missing price MUST produce unknown cost, not `$0`.

Context-packaging telemetry SHOULD additionally record:

- artifact/window count;
- source bytes selected;
- framed payload bytes;
- repeated/overlapping evidence bytes avoided where measurable;
- disclosure class/local-vs-remote placement without retaining raw sensitive contents.

## 6. Relationship to existing OTX

Existing `residual.otx` timing and topology observations remain authoritative for the OTX model.

IE-002 SHALL provide a production observation adapter into OTX-compatible timing rather than creating a competing orchestration-tax controller.

If OTX cannot consume an observation because required phases are missing, the result SHALL remain incomplete/UNKNOWN.

## 7. Evidence retention

Introduce an additive, standalone observation format such as:

`residual.inference-economics.observation.v1`

This MUST NOT replace or mutate shared Factory/M4 evidence schemas.

The retained stream SHOULD support:

- deterministic projection into summary metrics;
- hash binding;
- bounded cardinality for exported labels;
- replay of metric calculations;
- explicit simulated/replayed/live classification.

Raw prompts, raw evidence contents and candidate source SHOULD NOT be added merely for telemetry.

## 8. Failure semantics

Telemetry failure MUST NOT change verifier PASS/FAIL/UNKNOWN, receipt authority or integration state.

Two modes SHALL be distinguished:

1. **normal operation** — execution may continue when optional economics telemetry fails, but telemetry health becomes ERROR/UNKNOWN;
2. **qualified experiment mode** — if complete economics evidence is preregistered as a required gate, missing/corrupt telemetry blocks qualification of the experiment/result.

Telemetry failure MUST never be rewritten into zero duration, zero cost, zero queue depth or success.

## 9. Required tests

### T1 — observer non-interference

Run equivalent deterministic fixtures with telemetry disabled and enabled. Accepted values, verifier decisions, receipt identities where telemetry is not part of their input, integration order and terminal outcomes MUST be equivalent.

### T2 — clock correctness

Wall-clock jumps MUST NOT produce negative/invalid normative durations. Monotonic timestamps drive duration calculations.

### T3 — attempt vs goodput divergence

A fixture with many rejected attempts MUST report high attempt throughput and lower accepted/integrated goodput.

### T4 — correctness non-conflation

Accepted work with no independent grade MUST NOT produce `correct_goodput`.

### T5 — missing usage

Missing token/cost fields remain UNKNOWN and cannot be coerced to zero.

### T6 — queue reconstruction

Given a frozen lifecycle event stream, reconstructed queue depth and active counts MUST match an independent oracle at every transition.

### T7 — duplicate/malformed events

Duplicate normative IDs, negative durations, impossible stage order and incompatible schema revisions MUST be rejected or explicitly quarantined from normative summaries.

### T8 — OTX adapter

A complete observation SHALL map into existing OTX phase timing without changing OTX decision semantics. Incomplete timing stays incomplete.

### T9 — bounded export labels

Dynamic task/topology/provider labels MUST be bounded or folded according to an explicit policy so telemetry cannot create unbounded metric cardinality.

### T10 — exact-head repository regression

All applicable existing CI remains green. No protected ownership pin or M4 trust-boundary artifact changes.

## 10. Command Station surface for this PR

Only a minimal read-only diagnostics surface is allowed in IE-002, if needed for acceptance:

- current queue depth;
- current active workers/verifiers;
- accepted/integrated goodput;
- major latency measurements;
- telemetry health.

The full operator economics/roofline UI belongs to IE-007.

## 11. Exit criteria

IE-002 is complete only when:

- IE-001 has a qualified, independently reviewed prototype;
- production telemetry remains passive;
- all T1–T10 tests pass on exact head;
- summaries replay from retained observations;
- normal and qualified-experiment failure semantics are independently tested;
- no execution-authority change is bundled into this PR.

## 12. Non-goals

This PR does not:

- throttle or prioritize work;
- change worker count;
- select models/topologies;
- cache new context artifacts;
- trigger speculative execution;
- alter provider budgets;
- claim performance improvement.

Those are downstream IE PRs.
