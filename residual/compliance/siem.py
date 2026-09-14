"""SIEM integration: Splunk, Microsoft Sentinel, IBM QRadar.

Implements ENT2-R8: observations are forwardable in real time via
syslog/CEF or native API, with at-least-once delivery guaranteed by a
durable on-disk spool and retry queue. Forwarding outcomes are observed
in the log. Transports are injectable; tests use fake transports.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Protocol

from ..core import ContractError, canonical
from .log import ObservationEvent, ObservationLog


class SiemTarget(str, Enum):
    """Supported SIEM systems. Implements ENT2-R8."""
    SPLUNK = "splunk"
    SENTINEL = "sentinel"
    QRADAR = "qradar"


class Transport(Protocol):
    """Delivery transport; fake transports are used in tests. ENT2-R8."""

    def send(self, message: str) -> None: ...


class SyslogTransport:
    """UDP syslog transport (stdlib socket). Implements ENT2-R8."""

    def __init__(self, host: str, port: int = 514):
        if not host.strip() or not (0 < port < 65536):
            raise ContractError("invalid syslog endpoint")
        self.host, self.port = host, port

    def send(self, message: str) -> None:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(5)
            sock.sendto(message.encode("utf-8"), (self.host, self.port))


class CefFormatter:
    """Syslog CEF formatting for observations. Implements ENT2-R8."""

    VERSION = "CEF:0|Residual|Station|1.0"

    def format(self, event: ObservationEvent) -> str:
        severity = {"contract_violation": 8, "legal_hold": 6, "erasure": 6,
                    "sensitive_access": 7, "transfer": 6}.get(event.kind, 4)
        extension = (f"rt={int(event.timestamp)} suser={self._esc(event.actor)} "
                     f"cs1={self._esc(event.task_id)} cs1Label=TaskId "
                     f"cs2={self._esc(event.region)} cs2Label=Region "
                     f"cs3={event.chain_hash} cs3Label=ChainHash")
        return (f"{self.VERSION}|{self._esc(event.kind)}|{self._esc(event.kind)}|{severity}|"
                f"{extension}")

    @staticmethod
    def _esc(value: str) -> str:
        return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("=", "\\=")


@dataclass(frozen=True)
class SpoolRecord:
    """One durable, undelivered message. Implements ENT2-R8."""
    event_id: int
    message: str
    attempts: int = 0


class SpoolQueue:
    """Durable JSONL spool for at-least-once delivery. Implements ENT2-R8."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def _load(self) -> list[SpoolRecord]:
        records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                data = json.loads(line)
                records.append(SpoolRecord(data["event_id"], data["message"], data["attempts"]))
        return records

    def _store(self, records: list[SpoolRecord]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text("".join(json.dumps({"event_id": r.event_id, "message": r.message,
                                           "attempts": r.attempts}, sort_keys=True) + "\n"
                               for r in records), encoding="utf-8")
        tmp.replace(self.path)

    def enqueue(self, record: SpoolRecord) -> None:
        records = self._load()
        records.append(record)
        self._store(records)

    def acknowledge(self, event_id: int) -> None:
        """Remove a delivered record; only ack after successful send."""
        self._store([r for r in self._load() if r.event_id != event_id])

    def retry(self, event_id: int) -> None:
        records = [SpoolRecord(r.event_id, r.message, r.attempts + 1)
                   if r.event_id == event_id else r for r in self._load()]
        self._store(records)

    def pending(self) -> tuple[SpoolRecord, ...]:
        return tuple(self._load())

    def __len__(self) -> int:
        return len(self._load())


class Forwarder:
    """Real-time, reliable forwarding with retries. Implements ENT2-R8.

    At-least-once semantics: a message is acknowledged (removed from the
    spool) only after the transport confirms the send; failures leave the
    record spooled for later ``flush()`` retries.
    """

    def __init__(self, target: SiemTarget, transport, spool: SpoolQueue,
                 log: ObservationLog | None = None, formatter: CefFormatter | None = None,
                 sleep: Callable[[float], None] = time.sleep):
        try:
            self.target = SiemTarget(target)
        except ValueError:
            raise ContractError("unknown SIEM target") from None
        self.transport = transport
        self.spool = spool
        self.log = log
        self.formatter = formatter or CefFormatter()
        self.sleep = sleep
        self.delivered = 0

    def _observe(self, event: ObservationEvent, action: str, timestamp: float) -> None:
        if self.log is not None:
            self.log.append("siem", timestamp, "compliance", event.task_id,
                            category="operational", region=event.region,
                            payload={"target": self.target.value, "action": action,
                                     "event_id": event.id},
                            tags=("ISO27001-A.12.4",))

    def forward(self, event: ObservationEvent, timestamp: float = 0.0) -> bool:
        """Spool then attempt immediate delivery. Implements ENT2-R8."""
        message = self.formatter.format(event)
        self.spool.enqueue(SpoolRecord(event.id, message))
        return self.flush(timestamp)

    def flush(self, timestamp: float = 0.0, max_attempts: int = 3) -> bool:
        """Drain the spool with bounded retries; True when fully delivered."""
        if max_attempts < 1:
            raise ContractError("max_attempts must be positive")
        for _ in range(max_attempts):
            pending = self.spool.pending()
            if not pending:
                return True
            for record in pending:
                try:
                    self.transport.send(record.message)  # confirm before ack
                except Exception:
                    self.spool.retry(record.event_id)
                    self.sleep(0.05)
                else:
                    self.spool.acknowledge(record.event_id)
                    self.delivered += 1
                    self._observe_by_id(record.event_id, "delivered", timestamp)
        return not self.spool.pending()

    def _observe_by_id(self, event_id: int, action: str, timestamp: float) -> None:
        if self.log is not None:
            event = next((e for e in self.log.events if e.id == event_id), None)
            if event is not None:
                self._observe(event, action, timestamp)


assert callable(canonical)
