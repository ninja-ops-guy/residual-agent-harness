# Swarm 6 — Runtime + Distributed-State Closure

Status: **IMPLEMENTATION REPAIRED — CURRENT-MAIN REQUALIFICATION REQUIRED**

The three integration defects exposed by the closure regressions have been repaired on
PR #118. Against main `1cf4e46c0ace8e3cdc76147ad4c7dc6480a9fb34`, the required
Python 3.11/3.12/3.13 CI matrices completed successfully with the unchanged
`test_runtime_distributed_closure.py`, `test_runtime005.py`, and `test_dsm.py`
regressions enabled explicitly. Current main has since advanced, so those results do
not authorize merge until the exact current-main synthetic merge is requalified.

This status is deliberately narrower than production readiness. It establishes that
the focused local implementation defects are repaired under the branch CI contract; it
does not establish multi-node consensus, host-loss recovery, M4 namespace
qualification, production behavior, or soak reliability.

This integration note reconciles the independently landed `SPEC-SWARM-RUNTIME-005`
and `SPEC-SWARM-DSM-004` lanes without treating reliable transport as consensus.

## Acceptance results

| Criterion | Result | Retained proof |
|---|---|---|
| Identical adapter conformance | PASS | `local-deterministic` and `claude-sdk` run the same 12 checks in `tests/swarm/test_runtime005.py`. |
| Probe before routing | PASS | Fresh dispatch probe; mismatch and degraded engines fail closed. |
| RESIDUAL HITL authority | PASS | Provider approval/autonomy metadata is stripped or rejected. |
| Stale telemetry | PASS | Stale/absent values return `UNKNOWN` and suppress the value. |
| Async cancellation | PASS on repaired branch | Owned worker process groups receive bounded TERM→KILL cancellation; the closure regression verifies descendant cleanup and fails closed if survivors remain. |
| Terminal observation flush | PASS | Close drains the buffer to an fsynced JSONL leg; stop or flush timeout fails closed. |
| Durable ack/cursor | PASS | Journal-backed outbox, ack log and monotonic replay cursor. |
| Replay idempotence | PASS on repaired branch | Exact retries remain duplicates; a reused transition key with changed payload fails closed. |
| Fencing at commit boundary | PASS on repaired branch, single process | The in-process lease guard is held from validation through the authoritative journal append. This is not distributed consensus. |
| Restart provenance | PASS | Recovery reconstructs accepted transitions and hash-linked provenance from the journal alone. |

## Authority map

| State domain | Authoritative writer |
|---|---|
| `task.lease` | scheduler |
| `receipt.publication` | verifier |
| `integration.intent` | integrator |
| `task.terminal` | orchestrator |

Terminal decisions (`succeeded`, `failed`, `rejected`, `unknown`) are absorbing and remain distinct.

## Exact local guarantees

The repaired local contract covers the following under crash-stop and arbitrary
duplicate, delayed, reordered or lost deliveries, provided one journal-writing process
owns the state directory and the filesystem honors `fsync`:

- durable acknowledgement and reconnect/catch-up;
- at-least-once delivery with exactly-once accepted effect for the local journal;
- deterministic replay and conflict projection;
- local-process fencing through the authoritative append;
- retained terminal decisions and provenance after restart;
- owned process-group cancellation that reports failure rather than claiming cleanup when descendants survive.

These guarantees must be revalidated on the exact current-main synthetic merge before
this PR can be considered merge-ready.

The implementation does **not** claim:

- Raft, Paxos or Byzantine consensus;
- split-brain-safe distributed lease acquisition;
- active-active linearizable journal writes;
- synchronous replicated durability or automatic machine failover;
- linearizable remote reads during failover;
- production readiness or soak reliability;
- M4 namespace qualification.

Those properties require a consensus-backed lease/log adapter, capable-host
qualification, and real multi-node/deployment evidence. Transport fault simulation and
local durable storage are not substitutes for that evidence.

## Evidence and reproduction

- Runtime artifact: `evidence/runtime/runtime005_evidence.json`
- Distributed artifact: `evidence/dsm/dsm-004-evidence.json`
- Focused integration regressions: `tests/swarm/test_runtime_distributed_closure.py`
- Runtime regeneration: `python -m residual.runtime.evidence`
- Distributed regeneration: `python -m residual.dsm.evidence`
- Branch CI retained the focused regression outputs as `runtime-dsm-*` artifacts for each Python matrix.

## Production-hardening decision

First requalify the repaired branch against the exact current main without changing the
regressions or security controls. If that remains green, the local integration closure
can be merged after review. Production hardening still requires real process
contention, restart/recovery and elapsed soak at the selected candidate revision;
multi-node consensus, network partitions and host-loss recovery require their own
implementation and evidence.