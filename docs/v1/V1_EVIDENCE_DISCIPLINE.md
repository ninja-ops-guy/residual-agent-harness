# RESIDUAL v1 evidence and convergence discipline

**Status:** proposed release-governance contract  
**Purpose:** convert current dogfood lessons into explicit admission rules without expanding v1 scope.

## Principles

1. **Informative first failure is evidence.** Never erase a failed attempt because a later attempt passes. Remediation gets a new attempt/receipt.
2. **Declared configuration is not effective state.** Qualification distinguishes authoritative config, normalized/derived state, session binding, runtime registry and observed execution.
3. **Inference cannot substitute for missing evidence.** When progress requires external facts or human authority, additional model attempts are not an admissible substitute.
4. **Coordination is not authority.** Coordinator proposes/routes/synthesizes; Orchestrator structures; Station authorizes; workers execute; verifiers accept/reject; humans dispose protected decisions.
5. **Context size is not semantic custody.** Preserve lossless evidence references separately from bounded working summaries. Context overflow is a retained failure, not a reason to silently discard provenance.
6. **Fleet recovery is admission-controlled.** A working seat/class does not qualify another seat/class. Widen only after the bounded canary for the preceding scope passes.
7. **v1 convergence should become boring.** New architecture is deferred unless it repairs a demonstrated violation of an accepted v1 invariant.
8. **Negative and superseded evidence is append-only.** Historical receipts remain bound to their exact bytes/environment and are never relabeled as evidence for a successor.

## V1 change-admission rule

A proposed change may enter the v1 convergence set only if at least one is true:

- it repairs a reproducible violation of an already accepted v1 invariant;
- it closes a release-matrix requirement already approved by the owner;
- it repairs a qualification/reproducibility/security defect in the release machinery;
- it is documentation/evidence reconciliation required to make an existing release claim accurate.

Otherwise:

`DEFER_TO_V2_OR_POST_V1`

Interesting, useful or performance-improving is not sufficient for v1 admission.

## Evidence-gated work rule

If deterministic checks pass but review requires facts not producible by the current task, classify the operator-facing blocker as external evidence/human authority rather than encouraging repeated inference.

Required behavior:

```
missing external fact
→ preserve current attempt
→ suppress pointless model retries
→ emit evidence requirement
→ wait for admissible evidence
→ deterministic re-evaluation
```

Evidence submission itself must not directly mutate task state, lease, owner, review approval, integration state or release state.

## Configuration qualification layers

Where applicable, receipts separately identify:

```
authoritative_config
normalized_config
derived_catalog
session_binding
runtime_registry
observed_execution
```

A digest at one layer does not prove another layer is unchanged. Byte identity and semantic identity are reported separately when software owns/re-serializes derived state.

## Experiment discipline

Before an experiment:

- state the claim;
- identify the independent variable;
- freeze baseline identities/digests;
- define PASS / FAIL / NOT_PROVEN;
- define stop conditions;
- define rollback;
- prohibit unrelated repair during the observation.

After first failure:

- preserve it;
- explain what layer it isolated;
- change the minimum independent variable;
- never retroactively call the failed attempt a pass.

A successful direct component call does not prove automatic routing/fallback/integration.

## Coordinator boundary

Shared Comms and coordinators are advisory/data-plane components by default.

They may:

- transport messages/evidence references;
- summarize state;
- propose decomposition;
- request bounded observations;
- surface blockers.

They may not, by message alone:

- grant worker authority;
- satisfy an evidence requirement;
- approve review/integration;
- mutate task eligibility;
- select an RC;
- authorize release.

## Fleet widening

Use staged admission:

```
one seat
→ one lifecycle class
→ multi-host canary
→ controlled fleet widening
```

For each widening step retain:

- host/seat identity;
- process creation identity;
- session identity;
- requested/actual transport;
- provider/model identity when inference occurs;
- cursor/recovery state;
- duplicate inference/response counts;
- protected-seat unchanged proof where applicable.

## Context continuity

For v1 operations:

- checkpoint before intentionally disruptive work;
- retain evidence/artifact references outside conversational summaries;
- after context overflow, resume from a bounded checkpoint rather than replaying an unbounded transcript;
- do not treat a summary as lossless evidence.

Portable SharedThread/ObservationPack/compaction-ledger semantics remain v2 work unless a current v1 invariant requires otherwise.

## Current freeze targets

Until current bounded lanes close:

- do not add new v1 features;
- do not widen the Shared Comms fleet beyond the approved Anvil canary;
- do not disturb Ghost while P3.3 durability/fallback work is active;
- do not execute physical F6 until the accepted #448 successor and exact helper binding are settled;
- do not repeatedly rerun the dogfood E0 mission without new admitted evidence.

## Required convergence order

```
bounded current experiments
→ independent dispositions
→ accepted product/helper identities
→ physical F6
→ independent F6 adjudication
→ one converged release tree
→ fresh exact-tree qualification
→ approved release matrix evidence
→ exact RC
→ install/recovery/rollback/soak
→ release disposition
```

## Non-claims

This policy does not itself approve a candidate, qualify a runtime, admit external evidence, authorize F6, select an RC or authorize release.
