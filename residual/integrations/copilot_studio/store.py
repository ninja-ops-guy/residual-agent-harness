"""Durable mission ownership and idempotency state for Copilot Studio."""
from __future__ import annotations

import os
import sqlite3
import stat
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from ...core import ContractError


@dataclass(frozen=True)
class MissionRecord:
    tenant_id: str
    object_id: str
    department: str
    request_id: str
    request_hash: str
    mission_id: str
    template_id: str

    def __post_init__(self):
        for name in (
            "tenant_id", "object_id", "department", "request_id",
            "request_hash", "mission_id", "template_id",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise ContractError(f"{name} is required")


@runtime_checkable
class MissionStore(Protocol):
    def get_by_request(self, tenant_id: str, object_id: str,
                       request_id: str) -> MissionRecord | None: ...
    def get_by_mission(self, mission_id: str) -> MissionRecord | None: ...
    def claim(self, record: MissionRecord) -> tuple[MissionRecord, bool]: ...


class InMemoryMissionStore:
    def __init__(self):
        self._by_request: dict[tuple[str, str, str], MissionRecord] = {}
        self._by_mission: dict[str, MissionRecord] = {}
        self._lock = threading.RLock()

    def get_by_request(self, tenant_id: str, object_id: str,
                       request_id: str) -> MissionRecord | None:
        with self._lock:
            return self._by_request.get((tenant_id, object_id, request_id))

    def get_by_mission(self, mission_id: str) -> MissionRecord | None:
        with self._lock:
            return self._by_mission.get(mission_id)

    def claim(self, record: MissionRecord) -> tuple[MissionRecord, bool]:
        if not isinstance(record, MissionRecord):
            raise ContractError("mission store requires a MissionRecord")
        key = (record.tenant_id, record.object_id, record.request_id)
        with self._lock:
            prior = self._by_request.get(key)
            if prior is not None:
                if prior != record:
                    raise ContractError("mission idempotency record conflict")
                return prior, False
            mission_prior = self._by_mission.get(record.mission_id)
            if mission_prior is not None:
                if mission_prior != record:
                    raise ContractError("mission id collision")
                return mission_prior, False
            self._by_request[key] = record
            self._by_mission[record.mission_id] = record
            return record, True


class SQLiteMissionStore:
    """Reference durable store.

    The database contains authorization metadata and hashes only; bearer tokens,
    provider credentials, prompts, tool output, and evidence bodies are never
    stored here.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path).absolute()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            if self.path.resolve(strict=False) != self.path:
                raise ContractError("mission store path must not traverse symlinks")
            flags = os.O_CREAT | os.O_RDWR
            flags |= getattr(os, "O_CLOEXEC", 0)
            flags |= getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(self.path, flags, 0o600)
            try:
                info = os.fstat(fd)
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_nlink != 1
                    or info.st_uid != os.geteuid()
                    or info.st_mode & 0o077
                ):
                    raise ContractError(
                        "mission store must be a private regular file owned by the service"
                    )
            finally:
                os.close(fd)
        self._lock = threading.RLock()
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS copilot_missions (
                    mission_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    department TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    template_id TEXT NOT NULL,
                    UNIQUE (tenant_id, object_id, request_id)
                )
                """
            )

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5.0)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _record(row: sqlite3.Row | None) -> MissionRecord | None:
        if row is None:
            return None
        return MissionRecord(
            tenant_id=row["tenant_id"],
            object_id=row["object_id"],
            department=row["department"],
            request_id=row["request_id"],
            request_hash=row["request_hash"],
            mission_id=row["mission_id"],
            template_id=row["template_id"],
        )

    def get_by_request(self, tenant_id: str, object_id: str,
                       request_id: str) -> MissionRecord | None:
        with self._connect() as db:
            row = db.execute(
                """
                SELECT * FROM copilot_missions
                WHERE tenant_id=? AND object_id=? AND request_id=?
                """,
                (tenant_id, object_id, request_id),
            ).fetchone()
        return self._record(row)

    def get_by_mission(self, mission_id: str) -> MissionRecord | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM copilot_missions WHERE mission_id=?",
                (mission_id,),
            ).fetchone()
        return self._record(row)

    def claim(self, record: MissionRecord) -> tuple[MissionRecord, bool]:
        if not isinstance(record, MissionRecord):
            raise ContractError("mission store requires a MissionRecord")
        with self._lock:
            db = self._connect()
            try:
                db.execute("BEGIN IMMEDIATE")
                prior = db.execute(
                    """
                    SELECT * FROM copilot_missions
                    WHERE tenant_id=? AND object_id=? AND request_id=?
                    """,
                    (record.tenant_id, record.object_id, record.request_id),
                ).fetchone()
                if prior is not None:
                    existing = self._record(prior)
                    if existing != record:
                        db.rollback()
                        raise ContractError("mission idempotency record conflict")
                    db.commit()
                    return existing, False

                collision = db.execute(
                    "SELECT * FROM copilot_missions WHERE mission_id=?",
                    (record.mission_id,),
                ).fetchone()
                if collision is not None:
                    existing = self._record(collision)
                    if existing != record:
                        db.rollback()
                        raise ContractError("mission id collision")
                    db.commit()
                    return existing, False

                db.execute(
                    """
                    INSERT INTO copilot_missions (
                        mission_id, tenant_id, object_id, department,
                        request_id, request_hash, template_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.mission_id, record.tenant_id, record.object_id,
                        record.department, record.request_id, record.request_hash,
                        record.template_id,
                    ),
                )
                db.commit()
                return record, True
            except BaseException:
                try:
                    db.rollback()
                except sqlite3.Error:
                    pass
                raise
            finally:
                db.close()
