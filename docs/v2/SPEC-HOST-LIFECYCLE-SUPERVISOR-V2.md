# SPEC-HOST-LIFECYCLE-SUPERVISOR-V2 — Governed Host Lifecycle Supervisor

**Status:** PARKED / POST-v1 DESIGN
**Program:** RESIDUAL v2 — Operability / Continuity
**Roadmap branch:** `v2/solpi-evidence-context-environment-bank`
**Implementation authority:** none until the v2 kickoff gate in `docs/v2/ROADMAP.md` is satisfied.
**Origin:** v1 dogfooding authority-boundary incident and `OWNER_PHYSICAL_ACTION_REQUIRED` during Kimi/OpenClaw gateway auth-snapshot refresh on 2026-09-28.
**Primary question:** How can RESIDUAL safely restart a dependency that hosts or coordinates part of RESIDUAL without granting ambient host/root authority, losing mission truth, or requiring the owner to be physically present?

## 1. Motivation

During v1 dogfooding, a bounded provider-path repair became durable on disk but remained invisible to a running gateway because the gateway held a boot-time auth snapshot. The only sanctioned refresh path was a full desktop lifecycle restart. The active agent correctly refused to improvise a force-kill, UI automation path, undocumented daemon intervention, or privilege expansion and returned `OWNER_PHYSICAL_ACTION_REQUIRED`.

That is correct v1 behavior and a v2 operability requirement.

RESIDUAL v2 needs a separately governed lifecycle supervisor that survives the processes it manages and can execute narrowly authorized lifecycle actions, checkpoint state before disruption, observe shutdown/startup, reconcile authoritative state after restart, and fail closed when the requested lifecycle operation cannot be proven safe.

The supervisor is not a general remote shell, service manager, or ambient root daemon.

## 2. Scope and non-goals

The Host Lifecycle Supervisor (HLS) MAY, for explicitly allowlisted targets and actions: identify the target; perform `START`, `STOP`, `GRACEFUL_RESTART`, and `HEALTH_CHECK`; capture pre/post evidence; observe identity transitions; trigger reconciliation; request a predeclared rollback; and return `OWNER_PHYSICAL_ACTION_REQUIRED`.

HLS MUST NOT expose arbitrary shell execution, silently elevate privileges, create persistence as part of restart, rewrite unrelated configuration, force-kill when only graceful authority exists, enter restart loops, infer authority from chat/history, broaden target/action scope, or treat process health as proof of mission recovery.

## 3. Authority model — DF-AUTH-001

Every mutation-capable lifecycle dispatch binds:

- `dispatch_id`, `authority_epoch`, `authorization_state`;
- issued/expiry timestamps;
- exact target identity and allowed action;
- allowed mechanism class;
- precondition/postcondition digests;
- rollback policy.

Immediately before every consequential mutation HLS MUST revalidate durable authority.

States: `ACTIVE | RESCINDED | SUPERSEDED | EXPIRED | CONSUMED`. Only `ACTIVE` may mutate. Rescissions identify the dispatch and epoch they void. Stale in-memory instructions are never executable.

Dispatches are single-use unless their canonical contract explicitly says otherwise. Terminal execution consumes the dispatch. Authority-boundary incidents remain separate evidence; later owner acceptance of resulting state never erases an earlier violation.

## 4. Allowlisted capability model

HLS exposes capabilities, not commands. Example IDs:

- `lifecycle:kimi-desktop:graceful-restart`
- `lifecycle:residual-station:graceful-restart`
- `lifecycle:freellmapi:graceful-restart`
- `lifecycle:ollama:health-check`

Each capability binds target selector, executable/service/application identity, permitted actions, permitted lifecycle mechanism, privilege class, expected supervisor ancestry, health contract, maximum duration, restart-attempt budget, rollback/failure policy, and evidence obligations.

No capability may contain an arbitrary runtime-supplied command string. Adding or widening capabilities is a protected configuration change with a separate gate.

## 5. Supervisor independence

HLS MUST survive the target it manages. An action is inadmissible when the only executor capable of completing and observing it is hosted inside the target being terminated.

Supervisor identity is distinct from target process identity, provider identity, worker/seat identity, mission identity, and Station acceptance authority. At least one control component outside the restart blast radius retains the authoritative lifecycle dispatch and observes terminal outcome.

## 6. Pre-action checkpoint

Before disruption HLS emits an immutable `LifecyclePrestateReceipt` binding:

- dispatch/authority epoch;
- target PID/service identity/start time and executable/config identity;
- Station/source/environment identities relevant to recovery;
- Mission Board/ledger digest;
- active assignments, generations, leases/fencing tokens;
- durable mission checkpoints;
- outstanding owner gates;
- provider/runner readiness relevant to the target;
- artifact/receipt roots;
- first failures/unresolved incidents;
- expected postconditions.

Affected workers checkpoint first or are explicitly classified non-checkpointable. HLS MUST NOT claim resumability for state never persisted.

## 7. Lifecycle state machine

Normal path:

`REQUESTED -> AUTHORITY_VALIDATED -> PRESTATE_BOUND -> MECHANISM_VERIFIED -> STOPPING -> STOP_CONFIRMED -> STARTING -> START_CONFIRMED -> RECONCILING -> HEALTH_VERIFIED -> COMPLETED`

Terminal alternatives:

`OWNER_PHYSICAL_ACTION_REQUIRED | AUTHORITY_REVOKED | PRECONDITION_FAILED | MECHANISM_UNAVAILABLE | STOP_FAILED | START_FAILED | HEALTH_FAILED | RECONCILIATION_FAILED | ROLLBACK_REQUIRED | ROLLBACK_FAILED`

Unexpected transitions fail closed. Restart-attempt budget defaults to one; another attempt requires a fresh dispatch/epoch.

## 8. Mechanism admission

Before actuation HLS proves the mechanism:

1. existed before dispatch or was installed by a separately qualified deployment;
2. is intended for lifecycle control of the named target;
3. survives target termination;
4. requires no authority broader than the dispatch/profile;
5. does not mutate unrelated configuration/processes;
6. performs the requested semantic action (full exit is not hide-to-tray);
7. has bounded failure/retry behavior.

Failure returns `OWNER_PHYSICAL_ACTION_REQUIRED` or `MECHANISM_UNAVAILABLE`. HLS never substitutes force-kill, synthetic UI actuation, undocumented endpoints, shell tricks, or newly-created persistence.

## 9. Restart identity proof

A successful process-backed restart proves at minimum:

- old PID differs from new PID;
- new start time is later;
- expected executable identity equals observed executable identity;
- expected service/application identity equals observed identity.

Where available, also bind executable digest, service-definition digest, configuration digest, environment identity, and supervisor ancestry. A responsive endpoint alone is insufficient.

## 10. Post-restart reconciliation

RESIDUAL reconciles from durable authority, never pre-restart chat context:

- Mission Board/ledger event continuity;
- seat identities/generations;
- assignments, leases and fencing tokens;
- checkpoint/resume positions;
- provider readiness and credential/config visibility;
- runner registrations and expected Station binding;
- workspace/data-root identity;
- outstanding owner gates;
- first-failure/incident continuity;
- receipt/evidence availability.

Stale generations cannot submit authoritative results after ownership advances. Late results remain evidence but are fenced from accepted state.

## 11. Health model

Lifecycle success is conjunctive:

`PROCESS_IDENTITY AND LIVENESS AND APPLICATION_READINESS AND AUTHORITATIVE_STATE_RECONCILED AND EVIDENCE_CHAIN_INTACT`

Target-specific predicates may strengthen the contract. `START_CONFIRMED` is not `HEALTH_VERIFIED`.

## 12. Provider/credential refresh integration

After lifecycle restart, provider readiness is re-evaluated from the running runtime, not disk configuration. `CONFIGURED != READY`.

Readiness follows provider-continuity requirements, including endpoint/auth/model visibility and BL-006 Model Admission before local-model activation. HLS never chooses fallback providers; provider-policy/continuity owns selection.

## 13. Mission/checkpoint continuity

Before disruption, affected model/tool work checkpoints or is marked interrupted; assignment/generation is frozen; pending irreversible actions are surfaced; unrelated deterministic work may continue.

After reconciliation, eligible missions resume from durable checkpoints, no duplicate acceptance is allowed, owner gates remain parked, and unavailable dependencies shrink the runnable DAG instead of freezing unrelated work.

## 14. Mission Board projection

The board SHOULD expose target, capability, lifecycle state, dispatch/epoch, prestate receipt, old/new process identity, health result, reconciliation result, affected missions, owner-action requirement, and terminal receipt.

`NEEDS YOU` includes lifecycle actions only when `owner_gate_actionable_now == true`.

## 15. Evidence and receipts

### LifecyclePrestateReceipt
Defined in §6.

### LifecycleActionReceipt
Binds dispatch/authority, capability/mechanism identity, target before/after identities, timestamps, stop/start observations, attempt count, terminal state, mutation summary, and unexpected observations.

### LifecycleReconciliationReceipt
Binds prestate/action digests, board/ledger before/after identities, seat/generation reconciliation, mission/checkpoint reconciliation, provider/runner readiness deltas, evidence continuity, unresolved discrepancies, and health verdict.

Receipts are immutable/content-addressed; UI state is rebuildable projection.

## 16. Failure and rollback doctrine

First unexpected result is preserved and stops the lifecycle lane unless the canonical capability explicitly authorizes rollback. Rollback is not retry-until-green.

Rollback requires a predeclared trigger, allowlisted rollback capability, fresh authority validation, bounded attempts, and separate receipts. Unsafe rollback returns `ROLLBACK_REQUIRED` or `OWNER_PHYSICAL_ACTION_REQUIRED`.

## 17. Cold-start recovery contract

HLS contributes lifecycle facts to the v2 reconciler. After host/control-plane restart RESIDUAL should reconstruct:

`Station -> workspace/data root -> Mission DAG -> seats/runners -> leases/fencing -> providers/readiness -> checkpoints -> pending verification -> owner gates`

HLS MUST NOT invent missing mission state.

## 18. Security requirements

- least privilege per target;
- no arbitrary shell;
- immutable capability allowlist during active dispatch;
- no secrets in receipts;
- target selectors fail closed on ambiguity;
- symlink/path substitution defenses for file-backed identities;
- no implicit privilege escalation;
- no force-kill fallback unless separately specified and qualified;
- supervisor compromise included in threat modeling before enterprise claims;
- all mutations auditable by dispatch/epoch.

## 19. Required negative matrix

| ID | Negative | Required outcome |
|---|---|---|
| HLS-N01 | dispatch rescinded immediately before mutation | `AUTHORITY_REVOKED`, zero mutation |
| HLS-N02 | stale authority epoch | reject, zero mutation |
| HLS-N03 | target identity changed after prestate | `PRECONDITION_FAILED` |
| HLS-N04 | no sanctioned lifecycle mechanism | `OWNER_PHYSICAL_ACTION_REQUIRED` or `MECHANISM_UNAVAILABLE` |
| HLS-N05 | executor inside restart blast radius | refuse actuation |
| HLS-N06 | graceful stop fails | `STOP_FAILED`, no force-kill substitution |
| HLS-N07 | target fails to return | `START_FAILED`, no restart loop |
| HLS-N08 | new PID but wrong executable/service identity | `HEALTH_FAILED` |
| HLS-N09 | endpoint healthy but mission state fails reconciliation | `RECONCILIATION_FAILED` |
| HLS-N10 | stale pre-restart worker submits result | fenced/rejected; evidence retained |
| HLS-N11 | disk config present but runtime snapshot stale | provider remains `NOT_READY` |
| HLS-N12 | unrelated process/config mutation observed | fail qualification |
| HLS-N13 | restart succeeds but receipt chain missing | no `COMPLETED` |
| HLS-N14 | second restart under single-use dispatch | reject |
| HLS-N15 | rollback without allowlisted rollback authority | reject |
| HLS-N16 | supervisor loses authority store during restart | fail closed |

## 20. Qualification campaigns

### HLS-Q1 — Kimi/OpenClaw coordinator restart
Active multi-seat mission -> prestate receipt -> authorized graceful restart -> supervisor survives -> old/new identity proof -> authoritative state rehydrates -> generations reconcile -> mission resumes from checkpoint -> independent verification -> no duplicate execution/acceptance -> evidence chain intact.

Target: owner intervention count = 0 after dispatch authorization.

### HLS-Q2 — RESIDUAL Station restart
Prove Station replacement without loss of Mission Board/ledger truth, assignments, acceptance receipts, workspace binding, or evidence.

### HLS-Q3 — Provider runtime restart
Prove runtime restart can refresh credential/config visibility while readiness remains `NOT_READY` until live post-restart checks pass.

### HLS-Q4 — Authority rescission race
Dispatch restart, rescind immediately before actuation; mutation MUST NOT occur. This directly qualifies DF-AUTH-001 against stale in-memory instructions.

### HLS-Q5 — Host reboot / cold-start reconstruction
After narrower campaigns qualify, prove host restart plus durable recovery without treating process health as mission recovery.

## 21. Release gates

HLS remains experimental until DF-AUTH-001 rescission races pass repeatedly; at least two target classes qualify including a coordinator/control-plane target; supervisor survival is directly evidenced; restart-loop prevention, checkpoint reconciliation and stale-generation fencing pass; no arbitrary shell/privilege-broadening path exists; the negative matrix passes with sensitivity controls; receipts reconstruct truth without chat history; supported authorized lifecycle actions require no owner intervention after dispatch; and independent verification binds exact supervisor/capability/source/environment identities.

Enterprise claims additionally require least-privilege deployment, hostile-local qualification, supported storage/topology profiles, and independent assurance where applicable.

## 22. Dependencies and roadmap integration

HLS composes with:

- DF-AUTH-001 revocable mutation authority;
- BL-007 Mission Board;
- BL-008 persistent workspace;
- BL-009 provider continuity;
- BL-006 Model Admission;
- SC-MESH seat identity/generations;
- EVPR-001 evidence verification;
- OBSH-003 / CMPE-004 durable context/checkpoint references;
- ENVB-002 replayable restart/failure environments;
- HarnessBench restart/host-loss campaigns;
- ENT-OWN-002 / ENT-THREAT-004 / ENT-HA-005 hardening.

This spec is additive to v2 and does not expand v1 scope.

## 23. Explicit v1 boundary

The v1 behavior observed on 2026-09-28 remains correct:

`safe lifecycle mechanism unavailable -> refuse improvisation -> OWNER_PHYSICAL_ACTION_REQUIRED`

v2 HLS exists so a pre-qualified mechanism can instead produce:

`bounded owner dispatch -> supervisor survives target restart -> durable state reconciles -> postconditions prove -> mission continues`

without turning the swarm into an ambient host administrator.

## 24. Terminal design state

`HOST_LIFECYCLE_SUPERVISOR_V2_SPECIFIED`

Implementation remains blocked by the v2 kickoff gates in `docs/v2/ROADMAP.md`.
