from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

from residual.factory import m4_protocol


def test_linux_child_protocol_literals_match_platform_neutral_host_constants():
    child = (Path(__file__).resolve().parents[2] / "residual" / "factory" / "_isolated_child.py").read_text(encoding="utf-8")
    values = {}
    for node in ast.parse(child).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in {"SANDBOX_ERROR_PREFIX", "SANDBOX_ERROR_EXIT", "SANDBOX_TIMEOUT_EXIT"}:
                values[name] = ast.literal_eval(node.value)
    assert values == {
        "SANDBOX_ERROR_PREFIX": m4_protocol.SANDBOX_ERROR_PREFIX,
        "SANDBOX_ERROR_EXIT": m4_protocol.SANDBOX_ERROR_EXIT,
        "SANDBOX_TIMEOUT_EXIT": m4_protocol.SANDBOX_TIMEOUT_EXIT,
    }


def test_host_factory_import_does_not_import_linux_isolated_child():
    code = (
        "import sys, residual.factory; "
        "assert 'residual.factory._isolated_child' not in sys.modules, "
        "sorted(name for name in sys.modules if name.startswith('residual.factory'))"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr or result.stdout
