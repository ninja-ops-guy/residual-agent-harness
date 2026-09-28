# HCOR-008 — Qualification Campaigns & Scale-Out Program

**Status:** PARKED / POST-v1 DESIGN  
**Parent:** HCOR-000  
**Purpose:** integrate HCOR-001..007 and prove the hierarchy under scale/failure.

## Phase A — Single coordinator kernel

Topology: one coordinator, three workers, one independent verifier, multiple missions.

Prove durable mission objects, DAG progression, leases/fencing, exact artifact transport, independent verification, owner-gate parking, and convergence.

Terminal: `HCOR_A_SINGLE_COORDINATOR_PROVEN`.

## Phase B — Coordinator replacement

Kill coordinator at preregistered transition points. Replacement acquires new generation/fencing, rebuilds from event log/checkpoint, and continues with no duplicate accepted work.

Terminal: `HCOR_B_COORDINATOR_REPLACEMENT_PROVEN`.

## Phase C — Two-level hierarchy

Root delegates two missions to child coordinators. One child recursively decomposes. Verify authority attenuation, aggregate budget enforcement, direct access to original controlling artifacts, and independent verification.

Terminal: `HCOR_C_HIERARCHY_PROVEN`.

## Phase D — Resource-aware cluster

At least four heterogeneous runners including CPU and GPU classes. Add a new machine during campaign. Scheduler qualifies/discovers capacity and widens placement without mission-spec/topology edits.

Terminal: `HCOR_D_SCALEOUT_PLACEMENT_PROVEN`.

## Phase E — Failure campaign

Inject worker loss, provider loss, verifier loss, child-coordinator loss, root-coordinator loss, Station restart, host loss/rejoin, artifact corruption, stale results, authority rescission, and owner absence.

Terminal: `HCOR_E_SURVIVABILITY_PROVEN`.

## Phase F — Verification independence

Run implementation and verification on distinct hosts/providers/harnesses where required. Inject false completion and self-reported PASS. Required independent challenge catches them.

Terminal: `HCOR_F_INDEPENDENCE_PROVEN`.

## Phase G — Convergence campaign

Feed continuous P2/P3 suggestions while P0/P1 work executes. Verify WIP limits, backlog admission, freeze/reopen rules, operator-return receipts, and falling owner-intervention rate.

Terminal: `HCOR_G_CONVERGENCE_PROVEN`.

## Phase H — Scale campaign

Target progression:
- 10 agents / 3 hosts;
- 25 agents / 5 hosts;
- 50 agents / 10+ hosts.

Do not increase scale until previous tier passes reliability floors.

Measure owner interventions/completed mission, accepted duplicate rate (target zero), stale-authority mutation (zero), lost evidence (zero), coordinator recovery time, runnable-to-dispatch latency, verifier backlog, provider/host utilization, cost/token/runtime, and mission completion.

## Phase I — North-star chaos campaign

During active work:
- remove a provider;
- kill a worker;
- kill a mission coordinator;
- remove a host;
- delay/corrupt an artifact transport;
- rescind a mutation dispatch;
- keep owner unavailable.

RESIDUAL must preserve truth, reallocate/fence, continue independent work, verify results, park protected gates, and converge.

## Environment Bank / HarnessBench integration

Every campaign is preregistered and replayable through ENVB generations. HarnessBench supplies controlled model/harness/topology comparisons and adversarial sensitivity controls. Screening and confirmatory environments remain separated.

## Release criteria

HCOR is dogfoodable only after A-C. Multi-host autonomous claims require D-F. Strong unattended hierarchical-swarm claims require G-I with repeated runs and no hidden owner-as-message-bus dependency.

## Cloud-swarm delegation packages

After v2 kickoff, independent cloud sessions can take:
- WP1 HCOR-001 schema/state machine;
- WP2 HCOR-002 event reducer/DAG engine;
- WP3 HCOR-003 scheduler/admission;
- WP4 HCOR-004 coordinator lease/runtime;
- WP5 HCOR-005 verification plane;
- WP6 HCOR-006 recovery/fencing;
- WP7 HCOR-007 convergence/backlog;
- WP8 HCOR-008 harness/campaign implementation.

Each package must deliver code, tests, exact artifact manifests, design-conformance receipt, first-failure evidence, and an independent review target. No package self-closes.

**Terminal:** `HCOR_SCALEOUT_QUALIFICATION_PROGRAM_SPECIFIED`.
