from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from residual.core import canonical, strict_json
from residual.factory.evidence_receipts import StationIdentity

CORPUS_SCHEMA = "factory-benchmark-corpus-v1"
CORPUS_DOMAIN = b"residual.factory.benchmark-corpus.v1\n"
BENCHMARKS = ("fb001", "fb002", "fb003", "fb004")
CONFIGS = ("single", "fixed", "dynamic")


def _sha(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _require_hash(value: str, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"invalid {name}")
    return value


def _command(argv: list[str]) -> str | None:
    try:
        proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = proc.stdout.strip()
    return value if proc.returncode == 0 and value else None


def host_evidence() -> dict[str, Any]:
    cpu_model = None
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name") and ":" in line:
                cpu_model = line.split(":", 1)[1].strip()
                break
    gpu = _command(["nvidia-smi", "--query-gpu=name,uuid,memory.total,driver_version", "--format=csv,noheader,nounits"])
    if gpu is None:
        gpu = _command(["rocm-smi", "--showproductname", "--showuniqueid", "--showmeminfo", "vram"])
    evidence = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "cpu_model": cpu_model or platform.processor() or "unknown",
        "logical_cpus": os.cpu_count(),
        "gpu": gpu or "unreported",
    }
    evidence["fingerprint"] = _sha(evidence)
    return evidence


@dataclass(frozen=True, slots=True)
class CorpusEntry:
    benchmark: str
    workload_hash: str
    report_hash: str
    simulation: bool
    engine_name: str
    engine_version: str

    def __post_init__(self):
        if self.benchmark not in BENCHMARKS:
            raise ValueError("unknown benchmark")
        _require_hash(self.workload_hash, "workload hash")
        _require_hash(self.report_hash, "report hash")
        if type(self.simulation) is not bool or not self.engine_name or not self.engine_version:
            raise ValueError("invalid corpus entry provenance")

    def to_dict(self) -> dict[str, Any]:
        return {"benchmark": self.benchmark, "workload_hash": self.workload_hash,
                "report_hash": self.report_hash, "simulation": self.simulation,
                "engine_name": self.engine_name, "engine_version": self.engine_version}


@dataclass(frozen=True, slots=True)
class CorpusManifest:
    source_commit: str
    model_name: str
    model_version: str
    host: dict[str, Any]
    configs: tuple[str, ...]
    runs: int
    entries: tuple[CorpusEntry, ...]
    station_key_id: str
    station_signature: str
    schema_version: str = CORPUS_SCHEMA

    def __post_init__(self):
        if self.schema_version != CORPUS_SCHEMA:
            raise ValueError("unsupported corpus schema")
        if not self.source_commit or not self.model_name or not self.model_version:
            raise ValueError("corpus identity required")
        if tuple(self.configs) != CONFIGS:
            raise ValueError("corpus requires single,fixed,dynamic")
        if type(self.runs) is not int or self.runs < 3:
            raise ValueError("corpus requires at least 3 runs")
        if tuple(e.benchmark for e in self.entries) != BENCHMARKS:
            raise ValueError("corpus must contain FB001-FB004 in order")
        if len({e.engine_name for e in self.entries}) != 1 or len({e.engine_version for e in self.entries}) != 1:
            raise ValueError("mixed engine corpus")
        if any(e.engine_name != self.model_name or e.engine_version != self.model_version for e in self.entries):
            raise ValueError("entry model identity does not match corpus")
        fingerprint = self.host.get("fingerprint") if isinstance(self.host, dict) else None
        if not isinstance(fingerprint, str) or _sha({k: v for k, v in self.host.items() if k != "fingerprint"}) != fingerprint:
            raise ValueError("host fingerprint mismatch")
        _require_hash(self.station_key_id, "station key id")
        if not isinstance(self.station_signature, str):
            raise ValueError("signature required")

    @property
    def simulation(self) -> bool:
        return any(e.simulation for e in self.entries)

    def unsigned_payload(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "source_commit": self.source_commit,
                "model_name": self.model_name, "model_version": self.model_version,
                "host": self.host, "configs": list(self.configs), "runs": self.runs,
                "entries": [e.to_dict() for e in self.entries], "simulation": self.simulation,
                "station_key_id": self.station_key_id}

    @property
    def manifest_hash(self) -> str:
        return _sha(self.unsigned_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.unsigned_payload(), "manifest_hash": self.manifest_hash,
                "station_signature": self.station_signature}

    def verify(self, public_key: bytes) -> bool:
        return StationIdentity.verify_hash(self.manifest_hash, self.station_signature, public_key,
                                           key_id=self.station_key_id, domain=CORPUS_DOMAIN)

    @classmethod
    def issue(cls, *, source_commit: str, model_name: str, model_version: str,
              host: dict[str, Any], runs: int, entries: tuple[CorpusEntry, ...],
              identity: StationIdentity) -> "CorpusManifest":
        fields = dict(source_commit=source_commit, model_name=model_name, model_version=model_version,
                      host=host, configs=CONFIGS, runs=runs, entries=entries,
                      station_key_id=identity.key_id, station_signature="")
        draft = cls(**fields)
        signature = identity.sign_hash(draft.manifest_hash, domain=CORPUS_DOMAIN)
        return cls(**{**fields, "station_signature": signature})

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CorpusManifest":
        value = strict_json(canonical(value))
        expected_hash = value.pop("manifest_hash", None)
        entries = tuple(CorpusEntry(**x) for x in value.pop("entries"))
        value["configs"] = tuple(value["configs"])
        value.pop("simulation", None)
        manifest = cls(entries=entries, **value)
        if expected_hash != manifest.manifest_hash:
            raise ValueError("corpus manifest hash mismatch")
        return manifest


def report_entry(benchmark: str, workload_path: Path, report_path: Path) -> CorpusEntry:
    workload = strict_json(workload_path.read_text(encoding="utf-8"))
    report = strict_json(report_path.read_text(encoding="utf-8"))
    engine = workload.get("engine") or {}
    workload_copy = dict(workload); workload_copy.pop("driver_argv", None)
    workload_hash = _sha(workload_copy)
    if report.get("workload_hash") != workload_hash:
        raise ValueError(f"{benchmark} report/workload hash mismatch")
    return CorpusEntry(benchmark=benchmark, workload_hash=workload_hash,
                       report_hash=_require_hash(report.get("report_hash"), "report hash"),
                       simulation=bool(report.get("simulation")),
                       engine_name=str(engine.get("name", "")),
                       engine_version=str(engine.get("version", "")))
