# Delegation and merge ownership

## Track A — owned by this Codex thread

**First implementation: verifier-receipt binding and the station extension registry.**

Reserved branch: `feat/receipt-extension-foundation`.

This track owns `WORLD_CLASS_SPECS.md` Part 1 (VRB-R1..R6), Part 2 (REG-R1..R7), and `NETOPS_SECOPS_SPECS.md` SPEC-MODULE-001. It also owns the small core adaptations required to connect the hooks. Runtime implementation is the next milestone; this handoff publishes the agreed interface direction and test gates first.

Why first: NetOps, SecOps, replay, memory, HITL and mesh all need stable verifier identities, evidence semantics, registration and lifecycle boundaries. Implementing those separately in each module would create incompatible acceptance rules.

Owned files:

- New `residual/receipts.py`, `residual/extensions.py` and `residual/station/extensions.py`.
- Receipt/cache integration in `residual/engine.py`, `residual/storage.py` and `residual/station/store.py` where needed, preserving legacy formats through explicit adapters.
- Shared types and integration changes in `residual/verifier.py`, `residual/loop.py`, `residual/quarantine.py`, `residual/station/control.py`, `residual/station/models.py` and `residual/station/service.py`.
- New `tests/foundation/` contract tests and reusable fixture builders.
- Shared dependency/configuration changes, public exports, schemas and core UI registration points.

Other tracks should keep core edits out of their PRs. If a required hook is missing, include a precise integration request and a fixture demonstrating the need. This owner wires it once.

### A1 — acceptance/evidence milestone

1. Immutable, domain-separated receipt and cache bindings with stable canonical JSON.
2. Namespaced verifier identity plus a revision tied to implementation, configuration, policy and proof artifacts.
3. Dependency receipts propagate from prerequisites to their dependents; deterministic ordering independent of arrival order.
4. Stale, tampered, mismatched or unknown receipts never establish acceptance. A cache hit still runs the active host verifier.
5. Existing v0.3.0 receipts remain readable without being relabeled as the new schema.

Required tests: changed verifier code/configuration/revision, changed goal/artifact/dependency, missing dependency evidence, stale approval, tampered value/receipt, unknown outcome, DAG reordering/cycle rejection and an unchanged successful cache hit that invokes the host verifier.

### A2 — extension milestone

1. One validated `StationModule` interface; atomic registration and collision rejection.
2. Freeze the registry before controller construction; preserve module registration order.
3. Runtime validation of policy/evaluator/brake outputs and safe failure codes.
4. Standard brakes plus extension brakes with global abort priority.
5. Trusted host events reach extension brakes without granting control authority to worker or optional telemetry claims.
6. A real fixture module passes through policy → execution → verifier → brake → run-close lifecycle in the web station.

Required tests: duplicate names, malformed signatures/return values, partial registration rollback, late registration, lifecycle ordering, concurrent runs with separate brake state, optional observation failure, spoofed worker events and UI evidence inspection.

## Parallel tracks to delegate now

Each row can go to a different agent. Branch names are suggestions; only the foundation branch is reserved by this thread. Work starts with pure logic, injected clients and deterministic fixtures. Runtime integration waits for A2. No track should merge directly to `main`.

| Track / branch | File ownership | Deliverable now | Merge dependency / acceptance gate |
|---|---|---|---|
| B NetOps / `feat/netops-module` | `residual/modules/netops/`, `tests/netops/` | Injected telemetry client, signed-or-host-resolved maintenance receipts, topology scope, stabilization verifier, emergency/drift brakes | A2; fake clock/client fixtures for stale telemetry, absent receipt, expiry, device mismatch, threshold breach and undeclared topology change. No live device mutations. |
| C SecOps / `feat/secops-module` | `residual/modules/secops/`, `tests/secops/` | Recursive secret checks, staged-candidate SAST, SBOM/license evidence, OPA adapter, vulnerability/secret brakes | A2; scan before Git staging, secrets never enter telemetry, missing scanner/license evidence blocks, positive and negative secret fixtures, OPA unavailable → unknown. |
| D Trajectory regression / `feat/trajectory-regression` | `residual/trajectory/`, `tests/trajectory/` | Canonical run recorder, structural replay, synthetic golden traces and comparison report | A1/A2; every outcome recorded, no real tool side effects during replay, altered verdict/brake/order fails, missing evidence is unverifiable. |
| E Operations UX / `feat/operations-observers` | `residual/tui/`, `tests/tui/`, new `residual/station/static/modules/` assets | Read-only TUI and module-status panels consuming exported/API events; retain the web interface as the main product | Existing observation API allows immediate fixture work; A2 for module panels. Slow/crashed observer cannot block execution. Desktop and 390px mobile checks. Keep optional UI dependencies optional. |
| F Epistemic memory / `feat/receipt-memory` | `residual/memory/`, `tests/memory/` | Rebuildable receipt/artifact index and read-only retrieval API | A1/A2; writes after run close, full content identities, stale revision and tampered witness rejection, no promotion of model claims. |
| G HITL / `feat/hitl-gateway` | `residual/hitl/`, `tests/hitl/` | Durable challenge queue, authenticated response protocol, expiry/replay handling, explicit amended-run proposal | A1/A2; single-use challenge, authorization tied to an authenticated operator, restart/race tests, no override for abort, no re-execution of a consumed action. |
| H Mesh/crypto design / `design/authenticated-mesh` | `docs/roadmap/mesh/`, `tests/mesh/fixtures/` | Corrected message/encryption/membership schemas and a two-device transport simulator | A1 plus security review of the design; duplicate/reordered delivery, partition/rejoin, replay, revocation and unavailable local evidence. Do not ship the draft longest-chain rule or label signed claims as verified results. |

If fewer agents are available, prioritize B, C and D. E can begin against today's observation API. F and G can build storage/protocol fixtures now and wait for A1/A2 to integrate. Keep H at design/simulation until the trust model is settled.

## Research queue after the first contracts land

- Context curator and sub-agent pool: retain per-task disclosure, aggregate reservations and verified-result admission; do not concatenate the shared chat into model context.
- Reasoning-engine adapters: wrap the existing provider routes and solver outputs behind typed intentions; do not replace working transports.
- Formal verifier certificates: define the property, assumptions, proof checker and certificate binding. A theorem about a model is not a proof of arbitrary Python or live network behavior.
- Falsification: isolate scenario execution in a bounded sandbox stage and give the pure quarantine policy a verified result. Measure counterexample quality separately.
- TPM and zk: prototypes with explicit hardware/cryptographic evidence. No HMAC-as-zk or software-chain-as-hardware-attestation substitution.
- Policy calibration: proposal-only initially. No threshold relaxation or verifier mutation during a frozen run.

## Shared handoff contract

Every PR should include: exact spec requirement IDs, implemented versus deferred behavior, changed files, integration hook requests, deterministic fixtures, test commands/results, observation examples without secrets, and any migration needed for existing data. Report measured token counts separately from estimated budgets and transport bytes.

The merge order is A1 → A2 → B/C/D → E/F/G → H integration. Independent module PRs may be prepared concurrently. Host-verified evidence, explicit run identity and existing cloud-sharing permission remain required at every boundary.
