"""Signed, validated, atomic installation for Residual modules."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from .registry import ModuleRegistry
from .signing import verify_signature

_INSTALL_LOCK = threading.Lock()


class ModuleInstaller:
    """Verify, protocol-validate, freeze registry, then atomically publish."""

    def __init__(self, module_path, *, registry: ModuleRegistry | None = None):
        self.module_path = Path(module_path)
        self.registry = registry or ModuleRegistry(self.module_path / "registry.json")

    @staticmethod
    def _validate_stage(stage: Path) -> dict:
        # Validation runs outside the station process so a malformed third-party
        # module cannot poison long-lived runtime state.
        probe = r'''
import importlib.metadata as metadata
import json
import os
from residual.marketplace.validate import validate_module

stage = os.environ["RESIDUAL_MODULE_STAGE"]
eps = metadata.entry_points()
selected = eps.select(group="residual.modules") if hasattr(eps, "select") else eps.get("residual.modules", ())
selected = list(selected)
assert len(selected) == 1, "package must expose exactly one residual.modules entry point"
print(json.dumps(validate_module(selected[0].load()(), source_root=stage), sort_keys=True))
'''
        proc = subprocess.run(
            [sys.executable, "-c", probe],
            env={**os.environ,
                 "PYTHONPATH": str(stage) + os.pathsep + os.environ.get("PYTHONPATH", ""),
                 "RESIDUAL_MODULE_STAGE": str(stage)},
            check=True, capture_output=True, text=True,
        )
        try:
            report = json.loads(proc.stdout.strip().splitlines()[-1])
        except Exception as exc:
            raise RuntimeError("module validation did not produce a report") from exc
        if not isinstance(report, dict) or not report.get("name") or not report.get("version"):
            raise RuntimeError("invalid module validation report")
        return report

    def install(self, package, *, public_key_b64, signature_b64, distribution_url=""):
        package = Path(package)
        verify_signature(package, public_key_b64, signature_b64)
        self.module_path.mkdir(parents=True, exist_ok=True)

        with _INSTALL_LOCK, self.registry.installation_freeze(), tempfile.TemporaryDirectory(prefix="residual-module-") as td:
            stage = Path(td) / "site"
            stage.mkdir()
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(stage), str(package)],
                check=True, capture_output=True, text=True,
            )
            validation = self._validate_stage(stage)

            safe_name = "".join(c for c in validation["name"] if c.isalnum() or c in "._-")
            safe_version = "".join(c for c in validation["version"] if c.isalnum() or c in "._-")
            if not safe_name or not safe_version:
                raise RuntimeError("module name/version cannot map to an install path")
            dest = self.module_path / f"{safe_name}-{safe_version}"
            pending = self.module_path / f".{safe_name}-{safe_version}.installing"
            backup = self.module_path / f".{safe_name}-{safe_version}.previous"
            for path in (pending, backup):
                if path.exists():
                    shutil.rmtree(path)
            shutil.copytree(stage, pending)

            moved_old = False
            try:
                if dest.exists():
                    os.replace(dest, backup)
                    moved_old = True
                os.replace(pending, dest)
                self.registry.admit(
                    package,
                    name=validation["name"], version=validation["version"],
                    public_key_b64=public_key_b64, signature_b64=signature_b64,
                    validation=validation, distribution_url=distribution_url,
                )
            except Exception:
                if dest.exists():
                    shutil.rmtree(dest)
                if moved_old and backup.exists():
                    os.replace(backup, dest)
                if pending.exists():
                    shutil.rmtree(pending)
                raise
            else:
                if backup.exists():
                    shutil.rmtree(backup)
            return dest
