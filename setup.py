"""Keep non-package AUTH measurement inputs bound to each built wheel.

Only candidate-tree files are copied. They remain inert data, not executable
hooks, and the running kernel modules are still measured from installed code.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

INPUTS = {"AUTH_INVARIANTS.md": "AUTH_INVARIANTS.md",
          "scripts/check_maintainer_approval.py": "check_maintainer_approval.py"}


class BuildPy(_build_py):
    def run(self):
        super().run()
        if self.editable_mode:
            return  # Editable installations measure the original candidate tree.
        source = Path(__file__).resolve().parent
        destination = Path(self.build_lib) / "residual" / "_authority_inputs"
        destination.mkdir(parents=True, exist_ok=True)
        hashes = {}
        for relative, filename in INPUTS.items():
            raw = (source / relative).read_bytes()  # Missing input is a build error.
            (destination / filename).write_bytes(raw)
            hashes[relative] = hashlib.sha256(raw).hexdigest()
        (destination / "manifest.json").write_text(json.dumps(
            {"schema": "residual.authority-inputs.v1", "sha256": hashes},
            sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    def get_outputs(self, include_bytecode=1):
        outputs = super().get_outputs(include_bytecode)
        if not self.editable_mode:
            folder = Path(self.build_lib) / "residual" / "_authority_inputs"
            outputs += [str(folder / name) for name in (*INPUTS.values(), "manifest.json")]
        return list(dict.fromkeys(outputs))


setup(cmdclass={"build_py": BuildPy})
