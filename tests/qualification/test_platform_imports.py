from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from residual.factory import m4_protocol


def test_linux_child_protocol_literals_match_platform_neutral_host_constants():
    child = (Path(__file__).resolve().parents[2] / "residual" / "factory" / "_isolated_child.py").read_text(encoding="utf-8")
    expected = {
        "SANDBOX_ERROR_PREFIX": repr(m4_protocol.SANDBOX_ERROR_PREFIX),
        "SANDBOX_ERROR_EXIT": str(m4_protocol.SANDBOX_ERROR_EXIT),
        "SANDBOX_TIMEOUT_EXIT": str(m4_protocol.SANDBOX_TIMEOUT_EXIT),
    }
    for name, literal in expected.items():
        match = re.search(rf"^{name}\s*=\s*(.+?)\s*$", child, re.MULTILINE)
        assert match is not None, name
        assert match.group(1) == literal, (name, match.group(1), literal)


def test_host_factory_import_does_not_import_linux_isolated_child():
    code = (
        "import sys, residual.factory; "
        "assert 'residual.factory._isolated_child' not in sys.modules, "
        "sorted(name for name in sys.modules if name.startswith('residual.factory'))"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr or result.stdout
