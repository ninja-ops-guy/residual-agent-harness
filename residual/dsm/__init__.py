"""Distributed State Maturity (SPEC-SWARM-DSM-004).

Explicit distributed-state guarantees layered on the harness: authoritative
ownership domains, durable acknowledgements, monotonic-sequence catch-up,
idempotent delivery, fencing tokens, deterministic conflict resolution, and a
deterministic fault/recovery simulation harness.

See docs/swarm/dsm-004.md for the consensus boundary.
"""
from .ownership import DOMAINS, OwnershipRegistry, owner_of
from .journal import Journal, JournalError
from .lease import LeaseManager, FencingError
from .delivery import Outbox, Inbox, AckLog
from .store import DistributedStateStore, CrashError, TERMINAL_STATES
from .faults import Fault, FaultSchedule, FaultyChannel, simulate
from .recovery import run_recovery_suite

__all__ = [
    "DOMAINS", "OwnershipRegistry", "owner_of",
    "Journal", "JournalError",
    "LeaseManager", "FencingError",
    "Outbox", "Inbox", "AckLog",
    "DistributedStateStore", "CrashError", "TERMINAL_STATES",
    "Fault", "FaultSchedule", "FaultyChannel", "simulate",
    "run_recovery_suite",
]
