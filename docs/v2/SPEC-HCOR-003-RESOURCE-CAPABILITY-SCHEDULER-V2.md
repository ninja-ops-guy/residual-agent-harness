# HCOR-003 — Resource / Capability Scheduler

**Status:** PARKED / POST-v1 DESIGN  
**Parent:** HCOR-000  
**Depends on:** HCOR-001/002, runner/provider readiness, BL-006-class admission

## Objective

Make hosts, seats, models, providers, and verifier capacity schedulable resources so adding a machine widens capacity without redesigning mission hierarchy.

## Resource inventory

Each runner advertises evidence-backed host identity/generation, CPU/RAM, GPU/VRAM/device class, OS/runtime/toolchain, network class, workspace/source access, qualified providers, local model manifests, lifecycle capabilities, pressure, active leases, and qualification profile.

Configured without readiness receipt is not READY.

## Task requirements

Assignments may request capability/tool classes, RAM/VRAM/CPU/GPU, model/provider constraints, environment/source identity, network policy, duration, isolation, verifier independence, locality/data constraints, and cost/token/runtime budgets.

## Admission chain

Placement requires:

`mission authority AND runner readiness AND host/resource admission AND provider readiness AND model admission AND workspace/source binding AND budget AND verification capacity`.

No scheduler decision bypasses model/resource admission.

## Deterministic policy

1. filter inadmissible placements;
2. enforce independence/locality constraints;
3. score by pressure, locality, cost, latency and priority;
4. reserve capacity atomically;
5. issue lease/fencing token;
6. record placement receipt.

Initial policy is inspectable/rule-based, not learned.

## Budgets

Mission/coordinator envelopes bound max workers, parallelism, provider cost, tokens, runtime, retries, allowed hosts/providers, verification requirements, and owner-interrupt budget. Child aggregate reservations cannot exceed parent budget.

## Reconciliation

Runner disappearance expires leases after policy bounds; replacement placement gets new generation/fencing. Rejoining stale runner cannot regain authority. Capacity changes update runnable placement without mutating mission intent.

## Verification independence

Scheduler enforces requirements such as independent host/provider/model/harness. A verifier cannot be placed where declared independence constraints collapse.

## Negative qualification

Test stale readiness, model too large, host pressure changes after reservation, provider READY receipt expiry, runner loss after lease, double reservation, budget race, verifier colocated when prohibited, spoofed capability, host mismatch, and late stale result.

## Scale target

Register heterogeneous CPU/GPU/local/cloud runners. Add a new qualified machine and demonstrate that capacity increases without mission-spec changes or owner topology edits.

**Terminal:** `RESOURCE_CAPABILITY_SCHEDULER_QUALIFIED`.
