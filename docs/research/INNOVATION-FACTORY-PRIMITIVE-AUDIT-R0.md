# INNOVATION FACTORY PRIMITIVE AUDIT R0

**Status:** Research program / composition audit  
**Repository:** `ninja-ops-guy/residual-agent-harness`  
**Research Workbench lane:** `feature/research-workbench` / PR #323  
**Intent:** Determine whether the primitives required for the proposed autonomous **Innovation Factory** already exist in RESIDUAL, and identify only the missing composition, wiring, qualification, and operational surfaces.

## 1. Research question

Can RESIDUAL operate an Innovation Factory primarily by composing existing primitives—Station, Research Workbench, scheduler/DAG machinery, mesh workers, OpenClaw runners, provider routing, project budgets, evidence/verification, Doctor, Shared Comms, and artifact transport—rather than by inventing a new subsystem?

The working hypothesis is:

> Most conceptual Innovation Factory primitives already exist in RESIDUAL. The dominant remaining work is likely integration at the seams, exact implementation-generation selection, deployment wiring, and live qualification.

This document is a **research/audit charter**, not authority to implement, deploy, merge, or mutate live fleet state.

## 2. Target operating mode

The proposed Innovation Factory is a bounded Station operating profile in which:

1. the owner defines a research program, budgets, allowed scopes, and protected actions;
2. Research Workbench supplies or admits experiment/research definitions;
3. Station owns durable mission/task state and dependency release;
4. eligible OpenClaw workers receive bounded assignments through existing runner/mesh machinery;
5. local models and FreeLLMAPI-backed routes are selected according to existing provider policy, capability, placement, readiness, and budget rules;
6. agents collaborate through Shared Comms/group-chat projection without making chat the source of mission authority;
7. artifacts, reviews, receipts, and experiment results return through governed evidence/admission paths;
8. verifier independence and integration gates are preserved;
9. known failures can be diagnosed through Doctor/health evidence;
10. owner involvement is reserved for explicit authority gates, unknown failure classes, or protected operations.

Desired shape:

```text
Owner
  ↓
Research program / budgets / protected authority
  ↓
Research Workbench
  ↓
Station task graph / scheduler
  ↓
Mesh / runner / OpenClaw seats
  ↓
local providers / FreeLLMAPI / other admitted routes
  ↓
artifacts + evidence + review
  ↓
verification / integration / Workbench promotion
  ↓
Station durable state
  ↓
Shared Comms projection
```

The group chat is a collaboration and observability surface. It is not the authoritative scheduler, artifact store, mission ledger, or owner authority.

## 3. Audit rule

Do **not** design or implement new architecture until existing primitives have been exhaustively mapped.

For every apparent gap:

1. inspect implementation code;
2. inspect tests;
3. inspect schemas/contracts;
4. inspect active candidate lineages and stacked PRs;
5. inspect Research Workbench and historical experiment branches;
6. distinguish accepted-main state from valid unmerged candidate state;
7. prove that no existing primitive provides the required semantics before proposing a new component.

Absence of an obvious UI or CLI command does not establish absence of a primitive.

Likewise, the existence of a specification does not establish implementation.

## 4. Required capability inventory

Audit at least the following capabilities.

### Research / task model
- research item / experiment representation;
- immutable experiment identity;
- prerequisite/dependency DAG;
- runnable-set computation;
- task/role representation;
- successor generation;
- terminal states including PASS/FAIL/UNKNOWN/BLOCKED;
- Workbench promotion path;
- run history and evidence bundles.

### Scheduler / execution control
- task assignment;
- worker leases;
- deadline processing;
- recovery/resume;
- stale-generation fencing;
- project generation;
- assignment acknowledgement;
- durable progress/result submission;
- integration/review transitions;
- owner gates.

### Worker / OpenClaw integration
- discovery;
- enrollment;
- capability declarations;
- project/capability scope;
- mapping;
- qualification;
- activation;
- local coordinator / multi-agent execution;
- worker availability/health;
- fresh-session recovery.

### Durable transport
- outbox;
- inbox;
- replay cursors;
- idempotency;
- dead letters;
- artifact transport;
- artifact identity/version binding;
- byte-exact verification;
- transport receipt;
- artifact-available dependency release;
- post-verification mutation handling.

### Provider/resource control
- local/cloud engine classification;
- provider route identity;
- project call budgets;
- cloud-call budgets;
- request-byte budgets;
- allow-cloud policy;
- provider readiness;
- breaker state;
- FreeLLMAPI integration;
- fallback policy;
- fresh readiness maintenance;
- exact-context admission;
- usage accounting;
- ambiguous-consumption handling.

### Verification / evidence
- evidence bus;
- receipts;
- prerequisite receipt binding;
- independent verifier assignment;
- review;
- deterministic integration;
- result acceptance;
- release evidence;
- provenance;
- Research Workbench evidence export.

### Health / recovery
- health observations;
- freshness;
- temporal/absence detection;
- first-divergence analysis;
- Doctor aggregation;
- qualified detector registry;
- health facts consumable by scheduler;
- UNKNOWN retention;
- safe-continuation classification;
- Workbench promotion of new failure specimens.

### Collaboration / projection
- Shared Comms envelopes;
- room/group projection;
- authenticated ingress;
- projection of Station events;
- agent-to-agent collaboration;
- transport-vs-authority distinction;
- owner-visible state;
- reconciliation after coordinator/session loss.

## 5. Classification vocabulary

Every capability must receive exactly one primary state:

- `EXISTS_AND_WIRED`
- `EXISTS_NOT_WIRED`
- `PARTIAL`
- `SPEC_ONLY`
- `SUPERSEDED`
- `MISSING`

An additional qualification status may be recorded independently:

- `UNQUALIFIED`
- `HOSTED_QUALIFIED`
- `LIVE_QUALIFIED`
- `HISTORICAL_ONLY`
- `BLOCKED`

Do not collapse implementation state and qualification state.

Example:

```text
provider continuity:
  implementation = EXISTS_AND_WIRED
  qualification  = HOSTED_QUALIFIED
  live qualification = BLOCKED/PENDING
```

## 6. Required evidence per finding

For each capability, bind findings to:

- source path;
- exact repository HEAD/TREE;
- implementation symbol(s);
- test path(s);
- governing spec/contract;
- active PR/branch lineage;
- known successor/superseding artifact;
- live qualification receipt where applicable;
- current blocker;
- consumer(s) and producer(s).

Do not rely on chat summaries as controlling evidence.

## 7. Required seam analysis

Produce a seam matrix using this shape:

| Producer | Produced contract/state | Consumer | Connected now? | Missing adapter/wiring | Qualification needed |
|---|---|---|---|---|---|

At minimum evaluate these seams:

1. Research Workbench → Station task graph
2. Station runnable set → scheduler
3. scheduler → mesh worker assignment
4. mesh assignment → OpenClaw runner
5. OpenClaw invocation → Station provider budget/accounting
6. execution path → provider continuity / FreeLLMAPI
7. provider readiness → scheduler/admission
8. worker result → verifier/reviewer assignment
9. verifier result → integration / successor release
10. artifact production → durable transport
11. transport receipt → artifact availability
12. artifact availability → dependency release
13. Station events → Shared Comms projection
14. Shared Comms ingress → governed Station action
15. telemetry/observations → Doctor
16. Doctor HealthFact → scheduler-safe continuation
17. Research Workbench failure specimen → qualified detector promotion
18. owner gate → unrelated-work continuation
19. coordinator/session death → durable mission continuation
20. Workbench terminal → successor research item generation, if supported.

## 8. Specific hypotheses to test

### H1 — Research Workbench is already the experiment-admission layer
Determine whether Workbench can feed the existing Station job/task system without a new research scheduler.

### H2 — roles can be expressed as existing task/capability policy
Determine whether Explorer / Builder / Challenger / Verifier / Integrator are simply task templates using existing fields such as role, capability requirements, engine hints, and independent-review constraints.

### H3 — provider economics already exist
Determine whether existing project ceilings, call reservations, cloud-call limits, placement rules, provider routes, and continuity policy are sufficient to govern local-vs-FreeLLMAPI usage without a separate token-economics subsystem.

### H4 — group chat is already projectable from Station
Determine whether Shared Comms can represent research collaboration as projection/ingress while Station remains authoritative.

### H5 — autonomy is primarily a seam problem
Determine whether native deadline consumption, runnable-set recomputation, durable assignment, artifact-availability release, and known-recovery actions already exist separately but are not yet composed end to end.

### H6 — Innovation Factory can be an operating profile
Determine whether the final implementation can be primarily configuration/templates/contracts over existing primitives rather than a new service.

## 9. Provider policy research target

The Innovation Factory should evaluate whether existing mechanisms can support a policy such as:

```text
local/cheap route
    ↓
quality or capability threshold unmet
    ↓
FreeLLMAPI admitted route
    ↓
stronger/premium route only if policy and budget permit
```

The audit must not assume cost alone controls routing.

Representative task classes to map:

- file scanning;
- log summarization;
- deterministic test generation;
- boilerplate implementation;
- broad research synthesis;
- adversarial review;
- independent verification;
- architecture adjudication;
- repetitive regression work.

Provider selection remains subject to exact route identity, readiness, authority, budget, placement, sharing policy, and result verification.

## 10. Research-governance target

Evaluate whether existing Workbench and Station primitives can support:

```text
IDEA
  ↓
TRIAGE
  ↓
HYPOTHESIS
  ↓
EXPERIMENT_DESIGN
  ↓
EXECUTION
  ↓
CHALLENGE
  ↓
VERIFICATION
  ↓
INTEGRATION
  ↓
PROMOTED / REFUTED / INCONCLUSIVE / BLOCKED / UNKNOWN
```

Do not create this lifecycle if equivalent existing states/transitions already cover it. Prefer mappings/adapters/templates over duplicated state machines.

## 11. Autonomy target

The desired future qualification is an owner-absent bounded research run:

```text
INNOVATION_FACTORY_8H

owner supplies:
  research program
  budgets
  allowed scopes
  protected authority

required:
  multiple admitted research items
  >= 3 concurrent functional roles
  >= 2 provider routes where policy permits
  >= 1 local model
  >= 1 FreeLLMAPI route
  automatic dependency release
  durable artifact delivery
  independent review
  budget enforcement
  provider continuity
  unknown-result handling
  durable final synthesis

forbidden:
  owner message routing
  chat-only authority
  unauthorized protected mutation
  lost accepted artifacts
  unbounded retry loops
  duplicate experiment loops
```

This is a future qualification target, not a current capability claim.

## 12. Self-improvement boundary

The Innovation Factory may research RESIDUAL itself:

- scheduler efficiency;
- provider routing;
- transport robustness;
- Doctor detectors;
- prompt/context efficiency;
- local-model benchmarking;
- adapters;
- coordination failure modes;
- test generation.

But research output must not automatically deploy control-plane modifications.

Required promotion path for protected/core changes:

```text
research result
→ candidate
→ independent verification
→ integration qualification
→ owner/protected authority gate
```

Lower-risk artifacts such as tests, benchmarks, research notes, sandbox fixtures, and experimental branches may be more autonomous according to existing policy.

## 13. Duplicate/loop controls

Audit whether existing identity, digest, DAG, replay, and Workbench mechanisms are sufficient to prevent repeated experiments.

Desired semantics include:

- hypothesis identity/fingerprint;
- experiment identity/fingerprint;
- artifact digest;
- result signature;
- duplicate admission rejection or explicit deduplication contract;
- bounded successor depth;
- synthesis/gate after repeated inconclusive descendants.

Do not invent semantic deduplication if existing exact-context identity rules intentionally forbid it.

## 14. Deliverables

Produce exactly these research artifacts:

1. `INNOVATION_FACTORY_PRIMITIVE_MAP_R0.md`
2. `INNOVATION_FACTORY_SEAM_MATRIX_R0.md`
3. `INNOVATION_FACTORY_MINIMAL_INTEGRATION_PLAN_R0.md`

The minimal integration plan must:

- reuse existing primitives wherever semantics match;
- identify exact implementation generations to compose;
- identify conflicts between lineages;
- separate wiring from new implementation;
- identify required migrations/adapters;
- list missing tests;
- define a bounded integration candidate;
- define live qualification gates;
- avoid a competing scheduler/supervisor if Station/SC-E already owns that responsibility.

## 15. Terminal dispositions

Allowed terminal conclusions:

- `INNOVATION_FACTORY_PRIMITIVES_SUFFICIENT__INTEGRATION_REQUIRED`
- `INNOVATION_FACTORY_PRIMITIVES_PARTIAL__BOUNDED_GAPS_IDENTIFIED`
- `INNOVATION_FACTORY_BLOCKED_ON_LINEAGE_OR_CONTROLLING_BYTES`

Do not claim the Innovation Factory operational from specs, hosted tests, or isolated primitives alone.

## 16. Non-goals

This lane does not authorize:

- live fleet mutation;
- production deployment;
- branch merge;
- release/tag;
- new network exposure;
- credential changes;
- automatic control-plane self-modification;
- broad architectural replacement of existing Station, SC-E, Research Workbench, Doctor, Shared Comms, mesh, or provider-continuity primitives.

The purpose of R0 is to determine how little new code is actually necessary.
