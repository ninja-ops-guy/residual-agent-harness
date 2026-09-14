# M2 implementation status: contract foundation only

## Scope and provenance

This is the first implementation slice of the user-supplied
`M2_M3_M4_SPECS.md`, version 1.0.0, dated 2026-09-13 (609 lines).
Source SHA-256: `fd96b9c80ec89f8ebf44ab1a787524b6c21f91dff3a80eae4be879d6bf58ad3d`.
The development base was main commit
`86d9f88958a5fdf87417ee3ebc90fbe366496815`.

**M2 is incomplete. M3, M4 and EVAL are not implemented by this change.**
The IDE remains deferred. No factory-run command or engine execution is enabled.

## Implemented

`residual/factory/worker_contract.py` adds a frozen, defensively copied
`WorkerContract` with schema validation and a canonical contract hash. It binds
the existing `ExecutionPlan.graph_hash`, requirement IDs, task dependencies,
swarm, acceptance criteria, full input Git object ID, and worker/attempt/lease
identity. Set-valued selectors are sorted before hashing. No second DAG model
or scheduler is introduced; the public ExecutionPlan protocol is consumed.

Contract plan validation checks the existing model's canonical payload and rejects
missing acceptance criteria, altered task bindings, and graph-hash mismatches.
This is integrity checking, **not authentication of a human approval**. The
caller must separately validate the frozen plan and authenticated authorization.

`AttemptGuard` supplies thread-safe mediated-operation accounting: contract
observation before start, denied-tool/path violations, token reservations and
settlement, duplicate-usage rejection, write/tool counters, memory/deadline
checks, stale lease detection, cancellation, and terminal-attempt behavior.
Unknown token usage is not treated as zero. Clock and memory-meter failures
fail closed. A finished attempt is only `CANDIDATE`, never Station-accepted.

## What these helpers do not enforce

Path decisions are lexical. They neither inspect symlinks nor stop filesystem
syscalls. Exact paths and explicit directory prefixes ending `/` are supported;
globs are rejected. Forbidden selectors take precedence; `.git` components are
always denied. These decisions need an OS-enforced sandbox and a race-safe file
broker before any untrusted engine may execute.

The guard does not create worktrees, start processes, sample RSS at 1 Hz, run an
independent watchdog, issue or expire leases, or integrate with an engine tool
broker. Its stop callback is host-supplied. A returned callback is **not proof
that a process group stopped**. A terminal Python state does not establish an OS
termination guarantee. Atomic authorization/dispatch and fencing after a
concurrent cancellation remain executor responsibilities.

The observation callback must acknowledge durable persistence before returning.
The tests use an in-memory list, not the production observation layer. Durable
journal/observation integration and restart recovery are still required. Callback
failures prevent further use of the attempt and request stopping; failed audit
writes cannot magically become persisted observations.

Token reservation requires a conservative bound for the complete provider call.
An upstream overrun may already incur usage before being reported; detection is
not a provider-independent hard billing guarantee. No provider calls run here.

## Requirement mapping

| Requirement | Current scope | Remaining gate |
|---|---|---|
| M2-R1 | Frozen contract and pre-start observation protocol | Durable observation and authenticated launch binding |
| M2-R2 | Lexical read/write/deny policy | OS isolation, syscall enforcement, symlink/race tests |
| M2-R3 | Mediated tool allowlist and terminal violations | Non-bypassable engine/tool broker |
| M2-R4 | Accounting, reservations, explicit deadline/RSS checks | Independent watchdog, 1 Hz RSS sampling, OS process limits |
| M2-R5 | Structured violation event with bound identities | Durable observation adapter and runtime delivery |
| M2-R6 | Full input commit and workspace identity | Worktree creation, quarantine, integration and cleanup |
| M2-R7 | Terminal attempt state and stop-hook invocation | Verified process-group termination and new-attempt reassignment |
| M2-R8 | Per-attempt counters and state | SwarmState, dependency readiness and capacity aggregation |
| M2-R9 | Not implemented | Resize policy, hysteresis and coordinator |
| M2-R10 | Identity fields only | Separate workers/workspaces, memory isolation and Evidence Bus |

## Validation performed

51 newly added unit tests passed on Python 3.13.5; zero failures or skips.
`compileall` passed for the new module and its tests. These were standalone
module tests against a public-plan-protocol fixture, not the full repository
regression suite or live ExecutionPlan/Station integration tests.

The local Git clone failed because the execution environment could not resolve
`github.com`. GitHub connector reads and writes worked. Docker and bubblewrap
were absent from the local environment. No OS isolation test was performed,
no live model was called, and no speedup, cost-saving, or production-readiness
claim is made. Repository-wide CI is a separate gate, not inferred from these
51 unit tests. Do not merge as a completed M2 implementation.

From a complete repository checkout:

```sh
python -m unittest discover -s tests -p 'test_factory_worker_contract.py' -v
python -m unittest discover -s tests -v
```

## Next dependency-ordered work

Finish the M2 launch boundary, OS backend, worktree manager, watchdog, durable
observations and worker lifecycle before enabling Factory execution. Then add
M3 Station-issued signed receipts and quarantine, M4 deterministic integration
and scheduling, and finally EVAL. Each phase needs its own conformance evidence.
