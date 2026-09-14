"""High Availability and Disaster Recovery (SPEC-ENT-004).

Implements ENT4-R1 through ENT4-R8:

* ENT4-R1 active-active multi-region registry with automatic takeover
  (:mod:`residual.hadr.cluster`).
* ENT4-R2 receipt chain replication, synchronous in the primary region,
  asynchronous to secondaries, with 30 second lag alerting
  (:mod:`residual.hadr.replication`).
* ENT4-R3 mid-run failover resuming from the last verified receipt
  (:mod:`residual.hadr.failover`).
* ENT4-R4 RPO=0 receipts and RTO < 60s failover, measurable via the
  injected clock (:mod:`residual.hadr.clock`, :mod:`residual.hadr.replication`,
  :mod:`residual.hadr.failover`).
* ENT4-R5 encrypted daily backups with separately managed keys
  (:mod:`residual.hadr.backup`).
* ENT4-R6 quarterly restore drills with integrity verification and a
  restoration report (:mod:`residual.hadr.restore`).
* ENT4-R7 degraded mode with local operation and later sync/conflict
  resolution (:mod:`residual.hadr.degraded`).
* ENT4-R8 observation and receipting of failover, backup, and restore
  events (:mod:`residual.hadr.events`).
"""
from .backup import BackupManager, BackupRecord, KeyManager, LocalKeyManager, decrypt_backup
from .chain import ChainReceipt, ReceiptChain
from .clock import Clock, ManualClock, SystemClock
from .cluster import Station, StationRegistry, Takeover
from .degraded import ConflictResolution, DegradedStation
from .events import EventJournal, EventReceipt
from .failover import FailoverController, FailoverReport, RunState, TaskRecord
from .replication import (
    LagAlert,
    ReceiptReplicator,
    ReplicaNode,
    SimulatedTransport,
    MAX_SECONDARY_LAG_SECONDS,
)
from .restore import RestorationReport, RestoreDrill

__all__ = [
    "BackupManager",
    "BackupRecord",
    "ChainReceipt",
    "Clock",
    "ConflictResolution",
    "DegradedStation",
    "EventJournal",
    "EventReceipt",
    "FailoverController",
    "FailoverReport",
    "KeyManager",
    "LagAlert",
    "LocalKeyManager",
    "ManualClock",
    "MAX_SECONDARY_LAG_SECONDS",
    "ReceiptChain",
    "ReceiptReplicator",
    "ReplicaNode",
    "RestorationReport",
    "RestoreDrill",
    "RunState",
    "SimulatedTransport",
    "Station",
    "StationRegistry",
    "SystemClock",
    "Takeover",
    "TaskRecord",
    "decrypt_backup",
]
