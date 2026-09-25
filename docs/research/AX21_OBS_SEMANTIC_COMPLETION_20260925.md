# AX-21 Observation — Process Success Is Not Semantic Task Success

**Observation ID:** AX21-OBS-SEMCOMP-20260925-001  
**Date:** 2026-09-25  
**Status:** OBSERVED / CORPUS EVIDENCE  
**Campaign:** SNYK-R4 adversarial qualification  
**Coordinator:** GPT-6 Astra via Codex  
**Worker:** local Gemma 4 via Codex local profile  
**Scope:** R4-02 archive-extraction adversarial review

## Claim

A worker process can terminate successfully at the transport/process layer while failing to complete the assigned semantic task.

This observation is evidence for RESIDUAL's distinction between **process completion** and **verified mission completion**. Exit status alone is not a sufficient completion predicate for agentic work.

## Observed execution

The coordinator launched the local Gemma worker with a bounded 1200-second execution window and retained:
- JSONL session transcript;
- stderr;
- final-message artifact.

The worker successfully:
1. started;
2. inspected the existing R4-02 archive-security tests;
3. inspected the real archive extractor;
4. identified the distinct ZIP, TAR, and TAR.ZST protection paths;
5. inspected the declared Python runtime requirement.

The worker did **not**:
1. create the requested adversarial harness;
2. execute the requested archive cases;
3. produce the requested structured audit/disposition.

The process nevertheless exited with **code 0** before the timeout.

The coordinator detected the missing deliverable, classified the subagent result as incomplete rather than successful, preserved the worker evidence, and continued the audit itself.

## Evidence summary

Observed retained artifacts from the orchestration session:

- `artifacts/security/r4-02/gemma-final.txt`
- `artifacts/security/r4-02/gemma-session.jsonl`
- `artifacts/security/r4-02/gemma-stderr.txt`

Observed sizes at reconciliation time:

- final message: 180 bytes
- session log: 33,161 bytes
- stderr: 226 bytes

The coordinator's reconciliation explicitly recorded that the worker exited 0 but had only inspected files and had not created the harness, run tests, or produced the requested report.

## State interpretation

| Layer | Observed state |
|---|---|
| Process | COMPLETED / exit 0 |
| Transport | Completed normally |
| Worker activity | Partial useful work |
| Required deliverables | Missing |
| Semantic mission | INCOMPLETE |
| Coordinator disposition | NOT SUCCESS |
| Recovery | Coordinator resumed mission |

The important contradiction is:

```
process_exit == 0
semantic_completion == false
```

A completion system that trusted only process exit status would have produced a false-positive success.

## RESIDUAL implications

### 1. Completion must be verifier-owned

Workers should not be authoritative for their own completion state. A worker may report completion, stop normally, or return exit 0 while required outputs remain absent.

The authoritative completion predicate should be based on mission requirements and independently checked evidence.

### 2. Deliverable contracts should be machine-verifiable

A mission should declare expected outputs where practical, for example:

- required artifact paths;
- required receipt schemas;
- required tests;
- required evidence fields;
- required final-state predicates.

The coordinator/verifier can then distinguish:

```
PROCESS_EXITED
WORKER_RETURNED
DELIVERABLES_PRESENT
DELIVERABLES_VALID
MISSION_VERIFIED
```

rather than collapsing them into one `COMPLETED` state.

### 3. Partial work can remain useful without becoming success

The Gemma run produced useful context gathering before failing semantic completion. RESIDUAL should preserve such partial work as evidence while preventing it from satisfying the mission completion gate.

Suggested distinction:

```
PARTIAL_USEFUL_WORK
INCOMPLETE
VERIFIED_COMPLETE
```

### 4. Coordinator recovery is a first-class behavior

The coordinator detected the missing deliverable and continued the mission itself rather than trusting exit status. This is a concrete example of semantic recovery after nominal worker termination.

### 5. Multi-model orchestration requires semantic handoff validation

When one model delegates to another, the receiving worker's process success is not proof that the requested handoff contract was satisfied. Handoffs need explicit acceptance criteria.

## Candidate invariant

**AX21-SC-INV-01 — Semantic Completion Authority**

> No worker process exit code, transport completion state, or self-reported completion message may independently transition a mission to VERIFIED_COMPLETE. Required deliverables and mission predicates must be independently reconciled by the authoritative verifier/coordinator.

## Candidate state machine

```
DISPATCHED
  -> RUNNING
  -> RETURNED
       -> VERIFYING
            -> VERIFIED_COMPLETE
            -> PARTIAL_USEFUL_WORK
            -> INCOMPLETE
            -> QUARANTINED
```

`RETURNED` is intentionally not synonymous with `VERIFIED_COMPLETE`.

## Candidate regression experiment

Create a deterministic worker fixture that:

1. receives a mission requiring artifacts A, B, and C;
2. creates only A;
3. performs useful repository reads;
4. emits a plausible progress/final message;
5. exits with status 0.

Expected RESIDUAL result:

- worker process recorded as returned;
- partial artifact A retained;
- mission not marked verified complete;
- missing B/C identified explicitly;
- recovery/reassignment permitted;
- no completion receipt issued until the requirements are satisfied.

Negative control:

A worker produces A, B, and C with valid schemas and passes the independent verifier. The same mission must then transition to VERIFIED_COMPLETE.

## Research classification

**Observation type:** orchestration / semantic completion / verifier authority  
**Evidence strength:** empirical single-run observation with retained transcript artifacts  
**Generalization:** hypothesis supported by this observation; broader frequency is not established  
**Product claim:** none — this observation motivates an invariant and regression experiment; it does not by itself prove all RESIDUAL completion paths enforce the invariant.

## Relationship to SNYK-R4

This observation was incidental to SNYK-R4-02 and is not itself a Snyk vulnerability. It should remain separate from the archive-extraction security disposition.

The security campaign supplied the workload; the research value comes from the worker/coordinator completion mismatch.
