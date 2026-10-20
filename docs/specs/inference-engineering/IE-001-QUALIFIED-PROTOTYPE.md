# IE-001 — Qualified Inference & Orchestration Economics Prototype

Status: proposed implementation contract  
Planning base: `main@f6f9bad84caccf68c7ab35e5788e756d12c55fb7`  
Program: Inference Engineering for RESIDUAL  
Role: prerequisite for IE-002 through IE-007

## 1. Purpose

Before changing production scheduling, routing, context construction, provider dispatch, verifier admission, or integration behavior, RESIDUAL SHALL build and qualify a deterministic prototype of the proposed inference-engineering control layer.

The prototype exists to answer one question before production implementation begins:

> Can RESIDUAL measure and reason about the path from submitted requirement to accepted/integrated state without weakening its evidence-first trust boundaries or confusing throughput with useful accepted work?

This PR is a specification only. It MUST NOT implement production runtime behavior.

## 2. Existing capabilities that MUST be reused rather than reinvented

Current `main` already contains several relevant primitives:

- ready-frontier obligation scheduling;
- bounded evidence-window requests and adaptive residual packet construction;
- receipt-bound cache semantics with verifier revalidation;
- `CapabilityRouter` for engine capability selection;
- `residual.otx.OrchestrationTaxController` for task/topology-conditioned orchestration-tax learning and replay;
- verifier-defined acceptance, deterministic integration, receipts and audit surfaces.

The prototype SHALL treat these as source architecture. It MUST NOT replace them with a second scheduler, second acceptance authority, second receipt format, or second evidence bus.

Open PR #93 contains additional orchestration-economics/observability hardening. The implementation of this program MUST NOT silently depend on that unmerged branch. If #93 is accepted before IE implementation begins, reuse its accepted interfaces. Otherwise, reimplement only the minimal required behavior on the then-current accepted `main` and document overlap/supersession explicitly.

## 3. Protected boundaries

The prototype MUST NOT modify:

- protected Factory/M4 trust-boundary implementation;
- protected M4 qualification tests or ownership pins;
- shared accepted-evidence schemas;
- verifier PASS/FAIL/UNKNOWN semantics;
- receipt acceptance authority;
- provider credential/authorization semantics;
- integration eligibility rules;
- release or research qualification thresholds.

If prototype work requires any protected change, STOP and report the dependency rather than widening scope.

## 4. Prototype location and authority

Implementation SHOULD live in a clearly experimental namespace such as:

- `residual/prototypes/inference_economics/`, or
- an equivalently isolated development-only package approved during implementation review.

The prototype MUST operate on frozen traces, deterministic fixtures, or replayed observations. It MUST NOT be wired into production dispatch or accepted-state authority.

The prototype SHALL be incapable of causing:

- a provider call;
- worker spawn/termination;
- verifier acceptance;
- receipt issuance;
- integration;
- mutation of production scheduling state.

## 5. Canonical lifecycle model

The prototype SHALL model the end-to-end path using monotonic timestamps and explicit stage identity.

Minimum stages:

1. `mission_submit`
2. `planning`
3. `scheduling`
4. `queue_wait`
5. `context_packaging`
6. `worker_execution`
7. `evidence_publication`
8. `verification`
9. `integration_queue`
10. `integration`
11. `terminal`

Each observation MUST bind:

- run/mission identity;
- obligation identity;
- task class;
- topology;
- engine/provider class when known;
- source commit/tree identity;
- monotonic start/end or point timestamp;
- outcome classification;
- simulated/replayed/live-evidence class;
- observation-schema revision.

Missing timestamps MUST remain missing/UNKNOWN. They MUST NOT be synthesized as zero-duration work.

## 6. Metric contract

### 6.1 Throughput classes

The prototype MUST distinguish at least:

- `attempt_throughput = completed_worker_attempts / wall_time`
- `accepted_goodput = verifier_accepted_obligations / wall_time`
- `integrated_goodput = integrated_obligations / wall_time`

`accepted_goodput` MUST NOT be labeled ground-truth correctness.

When and only when an independent gold label exists, the prototype MAY also report:

- `correct_accepted_goodput`
- `correct_integrated_goodput`

No gold label means correctness goodput is `UNKNOWN`, not zero.

### 6.2 Latency classes

Minimum derived measurements:

- TTFW — time from mission submission to first worker start;
- TTE — time from mission submission to first evidence publication;
- TTA — obligation eligible/dispatch point to verifier terminal decision;
- TTI — mission submission to controlled integration of the final required accepted artifact;
- per-stage queue/service time distributions;
- p50/p95/p99 where sample count permits.

A mission-level scalar MUST NOT erase per-obligation or per-stage distributions.

### 6.3 Resource/pressure measurements

Minimum signals:

- ready-frontier size;
- worker active/capacity;
- verifier active/capacity;
- integration queue depth;
- context bytes and tokens when known;
- provider-reported prompt/completion/cache tokens when known;
- provider/model cost when authoritative usage and price data exist;
- cache lookup/hit/miss/revalidation outcomes;
- retries/rework/rejection/conflict counts;
- cancellation/escalation counts.

Unknown usage or price MUST remain `null`/UNKNOWN.

### 6.4 Orchestration tax

The prototype SHALL preserve the existing OTX concept rather than inventing an incompatible definition.

It MAY additionally expose decomposed control-plane costs, but any alternate tax ratio MUST have a distinct name and formula.

## 7. Prototype scenarios

A frozen deterministic scenario set SHALL exercise at least:

1. **worker-bound** — worker service dominates;
2. **verifier-bound** — worker output arrives faster than verification capacity;
3. **context-bound** — context packaging/transfer dominates;
4. **integration-bound** — accepted work accumulates behind integration;
5. **coordination-bound** — swarm overhead dominates useful worker service;
6. **provider-bound** — synthetic rate/latency constraints dominate;
7. **mixed** — no single stage dominates by a large margin;
8. **UNKNOWN evidence** — required observations are missing or incomparable.

Each scenario MUST have an independent oracle describing the expected bottleneck class, queue behavior and metric values/ranges.

## 8. Prototype policy models

The prototype SHALL model, but not activate, the policies later implemented by IE-002 through IE-007:

- passive production telemetry;
- pressure-aware admission/backpressure;
- context paging/reuse;
- evidence-gated compute escalation;
- capability/topology selection;
- roofline/bottleneck classification.

All prototype policies MUST be replayable from retained input events.

## 9. Qualification gates

The prototype is QUALIFIED only if all gates pass on one exact head.

### Q1 — Determinism

Given identical frozen inputs/config, two clean executions MUST produce byte-equivalent normative decisions and metric records except explicitly non-normative environment metadata.

### Q2 — Replay

Retained observation streams MUST reproduce every policy decision exactly. Tampered, missing, reordered, or incompatible normative observations MUST fail closed.

### Q3 — Independent metric oracle

A separately implemented oracle MUST agree on:

- throughput classes;
- accepted/integrated goodput;
- TTFW/TTE/TTA/TTI;
- queue depths;
- stage utilization;
- orchestration-tax input totals.

### Q4 — Correctness non-conflation

Tests MUST prove:

- high attempt throughput can coexist with low accepted goodput;
- high accepted goodput does not become `correct_goodput` without gold labels;
- UNKNOWN evidence never becomes PASS/zero/correct.

### Q5 — Pressure model

In verifier/integration-bound fixtures, the simulated pressure-aware policy MUST keep queues within configured bounds or emit an explicit saturation/overload result. It MUST NOT silently drop accepted/evidence-bearing work.

### Q6 — Provenance cache model

Changing any normative cache-key input required by IE-004 MUST invalidate reuse. Cache reuse MUST never bypass verifier authority or disclosure policy.

### Q7 — Escalation model

A cheap tier accepted by independent verification MUST prevent unnecessary expensive escalation in the sequential policy. FAIL/UNKNOWN MUST escalate according to frozen policy without being converted to PASS.

### Q8 — Routing model

A retained profile set MUST reproduce engine/topology choices exactly. Cold-start/insufficient-evidence conditions MUST remain explicit and deterministic.

### Q9 — Bottleneck classifier

All single-dominant frozen scenarios MUST be classified according to the independent oracle. Mixed and insufficient-evidence fixtures MUST return `MIXED`/`UNKNOWN` rather than a fabricated single bottleneck.

### Q10 — Repository regression

All applicable existing exact-head CI remains green. Prototype tests are additive. No protected ownership baseline is changed.

### Q11 — Independent review

A genuinely independent current-head technical review is required before the prototype can be used as the implementation contract for IE-002 through IE-007.

## 10. Prototype evidence bundle

Qualification SHALL retain a hash-bound bundle containing:

- exact commit and tree;
- configuration;
- fixture/scenario manifest and hashes;
- normative event streams;
- oracle results;
- prototype results;
- replay result;
- test results;
- metric schema revision;
- non-claims.

Suggested artifact schema prefix:

`residual.inference-economics.prototype.v1`

This schema is development-only and MUST NOT be treated as a shared Factory/M4 evidence schema.

## 11. Exit criteria

IE-001 exits only when:

- the prototype is implemented outside production authority;
- Q1–Q11 pass on the same exact head;
- the evidence bundle is retained and hash-bound;
- independent review accepts the prototype;
- the formulas and stage vocabulary are frozen for the next implementation sequence.

Only then should production implementation begin.

## 12. Downstream sequence

After qualification, implement in this order:

1. IE-002 — passive lifecycle telemetry + verified goodput;
2. IE-003 — pressure-aware admission/backpressure and logical pool separation;
3. IE-004 — context economics + provenance-safe context reuse;
4. IE-005 — evidence-gated compute ladder/speculative escalation;
5. IE-006 — capability-aware engine/topology routing;
6. IE-007 — orchestration roofline, Command Station UX and adaptive-control release gate.

Later PRs MUST rebase on accepted `main`; they MUST NOT assume this planning base remains current.

## 13. Non-claims

A qualified prototype proves only that the measurement/policy model is coherent, deterministic, replayable and compatible with RESIDUAL's stated trust boundaries on frozen inputs.

It does NOT prove:

- production speedup;
- lower real provider cost;
- model quality improvement;
- production reliability;
- live scheduling safety;
- GPU-level inference optimization;
- paper-facing research results.
