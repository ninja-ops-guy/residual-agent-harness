"""Signed, sandbox-validated, atomic installation for RESIDUAL modules."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from residual.sandbox import FsAllowlist, NetworkPolicy, SandboxLimits, SandboxSpec, select_backend

from .registry import ModuleRegistry
from .signing import verify_signature

_INSTALL_LOCK = threading.Lock()
_VALIDATION_PREFIX = "RESIDUAL_MARKETPLACE_VALIDATION:"


class ModuleInstaller:
    """Verify, kernel-sandbox validate, freeze registry, then atomically publish."""

    def __init__(self, module_path, *, registry: ModuleRegistry | None = None):
        self.module_path = Path(module_path)
        self.registry = registry or ModuleRegistry(self.module_path / "registry.json")

    @staticmethod
    def _validate_stage(stage: Path) -> dict:
        """Load third-party entry points only behind a kernel isolation boundary.

        Validation is executable code. Signature verification proves artifact
        provenance relative to the supplied key; it does not make publisher code
        safe to execute in the Station process. Network is denied, the staged
        wheel and RESIDUAL source are read-only, ambient credentials are not
        propagated, and the operation fails closed when kernel isolation is
        unavailable.
        """
        stage = stage.resolve()
        residual_parent = Path(__file__).resolve().parents[2]
        python = Path(sys.executable).resolve()
        python_root = Path(sys.base_prefix).resolve()

        probe = r'''
import importlib.metadata as metadata
import json
import sys

PREFIX = "RESIDUAL_MARKETPLACE_VALIDATION:"
envelope = json.loads(sys.stdin.read())
stage = envelope["stage"]
residual_parent = envelope["residual_parent"]
sys.path.insert(0, stage)
sys.path.insert(0, residual_parent)

from residual.marketplace.validate import validate_module

selected = []
for dist in metadata.distributions(path=[stage]):
    selected.extend(ep for ep in dist.entry_points if ep.group == "residual.modules")
if len(selected) != 1:
    raise RuntimeError("package must expose exactly one residual.modules entry point")
report = validate_module(selected[0].load()(), source_root=stage)
sys.stdout.write(PREFIX + json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n")
'''

        read_paths = tuple(dict.fromkeys(
            str(path) for path in (stage, residual_parent, python_root) if path.exists()
        ))
        spec = SandboxSpec(
            name="marketplace-validation",
            limits=SandboxLimits(
                cpu_seconds=30,
                memory_mb=512,
                max_pids=16,
                timeout_seconds=45,
                max_output_bytes=1 << 20,
            ),
            fs=FsAllowlist(read=read_paths),
            network=NetworkPolicy.DENY,
            workdir="/tmp",
        )
        backend = select_backend(require_kernel=True)
        backend.start(spec)
        try:
            result = backend.exec(
                [str(python), "-I", "-S", "-c", probe],
                stdin=json.dumps(
                    {"stage": str(stage), "residual_parent": str(residual_parent)},
                    separators=(",", ":"),
                ),
            )
        finally:
            backend.stop()

        if result.enforcement != "kernel":
            raise RuntimeError("module validation did not enforce kernel isolation")
        if not result.ok:
            raise RuntimeError("module validation failed inside kernel sandbox")

        line = next(
            (line for line in reversed(result.stdout.splitlines())
             if line.startswith(_VALIDATION_PREFIX)),
            None,
        )
        if line is None:
            raise RuntimeError("module validation did not produce a report")
        try:
            report = json.loads(line[len(_VALIDATION_PREFIX):])
        except (json.JSONDecodeError, TypeError) as exc:
            raise RuntimeError("module validation did not produce a valid report") from exc
        if not isinstance(report, dict) or not report.get("name") or not report.get("version"):
            raise RuntimeError("invalid module validation report")
        return report

    def install(self, package, *, public_key_b64, signature_b64, distribution_url=""):
        package = Path(package)
        # sdists can execute arbitrary build-backend code before validation.
        # Marketplace admission therefore accepts prebuilt wheels only.
        if package.suffix.lower() != ".whl":
            raise RuntimeError("marketplace installation requires a prebuilt .whl artifact")
        verify_signature(package, public_key_b64, signature_b64)
        self.module_path.mkdir(parents=True, exist_ok=True)

        with _INSTALL_LOCK, self.registry.installation_freeze(), tempfile.TemporaryDirectory(prefix="residual-module-") as td:
            stage = Path(td) / "site"
            stage.mkdir()
            subprocess.run(
                [
                    sys.executable, "-m", "pip", "install",
                    "--no-deps", "--no-index", "--disable-pip-version-check",
                    "--target", str(stage), str(package),
                ],
                check=True,
                capture_output=True,
                text=True,
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "HOME": td,
                    "PYTHONNOUSERSITE": "1",
                    "PIP_CONFIG_FILE": os.devnull,
                },
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
                    name=validation["name"],
                    version=validation["version"],
                    public_key_b64=public_key_b64,
                    signature_b64=signature_b64,
                    validation=validation,
                    distribution_url=distribution_url,
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
