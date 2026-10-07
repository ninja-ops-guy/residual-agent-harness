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

## PR #96 review remediation (supersedes pending-only status)

The matrix at head `4ab4de97ec61415151e8608d1399c1bd884ceaff` completed but
**failed**, rather than merely remaining incomplete. Workflow `34919762576`
normal-profile artifact `10377473024` (ZIP SHA-256
`6de6aa4f45cbf8469bfefa372044d4ff17e63763faba4662d3951bd348ddf577`)
binds checkout `90dc12c5005368cbd73277f922a3440cd4130787`, tree
`cda3fa8b9410c45486865005055d99d8d7e220d7`. It retains 3/500 blocked-audit
failures and 0/500 raw-SIGSYS failures. The three failures are two unreached
barriers and one `watchdog_lease_fence` result. Those results are not discarded,
pooled with successful development runs, or reclassified as security success.

**Causal correction:** `RuntimeJournal.lease_is_current()` explicitly accepts
both RESERVED and RUNNING. A watchdog tick before `journal.started()` does not
by itself prove an invalid lease. A forced pre-persistence tick passes locally;
500 additional diagnostic local repetitions also had zero failures. The earlier
PR-comment explanation that RESERVED is not current is therefore incorrect.
The retained failed CI record combined revoked/unavailable reads and omitted
the underlying exception, so its exact lease-read cause remains unresolved.

A separate deterministic test forces a real SQLite exclusive lock only during
started-state persistence. Before the startup handshake it reproduces the
same *class* of premature lease fencing; after the handshake it passes. This
is a demonstrated startup-unavailability mechanism, not proof that this exact
lock caused the historical CI failures. Production now defers lease polling
until the host-owned `started_persisted` event is set. Wall-clock and memory
enforcement remain active during persistence; source dispatch still follows
durable acknowledgement. Post-acknowledgement lease unavailability remains
fail-closed; SQLite exceptions retain their type and numeric error code without
raw exception text. Existing blocked-audit waits and assertions are unchanged.

### Descriptor lifetime and late requests

Non-consuming `exited()` probes and signal sends hold the state lock through
the syscall. `close()` is allowed only after reaping and is then idempotent.
An invalid/closed descriptor is never treated as proof of process exit.
The blocking reap does not hold the state lock, so a concurrent watchdog can
still signal; one reap lock serializes all consuming waits.

`kill()` retains its API and explicitly means "request SIGKILL if still live,
then reap." If an exit is already observable it only reaps: the late caller
cannot claim authorship of that exit. A request racing an independent exit
retains its intent but cannot relabel a normal exit or SIGSYS as a host kill.
Host-request classifications indicate a recorded successful send consistent
with an observed SIGKILL, not forensic proof that no competing killer existed.

### Typed wait evidence and immutable publication

`CLD_EXITED`, `CLD_KILLED`, and `CLD_DUMPED` determine the preferred exit kind
and are cross-checked against the consuming wait result. Unsupported waitid
observation permits return-code fallback. Contradictory statuses, unexpected
observation errors, and lost child ownership produce `unknown_wait_status`;
the runtime cannot publish a candidate from that outcome. Neither wait result
identifies the signal sender. Exact SIGSYS assertions are unchanged.

The terminal record is constructed once during reap, before `stopped` is
published. Its nested mappings/sequences are frozen and `to_dict()` returns a
detached export. Later requests and caller mutations cannot rewrite it.

### Direct tests and matrix import isolation

`tests/test_factory_termination_provenance.py` directly covers request-before-
signal, reasonless requests, late/racing exits, non-consuming probes, locked
fd lifetime, concurrent/idempotent reap, close lifetime/idempotence, typed
wait outcomes, contradictory/unavailable evidence, and nested immutability.
`tests/test_factory_runtime_startup.py` covers startup lock interleavings,
resource enforcement during blocked persistence, failed acknowledgement,
post-acknowledgement lease-read errors, and UNKNOWN rejection.

Every public call to the matrix runner launches a fresh isolated interpreter
for the target repository. This isolates both `sys.path` and `sys.modules`;
merely restoring the path would not prevent baseline/candidate module reuse.
`tests/test_factory_termination_matrix.py` exercises two different repositories
from one caller and verifies failure/skip propagation. Skipped cases produce
no zero-failure confidence bound and never qualify. The fixed workload,
100/500 counts, four load conditions, and failure thresholds are unchanged.

Every amended head requires fresh ordinary CI and all four retained matrix
artifacts. A completed old matrix, a green subset, or an unexplained new failure
cannot authorize merge. The original historical raw SIGKILL stays UNKNOWN.
