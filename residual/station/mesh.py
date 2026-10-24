"""Typed Shared Communications Mesh contracts for SPEC-SC-MESH-001.

This module is authority-neutral: it validates enrollment declarations and
message envelopes but never admits tasks, integrates code, or changes project
state. Station remains authoritative.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import time
import uuid

from residual.core import ContractError, canonical

MESH_SCHEMA = "residual.sc.mesh/1"
ENROLLMENT_SCHEMA = "residual.sc.mesh.enrollment/1"
STATUS_SCHEMA = "residual.sc.mesh.status/1"

MAX_INLINE_PAYLOAD_BYTES = 32 * 1024
MAX_ENVELOPE_BYTES = 48 * 1024
MAX_IDEMPOTENCY_KEY = 128
MAX_IDENTIFIER = 128
MAX_TOKEN = 96
MAX_CAPABILITIES = 64
MAX_TOPICS = 64
DEFAULT_TTL_S = 900
MAX_TTL_S = 3600
MAX_PAGE = 200
MAX_REPLAY_AGE_S = 24 * 60 * 60
MAX_PROJECT_MESSAGES = 5000
MAX_BULK_MESSAGES = 4500
MAX_DEAD_LETTERS = 1000
BULK_KINDS = {"message", "status", "task.note"}

WORKER_STATES = {"UNENROLLED", "ENROLLED", "SYNCING", "READY", "DRAINING", "DISCONNECTED", "REVOKED"}
MESSAGE_KINDS = {
    "message",
    "evidence.reference",
    "status",
    "task.note",
    "task.result",
    "control.cancel_ack",
}
TASK_SCOPED_KINDS = {"task.note", "task.result", "control.cancel_ack"}
AUTHORITY_FIELDS = {"task_id", "attempt", "lease_id", "fencing_token"}

TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,95}$")
IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def _text(value, name, maximum=MAX_IDENTIFIER):
    if not isinstance(value, str) or not value or len(value) > maximum or "\x00" in value:
        raise ContractError(f"{name} must be bounded non-empty text")
    return value


def _token_list(value, name, maximum):
    if not isinstance(value, list) or len(value) > maximum or len(set(value)) != len(value):
        raise ContractError(f"{name} must be a unique bounded list")
    for item in value:
        if not isinstance(item, str) or not TOKEN.fullmatch(item):
            raise ContractError(f"{name} contains an invalid token")
    return tuple(value)


def payload_digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EnrollmentRequest:
    worker_id: str
    host_id: str
    adapter: str
    adapter_version: str
    project_ids: tuple[str, ...]
    capabilities: tuple[str, ...]
    topics: tuple[str, ...]
    expires_at: float

    @classmethod
    def parse(cls, value, *, now=None):
        allowed = {"worker_id", "host_id", "adapter", "adapter_version", "project_ids",
                   "capabilities", "topics", "expires_at"}
        if not isinstance(value, dict) or set(value) != allowed:
            raise ContractError("Enrollment request fields do not match the mesh contract")
        worker_id = _text(value["worker_id"], "worker_id")
        host_id = _text(value["host_id"], "host_id")
        adapter = _text(value["adapter"], "adapter", MAX_TOKEN)
        adapter_version = _text(value["adapter_version"], "adapter_version", MAX_TOKEN)
        if not TOKEN.fullmatch(adapter) or not TOKEN.fullmatch(adapter_version):
            raise ContractError("Adapter identity/version contains unsupported characters")
        project_ids = _token_list(value["project_ids"], "project_ids", 64)
        if not project_ids:
            raise ContractError("Enrollment requires at least one project")
        capabilities = _token_list(value["capabilities"], "capabilities", MAX_CAPABILITIES)
        topics = _token_list(value["topics"], "topics", MAX_TOPICS)
        expires_at = value["expires_at"]
        if not isinstance(expires_at, (int, float)) or isinstance(expires_at, bool):
            raise ContractError("expires_at must be a unix timestamp")
        current = time.time() if now is None else now
        if expires_at <= current or expires_at > current + 31 * 24 * 60 * 60:
            raise ContractError("Enrollment expiry must be in the next 31 days")
        return cls(worker_id, host_id, adapter, adapter_version, project_ids, capabilities, topics, float(expires_at))


@dataclass(frozen=True)
class MeshEnvelope:
    message_id: str
    idempotency_key: str
    project_id: str
    sender: str
    recipient: str
    kind: str
    generation: int
    created_at: float
    expires_at: float
    correlation_id: str | None
    causation_id: str | None
    payload_digest: str
    payload: object | None
    artifact_ref: str | None
    task_id: str | None
    attempt: int | None
    lease_id: str | None
    fencing_token: int | None
    extensions: dict

    @classmethod
    def parse(cls, value, *, now=None):
        allowed = {
            "schema", "message_id", "idempotency_key", "project_id", "sender", "recipient",
            "kind", "generation", "created_at", "expires_at", "correlation_id", "causation_id",
            "payload_digest", "payload", "artifact_ref", "task_id", "attempt", "lease_id",
            "fencing_token", "extensions",
        }
        required = {
            "schema", "message_id", "idempotency_key", "project_id", "sender", "recipient",
            "kind", "generation", "created_at", "expires_at", "payload_digest", "extensions",
        }
        if not isinstance(value, dict) or not required.issubset(value) or set(value) - allowed:
            raise ContractError("Mesh envelope fields do not match the versioned contract")
        if value["schema"] != MESH_SCHEMA:
            raise ContractError("Unsupported mesh envelope major version")
        message_id = _text(value["message_id"], "message_id")
        idem = _text(value["idempotency_key"], "idempotency_key", MAX_IDEMPOTENCY_KEY)
        project = _text(value["project_id"], "project_id")
        sender = _text(value["sender"], "sender")
        recipient = _text(value["recipient"], "recipient")
        kind = value["kind"]
        if kind not in MESSAGE_KINDS:
            raise ContractError("Unknown mesh message kind")
        generation = value["generation"]
        if type(generation) is not int or generation < 1:
            raise ContractError("generation must be a positive integer")
        created = value["created_at"]
        expires = value["expires_at"]
        if (not isinstance(created, (int, float)) or isinstance(created, bool)
                or not isinstance(expires, (int, float)) or isinstance(expires, bool)):
            raise ContractError("created_at/expires_at must be unix timestamps")
        current = time.time() if now is None else now
        if expires <= current:
            raise ContractError("Mesh envelope has expired")
        if created < current - MAX_REPLAY_AGE_S:
            raise ContractError("Mesh envelope exceeds the maximum replay age")
        if expires - created <= 0 or expires - created > MAX_TTL_S:
            raise ContractError("Mesh envelope TTL exceeds the qualification profile")
        if created > current + 300:
            raise ContractError("Mesh envelope creation time is implausibly far in the future")

        correlation = value.get("correlation_id")
        causation = value.get("causation_id")
        for name, item in (("correlation_id", correlation), ("causation_id", causation)):
            if item is not None:
                _text(item, name)

        payload = value.get("payload")
        artifact_ref = value.get("artifact_ref")
        if (payload is None) == (artifact_ref is None):
            raise ContractError("Exactly one of payload or artifact_ref is required")
        if artifact_ref is not None:
            _text(artifact_ref, "artifact_ref", 240)
        else:
            if len(canonical(payload).encode("utf-8")) > MAX_INLINE_PAYLOAD_BYTES:
                raise ContractError("Inline mesh payload exceeds 32 KiB")
        supplied_digest = value["payload_digest"]
        if not isinstance(supplied_digest, str) or not re.fullmatch(r"[a-f0-9]{64}", supplied_digest):
            raise ContractError("payload_digest must be lowercase SHA-256")
        material = payload if payload is not None else {"artifact_ref": artifact_ref}
        if payload_digest(material) != supplied_digest:
            raise ContractError("payload_digest does not match the payload")

        task_values = {
            "task_id": value.get("task_id"),
            "attempt": value.get("attempt"),
            "lease_id": value.get("lease_id"),
            "fencing_token": value.get("fencing_token"),
        }
        if kind in TASK_SCOPED_KINDS:
            if any(task_values[k] is None for k in AUTHORITY_FIELDS):
                raise ContractError("Task-scoped mesh messages require task/attempt/lease/fencing bindings")
            _text(task_values["task_id"], "task_id")
            _text(task_values["lease_id"], "lease_id")
            if type(task_values["attempt"]) is not int or task_values["attempt"] < 1:
                raise ContractError("attempt must be a positive integer")
            if type(task_values["fencing_token"]) is not int or task_values["fencing_token"] < 1:
                raise ContractError("fencing_token must be a positive integer")
        elif any(task_values[k] is not None for k in AUTHORITY_FIELDS):
            raise ContractError("Non-task messages may not carry authority-bearing task fields")

        extensions = value["extensions"]
        if not isinstance(extensions, dict):
            raise ContractError("extensions must be an object")
        for key in extensions:
            if not isinstance(key, str) or not TOKEN.fullmatch(key):
                raise ContractError("Invalid mesh extension key")
        if len(canonical(value).encode("utf-8")) > MAX_ENVELOPE_BYTES:
            raise ContractError("Mesh envelope exceeds 48 KiB")

        return cls(
            message_id, idem, project, sender, recipient, kind, generation,
            float(created), float(expires), correlation, causation, supplied_digest,
            payload, artifact_ref, task_values["task_id"], task_values["attempt"],
            task_values["lease_id"], task_values["fencing_token"], extensions,
        )

    def to_dict(self):
        value = {
            "schema": MESH_SCHEMA,
            "message_id": self.message_id,
            "idempotency_key": self.idempotency_key,
            "project_id": self.project_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "kind": self.kind,
            "generation": self.generation,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "payload_digest": self.payload_digest,
            "payload": self.payload,
            "artifact_ref": self.artifact_ref,
            "task_id": self.task_id,
            "attempt": self.attempt,
            "lease_id": self.lease_id,
            "fencing_token": self.fencing_token,
            "extensions": self.extensions,
        }
        return value


def new_envelope(*, project_id, sender, recipient, kind, generation, payload=None,
                 artifact_ref=None, correlation_id=None, causation_id=None,
                 task_id=None, attempt=None, lease_id=None, fencing_token=None,
                 ttl_s=DEFAULT_TTL_S, idempotency_key=None, now=None):
    current = time.time() if now is None else now
    material = payload if payload is not None else {"artifact_ref": artifact_ref}
    raw = {
        "schema": MESH_SCHEMA,
        "message_id": uuid.uuid4().hex,
        "idempotency_key": idempotency_key or uuid.uuid4().hex,
        "project_id": project_id,
        "sender": sender,
        "recipient": recipient,
        "kind": kind,
        "generation": generation,
        "created_at": current,
        "expires_at": current + ttl_s,
        "correlation_id": correlation_id,
        "causation_id": causation_id,
        "payload_digest": payload_digest(material),
        "payload": payload,
        "artifact_ref": artifact_ref,
        "task_id": task_id,
        "attempt": attempt,
        "lease_id": lease_id,
        "fencing_token": fencing_token,
        "extensions": {},
    }
    return MeshEnvelope.parse(raw, now=current).to_dict()


class ClawAdapter:
    """Semantic adapter interface; implementations may expose fewer capabilities."""

    name = "abstract"
    version = "0"
    capabilities: frozenset[str] = frozenset()

    def discover(self):
        raise NotImplementedError

    def connect(self):
        raise NotImplementedError

    def execute(self, assignment):
        raise NotImplementedError

    def cancel(self, assignment_id):
        raise NotImplementedError

    def shutdown(self):
        raise NotImplementedError
