# Sandbox timing repair after the b127d000 review

This is the implementation follow-up to the independent Lane 2 review of
PR #108 at `b127d000dbac7d75723969840491be5f44ec7c4e`. The failed review and its
unmodified reproductions remain retained in
[the review bundle](https://github.com/ninja-ops-guy/residual-agent-harness/blob/32101e6d47c0969f8e51a213df8a349dbc40d920/runs/reviews/pr108/b127d000/README.md).
The repair includes main `326eb2af47a4635c75c81735738801dd065fdd81` without
changing the owner's demo implementation. This document records implementation,
not independent acceptance or M4 qualification.

| Finding | Repair | Regression evidence |
| --- | --- | --- |
| R1: declared payload timeout extended by five seconds | Both ordinary subprocess paths use the declared timeout; no extra payload allowance | Real two-second payloads cannot succeed under a one-second limit, with and without the environment wrapper |
| R2: lease gate suspends watchdog resource enforcement | One short lease read per watchdog poll, bounded by the resource and lease deadlines; unknown state persists across polls | Real locked SQLite + child wall deadline; memory enforcement while the lease stays unknown |
| R3: unreaped finalizer has no recovery owner | Keep the active control and workspace; return UNKNOWN/reap_pending; one recovery thread drives the existing consuming reap and subsequent cleanup/publication | Persistent and transient timeout, terminal publication exactly once, physical cleanup, original watchdog/operator provenance, publication failure remaining pending |
| R4: exhausted retry overwrites genuine SQLite error | Refuse another read after the deadline; preserve the last actual per-call diagnostic | Real repeated SQLITE_BUSY reads retain error code 5 |
| R5: each reader retry restarts the full busy budget | Recompute remaining time at connection opening and before SQL; retry only BUSY/LOCKED | Late initial failure + real locked retry; no query after expired opening; non-contention errors are not retried |
| C1: stale v3 assertion breaks compatibility and ownership | Restore the original v2 assertion and its original blob | Existing M4 safety test and ownership checker; its pin remains unchanged |

The registered regressions are in `tests/test_sandbox_timing_repairs.py`.
Existing watchdog/startup tests now patch the actual `lease_read` dependency.
No assertion has been replaced by a skip or an increased worker time limit.
The protected regression module is added to the ownership baseline. Updated
pins describe a proposed repair tree; they are not an independent approval.

## Pending reap contract

`ProcessControl.reap()` remains the only consuming wait for an owned child.
`stopped` remains evidence of actual consuming reap. An unreaped control cannot
produce a termination record or lose its owned descriptors/workspace merely
because a wait timed out.

The synchronous runtime returns `status=UNKNOWN`, `reason=reap_pending`,
`process_reaped=false`, with no return code, termination record or candidate.
The journal remains RESERVED/RUNNING and therefore fences a competing attempt.
A `RuntimeReapPending` observation records this state when the journal is
available. A daemon owned by the runtime retries the existing reap path. Only
after actual reap does it close resources, discard a failed workspace and write
the original terminal decision. A later drain timeout cannot replace an earlier
watchdog cause or operator cancellation.

A permanently unreapable child remains pending. Unexpected recovery/cleanup or
journal-publication errors retain the active/pending entry and a sanitized error
class in `FactoryRuntime._reap_errors`; they do not claim a persisted terminal
row. The recovery thread does not automatically retry arbitrary cleanup/storage
errors. Operator reconciliation is required for those errors and after a
controller restart. This repair is not a claim of distributed recovery or an
elapsed soak qualification.

## Acceptance still required

Run the original 12-test battery, the five retained review probes, the new
regressions and reversion attacks. Retain full ordinary suites, ownership and
current-main integration evidence on the actual published revision. An incapable
host's namespace/seccomp skips remain UNKNOWN for qualification; earlier
`d750c48` determinism evidence is not reused as proof of changed code.

The author of this follow-up also performed the preceding review, so the repaired
implementation needs a fresh independent reviewer. No merge or self-approval is
included in this follow-up.
