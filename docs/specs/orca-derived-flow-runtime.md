# ORCA-DERIVED FLOW RUNTIME SPECIFICATION

Status: EXPERIMENTAL / ADDITIVE

Upstream reference: VirtusLab/orca, reviewed at commit lineage containing `edebe599e084dc65ce847f4bc045740cf331dd9f`.

License note: Orca is Apache-2.0 licensed. This integration does **not** vendor Orca or introduce a runtime dependency. It borrows architectural ideas and re-expresses them in RESIDUAL's own contracts.

## 1. Purpose

RESIDUAL SHALL gain a small flow-runtime layer between orchestration planning and execution. The layer exists to:

1. keep deterministic work deterministic;
2. represent agent/swarm work as explicit stages rather than implicit prompt sequences;
3. bind every stage to explicit capabilities;
4. choose the lightest execution profile justified by risk and ambiguity;
5. make stage completion resumable only when its identity and evidence still match;
6. preserve the existing M2-M4 trust boundary, WorkerContract authority, Evidence Fabric, verification, and deterministic integration.

This work is inspired by Orca's stage-bound flow runtime, resumable stages, capability gating, and simple-vs-planned flow split. RESIDUAL SHALL NOT adopt Orca's privileged-agent trust model, Scala DSL, git-index semantics, or automatic tool approval.

## 2. Non-goals

This feature MUST NOT:

- replace `ExecutionPlan`, `WorkerContract`, Station receipts, Evidence Fabric, M4 integration, or HITL approval;
- allow workers to mint or widen capabilities;
- execute model-generated Python;
- create a second scheduler or second authoritative DAG;
- make Orca a package/runtime dependency;
- modify `residual/factory/**` in the initial integration;
- silently resume a stage when its flow, inputs, repository state, or output evidence no longer match.

## 3. Core objects

### 3.1 ResidualFlow

`ResidualFlow` is an immutable, content-addressed execution view derived from an existing orchestration `Plan`.

It SHALL contain:

- source `plan_hash`;
- execution profile;
- ordered stage list;
- schema version;
- deterministic `flow_hash`.

A flow MUST NOT change the source plan. Recompilation produces a new flow object.

### 3.2 FlowStage

A stage SHALL have:

- stable stage id;
- descriptive name;
- kind;
- requirement ids;
- packet ids;
- dependency stage ids;
- capability grant;
- explicit budget;
- human-readable routing reason.

Initial kinds:

- `DETERMINISTIC`
- `AGENT`
- `REVIEW`
- `SWARM`
- `HUMAN_GATE`

### 3.3 CapabilityGrant

A grant SHALL define only the authority required by the stage:

- allowed tools;
- allowed path scopes;
- network permission;
- workspace-write permission.

The grant is immutable. A stage runtime MAY narrow it and MUST NOT widen it after dispatch.

No side effect is permitted merely because an agent requested it. Authority requires:

`stage identity + capability grant + existing RESIDUAL execution authority`.

### 3.4 StageBudget

Every stage SHALL carry explicit ceilings for:

- tokens;
- wall-clock seconds;
- attempts.

Deterministic stages SHOULD normally use zero model-token budget.

## 4. Deterministic-vs-intelligence split

RESIDUAL SHOULD perform mechanically decidable operations without an LLM. Examples include:

- plan/flow hashing;
- schema validation;
- test invocation;
- lint/format invocation;
- receipt serialization;
- artifact hashing;
- deterministic integration;
- checkpoint verification;
- branch/ref bookkeeping when an authorized host executor performs it.

An agent is appropriate when semantic judgment, synthesis, diagnosis, or implementation is required.

The initial compiler SHALL emit deterministic preparation, verification, and integration stages around agent/swarm implementation stages.

## 5. Adaptive execution profiles

The compiler SHALL choose among:

- `SINGLE`: one bounded agent path plus deterministic verification;
- `REVIEWED`: agent implementation plus an explicit review stage;
- `SWARM`: swarm execution plus explicit review and deterministic verification.

The routing decision SHALL be deterministic for a fixed `Plan`.

Initial routing signals MAY include:

- ambiguity presence;
- maximum packet risk;
- packet count;
- protected-path proximity;
- external I/O.

Routing MUST NOT grant more authority than the underlying plan permits.

## 6. Stage capability enforcement

A named authorization door SHALL verify requested operations against the stage grant before an executor is released.

Negative cases MUST include:

- undeclared tool;
- undeclared path;
- network use without network permission;
- workspace write without write permission.

This layer is additive. WorkerContract, sandbox, quarantine, verification, and existing policy remain authoritative downstream gates.

## 7. Checkpoints and resume

A `StageCheckpoint` SHALL bind at minimum:

- `flow_hash`;
- `stage_id`;
- input digest;
- output digest;
- repository head before;
- repository head after;
- evidence ids.

Resume MUST fail closed unless:

1. the checkpoint flow hash equals the current flow hash;
2. the stage still exists;
3. the expected input digest matches;
4. current repository state matches the checkpoint's recorded post-stage state;
5. required output/evidence digests remain valid.

Unlike Orca's decode-safe stage replay, RESIDUAL SHALL prefer evidence-safe replay: a stage result is reusable only when its authority and evidence bindings are still valid.

## 8. Dependency mapping

The flow compiler SHALL NOT invent a second requirement graph.

Execution-stage dependencies SHALL be derived from existing WorkPacket levels:

- stage level 0 depends on preparation / required human gate;
- stage level N depends on execution stages at level N-1;
- review depends on all implementation stages;
- verification depends on review when present, otherwise all implementation stages;
- integration depends on successful verification.

## 9. Human gates

If the plan remains ambiguous, the flow MAY include an explicit `HUMAN_GATE` stage before implementation.

The flow object itself does not approve anything. Existing HITL mechanisms remain authoritative.

## 10. Integration with current Orchestrator

`Orchestrator.plan(intent)` remains unchanged.

An additive `Orchestrator.flow(intent)` SHALL:

1. produce the existing plan using the unchanged pipeline;
2. compile that plan into a `ResidualFlow`;
3. return the flow without executing it.

This preserves all current callers while exposing the new execution representation.

## 11. Required tests

### Unit / contract

- identical plans produce identical flow hashes;
- different plans produce different flow hashes;
- stage ids are unique;
- stage dependencies reference earlier stages only;
- deterministic stages have zero model-token budget;
- ambiguous plans include a human gate;
- higher-risk/multi-packet plans route to REVIEWED/SWARM deterministically;
- undeclared tool/path/network/write operations are denied;
- checkpoint resume succeeds only on exact bindings;
- checkpoint flow/input/repository mismatches fail closed.

### Integration

- `Orchestrator.flow(Intent(...))` preserves the source `plan_hash`;
- the existing `Orchestrator.plan` behavior remains unchanged;
- no files under `residual/factory/**` are required for the new flow compiler;
- the integration stage remains deterministic and does not grant agent authority.

### Smoke

A credential-free smoke script SHALL:

1. create an Intent;
2. compile a ResidualFlow;
3. assert preparation -> implementation -> verification -> integration ordering;
4. assert capability denial for an undeclared write;
5. print the flow hash/profile and exit 0.

## 12. Qualification / merge gates

Before merge:

- Python compileall passes;
- focused flow tests pass on supported Python versions;
- smoke script exits 0 without credentials;
- existing orchestrator tests pass;
- full CI remains green;
- factory ownership / M4 trust-boundary checks remain green;
- no runtime Orca dependency is present.

## 13. Deferred extensions

After this additive substrate proves stable, future work MAY add:

- durable checkpoint storage;
- Evidence Fabric-backed checkpoint certification;
- Station/portal flow visualization;
- per-stage model/provider routing;
- deterministic host executors for mechanical actions;
- resumable long-running flows;
- automatic selection among single-agent, reviewed, swarm, experiment, and human-gated templates;
- OpenViking ContextPackage binding per stage.

These extensions require separate PRs and must preserve existing trust boundaries.
