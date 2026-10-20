# IE-007 — Orchestration Roofline, Command Station UX and Adaptive-Control Release Gate

Status: proposed implementation contract  
Prerequisites: qualified IE-001 prototype / #160; IE-002 telemetry / #161; IE-003 pressure control / #162; IE-004 context economics / #163; IE-005 compute ladder / #164; IE-006 routing / #166

## 1. Objective

Turn the inference-engineering program into an operator-visible, evidence-backed control surface.

IE-007 SHALL:

- classify where the end-to-end requirement→accepted-state path is bottlenecked;
- explain that classification from retained measurements;
- expose verified/integrated goodput, queues, stage latency, context economics, escalation and routing behavior in Command Station;
- produce bounded recommendations;
- provide a separately gated path from advisory recommendations to adaptive control.

The term **Orchestration Roofline** is an analogy for system bottleneck diagnosis. It MUST NOT imply that RESIDUAL is computing a hardware FLOP/byte roofline unless real hardware measurements justify that separate claim.

## 2. Bottleneck classes

The qualified classifier SHALL support at least:

- `WORKER_BOUND`
- `CONTEXT_BOUND`
- `VERIFIER_BOUND`
- `INTEGRATION_BOUND`
- `SCHEDULER_ADMISSION_BOUND`
- `COORDINATION_BOUND`
- `PROVIDER_BOUND`
- `MIXED`
- `UNKNOWN`

The exact deterministic classification algorithm/thresholds MUST come from the qualified IE-001 prototype and be revisioned. Production implementation MUST NOT silently tune thresholds after seeing favorable results.

## 3. Evidence required for classification

The classifier MAY use only retained/validated signals such as:

- stage service/queue times;
- queue depth trends;
- pool utilization/capacity;
- provider throttle/rate-limit evidence;
- context packaging bytes/tokens/round trips;
- OTX coordination/tax estimates;
- worker/verifier/integration completion rates;
- accepted/integrated goodput;
- missing/UNKNOWN signal state.

A single slow span is not sufficient by itself to label a persistent bottleneck unless the frozen classifier explicitly says so.

If required signals are missing or contradictory, the classifier SHALL return `UNKNOWN` or `MIXED` rather than inventing precision.

## 4. Recommendation engine

Recommendations SHALL be rule/policy driven, inspectable and evidence-linked.

Examples of allowed recommendation families:

- `VERIFIER_BOUND` → reduce worker admission and/or increase verifier capacity;
- `INTEGRATION_BOUND` → reduce upstream admission and/or increase integration capacity;
- `CONTEXT_BOUND` → inspect IE-004 paging/cache effectiveness, reduce redundant context if policy permits;
- `COORDINATION_BOUND` → consider simpler topology through existing OTX/IE-006 policy;
- `PROVIDER_BOUND` → surface rate/latency evidence and eligible alternative route if one exists;
- `WORKER_BOUND` → consider additional feasible worker capacity or an alternate eligible engine;
- `SCHEDULER_ADMISSION_BOUND` → inspect configured limits/fairness/pressure thresholds.

A recommendation MUST never suggest:

- bypassing verifier authority;
- weakening UNKNOWN/fail-closed behavior;
- sending local-only evidence remote;
- exceeding budget/deadline policy;
- changing protected trust-boundary/qualification thresholds for performance.

## 5. Recommendation confidence

Each recommendation SHALL include:

- bottleneck class;
- classifier revision;
- evidence window/time range;
- supporting metrics;
- missing signals;
- confidence/evidence sufficiency class;
- whether it is advisory or actively applied.

Confidence MUST reflect evidence sufficiency, not stylistic model certainty.

## 6. Command Station experience

Add an operator surface containing at minimum:

### 6.1 End-to-end flow

Visualize:

`Submit → Plan → Admission → Context → Worker → Evidence → Verify → Integrate`

Each stage should show current/selected run measurements and drill-down explanation.

### 6.2 Core economics

Display separately:

- attempt throughput;
- verifier terminal throughput;
- accepted goodput;
- integrated goodput;
- correctness goodput only when independently graded;
- TTFW/TTE/TTA/TTI;
- orchestration tax;
- provider/token/cost fields only when authoritative.

### 6.3 Pressure

Display:

- ready/admission queue;
- active/capacity worker pool;
- verifier queue/utilization;
- integration queue/utilization;
- backpressure state and reason.

### 6.4 Context economics

Display:

- context source/framed bytes;
- prompt/cache tokens when authoritative;
- semantic fragment hit/miss/invalidation;
- window request/round-trip counts;
- no raw local-only evidence by default.

### 6.5 Compute ladder

Display:

- current tier;
- escalation reason;
- speculative/sequential state;
- canceled/late work;
- budget/placement blocks.

### 6.6 Routing

Display:

- selected engine/topology;
- hard feasibility filters;
- empirical profile sample size/uncertainty;
- shadow vs active decision when applicable;
- reason/fallback.

## 7. Data/privacy UI rules

The UI SHALL default to metadata, metrics, hashes/identities and bounded explanations.

It MUST NOT expose raw private evidence, prompts or candidate contents merely because economics telemetry exists.

Existing Command Station authentication/authorization and CSP/security boundaries remain authoritative.

## 8. Advisory mode

The first accepted IE-007 implementation SHALL be advisory by default.

Advisory mode:

- classifies bottlenecks;
- shows recommendations;
- may compute what control changes would be proposed;
- MUST NOT automatically change routing, concurrency, context, budgets or tier policy.

Advisory decisions MUST be replayable from retained observations/config.

## 9. Adaptive control mode

Adaptive mode is a separately gated capability.

Permitted adaptive knobs MAY include only already-authorized operational policy surfaces, for example:

- IE-003 admission/concurrency thresholds within configured min/max bounds;
- IE-004 context paging mode within disclosure/budget policy;
- IE-005 eligible sequential/speculative policy within pre-authorized modes;
- IE-006 empirical engine/topology choice within the hard-feasible set.

Adaptive mode MUST NOT change:

- verifier code/revision/thresholds;
- PASS/FAIL/UNKNOWN semantics;
- receipt authority;
- integration eligibility/trust rules;
- privacy/disclosure authority;
- maximum budget/deadline ceilings;
- protected M4 security controls.

## 10. Bounded-control invariant

Every adaptive knob SHALL have operator-configured immutable bounds for the run/config revision.

The controller cannot expand those bounds itself.

Every applied change MUST retain:

- previous value;
- new value;
- permitted bound;
- evidence/recommendation that triggered it;
- controller/config revision;
- timestamp/run identity;
- rollback result if later reverted.

## 11. Rollback / kill switch

Adaptive control SHALL have a deterministic immediate disable path that returns to accepted static policy without altering accepted state.

Failure of the adaptive controller MUST result in:

- safe fallback to static accepted configuration, or
- explicit stop/BLOCKED when safe fallback cannot be established.

It MUST NOT continue with unknown controller state.

## 12. Required tests

### T1 — bottleneck oracle

All single-dominant IE-001 frozen scenarios classify exactly according to the independent oracle.

### T2 — mixed/unknown

Mixed and missing-evidence fixtures return `MIXED`/`UNKNOWN`, not a fabricated dominant class.

### T3 — explanation binding

Every classification/recommendation references the exact supporting metric snapshot/config revision used.

### T4 — unsafe recommendation suppression

A local-only/provider-bound fixture cannot recommend an ineligible remote engine or disclosure expansion.

### T5 — trust-boundary immutability

No recommendation/adaptive action can modify verifier/receipt/integration/privacy/M4 authority.

### T6 — UI metric fidelity

Displayed values match the retained observation projection for a frozen run. UNKNOWN remains visibly UNKNOWN.

### T7 — correctness labeling

Without independent grades, UI never relabels accepted goodput as correct goodput.

### T8 — sensitive-data boundary

Telemetry/roofline pages do not expose raw protected evidence/prompt content by default.

### T9 — advisory non-interference

Advisory mode produces no execution-policy mutations.

### T10 — bounded adaptive action

Adaptive controller attempts outside operator-configured bounds are rejected and retained as blocked actions.

### T11 — deterministic rollback

Kill switch/failure fallback restores the declared static policy deterministically and records the transition.

### T12 — replay

Given the same validated observations/config/profile snapshots, classification, recommendations and adaptive actions replay exactly.

### T13 — stale data

A stale/incompatible observation/profile revision cannot drive an active change without explicit compatibility policy.

### T14 — browser/UX qualification

Desktop and narrow/mobile Command Station views render the full economics surface without hiding UNKNOWN/error states. Keyboard/focus/accessibility behavior is included in browser acceptance.

### T15 — exact-head repository qualification

All applicable existing CI remains green. No protected M4 file/test/pin/shared evidence schema change occurs without explicit dependency stop.

## 13. Adaptive release gate

Do not enable adaptive mode by default merely because T1–T15 pass.

Required sequence:

1. qualified IE-001 prototype;
2. accepted IE-002–IE-006 prerequisites;
3. advisory-only exact-head qualification;
4. frozen engineering workload and baseline configuration;
5. preregistered comparison criteria before observing adaptive outcomes;
6. bounded opt-in adaptive run/canary;
7. independently reviewed evidence showing no trust-boundary violation and acceptable reliability/economics behavior;
8. explicit operator/maintainer decision before default-on rollout.

Where ground-truth task grading exists, the release comparison SHOULD include accepted error/correct-integrated outcomes as well as economics. Without independent grades, no correctness-improvement claim is allowed.

## 14. Command Station product language

The UI MUST prefer factual labels such as:

- `Observed bottleneck`
- `Evidence sufficiency`
- `Recommendation`
- `Shadow decision`
- `Applied bounded control`

Avoid claims such as "optimal", "self-optimizing", or "best model" unless separately proven under a defined scope.

## 15. Exit criteria

IE-007 exits when:

- the roofline classifier reproduces the qualified prototype;
- Command Station faithfully renders metrics/UNKNOWN states;
- advisory mode is non-interfering and independently reviewed;
- all adaptive actions, if implemented, remain within explicit bounds and replay exactly;
- rollback is qualified;
- exact-head browser + repository CI passes;
- no protected trust authority is tuned for performance.

## 16. Program completion condition

The seven-PR inference-engineering program is technically integrated when IE-001 through IE-007 are accepted and their exact-head gates pass.

A stronger claim — that the program improves real RESIDUAL performance/cost — requires measured comparison on declared workloads/providers/hardware and is separate evidence.
