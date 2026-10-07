from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "residual.qualification.evidence.v1"


class GateResult(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    SKIP = "SKIP"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _git(root: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True,
            timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def source_identity(root: Path | str = ".") -> dict[str, Any]:
    root = Path(root).resolve()
    dirty = _git(root, "status", "--porcelain", "--untracked-files=no")
    return {
        "commit": _git(root, "rev-parse", "HEAD"),
        "tree": _git(root, "rev-parse", "HEAD^{tree}"),
        "tracked_source_dirty": None if dirty is None else bool(dirty),
    }


def environment_identity() -> dict[str, Any]:
    keys = (
        "GITHUB_ACTIONS", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_JOB",
        "RUNNER_OS", "RUNNER_ARCH", "ImageOS", "ImageVersion",
    )
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "ci": {key: os.environ.get(key) for key in keys if os.environ.get(key)},
    }


def evidence_digest(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_files(paths: Iterable[Path | str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for value in paths:
        path = Path(value)
        if path.is_file():
            out[str(path)] = evidence_digest(path)
    return out


@dataclass(frozen=True)
class EvidenceEnvelope:
    gate_id: str
    result: GateResult
    started_at: str
    finished_at: str
    source: dict[str, Any]
    environment: dict[str, Any]
    command: list[str] = field(default_factory=list)
    evidence: dict[str, str] = field(default_factory=dict)
    skip_count: int = 0
    unknown_count: int = 0
    notes: list[str] = field(default_factory=list)
    non_claims: list[str] = field(default_factory=list)
    schema: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        doc = asdict(self)
        doc["result"] = self.result.value
        return doc

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EvidenceEnvelope":
        if raw.get("schema") != SCHEMA_VERSION:
            raise ValueError(f"unsupported evidence schema: {raw.get('schema')!r}")
        result = GateResult(raw["result"])
        source = raw.get("source") or {}
        if not source.get("commit") or not source.get("tree"):
            raise ValueError("evidence must bind commit and tree")
        return cls(
            gate_id=str(raw["gate_id"]), result=result,
            started_at=str(raw["started_at"]), finished_at=str(raw["finished_at"]),
            source=dict(source), environment=dict(raw.get("environment") or {}),
            command=list(raw.get("command") or []), evidence=dict(raw.get("evidence") or {}),
            skip_count=int(raw.get("skip_count", 0)),
            unknown_count=int(raw.get("unknown_count", 0)),
            notes=list(raw.get("notes") or []), non_claims=list(raw.get("non_claims") or []),
        )


def write_envelope(envelope: EvidenceEnvelope, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(envelope.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_envelope(path: Path | str) -> EvidenceEnvelope:
    return EvidenceEnvelope.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def new_envelope(
    gate_id: str,
    result: GateResult,
    *,
    root: Path | str = ".",
    started_at: str | None = None,
    command: list[str] | None = None,
    evidence_paths: Iterable[Path | str] = (),
    skip_count: int = 0,
    unknown_count: int = 0,
    notes: list[str] | None = None,
    non_claims: list[str] | None = None,
) -> EvidenceEnvelope:
    return EvidenceEnvelope(
        gate_id=gate_id,
        result=result,
        started_at=started_at or _utc_now(),
        finished_at=_utc_now(),
        source=source_identity(root),
        environment=environment_identity(),
        command=command or [],
        evidence=hash_files(evidence_paths),
        skip_count=skip_count,
        unknown_count=unknown_count,
        notes=notes or [],
        non_claims=non_claims or [],
    )
