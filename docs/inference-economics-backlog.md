# RESIDUAL Inference-Economics Implementation Backlog

Status: planning backlog only

Purpose: capture the follow-on engineering work required to turn the IE-002 through IE-007 prototype ideas into production-qualified RESIDUAL capabilities without weakening the existing trust boundary, evidence semantics, or governance gates.

This document is intentionally non-authoritative for runtime behavior. It is a work queue for future implementation PRs. The frozen specs and accepted production contracts remain authoritative.

## Prerequisites and sequencing

1. IE-001 qualification must complete first. PR #177 is the current IE-001 qualification candidate.
2. Do not treat the uploaded IE-002 through IE-007 prototype package as production source of truth. It is design/test input only.
3. Implement downstream work against accepted `main`, not against stale planning bases.
4. Preserve M4 trust-boundary protections, Factory ownership, verifier authority, receipt semantics, integration authority, and existing provider-routing controls.
5. Each implementation PR must carry exact-head evidence, applicable repository CI, maintainer attestation, and any independent review required by the corresponding frozen spec.
6. Do not claim runtime speedup, cost reduction, quality improvement, scheduling safety, GPU efficiency, or research validity until measured by the applicable qualified evaluation.

Recommended dependency order:

`IE-001 -> IE-002 -> IE-003 -> IE-004 -> IE-005 -> IE-006 -> IE-007`

Parallel work is acceptable only where the contracts prove independence and the eventual integration order still preserves this dependency chain.

---

## IE-002 — Production inference telemetry

Goal: extend the existing RESIDUAL telemetry/evidence system so inference-economics measurements are attributable, replayable, privacy-safe, and useful for later policy decisions.

### IE2-01 — Map canonical inference lifecycle observations
- Define the production adapter from the IE-001 lifecycle model into existing `residual/telemetry` observation/evidence contracts.
- Reuse existing OBS-006 validation, canonical hashing, bounded labels, and fail-closed evidence semantics where compatible.
- Avoid a second competing telemetry authority.

Acceptance:
- every required lifecycle stage has a documented source event;
- missing stage evidence stays UNKNOWN rather than becoming zero;
- duplicate and out-of-order observations cannot silently alter authoritative totals;
- no production authority is introduced by the observer.

### IE2-02 — Add stable execution identity and provenance
- Bind observations to run, obligation, attempt, task class, topology, engine/provider class where known, source commit, source tree, and schema revision.
- Define which identifiers are retained only in evidence versus exposed as metrics labels.
- Preserve bounded-cardinality label policy.

Acceptance:
- one execution can be reconstructed deterministically from retained evidence;
- source commit/tree mismatches fail closed for qualification artifacts;
- high-cardinality/private identifiers never leak into exported metric labels.

### IE2-03 — Capture resource/accounting signals
Add evidence for, where available:
- input/output/context token counts;
- provider/model usage cost or explicit UNKNOWN;
- cache hits/misses and reused context volume;
- retries, rework, verifier rejections, integration conflicts, cancellations and escalations;
- provider throttling/rate-limit evidence;
- worker/pool capacity and active-count samples.

Acceptance:
- absent provider accounting remains UNKNOWN;
- no synthetic zero-cost or zero-token interpretation;
- unit normalization is explicit and tested.

### IE2-04 — Capture queue, frontier and pool pressure
- Instrument ready-frontier depth, pending/deferred work, verifier queue, integration queue, active workers and configured/observed capacity.
- Define monotonic sampling semantics and sample freshness.

Acceptance:
- pressure snapshots can be correlated to exact mission/obligation intervals;
- stale samples are labeled stale/UNKNOWN rather than reused silently;
- instrumentation does not mutate scheduler state.

### IE2-05 — OTX / metrics projection adapter
- Produce a bounded derived projection for observability/OTX consumers without making the projection authoritative.
- Include incomplete/unknown markers.

Acceptance:
- raw retained evidence remains authoritative;
- projection can be regenerated deterministically from the same evidence;
- unsupported fields remain absent/UNKNOWN.

### IE2-06 — Failure and corruption semantics
Test malformed observations, missing fields, non-finite values, duplicate identifiers, partial traces, schema mismatch, tamper, and source-identity mismatch.

Acceptance:
- qualification/report generation fails closed on corrupt authoritative evidence;
- normal runtime can continue where the frozen spec permits incomplete non-authoritative telemetry;
- no corrupted sample is silently converted into a valid zero.

### IE2-07 — Qualification evidence
- frozen fixtures;
- deterministic replay checks;
- tamper corpus;
- telemetry overhead measurement;
- exact-head bundle;
- full repository CI.

Exit condition: IE-002 telemetry is trustworthy enough for IE-003 through IE-007 to consume without inventing missing economics.

---

## IE-003 — Pressure-aware admission and backpressure

Goal: regulate dispatch/admission using measured system pressure while preserving safety, fairness, boundedness, cancellation, and production scheduler authority.

### IE3-01 — Integrate with the real ready-frontier scheduler
- Attach the policy only at an approved scheduler/admission seam.
- Do not create a parallel scheduler.
- Preserve existing Factory/M4 ownership and cancellation paths.

### IE3-02 — Define explicit capacity semantics
- Unknown worker/verifier/integration/provider capacity must not default to unlimited capacity.
- Distinguish `UNKNOWN`, `AVAILABLE`, `SATURATED`, and `UNAVAILABLE` conditions where the spec requires them.

Acceptance:
- constrained dispatch fails or defers explicitly when required capacity evidence is unavailable;
- unknown cannot silently mean admit.

### IE3-03 — Atomic reservation accounting
- Model reservations for worker slots, verifier capacity, integration capacity, provider budget and other bounded resources as applicable.
- Ensure concurrent admissions cannot oversubscribe a limit due to check-then-act races.

Acceptance:
- reservation and release are deterministic and idempotent;
- cancellation/deadline expiry releases held capacity exactly once;
- negative/overflow counters are impossible under tests.

### IE3-04 — High/low watermark hysteresis
- Implement bounded high/low thresholds.
- Prevent rapid oscillation between admit/defer states.
- Make threshold revisions versioned and evidence-visible.

### IE3-05 — Fairness and starvation resistance
- Define fairness across obligations/task classes without weakening priority/safety semantics.
- Add long-run starvation tests.

### IE3-06 — Overload behavior
- No silent drops.
- Every defer/reject/cancel decision gets a reason and evidence.
- Bound queues and retained deferred work.

### IE3-07 — Cancellation and deadline propagation
- Respect mission/obligation cancellation before and after reservation.
- Stop admissions that can no longer satisfy hard deadlines when required by contract.

### IE3-08 — Adversarial scheduler tests
Test:
- unknown capacity;
- verifier stall;
- integration stall;
- provider throttle;
- burst admission;
- cancellation storms;
- reservation race;
- queue saturation;
- threshold oscillation;
- fairness under mixed priorities.

Exit condition: admission control is production-safe and measurably bounded, not merely a prototype pressure score.

---

## IE-004 — Provenance-safe context reuse/cache

Goal: reuse previously packaged context/evidence only when identity, provenance, disclosure, freshness and re-verification constraints prove the reuse safe.

### IE4-01 — Immutable cache key contract
Key must include every authority-relevant identity required by the frozen spec, including source/evidence identity and policy/schema revision where applicable.

Acceptance:
- semantically different obligations cannot collide into a reusable entry;
- cache-key canonicalization is deterministic;
- hash collision/tamper paths fail closed.

### IE4-02 — Connect to authoritative RESIDUAL evidence snapshots
- Cache references immutable retained evidence or content-addressed snapshots rather than mutable runtime objects.
- Define lifecycle/eviction behavior.

### IE4-03 — Disclosure/privacy non-promotion
- A cached artifact produced under one disclosure/privacy scope must never be silently reused in a broader or incompatible scope.
- Enforce provider/placement restrictions before cache use.

### IE4-04 — Re-verification on reuse
- Cached context can reduce repackaging/retrieval work but must not inherit verifier acceptance unless the frozen contract explicitly permits it.
- Reuse must produce evidence that identifies reused versus newly produced material.

### IE4-05 — Bounded storage and eviction
- Bound in-memory and wire caches.
- Use deterministic eviction rules where qualification depends on replay.
- Prevent unbounded cache growth from unique obligations.

### IE4-06 — Freshness and invalidation
Invalidate on relevant changes such as source tree, policy revision, schema revision, disclosure context, content identity, and any other contract-defined dependency.

### IE4-07 — Tamper/adversarial corpus
Test mutated cached payload, wrong provenance, stale tree, wrong disclosure scope, stale schema, duplicate key, truncated entry, replay after eviction, and concurrent insert/read.

Exit condition: context reuse can be enabled without transferring authority or leaking stale/private context.

---

## IE-005 — Evidence-gated model/provider escalation ladder

Goal: move from cheaper/lower-capability inference to stronger inference only when evidence justifies escalation and hard constraints allow it.

### IE5-01 — Real provider capability integration
- Compose with accepted provider registry/capability contracts.
- Do not introduce a second provider authorization path.

### IE5-02 — Hard constraints before escalation
Check before dispatch:
- capability;
- privacy/disclosure;
- placement/local-only restrictions;
- remaining budget;
- deadline feasibility;
- cancellation state;
- provider availability/rate-limit state where required.

Acceptance:
- a failed hard constraint cannot be overridden by a score;
- UNKNOWN budget or latency cannot be treated as zero when a hard limit exists.

### IE5-03 — Atomic budget reservation
- Reserve expected/maximum allowed spend before dispatch when required.
- `0` or failed reservation must never be interpreted as authorization unless a truly zero-cost provider path is explicitly known and valid.
- Release/reconcile reservation exactly once.

### IE5-04 — Evidence-gated escalation reasons
Examples:
- verifier rejection;
- insufficient evidence;
- capability mismatch discovered after bounded attempt;
- explicit retryable provider failure.

Do not escalate merely because a stronger model exists.

### IE5-05 — Terminal semantics
- PASS stops.
- Hard policy rejection stops.
- Cancellation/deadline stops.
- Exhausted ladder returns unresolved/failure explicitly rather than fabricating acceptance.

### IE5-06 — Retry/escalation loop bounds
- Bound total steps, retries, spend and wall time.
- Detect loops caused by provider aliases or repeated equivalent tiers.

### IE5-07 — Qualification matrix
Test local/free path, paid path, unavailable provider, privacy block, budget exhaustion, deadline block, verifier reject then pass, full ladder exhaustion, cancellation, throttle and UNKNOWN economics.

Exit condition: escalation is a bounded evidence-driven policy layered on existing provider authority.

---

## IE-006 — Empirical inference routing

Goal: choose among eligible inference engines using measured evidence while keeping hard safety constraints authoritative and routing decisions replayable.

### IE6-01 — Compose with existing CapabilityRouter/OTX/provider contracts
- Keep capability/privacy/placement eligibility authoritative.
- Empirical optimization occurs only after hard eligibility filtering.

### IE6-02 — Versioned empirical profile store
Track by bounded routing identity where justified:
- observed latency distribution;
- cost/usage distribution;
- success/verification outcomes;
- sample count/freshness;
- uncertainty/confidence metadata;
- policy/profile revision.

Do not create unbounded per-prompt labels or profiles.

### IE6-03 — UNKNOWN and cold-start policy
- Missing metrics receive explicit uncertainty/penalty/exploration treatment.
- They must never be treated as zero cost/zero latency/perfect quality.
- Revision changes trigger defined cold-start/requalification behavior.

### IE6-04 — Deterministic decision record
Persist enough input state to reproduce the routing decision:
- candidate set;
- hard constraints;
- empirical summaries;
- scoring revision;
- tie-break rule;
- selected provider/engine;
- rejection reasons for ineligible candidates.

### IE6-05 — Real deterministic replay
Replace the prototype's membership-style replay with actual recomputation from retained decision inputs.

Acceptance:
- replay recomputes the same eligible set, scores, tie break and selection;
- tampered inputs or missing required evidence cause mismatch/failure;
- replay does not merely check that a logged decision exists.

### IE6-06 — Constraint-aware scoring
Possible dimensions only after hard filtering:
- expected verified/integrated goodput;
- expected latency;
- expected spend;
- uncertainty penalty;
- provider health/throttle evidence;
- context/cache compatibility.

Weights/revisions must be explicit and versioned.

### IE6-07 — Exploration bounds
If adaptive exploration is allowed:
- cap exploration rate/cost;
- exclude candidates violating hard constraints;
- make exploration decisions evidence-visible;
- provide disable/rollback control.

### IE6-08 — Adversarial routing qualification
Test tie stability, stale profiles, missing cost, missing latency, new engine cold start, privacy conflicts, budget constraints, deadline constraints, provider throttle, policy revision and tampered replay record.

Exit condition: routing can demonstrate reproducible hard-constraint-first decisions using empirical evidence.

---

## IE-007 — Inference roofline / bottleneck analysis and bounded adaptation

Goal: classify the dominant bottleneck in a RESIDUAL run and expose safe, evidence-backed recommendations or bounded adaptive controls without bypassing production authorities.

Required canonical classes:
- WORKER_BOUND
- CONTEXT_BOUND
- VERIFIER_BOUND
- INTEGRATION_BOUND
- SCHEDULER_ADMISSION_BOUND
- COORDINATION_BOUND
- PROVIDER_BOUND
- MIXED
- UNKNOWN

### IE7-01 — Complete classifier contract
- Add all required classes, especially scheduler/admission pressure.
- Define minimum evidence requirements and ambiguity rules.
- UNKNOWN when evidence is insufficient.

### IE7-02 — Independent classifier oracle
- Maintain a separately implemented reference classifier for frozen scenarios.
- Avoid circular tests that call the production classifier internally.

### IE7-03 — Sensitivity and stability tests
- Test near-threshold cases.
- Ensure tiny metric noise does not cause uncontrolled policy flapping.
- Version thresholds and classification revision.

### IE7-04 — Command Station integration
Expose:
- current/last-run bottleneck class;
- evidence supporting classification;
- incomplete/UNKNOWN state;
- recommended experiment or safe operator action;
- historical comparison where evidence identity is comparable.

The UI must not imply a measured speedup/cost saving that has not been observed.

### IE7-05 — Recommendation-only mode first
Before any automatic adaptation, support non-authoritative recommendations such as:
- investigate provider throttle;
- reduce concurrency experiment;
- increase/decrease bounded concurrency experiment;
- inspect verifier backlog;
- inspect context packaging/cache effectiveness.

### IE7-06 — Bounded adaptive controls, only if spec permits
For each adaptive knob:
- define min/max;
- rate limit changes;
- require sufficient evidence;
- preserve hard safety constraints;
- emit decision evidence;
- provide rollback;
- fall back to static safe configuration on uncertainty/failure.

No placeholder safety flag is acceptable.

### IE7-07 — Rollback and failure containment
Test bad recommendation, stale metrics, conflicting bottlenecks, oscillation, provider outage, verifier outage, failed adaptation, restart and rollback.

### IE7-08 — Browser/Command Station qualification
Where the feature is visible in the public demo or Command Station:
- desktop acceptance;
- narrow Chromium/mobile acceptance where applicable;
- accessibility/readability checks;
- no stale cached classification after a new run;
- evidence link opens the correct exact run.

### IE7-09 — Measured experiment harness
Provide controlled experiments that vary one bounded resource at a time and compare:
- verified/integrated goodput;
- TTFW/TTE/TTA/TTI;
- token/cost usage;
- retries/rework;
- bottleneck class stability.

Exit condition: the roofline layer produces reproducible classifications and any automated change is bounded, reversible, evidence-backed and subordinate to existing safety authority.

---

## Cross-cutting qualification tasks

### X-01 — Authority-boundary tests
For every IE PR, statically and dynamically prove no unintended path can:
- call providers outside accepted provider authority;
- spawn/terminate workers outside accepted runtime authority;
- grant verifier acceptance;
- issue authoritative receipts;
- integrate results;
- mutate protected scheduler/Factory/M4 state.

### X-02 — Exact-head evidence bundle
Each qualification candidate should retain externally or in an approved non-self-referential form:
- exact commit and tree;
- schema/policy revisions;
- frozen scenario inputs;
- normative event streams;
- expected and observed results;
- replay results;
- tamper results;
- focused test results;
- repository CI references;
- applicable measurements.

### X-03 — No false zero semantics
Create shared conformance tests proving UNKNOWN/missing measurements cannot become:
- zero latency;
- zero spend;
- zero tokens;
- zero queue depth when unsampled;
- unlimited capacity;
- perfect success/quality.

### X-04 — Determinism and replay
Every policy decision that may later be cited as qualification/research evidence should have enough retained inputs to be recomputed, not merely looked up.

### X-05 — Concurrency/race qualification
Run adversarial tests around reservations, cancellation, queue transitions, cache operations, profile updates and evidence emission.

### X-06 — Privacy/disclosure review
Ensure observability, caches, profiles and routing records do not expose prompt/content/private identity through metric labels, logs, dashboards or exported bundles.

### X-07 — Performance overhead budget
Measure observer/policy overhead independently from claimed inference savings. A feature that saves inference but imposes disproportionate coordinator overhead must be visible in the evaluation.

### X-08 — Baseline and ablation framework
Before claiming improvements, compare against:
- feature disabled;
- single-variable feature enabled;
- combined policy stack;
- representative task/topology classes.

### X-09 — Regression corpus
Retain frozen scenarios for:
- normal healthy execution;
- unknown evidence;
- provider-bound;
- worker-bound;
- context-bound;
- verifier-bound;
- integration-bound;
- scheduler/admission-bound;
- coordination-bound;
- mixed bottleneck;
- cancellation;
- deadline;
- privacy block;
- budget exhaustion;
- tampered evidence;
- stale source tree/policy revision.

### X-10 — Documentation and non-claims
Each PR must state what it proves and what it does not prove. Prototype correctness is not evidence of production cost reduction, latency reduction, quality improvement, scheduling safety or paper-facing research validity.

---

## Suggested future PR split

1. `IE-002A` — lifecycle/provenance telemetry adapter
2. `IE-002B` — resource/queue/accounting signals + OTX projection
3. `IE-003A` — pressure model + scheduler observation seam
4. `IE-003B` — admission reservations/hysteresis/fairness
5. `IE-004` — provenance-safe bounded context cache
6. `IE-005` — evidence-gated escalation ladder
7. `IE-006A` — empirical profile store + hard-filter composition
8. `IE-006B` — deterministic routing/replay + exploration bounds
9. `IE-007A` — canonical roofline classifier + independent oracle
10. `IE-007B` — Command Station visualization/recommendation mode
11. `IE-007C` — optional bounded adaptation + rollback qualification
12. `IE-EVAL` — controlled ablation/performance/cost evaluation across the integrated stack

This split is deliberately finer than one PR per frozen spec so the highest-risk production-authority changes can be reviewed and qualified separately.

## Deferred ideas after qualification

These are intentionally out of scope until the core chain above is qualified:
- automatic self-tuning across multiple inference-economics knobs at once;
- learned routing policies trained from RESIDUAL telemetry;
- cross-run/cross-user shared cache reuse;
- provider price-arbitrage automation;
- GPU/kernel-level optimization claims;
- autonomous policy promotion to production;
- paper-facing benchmark claims;
- self-modifying scheduler policies.

Any of these should begin as a new frozen spec and must not be smuggled into IE-002 through IE-007 implementation PRs.
