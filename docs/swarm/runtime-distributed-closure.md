# Swarm 6 — Runtime + Distributed-State Closure

Status: **REVIEW REPAIRS PUBLISHED — FRESH EXACT-HEAD REQUALIFICATION REQUIRED**

PR #118 was refreshed onto accepted M4 main
`22a5bae54ec12987ffd7a90d881fb4533c9b4b97`. Candidate `8c704d3d...`
completed the applicable GitHub workflows successfully, including the required
Python 3.11/3.12/3.13 matrices and the focused runtime/DSM regressions. That
result is retained as evidence for that exact candidate only.

Independent review then identified two scope/safety gaps that are repaired in a
newer candidate and therefore require fresh exact-head CI:

1. **Same-process DSM multi-instance admission.** The earlier store lock was
   per `DistributedStateStore` instance while `Journal` cached its head and
   sequence. Two stores pre-opened on the same path could therefore race or
   append from stale journal state. Stores targeting the same resolved journal
   path now share one process-local admission lock and refresh/verify durable
   journal state before admission and projection. Regressions cover both a
   pre-opened stale store and concurrent sibling-store writers.
2. **Process-group signal authority.** A raw caller-supplied PGID is no longer
   accepted as sufficient ownership. Group cancellation requires the tracked
   process to lead a dedicated POSIX session/process group at registration
   (`PID == PGID == SID`). This prevents granting signal authority over an
   arbitrary existing group. The runtime still does not claim cgroup-grade or
   cross-host stable process identity.

This status remains deliberately narrower than production readiness. The
component implementation and CI evidence do not establish multi-node consensus,
host-loss recovery, production worker wiring, production behavior, or elapsed
soak reliability.

## Acceptance results

| Criterion | Result | Retained proof |
|---|---|---|
| Identical adapter conformance | PASS on prior exact candidate; fresh head pending | `local-deterministic` and `claude-sdk` run the same 12 checks in `tests/swarm/test_runtime005.py`. |
| Probe before routing | PASS on prior exact candidate; fresh head pending | Fresh dispatch probe; mismatch and degraded engines fail closed. |
| RESIDUAL HITL authority | PASS on prior exact candidate; fresh head pending | Provider approval/autonomy metadata is stripped or rejected. |
| Stale telemetry | PASS on prior exact candidate; fresh head pending | Stale/absent values return `UNKNOWN` and suppress the value. |
| Async task cancellation | PASS on prior exact candidate; fresh head pending | Bounded cancellation and fail-closed survivor reporting. |
| POSIX process-group cancellation primitive | REVIEW REPAIRED; fresh head pending | Dedicated-session ownership validation plus real descendant regression. This is not yet production worker wiring. |
| Terminal observation flush | PASS on prior exact candidate; fresh head pending | Close drains the buffer to an fsynced JSONL leg; stop or flush timeout fails closed. |
| Durable ack/cursor | PASS on prior exact candidate; fresh head pending | Journal-backed outbox, ack log and monotonic replay cursor. |
| Replay idempotence | REVIEW REPAIRED; fresh head pending | Exact retries remain duplicates; reused transition keys with changed payload fail closed, including pre-opened sibling stores. |
| Same-process journal serialization | REVIEW REPAIRED; fresh head pending | Shared resolved-path lock + durable `Journal.refresh()`; concurrent sibling-store regression. |
| Fencing at commit boundary | PASS for one shared `LeaseManager`; fresh head pending | Lease guard is held from validation through authoritative append. Separate lease managers are not a common fencing authority. |
| Restart provenance | PASS on prior exact candidate; fresh head pending | Recovery reconstructs accepted transitions and hash-linked provenance from the journal alone. |

## Authority map

| State domain | Authoritative writer |
|---|---|
| `task.lease` | scheduler |
| `receipt.publication` | verifier |
| `integration.intent` | integrator |
| `task.terminal` | orchestrator |

Terminal decisions (`succeeded`, `failed`, `rejected`, `unknown`) are absorbing
and remain distinct.

## Exact local guarantees

After the new review repairs requalify, the intended local contract is limited
to one Python process owning the journal state directory, with all
`DistributedStateStore` instances using the same implementation and the
filesystem honoring `fsync`:

- same-process stores for the same resolved journal path serialize admission and
  refresh durable state before dedupe/projection;
- durable acknowledgement and reconnect/catch-up;
- at-least-once delivery with exactly-once accepted effect for the local journal;
- deterministic replay and conflict projection;
- local lease fencing through the authoritative append **when callers share the
  same `LeaseManager`**;
- retained terminal decisions and provenance after restart;
- async task cancellation with explicit fail-closed survivor reporting;
- a POSIX dedicated-session process-group cancellation primitive for callers
  that explicitly register the group.

The implementation does **not** claim:

- Raft, Paxos or Byzantine consensus;
- split-brain-safe distributed lease acquisition;
- active-active or cross-process linearizable journal writes;
- synchronous replicated durability or automatic machine failover;
- linearizable remote reads during failover;
- durable/recoverable in-memory lease state;
- production worker-process registration or end-to-end process cancellation;
- cgroup-grade stable process ownership after arbitrary lifecycle/reuse races;
- production readiness or soak reliability;
- additional M4 namespace qualification from this lane.

Those properties require stronger process ownership and/or a consensus-backed
lease/log adapter plus real deployment evidence. Transport fault simulation and
local durable storage are not substitutes for that evidence.

## Evidence and reproduction

- Runtime artifact: `evidence/runtime/runtime005_evidence.json`
- Distributed artifact: `evidence/dsm/dsm-004-evidence.json`
- Focused integration regressions: `tests/swarm/test_runtime_distributed_closure.py`
- Process ownership regressions: `tests/swarm/test_cancellation_ownership.py`
- Runtime regeneration: `python -m residual.runtime.evidence`
- Distributed regeneration: `python -m residual.dsm.evidence`
- Branch CI retains focused regression outputs as `runtime-dsm-*` artifacts for
  each Python matrix.

## Production-hardening decision

Fresh exact-head CI must pass without weakening assertions, security controls,
or frozen research procedures. If the review-repaired candidate remains green,
this PR can be reconsidered for local integration. Production hardening remains
separate: production worker wiring, real process contention, restart/recovery,
blank-environment qualification and elapsed soak must be demonstrated at the
selected accepted revision. Multi-node consensus, network partitions and
host-loss recovery require their own implementation and evidence.
