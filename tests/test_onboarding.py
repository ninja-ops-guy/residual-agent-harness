"""Track O (Swarm 8): executable onboarding docs.

The quickstart commands in ``docs/quickstart.md`` MUST execute successfully
end-to-end; the one-command demo script MUST exit 0; the module-author
tutorial validation script MUST pass. These tests run the documented commands
in subprocesses inside a temporary workspace so the repository stays clean.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
QUICKSTART = REPO_ROOT / "docs" / "quickstart.md"
ONBOARDING = REPO_ROOT / "examples" / "onboarding"


def _bash_blocks(text: str) -> list[str]:
    return re.findall(r"```bash\n(.*?)```", text, flags=re.DOTALL)


@pytest.fixture()
def workspace(tmp_path):
    """Temp workspace: onboarding examples copied in, residual importable."""
    shutil.copytree(ONBOARDING, tmp_path / "examples" / "onboarding")
    env = dict(os.environ, PYTHONPATH=str(REPO_ROOT))
    return tmp_path, env


def _run(cmd: str, cwd: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", cmd], cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=300)


def test_quickstart_commands_execute(workspace):
    tmp_path, env = workspace
    text = QUICKSTART.read_text()
    blocks = [b for b in _bash_blocks(text) if "pip install" not in b]
    assert len(blocks) >= 3, "quickstart must contain runnable command blocks"
    for block in blocks:
        proc = _run(block, tmp_path, env)
        assert proc.returncode == 0, (
            f"quickstart block failed ({proc.returncode}):\n{block}\n"
            f"stdout: {proc.stdout[-2000:]}\nstderr: {proc.stderr[-2000:]}")
    trace = tmp_path / "runs" / "quickstart" / "trace.jsonl"
    result = tmp_path / "runs" / "quickstart" / "result.json"
    assert trace.is_file() and result.is_file()
    outcome = json.loads(result.read_text())
    assert outcome["success"] is True


def test_demo_script_exits_zero(workspace):
    tmp_path, env = workspace
    proc = _run("bash examples/onboarding/demo.sh runs/onboarding-demo", tmp_path, env)
    assert proc.returncode == 0, (
        f"demo.sh failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")
    assert "onboarding demo OK" in proc.stdout
    assert (tmp_path / "runs" / "onboarding-demo" / "trace.jsonl").is_file()


def test_demo_script_failure_propagates(workspace):
    tmp_path, env = workspace
    # Remove the declared evidence artifact so the run MUST fail.
    inventory = tmp_path / "examples" / "onboarding" / "sample_project" / "inventory.json"
    inventory.unlink()
    proc = _run("bash examples/onboarding/demo.sh runs/should-fail", tmp_path, env)
    assert proc.returncode != 0


def test_tutorial_validation_script(workspace):
    tmp_path, env = workspace
    proc = subprocess.run([sys.executable, str(ONBOARDING / "validate_tutorial.py")],
                          cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, (
        f"tutorial validation failed:\n{proc.stdout}\n{proc.stderr[-2000:]}")
    assert "tutorial validation OK" in proc.stdout


def test_quickstart_documents_studio_launch():
    text = QUICKSTART.read_text()
    assert "residual.studio_frontend.stub_server" in text
