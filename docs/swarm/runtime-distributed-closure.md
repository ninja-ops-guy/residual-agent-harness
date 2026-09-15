# Swarm 6 — Runtime + Distributed-State Closure

Status: **BLOCKED — integration regressions expose missing implementation**

At main `1cf4e46c0ace8e3cdc76147ad4c7dc6480a9fb34`, the combined
`test_runtime_distributed_closure.py`, `test_runtime005.py`, and `test_dsm.py`
suite has three failing regressions. The runtime has no `track_process` API;
lease reassignment is not locked through journal append; and a reused event
ID with a changed payload is incorrectly returned as a duplicate. The earlier
QUALIFIED label was premature. Existing component evidence cannot close these
integration failures or qualify production/soak behavior.

These pytest functions are now explicitly executed in the required CI `tests`
job on Python 3.11/3.12/3.13; unittest discovery alone did not collect them.
Keep their assertions and timing budgets intact while repairing the runtime
and DSM implementations. Retain failures in the job artifacts and obtain
independent review before changing this status.

This integration note reconciles the independently landed `SPEC-SWARM-RUNTIME-005`
and `SPEC-SWARM-DSM-004` lanes without treating reliable transport as consensus.

## Acceptance results

| Criterion | Result | Retained proof |
|---|---|---|
| Identical adapter conformance | PASS | `local-deterministic` and `claude-sdk` run the same 12 checks in `tests/swarm/test_runtime005.py`. |
| Probe before routing | PASS | Fresh dispatch probe; mismatch and degraded engines fail closed. |
| RESIDUAL HITL authority | PASS | Provider approval/autonomy metadata is stripped or rejected. |
| Stale telemetry | PASS | Stale/absent values return `UNKNOWN` and suppress the value. |
| Async cancellation | PARTIAL / BLOCKED | Async-task cancellation exists; dedicated process-group tracking required by the new regression is absent. |
| Terminal observation flush | PASS | Close drains the buffer to an fsynced JSONL leg; stop or flush timeout fails closed. |
| Durable ack/cursor | PASS | Journal-backed outbox, ack log and monotonic replay cursor. |
| Replay idempotence | PARTIAL / BLOCKED | Exact retry after recovery passes; changed-payload key collisions are not rejected. |
| Fencing at commit boundary | BLOCKED | Reassignment succeeds during authoritative append; the required shared lock is absent. |
| Restart provenance | PASS | Recovery reconstructs accepted transitions and hash-linked provenance from the journal alone. |

## Authority map

| State domain | Authoritative writer |
|---|---|
| `task.lease` | scheduler |
| `receipt.publication` | verifier |
| `integration.intent` | integrator |
| `task.terminal` | orchestrator |

Terminal decisions (`succeeded`, `failed`, `rejected`, `unknown`) are absorbing and remain distinct.

## Exact cluster guarantees

The intended local contract covers the following under crash-stop and arbitrary
duplicate, delayed, reordered or lost deliveries, provided one journal-writing process
owns the state directory and the filesystem honors `fsync`. This combined
contract remains unqualified until the three failures above are repaired:

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

Those properties require a consensus-backed lease/log adapter and a real multi-node
deployment. Transport fault simulation and local durable storage are not substitutes
for that evidence.

## Evidence and reproduction

- Runtime artifact: `evidence/runtime/runtime005_evidence.json`
- Distributed artifact: `evidence/dsm/dsm-004-evidence.json`
- Focused integration regressions: `tests/swarm/test_runtime_distributed_closure.py`
- Runtime regeneration: `python -m residual.runtime.evidence`
- Distributed regeneration: `python -m residual.dsm.evidence`

## Production-hardening decision

Repair the three missing local guarantees and independently verify the required
CI regressions first. Then qualify real process contention, restart/recovery and
elapsed soak at the selected candidate revision. Multi-node consensus, network
partitions and host-loss recovery require their own implementation and evidence;
they are not established by these local tests.
