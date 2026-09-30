# SPEC-SINGLE-STATION-AUTONOMY-R0

Status: **INTEGRATION PROGRAM / NO DEPLOYMENT AUTHORITY**

Baseline: `main@8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2`
Tree: `7cd0d32be6fd61948f2fce753b122e5b6f0c6500`

## 1. Objective

Deliver one exact-tree RESIDUAL candidate that can operate a single authoritative Station with mapped OpenClaw claws without owner or Kimi routing ordinary work.

The operational slice is complete only when all required capabilities below are implemented, integrated, deployed in the bounded qualification environment, and live-qualified together.

A specification, script, hosted test, isolated PR, or historical receipt does not by itself make a capability operational.

## 2. Required capabilities

### SSA-01 Onboarding and mapping

Lifecycle:

`DISCOVERED -> MAPPED -> ENROLLED -> QUALIFIED -> ACTIVE`

Required behavior:
- discover actual OpenClaw profiles/listeners/config roots;
- explicit map/ignore authority boundary;
- enroll runner identity;
- validate binding;
- qualify native execution;
- activate only qualified mappings;
- repeated invocation is idempotent;
- wrong-host/stale-discovery evidence fails closed.

Controlling input: `OPENCLAW_ONBOARDING_CONTRACT_E_V1` digest
`c615700a6ee8363caa17dd9f2d8d0cf7f60be82259e82497e7e4feb93efa15fe`.

### SSA-02 Native runner execution

Required chain:

`Station -> assignment -> runner -> mapped claw -> result -> Station acceptance`

Current source lineage:
- SC-MESH base PR #404, HEAD `7783081c858ad9ddf98b2e64e740e1104ae5d08b`
- repair PR #493, HEAD `b53fb74c992830fe6d8912b62019c88bbf973f84`, TREE `a4efc2b3ef702965c1b1070f692fa032382654a8`

Historical defect:
`ADMIT_REJECTED__STALE_MESH_EXECUTION_BUDGET`

Operational acceptance requires physical successor-generation QUAL-001 and subsequent 1->2->3 runner qualification plus independent Phase F.

### SSA-03 Native scheduler and deadlines

Station must own:
- authoritative runnable set;
- dependency release;
- durable assignment;
- lease/deadline state;
- terminal -> DAG recompute -> successor selection;
- deadline consumption without LLM turn, Shared Comms traffic, owner activity, or agent-session wake dependency;
- crash-safe claim/fire/reducer transitions;
- liveness detection for timer/consumer path.

Controlling design lineage: SC-E v1.1 and accepted SC-D/SC-H contracts. Implementation remains separately gated until all controlling bytes and authorization predicates are satisfied.

### SSA-04 Artifact availability and byte admission

Required chain:

`required artifact -> durable locator -> transport -> recipient bytes -> recipient digest -> BYTE_EXACT_VERIFIED -> admission`

Required distinctions:
- digest citation != artifact possession;
- transported != byte-exact verified;
- byte-exact verified != authenticated;
- authenticated != semantically valid;
- semantically valid != independently verified;
- verified != authorized.

Original BL-016 v1.0 and the existing v1.1 have been recovered unchanged from the uploaded `OVERNIGHT_CONVERGENCE_2026-09-28.zip` (`03_QUALIFICATION/BL017/`):
- `BL-016_Design_Spec_v1.md`: 14,083 bytes, SHA-256 `ca063e2b5fadd1b7fa03af56957d7c0770bc32a2f00f2ccf185f90aebeb3697e`;
- `BL-016_Design_Spec_v1_1.md`: 17,915 bytes, SHA-256 `5d7bbe879845bad06c583515dc40f032db10f76e04941ac854c4ac695bf523d9`.

Current blocker: **BL016_V11_BLOCKED_ON_REVIEW_PROVENANCE_AND_CONFLICTING_SUCCESSOR_SEMANTICS**.

The full Piston review cited as `ef63bb15…`, focused A1–A5 confirmation bound to the recovered v1.1, and authoritative reconciliation of the separate Tester transport-hardening packet remain unresolved. In particular, reconcile container-digest mismatch handling, context-bound receipt replay/dedup, and content identity versus authenticated sender commitment. Do not invent another v1.1 or reconstruct review text from summaries.

Evidence-only handoff delivered to the owner: `BL016_Source_Recovery_and_Gap_Packet_2026-09-30.zip`, 55,223 bytes, SHA-256 `ea829fea4ecf69b0bb968cb9ada79aee2cbc750c6d61956d51e953541db450b6`. It preserves both originals and includes the provenance findings, gap analysis and admission-boundary matrix. Byte recovery does not establish implementation qualification, physical Q2 deposit, independent acceptance, or SC-E implementation authorization.

### SSA-05 Local multi-claw coordination

One Station parent assignment may be decomposed only under the qualified local-coordinator contract.

Required:
- >=2 QUALIFIED/ACTIVE mapped claws;
- preregistered/digest-bound decomposition;
- coordinator mints no authority;
- subtask scope <= parent scope;
- parent fencing quiesces local subtasks;
- independent verification is not bypassed;
- exactly one parent terminal result upstream;
- PARTIAL remains honest.

### SSA-06 Provider continuity / FreeLLMAPI

Current source candidate: PR #489, HEAD
`0472f46af1f137d1f808bf7b03cf12b4afa1f1ca`, TREE
`06da1cbfdc4f9966fdb73b9cd29159a16a8f3dd2`.

The uploaded `RESIDUAL Overnight Run 2026-09-30.zip` ledger reports Scout's independent PASS on this candidate (HEAD `0472f46a`, TREE `06da1cbf`) and owner advancement to `PROVIDER_CONTINUITY_CANDIDATE_INDEPENDENTLY_VERIFIED` with `LIVE_PROVIDER_QUALIFICATION_PENDING`. The cited originals are:
- `PR489_INDEPENDENT_REVIEW_2026-09-30.json`, digest citation `1fd9abca…bc87d`;
- `PR489_REVIEW_AMENDMENT_N1_2026-09-30.json`, digest citation `154d36e8…6310c`.

The archive manifest marks both receipts host-bound; their full bytes and full digests have not been locally verified. SSA-06's `INDEPENDENTLY_REVIEWED` state records that reported history, with this evidence limitation, and is not a new receipt-verification claim. Obtain and bind both original receipts before relying on them for a new integration admission. Absence of GitHub review submissions does not establish absence of independent review. The separate Piston historical BL-009 F-1 receipt is not a review of PR #489.

Required:
- route identity distinct from provider kind;
- only qualified failure classes auto-fallback;
- CONFIGURED != READY != ADMITTED != ACCEPTED;
- authority/policy/budget rechecked between attempts;
- current readiness required;
- fresh exact-context admission required;
- durable result reuse after restart;
- stranded provider invocation fails closed as `INDETERMINATE_PROVIDER_OUTCOME`;
- no provider-side exactly-once claim.

Readiness currently expires no later than its bounded freshness window. The integrated system therefore requires an authorized readiness-maintenance mechanism; a one-time qualification is insufficient for long-lived autonomy.

Fleet setup automation must be independently reviewed, canaried, then expanded profile-by-profile. Credential values never enter command lines, receipts, or Shared Comms.

### SSA-07 Health / Doctor

Doctor consumes existing telemetry, Station observations and authority events.

Required:
- canonical HealthObservation/HealthFact wiring;
- detector registry;
- first-divergence reducer;
- temporal/absence detectors;
- OpenClaw/Station/provider/Shared-Comms adapters;
- UNKNOWN retention;
- safe-continuation classification;
- no scheduling/repair authority minted by Doctor.

Design source: PR #488. Operational completion requires executable detectors/fixtures and integration into the scheduler evidence boundary.

### SSA-08 Shared Comms projection

Shared Comms is projection/transport/observability only.

Required:
- authoritative source event identity;
- stable projection identity;
- attempts/dedup;
- cursor reconciliation;
- bounded retry/degraded classification;
- restart recovery;
- no ability to advance mission truth independently;
- delivery-state distinctions sufficient to separate emitted, delivery-accepted, room-visible, recipient-consumed and owner-rendered where evidence permits.

### SSA-09 Recovery

Known failures with approved deterministic policy may be repaired automatically.

Examples:
- expired lease -> fence/recompute;
- stale session -> fence and rehydrate from durable state;
- missing artifact -> transport request;
- eligible provider failure -> continuity policy;
- known dead runner -> reassignment where contract permits.

Unknown or unauthorized recovery -> PARK or OWNER_GATE.

### SSA-10 Durable owner gates

Owner-exclusive authority is represented as a durable object, not merely a chat request.

A gate blocks only dependent work. Unrelated runnable work continues.

Minimum fields:
`gate_id, subject, requested_authority, reason, evidence_refs, choices, created_at, blocked_scope, status`.

## 3. Integration owner

One integration owner maintains a composition manifest. Upstream candidate authors do not self-certify the integrated tree.

For every selected component record:

`source_ref, source_head, source_tree, integration_commit, schemas, migrations, config requirements, tests, limitations`.

Any rebase/cherry-pick/conflict resolution creates a new integrated candidate identity and requires relevant tests to rerun.

## 4. Capability readiness states

Every capability is tracked independently:

- `SPECIFIED`
- `IMPLEMENTED_ISOLATED`
- `INDEPENDENTLY_REVIEWED`
- `INTEGRATED`
- `DEPLOYED_BOUNDED`
- `LIVE_QUALIFIED`

Never collapse these into COMPLETE.

## 5. Autonomy oracle

After authoritative parent dispatch T0:

Kimi/owner may observe, relay immutable evidence and satisfy genuine owner gates.

They may not:
- manually wake a claw when native scheduling is expected;
- choose ordinary successors;
- manufacture ACK/progress/result;
- consume deadlines in place of Station;
- substitute conversation state for durable mission authority.

Any such transition increments `manual_intervention_count`.

## 6. Qualification campaign

PR #490 preregisters:

`C0 -> A1 -> A2 -> COMMS1 -> FAIL1 -> REC1 -> DOCTOR1`

This campaign becomes a valid autonomy qualification only after the native mechanisms required by the corresponding generation are actually integrated.

The campaign must stop at first failed generation and preserve first divergence.

## 7. Final acceptance

`SINGLE_STATION_AUTONOMY_QUALIFIED` requires all of:

- onboarding/mapping live-qualified;
- DELL runners live-qualified;
- native DAG/scheduler/deadline path live-qualified;
- artifact delivery/admission live-qualified;
- >=2-claw local coordination live-qualified;
- Shared Comms projection live-qualified and non-authoritative;
- provider continuity live-qualified;
- restart/recovery live-qualified;
- Doctor first-divergence behavior live-qualified;
- owner-gate behavior proven;
- `manual_intervention_count = 0` after campaign parent dispatches.

## 8. Owner-absence test

Final endurance target:

`OWNER_ABSENT_8H`

Required:
- Kimi not required for mission progression;
- no lost accepted work;
- no duplicate accepted work;
- no stale authority accepted;
- no unexplained runnable-seat idleness;
- no missed native deadlines;
- known failures either recovered by authorized policy or explicitly parked;
- owner gates may accumulate while unrelated work continues.

Only after that passes should `OWNER_ABSENT_24H` be attempted.

## 9. Non-goals for R0

- multi-Station authority transfer;
- automatic split-brain resolution;
- enterprise fleet control;
- broad self-modifying detector promotion;
- merge/release authorization.

Those remain later phases after single-Station autonomy is proven.
