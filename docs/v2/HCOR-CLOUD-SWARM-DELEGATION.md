# HCOR Cloud Swarm Delegation Pack

**Status:** PARKED / POST-v1 PREPARATION
**Parent:** HCOR-000
**Purpose:** make HCOR-001..008 independently delegable to cloud swarm sessions after explicit v2 kickoff.

## 1. Common rules for every work package

Each session receives the exact parent/master spec plus its assigned child spec by repository ref/digest. Chat summaries are not controlling inputs.

Every session MUST:
- acceptance-receipt first;
- bind exact controlling spec/source/environment identities;
- declare authority and exclusions;
- preserve first failure before repair;
- checkpoint before material redesign/correction;
- produce byte-authoritative artifacts with sender digests;
- provide tests plus negative/sensitivity tests;
- produce a design-conformance matrix;
- identify unresolved dependencies honestly;
- never self-close;
- return a verifier-ready evidence pack.

No session may broaden authority, modify another work package's controlling spec, silently weaken acceptance criteria, or merge/promote its own work.

## 2. Standard output bundle

```text
ACCEPTANCE_RECEIPT.json
IMPLEMENTATION/
TESTS/
NEGATIVE_MATRIX.json
ARTIFACT_MANIFEST.sha256
DESIGN_CONFORMANCE.md
FIRST_FAILURE/          # if any
CHECKPOINTS/
QUALIFICATION_REQUEST.json
```

The manifest covers every delivered byte. Recipient verification begins with transport integrity.

## 3. Work packages

### WP1 — HCOR-001 Mission Kernel
Deliver schema/migrations, canonical serializers, mission state machine, delegation/authority attenuation, lease/fencing objects, owner-gate objects, event/receipt types, and negative tests.

### WP2 — HCOR-002 DAG Coordinator
Deliver deterministic event reducer, DAG/runnable computation, checkpoint/replay, event idempotency/order handling, backpressure metrics, crash-boundary tests.

### WP3 — HCOR-003 Scheduler
Deliver runner/resource/provider capability registry interfaces, admission chain, deterministic placement policy, reservation/budget accounting, verifier-independence placement, scale-out tests.

### WP4 — HCOR-004 Coordinator Runtime
Deliver coordinator lease/runtime, recursive decomposition API, child-budget/authority enforcement, coordinator replacement/reconciliation, stale-generation fencing.

### WP5 — HCOR-005 Verification Plane
Deliver candidate-admission/transport contract, verifier scheduling, challenge profile, adjudication receipts, independent-host/provider constraints, corruption/self-verification negatives.

### WP6 — HCOR-006 Survivability
Deliver recovery state machines, durable coordinator checkpoints, exactly-once authority semantics, provider/coordinator/host recovery integration, crash-cut campaign.

### WP7 — HCOR-007 Convergence
Deliver P0-P3 backlog admission, WIP limits, freeze/reopen rules, owner-interrupt budget, operator-return receipt, anti-thrashing policy.

### WP8 — HCOR-008 Qualification
Deliver campaign harnesses for phases A-I, preregistration schemas, Environment Bank/HarnessBench integration, metrics and scale gates.

## 4. Dependency graph

```text
WP1 ──┬──> WP2 ──┬──> WP3 ─────┐
      │           ├──> WP4 ──┐  │
      │           └──> WP6 <─┼──┤
      └──────────────> WP5 ──┤  │
                              ├──> WP8
WP7 ──────────────────────────┘

External:
SC-MESH / DF-AUTH-001 / BL-006 / BL-009 / Mission Board / HLS
EVPR / OBSH / CMPE / ENVB / HarnessBench
```

WP1/2 can start first. WP5 can proceed largely in parallel after WP1 contracts stabilize. WP3 and WP4 consume WP1/2. WP6 consumes runtime/fencing/continuity contracts. WP7 is policy-heavy and can prototype in parallel but integrates after core mission/event semantics stabilize. WP8 never defines missing product behavior; it qualifies delivered behavior.

## 5. Branch/isolation convention

Suggested branches after kickoff:
- `v2/hcor-001-mission-kernel`
- `v2/hcor-002-dag-coordinator`
- ...
- `v2/hcor-008-qualification`

Each branch starts from the owner-frozen HCOR integration base. No package silently rebases onto unqualified sibling work; integration uses explicit dependency pins.

## 6. Integration gates

A package may enter the HCOR integration branch only when:
1. artifact transport is byte-exact verified;
2. controlling-spec conformance is complete;
3. package tests and required negatives pass independently;
4. first failures/corrections are preserved by generation;
5. independent verifier signs the exact candidate identity;
6. dependency versions are pinned;
7. no unresolved P0/P1 finding is hidden by integration.

Integration does not equal release qualification.

## 7. Coordinator implementation sequence

- **Alpha:** WP1+WP2; one coordinator / three workers / one verifier.
- **Beta:** WP4 replacement; kill coordinator and resume without duplicate accepted work.
- **Hierarchy:** two-level root->mission coordinators with authority attenuation.
- **Cluster:** WP3 resource-aware multi-host scheduling.
- **Survivability:** WP6 provider/coordinator/host recovery.
- **Convergence:** WP7 autonomous freeze/backlog discipline.
- **Scale qualification:** WP8 10 -> 25 -> 50-agent campaigns.

## 8. Session prompt template

```text
You own <WP>. Controlling artifacts are HCOR-000 and <child spec> at the supplied exact repository ref/digests.

Authority: implementation/preparation only within this work package. Do not modify sibling specs, broaden authority, merge/promote, or self-close.

Acceptance receipt first. Preserve first failure. Produce exact-byte artifacts, manifest, tests, negative matrix, design-conformance mapping, checkpoints, and verifier-ready qualification request.

Where a dependency is unavailable, implement only the declared interface/test double permitted by the spec and mark it NON-QUALIFYING. Never turn a missing dependency into an implied PASS.

Stop at first load-bearing contradiction with the controlling spec and file it rather than silently redesigning.
```

## 9. Owner-facing integration report

Every package returns:
- what changed;
- exact identities;
- tests/negatives;
- first failures;
- independent-verification state;
- dependency pins;
- owner gates;
- what remains blocked;
- whether it is safe to integrate.

**Terminal preparation state:** `HCOR_CLOUD_DELEGATION_PACK_READY`.
