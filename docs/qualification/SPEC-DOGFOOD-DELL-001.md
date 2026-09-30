# SPEC-DOGFOOD-DELL-001 — DELL Swarm Dogfood Qualification Campaign

Status: **PREREGISTERED / EXECUTION GATED**

Purpose: turn DELL runner qualification into a bounded proof that RESIDUAL can execute useful work through mapped OpenClaw claws, coordinate multiple claws, project authoritative state to Shared Comms, degrade safely, recover from process loss, and expose the resulting health state to Doctor.

This document authorizes **no execution by itself**. Campaign execution begins only after a durable `DELL_RESIDUAL_RUNNER_QUALIFIED` receipt exists.

## 0. Controlling principles

1. Stop at the first failed generation. Preserve the first divergence; no retry-until-green.
2. After each parent Station dispatch, Kimi/owner/chat may observe and relay evidence but MUST NOT be the mechanism that wakes a claw, advances the workflow, assigns a successor, handles a deadline, or manufactures a result.
3. Shared Comms is a projection surface, never mission authority.
4. Historical LEGION evidence is a control/oracle, never authority for the DELL run.
5. Mission definitions are frozen/digest-bound before dispatch. Coordinator decomposition is preregistered; the coordinator does not invent scope.
6. Output-byte equality is required only when the mission contract requires deterministic bytes/text. Otherwise compare contractual acceptance predicates.
7. Every experiment emits the common evidence envelope in §10.
8. No secret values enter receipts, telemetry, Shared Comms, or campaign artifacts.

## 1. Campaign terminal predicate

```
DELL_SWARM_DOGFOOD_QUALIFIED :=
    DELL_RESIDUAL_RUNNER_QUALIFIED
 && C0_RUNNER_PATH_CONFORMANCE_PASS
 && A1_KNOWN_GOOD_MISSION_PASS
 && A2_LOCAL_COORDINATOR_PASS
 && COMMS1_PROJECTION_PASS
 && FAIL1_GRACEFUL_DEGRADATION_PASS
 && REC1_RESTART_RECOVERY_PASS
 && DOCTOR1_OBSERVABILITY_PASS
 && ZERO_MANUAL_KIMI_ROUTING_AFTER_PARENT_DISPATCH
```

A single false/unknown required predicate prevents the terminal receipt.

## 2. Frozen historical controls

Source packet identity supplied by the LEGION read-only extraction:

`KNOWN_GOOD_MISSION_REPLAY_PACKET_2026-09-29.md`
sha256 `144c0216bdc88f537e8dfe7807de2e58a0fbd081f87e82294a16c4a0510d5bc9`

Roles:

- **Candidate C — RUNNER_PATH_CONFORMANCE_CONTROL.** Historical operator probe expects exact response `SHARED_COMMS_OLLAMA_OK`; historical evidence traversed Station -> runner/bridge -> OpenClaw seat.
- **Candidate A — KNOWN_GOOD_STATION_MISSION_CONTROL.** Historical mission creates `ONBOARDING.md` containing `PREPARED_FOR_ACTIVATION`; historical Station run reached successful checks/review/integration.
- **Candidate B — HISTORICAL_PARTIAL_NEGATIVE_SPECIMEN.** Preserve unchanged for later Doctor/Research Workbench recovery tests. It is NOT part of the happy-path campaign and MUST NOT be repaired as preparation.

The campaign consumes exact mission bytes/records from the packet or their byte-verified durable source. It MUST NOT reconstruct mission text from chat memory.

## 3. Generation C0 — runner-path conformance

Gate: `DELL_RESIDUAL_RUNNER_QUALIFIED`.

Target: exactly one mapped DELL claw; prefer Piston if Phase-F qualification permits.

Replay Candidate C semantics through the new DELL authority domain.

Required path:

```
DELL Station :48953
-> authoritative parent assignment
-> runner-dell-piston (or explicitly selected qualified runner)
-> mapped OpenClaw seat
-> OpenClaw execution
-> runner result
-> Station receipt/acceptance
```

Acceptance:

- exact contractual response `SHARED_COMMS_OLLAMA_OK`;
- complete parent dispatch/assignment/epoch/generation identity;
- correct runner-to-seat binding;
- ACK and execution evidence originate from the native runner path;
- Station receives and accepts the result;
- no manual Kimi/owner routing after Station dispatch;
- no stale-generation acceptance;
- no protected-root mutation outside the campaign's authorized state.

Seeing the expected string in chat is explicitly insufficient.

## 4. Generation A1 — known-good useful mission

Gate: C0 PASS.

Replay exact Candidate A mission definition/checks through one qualified mapped DELL claw.

Historical acceptance oracle: mission contract and historical acceptance predicates, not incidental execution metadata.

Required:

- `ONBOARDING.md` produced as required by the frozen mission;
- required content predicate `PREPARED_FOR_ACTIVATION` satisfied;
- mission checks execute;
- review/integration semantics required by the mission are preserved;
- result/artifact identities durable;
- no manual Kimi routing after parent dispatch.

## 5. Generation A2 — local coordinator

Gate: A1 PASS.

Use an A-derived deterministic parent mission with an explicit, digest-bound decomposition under `OPENCLAW_LOCAL_COORDINATOR_CONTRACT_V1`.

Requirements:

- at least two QUALIFIED/ACTIVE mapped claws;
- one Station parent assignment;
- decomposition is frozen before dispatch;
- each subtask is strictly within parent scope;
- subtask identities never become independent top-level Station authority;
- coordinator performs aggregation-integrity only and cannot bypass independent verification;
- stale parent generation fences/quiesces all subtasks;
- PARTIAL remains honest if any required subtask cannot complete;
- exactly one parent terminal result is returned upstream.

The coordinator MUST NOT invent new decomposition scope at runtime.

## 6. Generation COMMS1 — Shared Comms projection

Gate: A2 PASS.

Project the A2 authoritative lifecycle to Shared Comms.

Predeclare the expected authoritative transition classes before execution. At minimum capture:

- parent assignment/dispatch;
- coordinator ACK;
- bounded decomposition identity;
- subtask progress;
- aggregate/result;
- verification/acceptance;
- terminal parent transition.

Acceptance:

- every projected control message correlates to an authoritative source event;
- projection identity/dedup semantics follow SC-A/SC-D;
- projection failure cannot mutate mission truth;
- Shared Comms contains no independent mission state that can advance the workflow;
- zero missing required projections at terminal reconciliation, or an explicit DEGRADED projection verdict with mission truth still correct.

## 7. Generation FAIL1 — graceful provider degradation

Gate: COMMS1 PASS and exact provider-continuity candidate has independently verified status. Live provider qualification must be separately authorized.

Use a bounded mission and force only an **eligible** primary-provider failure.

Required sequence:

```
primary attempt
-> eligible failure classification
-> durable breaker/route transition
-> current fallback readiness
-> fresh exact-context BL-006 admission
-> fallback invocation
-> durable result
-> verification
-> Station acceptance
```

Required negatives:

- ineligible failure never auto-falls back;
- CONFIGURED does not imply READY;
- READY does not imply BL-006 PASS;
- authority/policy/budget are rechecked before fallback;
- no duplicate provider invocation after durable result;
- stranded invocation without result fails closed as indeterminate unless provider-side idempotency proves replay safe;
- provider-side exactly-once is not claimed where it cannot be proven.

## 8. Generation REC1 — restart/recovery

Gate: FAIL1 PASS.

Inject exactly one predetermined process failure at a durable boundary. Prefer runner or local coordinator process; do not kill the authoritative Station in the first REC1 generation.

Pre-register:

- process to stop;
- durable boundary;
- expected reconstruction source;
- expected fenced generation;
- expected successor/resume behavior.

Acceptance:

- no duplicate accepted work;
- no stale-generation resurrection;
- no chat-memory reconstruction of authority;
- durable state reconstructs the active parent/subtask state;
- workflow resumes or parks honestly according to policy;
- no owner/Kimi action is required to advance a recoverable workflow after the injection.

## 9. Generation DOCTOR1 — health/causal observability

Gate: REC1 terminal.

Consume campaign telemetry/evidence through the Health Coordination Doctor design.

Doctor must distinguish at least:

- runner execution failure;
- provider failure;
- transport/projection failure;
- coordinator/process failure;
- authoritative Station failure/uncertainty.

Acceptance:

- first divergence is preserved;
- downstream symptoms remain impacts;
- missing evidence yields UNKNOWN/NOT_QUALIFIED, never inferred green;
- DEGRADED vs BLOCKED is explicit;
- Doctor emits evidence only and performs no scheduling/repair authority;
- every injected campaign failure maps to either a qualified HC detector or an explicit UNKNOWN_FAILURE_PATTERN.

## 10. Common evidence envelope

Every generation captures, when applicable:

```
campaign_id
generation_id
experiment_id
mission_definition_digest
historical_control_refs[]

cluster_id
station_instance_id
station_data_root_identity
station_epoch

mission_id
task_id
dispatch_id
assignment_id
generation
authority_epoch

runner_id
runner_runtime_identity
seat_id
seat_fingerprint
mapping_identity
coordinator_id
decomposition_id
subtask_id
attempt_id

provider_route_id
provider_runtime_identity
readiness_receipt
admission_receipt
invocation_id

ack_event
started_event
progress_events[]
deadline_events[]
result_event
verification_receipt
acceptance_event
terminal_event

artifact_refs[]
event_hashes[]
trace_id
timestamps
first_divergence
manual_intervention_count
```

Secrets, prompts/responses not required by the mission oracle, auth tokens, and credential values are excluded.

## 11. Manual-routing oracle

For each parent dispatch define `T0 = authoritative Station dispatch committed`.

From T0 through terminal:

- owner/Kimi may observe, report, relay immutable artifacts, or declare a genuine owner gate;
- owner/Kimi may NOT create the next work transition that the native scheduler/runner/coordinator is expected to create;
- any such manual transition sets `manual_intervention_count > 0` and fails the campaign's zero-manual-routing terminal predicate.

Owner-exclusive actions explicitly preregistered before T0 are not hidden; if required mid-run they produce an owner gate and the generation does not claim autonomous PASS.

## 12. Failure discipline

At first failure:

1. freeze exact evidence;
2. identify first divergence;
3. stop the current generation;
4. do not continue to later generations;
5. do not retry-until-green;
6. classify whether failure is product, harness/probe, environment, transport, or UNKNOWN only after evidence;
7. harvest a Doctor/Workbench specimen without rewriting historical outcomes.

## 13. Campaign completion receipt

Only after every required predicate passes emit:

`DELL_SWARM_DOGFOOD_QUALIFIED`

Receipt must cite every generation's terminal receipt/digest and explicitly state:

- native DELL runner path proven;
- useful known-good mission proven;
- >=2-claw local coordination proven;
- Shared Comms projection proven non-authoritative;
- graceful provider degradation proven at the qualified boundary;
- restart/recovery proven;
- Doctor causal observability proven;
- manual intervention count after parent dispatch = 0 for every autonomous generation.

Anything less remains a partial campaign result, never a qualified terminal.
