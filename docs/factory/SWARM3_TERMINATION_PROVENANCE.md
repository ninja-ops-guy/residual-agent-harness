# Swarm 3 — termination provenance and timing qualification

## Scope

This work addresses the two timing-sensitive Python 3.11 failures retained from the historical clean-install qualification without weakening the security assertions.

Historical evidence identity:

- failing synthetic integration tree: `83016683188040aea4213aec46cc433caad67766`
- PR head that produced it: `52e5805468be15919088d4d77214d33825861fc4`
- workflow run: `34852081999`
- retained failing artifact: `10351243784`
- artifact SHA-256: `c3e866fd23a020ee2ee626e14b35c1ab236113017afc53442013d49636fe9244`
- suspect tests:
  - `ExecutionTests.test_raw_file_syscall_is_kernel_killed`
  - historical `ExecutionTests.test_watchdog_kills_even_when_audit_callback_is_blocked`

The historical raw-file failure observed `SIGKILL` where the test requires `SIGSYS`. The retained evidence cannot identify the killer, so its cause remains **UNKNOWN**. It is not reclassified as a seccomp success.

The historical blocked-audit failure did not reach its `PathAuthorized` barrier within the test's two-second host wait while the runtime contract had a 250 ms wall-clock budget. That is classified as a **test nondeterminism / invalid startup-scheduler assumption**, not as a demonstrated watchdog or seccomp failure.

## Remediation boundary

The patch is intentionally narrow and does not modify M4 trust-boundary files or shared M4 evidence schemas.

### Single-owner process lifecycle

`ProcessControl` owns the child pidfd, immutable PID/start-time/boot identity, host termination intent, non-consuming exit observation and the consuming reap. `waitid(..., WNOWAIT)` is used where the platform supports it to observe `siginfo`; the only consuming child wait for a `ProcessControl`-owned child is `ProcessControl.reap()`.

The bootstrap-error path before `ProcessControl` ownership exists remains a separate fail-closed fallback and may directly kill/reap that not-yet-owned child.

### Cause is not inferred from signal alone

Every terminal result records:

- correlation/attempt ID;
- PID, `/proc/<pid>/stat` start ticks and boot ID;
- host termination requester, boundary, field and action when one exists;
- monotonic request, observation and reap timestamps;
- return code and observed signal;
- `waitid` code/status when available;
- cgroup-v2 `memory.events` snapshots and `oom_kill` delta when available;
- a typed classification;
- explicit kernel-audit availability status.

An externally observed `SIGKILL` with no recorded host request is classified `unknown_sigkill` (or `unknown_sigkill_with_cgroup_oom_activity` when the shared cgroup reports OOM activity). The latter remains non-causal because shared cgroup counters do not identify which process was killed.

A raw `SIGSYS` test still requires exact `SIGSYS`. No code maps generic `SIGKILL` to seccomp success.

## Blocked-audit test split

The invalid 250 ms/2 s scheduler race is removed rather than widened.

The replacement property test injects a deterministic watchdog clock. The clock is frozen before `PathAuthorized`, so startup/scheduling latency cannot consume the watchdog budget. Once the audit callback is known to be blocked, the clock advances beyond the deadline and the test requires watchdog termination with typed `watchdog_wall_clock` provenance.

The existing real-process noncooperative-worker test remains the separate real watchdog integration test and now verifies the same provenance classification.

## Qualification matrix

`scripts/factory_termination_matrix.py` runs the raw seccomp case and the applicable blocked-audit case under four host conditions:

- `normal`
- `cpu`
- `io`
- `combined`

The PR workflow runs:

- **pre-fix:** 100 repetitions per test per condition against exact tree `83016683188040aea4213aec46cc433caad67766`; failures are retained rather than causing evidence loss;
- **post-fix:** 500 repetitions per test per condition against the PR candidate; any unexplained failure fails the job.

For a test with zero failures in `n` runs, the report gives the exact one-sided 95% upper bound `1 - 0.05^(1/n)`. At `n=500` this is approximately 0.6%. Zero failures are therefore reported as an upper-bound result, **not proof of determinism**.

## Claim discipline

Until the full matrix finishes successfully:

- blocked-audit root cause: **classified test defect**;
- historical raw `SIGKILL`: **UNKNOWN provenance**;
- seccomp failure: **not demonstrated**;
- exact local blocked-audit watchdog reproduction: **worked in the previously observed local reproduction only**;
- prior 100/100 local runs: **uncongested local baseline only**, not the required pre-fix distribution;
- Swarm 3: **partially complete** until termination provenance and all retained contention evidence satisfy the qualification gates.
