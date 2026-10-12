# Disposable local Python process test adapter

## v9 constructor ownership repair

The constructor now retains its Popen immediately after spawn and wraps all later
initialization, including identity construction and reader startup, in cleanup.
On failure it terminates/waits only for that owned child, joins a reader only if
it actually started (including start-then-raise), and closes streams when safe.
A wait timeout can escalate only to kill on the same owned object. A termination
error does not trigger a different termination route. An active reader's stdout
is not closed underneath its blocking read.

The original exception is re-raised unchanged. Cleanup diagnostics and the owned
process/reader/stderr references are attached to it, so a cleanup failure does not
hide the initial error or discard ownership. Cleanup exceptions, including an
unexpected cleanup-helper failure, remain secondary diagnostics. This does not
guarantee successful cleanup when OS operations themselves fail or block.

Focused fault-injection tests use actual children with injected failures at
identity creation, before Thread.start, and after a real Thread.start. Separate
injected termination/helper failures verify original-exception identity and retained
ownership. The test owner cleans those children using the same captured Popen after
removing the injected RuntimeError; this is not a retry of an actual access denial.
Per-child records distinguish constructor cleanup from test-owner cleanup.

Focused result: 3 PASS with five actual children. The combined v9 command is
`python -B run_rc_process_v9_checks.py`; its fresh result and ownership totals are
stored separately from the historical v8 evidence below. No end-to-end bridge
extension was included while review is pending.

Final v9 suite: 102 discovered, 100 PASS, two preserved sealing SKIP, zero
os.link calls. Its 23 children comprise 18 ordinary process fixtures and five
constructor-fault children. Three of the latter are reaped by constructor cleanup;
two deliberately injected cleanup failures require explicit test-owner cleanup.
All 23 are reaped. Earlier focused/full runs and their diagnostics are preserved
separately; injected failures are never described as successful constructor cleanup.

## Preserved v8 scope and evidence

This additive test-tooling slice uses installed Python and standard-library code
only. It leaves all nine reviewed v7 source/test/document files unchanged. It does
not connect the production runner, journal bridge publisher or a native runtime.

The available qualification_process_soak.py and qualification_long_soak.py were
inspected. Their Linux /proc metrics, Station/network campaign and broad cleanup
helper are unsuitable here. No protected or existing process utility was edited.

## Ownership and transport

Each test creates three separate Python children: observer-role sentinel, target,
and driver. OwnedPython retains the exact Popen it creates, a random spawn token,
the child PID, and the SHA-256 of the selected executable's file bytes. A child
handshake returns PID, token and role; mismatches reach the existing Supervisor's
identity rejection. No arbitrary-PID handle attachment, process enumeration or
service termination exists. Windows children use CREATE_NO_WINDOW and shell=False.

The observer-role child is a distinct sentinel, not an independent watchdog for
the parent coordinator. A spawn token and held Popen handle establish fixture
ownership; they do not independently measure an OS creation timestamp, loaded
image identity, observer lease or production target provenance.

stdout carries bounded JSON frames. A dedicated daemon reader thread performs
blocking pipe reads into a four-item queue with a 65536-byte frame cap. poll()
drains at most four queued frames and uses Popen.poll; it never waits for a result.
The parent drives externally selected monotonic task deadlines while an alive
child can withhold its second outcome indefinitely. A reader waiting on a pipe
does not block deadline observation. This proves responsiveness for this adapter,
not preemption of arbitrary hanging Python callbacks or a hung coordinator.

All test timeouts are selected explicitly in the test fixture: startup 5 seconds,
child lifetime 15 seconds, cleanup wait 2 seconds, cadence 0.15 seconds,
maximum gap 2 seconds, poll budget 0.1 seconds, task deadlines at start+2 and
start+4 seconds. These are test values, not production or RC thresholds.
The child has a finite self-expiry as a cleanup backstop; this is not an external
watchdog. No child creates descendants, sockets or services.

Cleanup operates only on each retained Popen, waits for exit, joins its reader,
and closes its streams. A timeout permits kill on that same owned object only;
no kill escalation was needed in this run. Access errors are not retried through
another mechanism. The test runner stops on the first test failure.

## Actual execution evidence

From the task workspace, the exact successful command was:

```powershell
python -B run_rc_process_v8_checks.py
```

The bundled runner records the opt-in environment, authorized fixture directory,
test discovery and os.link guard. Without explicit opt-in, the six process tests
are skipped. Every child command (full argument list), PID, generation token,
handshake, termination action, return code and reader cleanup result is retained
under rc-soak-fixtures-process-v8/owned-python-*/ownership-cleanup.json. Child
stderr files and task configurations are included as supporting evidence.

Fresh combined result: 99 discovered, 97 PASS, two preserved actual-sealing SKIP,
zero failures/errors and zero os.link calls. Six new tests use actual disposable
children: healthy correlated responses; neverresponding second task with one
previously accepted result; early target exit; wrong generation token; stale
attempt outcome; cancellation preserving progress followed by owned cleanup.
The previous 91 offline passes are separate evidence, not upgraded runtime claims.

Initial preflight created three children and failed with invalid_timing_requirements
because its test poll budget (0.5) exceeded cadence (0.15). All three were cleaned
up; the failure log is preserved. After correcting only that fixture value to 0.1,
the full run created 18 children and passed. Across both attempts, all 21 children
were reaped and all reader threads joined, with zero cleanup errors. One target
exited naturally; 20 children were terminated using their owned Popen handles.
Windows termination return code 1 is recorded as cleanup, not a successful workload.
No execution/access denial occurred.

## Boundaries that remain unverified

Actual local Windows child creation, stdout transport, Popen exit observation,
parent-driven pending-result timeout and owned cleanup worked. Task results remain
synthetic fixture operations: they do not prove work occurred inside the target.
The executable digest is a disk-file snapshot, not loaded-image attestation.
The adapter has not been tested on other operating systems or hostile process trees.

All Supervisor missing-capability labels remain unchanged: OS process identity,
poll preemption, external watchdog, workload attribution and observer lease remain
unverified in the general runtime sense. rc_qualified is always false. No 24-hour
acceptance, seal capability, durable journal guarantee or native/Station/provider
qualification was enabled or claimed. No socket/network call, installation,
credential/security change, WSL use or remote publication was performed.
