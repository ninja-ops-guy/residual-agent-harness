from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from .signing import verify_signature

_INSTALL_LOCK = threading.Lock()


class ModuleInstaller:
    """Verify, protocol-validate, stage, then atomically publish a module package."""

    def __init__(self, module_path):
        self.module_path = Path(module_path)

    def install(self, package, *, public_key_b64, signature_b64):
        package = Path(package)
        verify_signature(package, public_key_b64, signature_b64)
        with _INSTALL_LOCK, tempfile.TemporaryDirectory(prefix="residual-module-") as td:
            stage = Path(td) / "site"
            stage.mkdir()
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--no-deps", "--target", str(stage), str(package)],
                check=True,
                capture_output=True,
                text=True,
            )

            # Validate the staged artifact before it becomes visible in the module path.
            # Import/validation occurs in a subprocess so a broken package cannot poison
            # the long-lived command station process.
            probe = r'''
import importlib.metadata as metadata
import json
import os
from residual.marketplace.validate import validate_module

stage = os.environ["RESIDUAL_MODULE_STAGE"]
eps = metadata.entry_points()
selected = eps.select(group="residual.modules") if hasattr(eps, "select") else eps.get("residual.modules", ())
selected = list(selected)
assert selected, "missing residual.modules entry point"
reports = []
for ep in selected:
    reports.append(validate_module(ep.load()(), source_root=stage))
print(json.dumps(reports, sort_keys=True))
'''
            subprocess.run(
                [sys.executable, "-c", probe],
                env={**os.environ, "PYTHONPATH": str(stage), "RESIDUAL_MODULE_STAGE": str(stage)},
                check=True,
                capture_output=True,
                text=True,
            )

            self.module_path.mkdir(parents=True, exist_ok=True)
            dest = self.module_path / package.stem
            tmp = self.module_path / (package.stem + ".installing")
            if tmp.exists():
                shutil.rmtree(tmp)
            shutil.copytree(stage, tmp)
            if dest.exists():
                shutil.rmtree(dest)
            os.replace(tmp, dest)
            return dest
