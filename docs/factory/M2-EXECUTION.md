# M2: brokered Linux worker execution

**Status: executable experimental M2 slice, not completed M2/M3/M4.**
The IDE is deferred. This backend executes independent, root-DAG tasks using
brokered Python controllers. It does not execute arbitrary shell/SDK agents,
call models, accept dependencies, issue receipts, or merge candidates.

## Run the real scripted demo

From the repository root, with Python 3.11+, Git, Linux and the system
`libseccomp.so.2` installed, and pidfd process-control support:

```sh
python examples/factory/brokered_worker_demo.py --output /tmp/residual-m2-demo
```

Choose a new output directory. The demo creates a fixture repository, approved
ExecutionPlan, WorkerContract, SQLite observation journal and a real sandboxed
worker. It reads only `numbers.json`, writes `total.txt` in its own worktree and
returns an **UNTRUSTED_CANDIDATE** commit/tree. `result.json` records the result;
`observations.jsonl` uses the existing observation_layer schema and hash chain.
This is evidence about orchestration and enforcement, **not model quality,
speedup, token savings or Station acceptance**. The declared `sum-check` remains
an acceptance obligation, not a verifier executed by this M2 backend.

For an existing approved plan and explicit contract, the opt-in CLI is:

```sh
python -m residual.factory.runtime \
  --repo /srv/projects/example \
  --runtime-root /srv/residual/work \
  --journal /srv/residual/state/run.db --run-id example-run \
  --plan plan.json --approval approval.json --contract contract.json \
  --source worker.py --allow-local-worker-code
```

`workspace_root` in the contract must equal
`runtime_root/swarm_id/attempt_id`. The runtime root and source repository must
be disjoint. Their runtime directories must be operator-owned, resolved paths
and not writable by others. A worker needs an address-space budget of at least
64 MiB for CPython startup. Success exit code 0 means **candidate produced**, not
project completion or approval. Unsupported platforms, unavailable seccomp,
cloud-only placement, stale approvals and dependent tasks fail closed. There is
no unsandboxed fallback.

## Execution boundary

1. Snapshot and validate the existing ExecutionPlan; bind the exact FrozenPlan
   and WorkerContract. No alternate DAG model is introduced. Claim unique worker,
   attempt, workspace and lease IDs with a monotonically increasing generation.
2. Create a detached Git worktree at the exact input commit. Commit the full
   contract to a FULL-synchronous SQLite observation transaction before Popen.
3. Start a clean CPython process with `-I -S`, no inherited provider credentials
   or non-stdio descriptors, a separate process group, core dumps disabled and
   hard resource limits. When launched by root, drop to uid/gid 65534.
4. Set no-new-privileges and parent-death SIGKILL. Load a deny-by-default seccomp
   filter. **Only after a successful handshake is worker source sent.** Direct
   file access, networking, exec, process/thread creation, tracing, privilege
   changes and descriptor creation are not allowed. A denied syscall kills the
   process rather than returning a catchable permission error.
5. Permit project operations only through framed `read_file`, `write_file`, and
   `delete_file` requests. The parent checks tool and path permissions, counters,
   lease, deadline, framing and request sequence. Each path component is opened
   relative to a held directory descriptor with O_NOFOLLOW. Symlinks, hard links,
   devices, FIFOs, Git metadata, traversal and oversized files are rejected.
6. An independent parent watchdog checks deadlines at a 20 ms polling interval,
   RSS at 1 Hz and durable revocation periodically. It kills/reaps the process
   through its pidfd (rather than a potentially reused PID) without acquiring the observation writer's lock. A blocked audit callback
   cannot keep the worker alive. Broker I/O is re-fenced after audit acknowledgement;
   cancellation is serialized against final candidate publication. A worker is
   the sole process in its fresh group because fork/clone/exec are denied.
7. Require protocol completion, clean process exit, current lease, settled usage
   and a durable terminal record. Capture only broker-touched output paths with
   Git clean filters and hooks disabled. No ref is moved and no merge occurs.

The supported worker API is deliberately narrow:

```python
text = read_file('declared-input.txt')
write_file('declared-output.txt', text.upper())
delete_file('declared-obsolete.txt')
```

An output must also be listed in `inputs` to be readable by a worker. Only UTF-8
text files up to 1 MiB per operation are supported. Controller source is capped
at 256 KiB; protocol frames at 2 MiB and total stdout/stderr at 8 MiB per attempt.
Stdout is a protocol channel, not a general logging sink. Untrusted stderr is
bounded and discarded, not copied into trusted observations. Worker code may
perform computation and use already-loaded modules; imports requiring filesystem
access fail. Shell access, installing dependencies and model SDK calls are **not**
supported in this profile. Token usage is zero because this engine makes no LLM
calls, not because missing provider usage is being estimated as zero.

## Candidate quarantine and retention

New candidate blobs/trees/commits are written to a private, per-attempt Git
object directory, **not the source repository's object store or an accepted
Evidence Bus store**. The candidate uses the original objects as read-only
alternates. Output commit/tree IDs and SHA-256 content hashes are recorded;
deletions have `null` tombstones. A downstream consumer must not treat these
references as Station receipts.

Rejected, violated and cancelled attempts have their worktrees removed. Successful
candidates remain quarantined for Station verification. `runtime.purge(contract)`
removes an exact candidate's worktree and private Git objects while retaining its
observations. `runtime.purge_expired()` applies a configurable retention interval,
default 3600 seconds. The host must invoke this reaper: **there is no hidden
background retention daemon**. Candidate publication prevents a new attempt for
the same task until disposition; terminal attempts require fresh identities and
a higher durable lease generation before reassignment.

`run_many(..., capacity=N)` executes independent tasks concurrently with separate
processes/worktrees, including tasks assigned to distinct swarms. This is a bounded
**fixed-capacity** primitive, not the adaptive scheduler or full swarm-role model.
No cross-swarm handoff or raw-output dependency admission is provided.

## Trust and reproducibility limits

The operator, supervisor process, CPython installation, bootstrap, system
libseccomp, Linux kernel, Git executable and **local repository Git configuration**
are trusted. Do not point the runtime at attacker-controlled Git configuration or
filters. The descriptor broker and restrictive syscall policy reduce the worker's
access; this is not a general-purpose container, independent security audit,
VM isolation or multi-tenant hosting certification. Kernel denial tests exercise
real syscalls rather than mocking an isolation flag.

FrozenPlan binding here is a local operator authorization record. It is not a
cryptographic authentication system or an enterprise identity-provider login.
The SQLite hash chain detects changes against a trusted checkpoint; it is not
Station signing, consensus, or protection from an administrator who can rewrite
both the database and its checkpoints. Durable revocation and generation fencing
are implemented. Automatic orphan recovery/lease-expiry scheduling after a host
crash is not. Active leases fail closed on restart until operator reconciliation.

The watchdog's intervals are configured polling bounds, not hard real-time latency
guarantees. Hard RLIMIT_AS is more conservative than RSS and can fail a worker
before the RSS ceiling; instantaneous RSS overshoot between samples is not claimed
impossible. A raw SIGSYS observation records the known profile/signal but leaves
the exact offending syscall/path **unknown**, rather than inventing attribution.
Disk failure may prevent an audit write; execution and candidate publication fail
closed, but the code does not claim an unavailable disk persisted anything.

Candidate commit metadata is fixed, but the message binds the contract hash, which
includes attempt/workspace identity. No M4 claim that different attempts yield the
same commit is made. Verifiers, signed receipts and deterministic project-level
integration remain the next trust boundary.

## Validation

```sh
RESIDUAL_REQUIRE_SECCOMP=1 python -m unittest \
  tests.test_factory_worker_contract tests.test_factory_runtime -v
python -m compileall -q residual/factory
```

The environment variable makes kernel-backend unavailability a test failure in
Linux CI. Without it, unavailable Linux isolation is an explicit test skip, never
a simulated pass. See the execution workflow for exact-source and test artifacts.

The syscall policy follows the Linux and libseccomp interfaces:
- [Linux seccomp filter documentation](https://docs.kernel.org/userspace-api/seccomp_filter.html)
- [libseccomp initialization and kill actions](https://libseccomp.readthedocs.io/en/latest/man/man3/seccomp_init.3/)
- [libseccomp rule API](https://libseccomp.readthedocs.io/en/latest/man/man3/seccomp_rule_add.3/)
