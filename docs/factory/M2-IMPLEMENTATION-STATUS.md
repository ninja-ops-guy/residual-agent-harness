# M2 implementation status: executable brokered-worker slice

Source: `M2_M3_M4_SPECS.md` v1.0.0, 2026-09-13, SHA-256
`fd96b9c80ec89f8ebf44ab1a787524b6c21f91dff3a80eae4be879d6bf58ad3d`.
The original foundation was based on `86d9f88958a5fdf87417ee3ebc90fbe366496815`.
This continuation preserves its WorkerContract and existing ExecutionPlan binding;
it does not change another stream's plan, engine, Station, or integration modules.

**M2 has real execution now, but is not wholly complete. M3, M4 and EVAL are not
implemented by this PR. The IDE remains deferred.**

See [execution guide and limitations](M2-EXECUTION.md) and the real scripted demo
at `examples/factory/brokered_worker_demo.py`.

## Requirement mapping

| Requirement | Implemented in this slice | Remaining gate |
|---|---|---|
| M2-R1 | Immutable/deep-copied contract, exact plan/approval binding, durable pre-start SQLite observation | Remote/operator identity authentication beyond trusted local caller |
| M2-R2 | Kernel seccomp denial of direct file I/O, descriptor-rooted broker, no-follow/link/special-file checks | General-purpose container/shell engines; independent sandbox audit |
| M2-R3 | Non-bypassable narrow broker tool surface; denied syscall/tool kills worker | Additional governed tool backends |
| M2-R4 | Tool/write counters, token reservation helpers, hard address-space/CPU limits, independent deadline watchdog and 1 Hz RSS | Real provider token-meter adapter; no LLM calls in this lane |
| M2-R5 | Durable contract-bound broker violations and termination observations | Exact native syscall/path attribution remains UNKNOWN for SIGSYS |
| M2-R6 | Fresh detached worktrees, per-attempt private candidate objects, rejection cleanup, explicit retention reaper | Station disposition/accepted-receipt merge depends on M3/M4 |
| M2-R7 | Kernel or supervisor SIGKILL, process wait/reap, terminal attempts, durable monotone generation fencing | Automatic host-crash recovery and distributed reassignment |
| M2-R8 | Durable attempt/PID/state records and bounded parallel independent-task execution | Full SwarmState, receipt-backed completion and dependency readiness |
| M2-R9 | Fixed-capacity parallel primitive only | Adaptive resizing, hysteresis and scheduler policy |
| M2-R10 | Separate worker processes/worktrees, no inherited credentials/host FDs, denied networking/process creation | Evidence Bus inter-swarm communication and full swarm-role lifecycle |

## Explicit non-claims

Successful worker exit produces `CANDIDATE`, not acceptance. No verification
result, Station signature, speedup, live model quality, cost reduction or production
readiness is inferred. Dependent tasks fail closed until receipt-backed admission
exists. Candidate objects are not inserted into the source repository's object
store. Local FrozenPlan integrity is not authenticated remote human approval.
No second requirement DAG is defined.

## Test evidence

The original 51 contract tests remain. New journal, filesystem and live-process
tests cover real kernel file/network/fork/exec/thread/ptrace denial, denied broker
paths/tools, stale generation, durable lease revocation, cancellation, memory and
deadline limits, missing-seccomp fail-closed behavior, replay rejection, bounded
output, two isolated swarms, private candidate objects, retention, and a watchdog
kill while the audit writer is deliberately blocked. The execution workflow
requires the actual Linux backend and archives exact source plus results.

Local validation on Linux x86_64 / Python 3.13.5: **100 focused tests and
428 full-repository tests passed, with no failures or skips**. This includes actual
seccomp worker execution, not only mocked enforcement. Compile checks and the
scripted demo passed. These are local results; new exact-head CI results are
reported separately. No real model or performance benchmark was run.
