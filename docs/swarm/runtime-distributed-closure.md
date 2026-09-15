# Swarm 6 — Runtime + Distributed-State Closure

Status: **QUALIFIED**

Branch: `swarm/runtime-distributed-closure`

This lane integrates `SPEC-SWARM-RUNTIME-005` and
`SPEC-SWARM-DSM-004` without treating reliable transport as consensus.

## Acceptance results

| Criterion | Result | Retained proof |
|---|---|---|
| Identical adapter conformance | PASS | `local-deterministic` and `claude-sdk` run the same 12 checks in `tests/swarm/test_runtime005.py`. |
| Probe before routing | PASS | Fresh dispatch probe; mismatch and degraded engines fail closed. |
| RESIDUAL HITL authority | PASS | Provider approval/autonomy metadata is stripped or rejected. |
| Stale telemetry | PASS | Stale/absent values return `UNKNOWN` and suppress the value. |
| Async cancellation | PASS | Tasks and dedicated POSIX worker process groups terminate within a fixed budget; survivors produce a failed cancellation report. |
| Terminal observation flush | PASS | Close drains the buffer to an fsynced JSONL leg; stop or flush timeout fails closed. |
| Durable ack/cursor | PASS | Journal-backed outbox, ack log and monotonic replay cursor. |
| Replay idempotence | PASS | The globally unique `event_id` is the authoritative transition key; exact retries are duplicates and key collisions with different payloads fail closed. |
| Fencing at commit boundary | PASS (single process) | The lease lock is held from token validation through journal `fsync`; reassignment cannot race the append. |
| Restart provenance | PASS | Recovery reconstructs accepted transitions and hash-linked provenance from the journal alone. |

## Authority map

| State domain | Authoritative writer |
|---|---|
| `task.lease` | scheduler |
| `receipt.publication` | verifier |
| `integration.intent` | integrator |
| `task.terminal` | orchestrator |

Terminal decisions (`succeeded`, `failed`, `rejected`, `unknown`) are
absorbing and remain distinct.

## Exact cluster guarantees

The current implementation guarantees the following under crash-stop and
arbitrary duplicate, delayed, reordered or lost deliveries, provided one
journal-writing process owns the state directory and the filesystem honors
`fsync`:

- durable acknowledgement and reconnect/catch-up;
- at-least-once delivery with exactly-once accepted effect;
- deterministic replay and conflict projection;
- local-process fencing through the authoritative append;
- retained terminal decisions and provenance after restart.

The implementation does **not** claim:

- Raft, Paxos or Byzantine consensus;
- split-brain-safe distributed lease acquisition;
- active-active linearizable journal writes;
- synchronous replicated durability or automatic machine failover;
- linearizable remote reads during failover.

Those properties require a consensus-backed lease/log adapter and a real
multi-node deployment. Transport fault simulation and local durable storage
are not substitutes for that evidence.

## Evidence and reproduction

- Runtime artifact: `evidence/runtime/runtime005_evidence.json`
- Distributed artifact: `evidence/dsm/dsm-004-evidence.json`
- Focused closure tests: `tests/swarm/test_runtime_distributed_closure.py`
- Runtime regeneration: `python -m residual.runtime.evidence`
- Distributed regeneration: `python -m residual.dsm.evidence`

## Production-hardening decision

A production-hardening swarm may start for adapter work, observability,
crash/replay soak testing and a consensus-backed storage proof of concept.
The current layer must remain labeled **QUALIFIED**, not production-ready,
until real multi-process/multi-node contention, network partitions,
consensus-backed fencing and host-loss recovery are measured.
