from __future__ import annotations

import os

import pytest

from residual.core import ContractError
import residual.supplychain.sandbox as supplychain_sandbox


def test_supplychain_runtime_uses_interpreter_inside_minimal_bwrap_root(monkeypatch):
    monkeypatch.setattr(
        supplychain_sandbox.sys,
        "executable",
        "/opt/hostedtoolcache/Python/3.12.14/x64/bin/python",
    )
    monkeypatch.setattr(
        supplychain_sandbox.os.path,
        "isfile",
        lambda path: path == "/usr/bin/python3",
    )
    monkeypatch.setattr(
        supplychain_sandbox.os,
        "access",
        lambda path, mode: path == "/usr/bin/python3" and mode == os.X_OK,
    )

    assert supplychain_sandbox._sandbox_python() == "/usr/bin/python3"


def test_supplychain_runtime_interpreter_missing_fails_closed(monkeypatch):
    monkeypatch.setattr(supplychain_sandbox.os.path, "isfile", lambda _path: False)

    with pytest.raises(ContractError, match="sandbox runtime interpreter unavailable"):
        supplychain_sandbox._sandbox_python()
