# Target/driver supervision interfaces: bounded local slice

Base main: 8369f0dc2a93d8dcb194220b85b9aaf87d1d6df2. Additions only:
scripts/qualification_rc_supervision.py, tests/qualification/test_rc_supervision.py,
and this document. The cleared manifest admission, existing driver loop,
publisher, protected code and acceptance rules are unchanged.

## Interface and enforced logic

The standard-library Supervisor takes externally selected frozen Requirements,
a monotonic clock and three injected handles: observer, target and driver.
ProcessIdentity binds host, PID, birth/generation token and expected image hash.
The three selected host/PID pairs must differ. These values are declarations;
fake handles do not establish OS process identity or actual loaded image bytes.

Requirements supplies start_at, cadence, maximum_gap, per-poll budget and an
ordered tuple of tasks. Every task supplies task_id, attempt_id, nonce, sequence,
absolute monotonic deadline and expected payload digest. There are no operational
time/resource defaults. Synthetic fixture values are not production thresholds.

ProcessHandle.poll returns identity/state. DriverHandle.poll(task) is a read-only,
nonblocking poll returning identity/state/outcome; None means pending, not success.
A ready result must remain stable for a repeated completion-boundary read. The
controller never calls a workload body, starts a process or kills a process.

Each tick validates clock monotonicity/cadence/gaps, observer continuity, target
liveness/generation, driver liveness/generation and task deadline. Successful
results require exact task/attempt/nonce/sequence and process correlations,
unique result IDs, success status and payload digest equality. Extra count claims
are rejected. Accepted counts are derived solely from accepted unique receipts,
not a driver's cumulative count. Target, observer and driver are checked again
at result completion boundaries; a healthy observer alone cannot prove a healthy
target. Returned data is copied before use/retention; prior reports cannot be
mutated through adapter-owned dictionaries.

Coverage uses a separate last successful observation timestamp for each role,
initially bounded by the externally selected start_at. A tick does not reset
these timestamps. Each returned poll includes elapsed callback time in its role's
gap check; only a validated alive identity advances that role's timestamp.
Exactly maximum_gap is permitted; larger gaps fail. The per-callback poll budget
is a separate bound. Pending and acceptance boundaries also check all roles.
The failure latch is rechecked after every injected clock/poll callback and
immediately before acceptance. Cancellation or interruption inside a callback
stops the tick, preserves the first failure and cannot advance accepted results,
the seen-result set or task index. This is a synchronous single-caller interface,
not a claim of cross-thread synchronization or callback preemption.

Exit, absence, replacement, cancellation, failed/missing/unknown result,
deadline violation, clock regression, malformed observation and observer
interruption fail closed. First failure is sticky. There is no resume operation;
resume_state or credited prior elapsed time is rejected. A matching payload
digest is only consistency with the caller's expectation, not independent proof
that representative business work occurred.

## Honest capability boundaries

All reports retain rc_qualified:false and list:
- os_process_identity_unverified
- adapter_poll_preemption_unverified
- external_watchdog_unverified
- workload_attribution_unverified
- cross_process_observer_lease_unverified

A pending external worker can exceed its deadline without voluntarily returning;
the controller detects that through a responsive poll handle. If poll itself
never returns, this synchronous API cannot preempt it. A late-returning poll is
detected only after it returns. An externally supervised watchdog is required.
Clock/handle fakes do not demonstrate preemption, OS birth-token measurement,
real target health or target termination on cancellation.

An observed_complete report describes the selected finite task plan and its
observation boundaries. It is not continuous liveness after completion, a soak
duration, finalRC24h evidence or a release gate. Starting another Python process
with fabricated observer identity cannot be ruled out without an external lease.

## Offline verification

Final command, from rc-soak-local-proposal, piped to python -B -:

```python
import os,tempfile,unittest
from unittest.mock import patch
fixture=r'C:\Users\jinis\Documents\Codex\2026-10-05\task-3\rc-soak-fixtures-supervision-v5'
tempfile.tempdir=fixture
os.environ['TMP']=fixture
os.environ['TEMP']=fixture
suite=unittest.defaultTestLoader.discover('tests/qualification',pattern='test_*.py')
with patch.object(os,'link',side_effect=AssertionError('DENIED_PRIMITIVE_MUST_NOT_BE_RETRIED')) as forbidden:
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print('actual_os_link_calls='+str(forbidden.call_count))
    forbidden.assert_not_called()
raise SystemExit(not result.wasSuccessful())
```

73 discovered, exit 0: 24 supervision tests PASS; 13 manifest tests PASS;
23 earlier proposal tests PASS; 11 original soak regressions PASS; two actual
seal tests explicitly SKIPPED. actual_os_link_calls=0. These are fresh results
after both supervision review fixes; the prior 64 passes are preserved separately.
New regressions cover exact and overdue per-role gaps, cumulative poll time,
failed identities not refreshing coverage, cancellation/interruption during all
three roles' initial and result-boundary polls, shared mutable outcomes, every
clock callback, existing accepted progress, and failure followed by an exception.

Coverage includes invalid/regressing monotonic time; a fake perpetually pending
worker; a late-returning fake poll; deadline/cadence/gap violations; target exit,
absence and same-PID replacement; driver exit/replacement; observer restart,
interruption, forbidden resume/time credit; cancellation; stale/duplicate/wrong
attempt results; failed/missing/fabricated count claims; payload mismatch;
snapshot aliasing; boundary mutation; fixed-code exception sanitization and
first-failure preservation. All supervision handles/clocks/outcomes are synthetic.
Existing admission subprocess tests remain short synthetic rejection checks.

Blocked actual-seal tests and every prior failure receipt remain preserved.
No live/native/provider campaign, process kill, network call, install, os.link
retry, permission/security change, remote write or publication occurred.

## Wiring gaps for the real representative driver/watchdog

1. Independently select/authorize the task plan and bind its requirements digest
   to the admitted manifest/profile and prerequisites. No new manifest schema
   fields or authority are inferred by this separate API.
2. Implement nonblocking process adapters that independently measure target and
   driver image identity, generation/birth token and exit state, avoiding PID
   reuse races. Establish a clock origin shared with externally selected deadlines.
3. Run the representative workload in a separately supervised worker. Attribute
   outcomes to real target operations using independently verifiable receipts;
   expected payload equality alone is insufficient.
4. Implement and verify an out-of-process watchdog and observer run lease. It
   must detect a stuck controller/poll, observer death/restart and missing samples
   without cooperation, and retain first failure. Define termination ownership;
   this API has no kill functionality.
5. Integrate approved source/probe/resource-slope gates and persist these reports
   into the evidence protocol. Actual sealing remains unverified; portable
   finalization remains design-only with postpublication crash protocol unresolved.

No installed-runtime, representative campaign, attestation or qualification
claim is made by this local slice.

## Future journal bridge (design only; not implemented)

Before any run, the external selector would bind the canonical Requirements
digest and run_id to the admitted manifest/profile digest and journal epoch.
Journal creation and replay would require those same externally supplied values;
neither a driver report nor journal content could select or replace them.

A bridge would append only copied, uniquely correlated accepted outcomes,
checking run, task, attempt, nonce, sequence and result identity. Progress would
be derived from these accepted entries, never from adapter counters. Replay would
reject duplicates, reordering, mismatched selection and missing outcomes. Task-plan
completion alone would not satisfy soak duration, resource or source gates.

The first supervision failure, including cancellation, interruption, coverage
loss or deadline failure, would latch a journal failure before any further progress
or completion. Journal write failure would invalidate the run rather than permit
unrecorded progress. Missing capabilities would be propagated unchanged and block
qualification; observed_complete would remain distinct from qualified evidence.
The bridge would need an explicit crash-consistency/ownership protocol and tests
for failure between acceptance and append, replay and finalization. Actual sealing
and external watchdog capabilities remain unverified. No journal, manifest schema,
runner, publisher or acceptance rules are wired or changed by this design note.
