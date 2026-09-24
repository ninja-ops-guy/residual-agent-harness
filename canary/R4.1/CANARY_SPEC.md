# R4.1 Bounded Continuity Canary Specification

Status: prepared only. Execution is not authorized.

## Scope and minimum useful operation

Perform exactly one authorized, non-privileged Shared Comms message to a pre-designated canary-only project/audience with one stable `operation_id`. Interrupt only the experiment-owned sender after the receiver durably commits but before the sender records its ACK. Restart only that sender, require receipt-first reconciliation, and prove that recovery performs `GET comms/receipt` followed by local ACK with zero retransmission POSTs and exactly one receiver event.

The canary may not deploy, merge, promote, push, restart protected services, change credentials, or write outside the designated canary project/evidence directory.

## Preconditions

All conditions are mandatory and fail closed:

1. Candidate HEAD is `8701367db6d3202f24b3eb9f4696b0cadf657985`, tree is `79bfe6ed1743907065ed44aeb9c460c47527e0c6`, and parent is `eada7577cf6f2de875b508c6a82f47870e3aa673`.
2. Candidate worktree is clean and `git remote` output is empty.
3. R4.1 seal `SHA256SUMS` verifies, its disposition is `READY_FOR_CANARY`, and it states canary execution has not occurred.
4. Protected services listed in `EXPECTED_SERVICES_FILE` match the expected active/running state before execution. No protected service may be restarted.
5. An independently approved authorization receipt exists as a regular file, is inside the evidence destination, and contains the operation scope, approver, expiry, and exact operation ID.
6. Operator supplies an executable adapter, an absolute safe evidence destination, a unique stable operation ID, and explicit GO using `RESIDUAL_R4_CANARY_GO=R4.1-CANARY-8701367D`.
7. Evidence destination must not be the candidate, seal, authoritative qualification run, filesystem root, home directory, or a symlink; it must be new or an empty canary evidence directory.
8. Adapter preflight confirms the designated canary-only receiver/project, expected service state, rollback readiness, and no broader authority.

## Required invariants

- No unauthorized production mutation; no credential mutation.
- One operation only; stable operation ID; duplicate receiver effects prohibited.
- Maximum one initial POST. No blind retransmission after indeterminate commit.
- Restart recovery begins with receipt lookup. A receipt hit permits local ACK and zero POST; unavailable reconciliation remains PENDING with zero POST.
- Durable outbox survives sender interruption.
- Retries are bounded to one initial attempt and one receipt lookup; total runner timeout is 120 seconds.
- Protected services remain stable and rollback remains independently available.
- Authority cannot widen silently: adapter commands receive an immutable scope file and evidence path; any scope/hash change aborts.
- Evidence must be complete before success can be declared.

## Abort conditions

Abort immediately on identity, cleanliness, remote, seal, authorization, path-safety, service-state, adapter-preflight, timeout, scope, or manifest mismatch; any credential/protected-file mutation; unexpected POST; more than one receiver event; changed operation ID; unavailable rollback; incomplete trace; protected service PID/state change; or any operator intervention not recorded before continuation.

On abort, stop network actions, preserve the outbox and evidence, invoke rollback independently if safe, collect poststate, and return failure. Never retry an indeterminate POST.

## Required evidence

The evidence set must include prestate, candidate identity, authorization receipt and hash, package manifest verification, scope and operation ID, timestamped network-action trace, durable outbox transitions, receipt lookup/result, receiver event count, protected process/service pre/post state, poststate, operator interventions, rollback evidence, and a SHA-256 manifest covering every evidence file except that manifest.

## Machine-verifiable success

`verify_canary.py` returns `CANARY_PASS` only when all required files and hashes validate, candidate/seal identities match, authorization was valid at start, all steps completed inside 120 seconds, the same operation ID appears throughout, the trace contains exactly one initial POST then (after interruption) a receipt GET and no subsequent POST, outbox transitions are `PENDING -> SENT_INDETERMINATE -> ACKED`, receiver event count is exactly 1, protected services match prestate, rollback is available/tested without production mutation, safety counters are zero, and no abort condition occurred.

It returns `EVIDENCE_INCOMPLETE` for missing or unverifiable evidence and `CANARY_FAIL` for complete evidence demonstrating any violated criterion. `CANARY_PASS` never deploys, merges, promotes, or pushes.
