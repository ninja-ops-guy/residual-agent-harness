"""Small PyPI-compatible module registry index used by the marketplace CLI.

The registry stores package metadata only; package distribution may be any
PEP-503/PyPI-compatible host. Admission requires a verified package signature
and a successful module validation report.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path

from .signing import verify_signature


class RegistryError(ValueError):
    pass


class ModuleRegistry:
    def __init__(self, path: str | os.PathLike):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._frozen = False

    @property
    def frozen(self) -> bool:
        with self._lock:
            return self._frozen

    def _read(self) -> dict:
        if not self.path.exists():
            return {"schema_version": "residual.module.registry.v1", "packages": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("schema_version") != "residual.module.registry.v1" or not isinstance(data.get("packages"), dict):
                raise ValueError()
            return data
        except Exception as exc:
            raise RegistryError("invalid module registry index") from exc

    def _write_atomic(self, data: dict) -> None:
        payload = json.dumps(data, sort_keys=True, indent=2) + "\n"
        fd, tmp = tempfile.mkstemp(prefix=self.path.name + ".", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    @contextmanager
    def installation_freeze(self):
        """Prevent concurrent registry mutation for one atomic installation."""
        with self._lock:
            if self._frozen:
                raise RegistryError("module registry is already frozen")
            self._frozen = True
            try:
                yield self
            finally:
                self._frozen = False

    def admit(self, package_path, *, name: str, version: str, public_key_b64: str,
              signature_b64: str, validation: dict, distribution_url: str = "") -> dict:
        """Admit one signed, validated distribution into the registry index."""
        with self._lock:
            if not self._frozen:
                raise RegistryError("registry admission requires installation freeze")
            if not validation or validation.get("name") != name or validation.get("version") != version:
                raise RegistryError("module validation report does not match package identity")
            verify_signature(package_path, public_key_b64, signature_b64)
            package_hash = hashlib.sha256(Path(package_path).read_bytes()).hexdigest()
            data = self._read()
            key = f"{name}=={version}"
            record = {
                "name": name,
                "version": version,
                "sha256": package_hash,
                "public_key": public_key_b64,
                "signature": signature_b64,
                "distribution_url": distribution_url,
                "validation": validation,
            }
            data["packages"][key] = record
            self._write_atomic(data)
            return dict(record)

    def lookup(self, name: str, version: str) -> dict | None:
        with self._lock:
            item = self._read()["packages"].get(f"{name}=={version}")
            return dict(item) if item else None
