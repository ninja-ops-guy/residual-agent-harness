# IE-006 — Capability-Aware Engine and Topology Routing from Observed Outcomes

Status: proposed implementation contract  
Prerequisites: qualified IE-001 prototype / #160; accepted IE-002 telemetry / #161; IE-005 compute ladder / #164; existing `CapabilityRouter` and `residual.otx` remain source authorities

## 1. Objective

Allow RESIDUAL to choose among feasible engines/providers and execution topologies using observed evidence about latency, acceptance behavior, cost and orchestration tax, while preserving hard capability/privacy/budget constraints and explicit uncertainty.

IE-006 MUST NOT implement a monolithic "best model" selector. It composes existing hard-feasibility routing and topology policy with an empirical decision layer.

## 2. Authority split

The following separation SHALL remain explicit:

- `CapabilityRouter` / equivalent hard constraints decide which engines are feasible for required capabilities/placement;
- disclosure/privacy policy decides which remote/local destinations are allowed;
- budget/deadline policy decides which candidates are affordable/eligible;
- `OrchestrationTaxController` or accepted successor estimates topology overhead/utility;
- IE-006 ranks only the remaining feasible engine/topology choices using retained observed evidence;
- verifier/integrator remain acceptance/state authorities.

No statistical profile may override a hard privacy, capability, budget, cancellation or trust-boundary rule.

## 3. Profile identity

Observed profiles SHALL be segmented by every revision that can materially change behavior, including as applicable:

- engine/provider/model immutable identity or revision;
- adapter revision;
- task class / obligation class;
- assurance class;
- topology;
- relevant tool/capability mode;
- local-vs-remote placement class;
- context policy revision where materially different.

A model upgrade MUST NOT silently inherit an old model revision's normative profile as if it were the same population.

Historical data MAY be used as an explicit prior only if marked as such and uncertainty remains visible.

## 4. Observed outcome fields

Minimum per-profile evidence when available:

- attempts;
- verifier PASS/FAIL/UNKNOWN/abstention/provider-error rates;
- accepted-goodput contribution;
- latency distribution;
- queue/admission delay distribution;
- request/input/output/cache token use when authoritative;
- calculated cost when authoritative;
- orchestration tax/topology overhead;
- cancellation/rework frequency;
- context size class;
- observation recency/revision.

Verifier PASS rate is **acceptance behavior**, not ground-truth correctness.

Correctness/reliability estimates beyond verifier acceptance may be used only when an independent grade/gold label exists and is bound to the observation.

## 5. Uncertainty-aware estimation

The controller SHALL retain uncertainty and sample count rather than using raw means alone.

Acceptable v1 approaches include:

- beta/binomial posterior for PASS/terminal-rate estimates;
- uncertainty-aware latency/cost estimates;
- reuse of existing OTX posterior machinery where semantically appropriate.

Cold-start profiles MUST be explicit. A single successful run MUST NOT make an engine/topology appear certain or universally preferred.

## 6. Feasible candidate construction

For an obligation, candidate construction SHALL occur in this order:

1. resolve hard required capabilities;
2. enforce placement/privacy constraints;
3. enforce tier eligibility from IE-005;
4. enforce budget/deadline constraints;
5. enumerate allowed topologies;
6. attach empirical profile estimates/uncertainty;
7. score/rank only the feasible set.

An empty feasible set produces an explicit typed reason, not a fabricated fallback.

## 7. Decision objective

The first decision objective SHALL be configuration-driven, inspectable and replayable.

It MAY combine quantities such as:

- predicted probability of verifier acceptance;
- predicted latency;
- predicted orchestration tax;
- predicted cost when known;
- uncertainty penalty;
- task/assurance-specific value weights.

It MUST NOT call `P(verifier PASS)` "P(correct)" unless independent correctness labels justify that mapping.

Suggested nomenclature:

`expected_verified_utility`

rather than `expected_correctness`.

If any required term is UNKNOWN, the scoring policy MUST define how UNKNOWN affects feasibility/ranking. UNKNOWN MUST NOT silently become zero cost/zero latency/perfect quality.

## 8. Shadow mode first

Initial production integration SHALL run in **shadow/advisory mode**:

- existing accepted routing decision executes;
- IE-006 computes the decision it would have made;
- both decisions and predicted outcomes are retained;
- no provider/topology behavior changes.

Active mode is gated until shadow replay/calibration and independent review are complete.

## 9. Active mode

When active mode is qualified:

- the chosen engine/topology MUST come from the hard-feasible set;
- the complete decision inputs/profile snapshot/config hash MUST be retained;
- fallback on missing/corrupt profile data MUST be deterministic and conservative;
- profile update occurs only after authoritative observed outcomes are available;
- a failed/UNKNOWN execution remains evidence and cannot be omitted from learning merely because it is unfavorable.

## 10. Selection bias and exploration

Observed profiles are affected by prior routing choices.

The implementation MUST disclose this limitation and MUST NOT claim unbiased comparative model quality from opportunistic production observations.

Optional bounded exploration MAY be implemented only when:

- explicitly enabled;
- allowed by assurance/privacy/budget policy;
- limited to eligible low-risk workloads or an experimental environment;
- separately measured/accounted;
- deterministic from a retained seed/config if replay is required.

No exploration is required for v1 active routing.

## 11. Drift and recency

Profiles SHOULD support explicit aging/recency without rewriting history.

Permitted strategies include revision segmentation and bounded recency weighting.

The controller MUST expose when evidence is stale or too sparse for confident preference.

## 12. Required tests

### T1 — hard constraint dominance

An empirically high-scoring remote engine is never selected when privacy/placement disallows it.

### T2 — capability dominance

An engine missing a required tool/capability is never selected regardless of historical performance.

### T3 — budget dominance

An otherwise preferred candidate exceeding remaining budget is excluded before scoring/dispatch.

### T4 — PASS vs correctness semantics

A profile with many verifier PASS observations but no gold labels exposes high acceptance rate only; correctness remains UNKNOWN.

### T5 — revision isolation

Changing model/adapter revision creates a separate profile/cold-start state rather than silently inheriting certainty.

### T6 — uncertainty

A low-sample perfect record does not receive the same confidence as a high-sample record under the configured uncertainty-aware estimator.

### T7 — deterministic replay

Given identical candidate set, profile snapshot and config, the decision and explanation replay exactly.

### T8 — shadow non-interference

Shadow mode cannot change actual engine/topology dispatch. Baseline outcomes remain equivalent.

### T9 — incomplete telemetry

Missing cost/latency/acceptance inputs follow the explicit UNKNOWN policy and cannot become zero/perfect values.

### T10 — OTX composition

Topology tax/utility comes from existing accepted OTX interfaces or an explicit adapter; IE-006 does not fork a second independent topology learner.

### T11 — failure learning

FAIL/UNKNOWN/provider errors that reached dispatch are retained in profile evidence according to the declared outcome model; unfavorable results cannot simply disappear.

### T12 — fallback

Corrupt/missing profile storage produces a deterministic safe fallback to accepted baseline routing or explicit no-decision, never arbitrary selection.

### T13 — active-mode boundedness

When active, every selected candidate is proven to be in the hard-feasible candidate set recorded for that decision.

### T14 — exact-head regression

All applicable existing CI remains green. No protected M4 file/test/pin/shared schema changes without dependency stop.

## 13. Qualification sequence

1. shadow mode only;
2. deterministic replay over frozen profile fixtures;
3. compare shadow choices with baseline on retained engineering workloads;
4. independently review calibration/UNKNOWN behavior;
5. enable active mode only in bounded opt-in configuration;
6. compare active vs baseline on a frozen workload before any default change.

Required comparison outputs:

- accepted/integrated goodput;
- acceptance coverage;
- latency;
- cost/tokens when authoritative;
- OTX/orchestration tax;
- routing decision distribution;
- fallback/UNKNOWN frequency;
- profile sample sizes/uncertainty.

## 14. Exit criteria

IE-006 exits when:

- IE-001 prototype routing model is qualified;
- shadow mode passes T1–T14 and independent review;
- replay is exact;
- PASS/correctness semantics remain separated;
- hard constraints provably dominate empirical scores;
- active mode, if included, is separately qualified on exact head.

## 15. Non-goals

This PR does not:

- claim an objective universal best model;
- infer model competence from brand/size alone;
- use verifier PASS as automatic ground-truth correctness;
- override privacy/budget/capability rules;
- produce election-style rankings or public model leaderboards;
- prove causal performance differences from opportunistic production observations.
