# M2 lifecycle guard restoration after PR #58

Review basis: main `655754022e4ad161339b744a28cd201e12e13114` and its
predecessor `beb09ea85922256bed0ad11eec58a936eccd2bb2`.

The #58 runtime change included more than watchdog attribution. It removed the
pre-deletion candidate/contract check in `FactoryRuntime.purge`, the durable
`RuntimeCapacitySelected` observation, and strict retention validation. It also
lost the CLI's sanitized error boundary. These changes were not covered by the
existing positive-path tests.

A deterministic temporary-repository reproduction of the original merged tree
showed `purge` deleting a RESERVED attempt's worktree, then raising JournalError
while the journal still reported RESERVED. Checking state after deletion does
not protect the worktree. The same attempt with a different contract hash could
also purge a candidate. This is a host API lifecycle regression, not a claim that
a sandboxed worker can directly invoke that API.

This repair restores the pre-#58 guards in place, preserving the new watchdog
termination-intent checks and the `--trace-id` alias for `--run-id`. It leaves the
new M4 receipt-backed planning module unchanged. Invalid capacity is checked
before the empty-batch path; the capacity observation must persist before any
worker is dispatched. Retention remains positive, finite, numeric, and not bool.
CLI failures again return nonzero with sanitized blocked JSON, not tracebacks.

`tests/test_factory_runtime_lifecycle.py` adds 19 tests covering destructive
cleanup ordering, contract identity, state rejection, valid purge, missing
worktrees, retention/clock validation, expiry boundaries, capacity observations,
audit-before-dispatch, CLI aliases, and preservation of watchdog intent versus
lease-failure enforcement. These include real temporary Git worktrees and
SQLite journals, but no model calls. Watchdog interleavings are deterministic
fixtures; the existing Linux execution suite remains necessary for OS evidence.

Ownership ordering: review this Factory repair before accepting a transition in
#59. Do not advance the ownership baseline to the uncorrected #58 tree just to
make #50 green. A baseline transition must identify the exact repaired commit,
retain all existing protected paths, and include the new canonical
`residual/factory/m4_evidence.py` path. #50 is packaging/source qualification,
not the place to relax Factory runtime protection.
