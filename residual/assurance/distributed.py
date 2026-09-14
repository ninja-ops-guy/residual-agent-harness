from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ReplicatedEntry:
    run_id: str
    index: int
    payload: Any
    idempotency_key: str


@runtime_checkable
class AuthoritativeLog(Protocol):
    """CP-oriented replicated log contract for receipts, observations and queue state.

    Implementations may use Raft/etcd/Consul/etc.; Residual depends on the
    consistency properties, not a bespoke consensus implementation.
    """

    def append(self, run_id: str, payload: Any, idempotency_key: str) -> ReplicatedEntry: ...
    def read_from(self, run_id: str, index: int) -> tuple[ReplicatedEntry, ...]: ...
    def snapshot(self, run_id: str) -> bytes: ...
    def has_quorum(self) -> bool: ...


class QuorumUnavailable(RuntimeError):
    pass


def require_quorum(log: AuthoritativeLog) -> None:
    if not log.has_quorum():
        raise QuorumUnavailable("authoritative writes require majority quorum")
