from __future__ import annotations

import pathlib
import py_compile
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[1]
SHELL = [
    ROOT / "scripts/automation/lib.sh",
    ROOT / "scripts/automation/r4_02_b1.sh",
    ROOT / "scripts/automation/f6_helper.sh",
    ROOT / "scripts/automation/swarm_comms.sh",
]


def test_automation_shell_scripts_parse():
    for path in SHELL:
        subprocess.run(["bash", "-n", str(path)], check=True, cwd=ROOT)


def test_mesh_advisory_bridge_compiles(tmp_path):
    py_compile.compile(
        str(ROOT / "scripts/automation/mesh_advisory_bridge.py"),
        cfile=str(tmp_path / "mesh_advisory_bridge.pyc"),
        doraise=True,
    )


def test_f6_runner_cannot_execute_physical_f6():
    text = (ROOT / "scripts/automation/f6_helper.sh").read_text(encoding="utf-8")
    assert "Run-F6-Physical.ps1" not in text
    assert "TUNNEL_DOWN" not in text
    assert "PHYSICAL F6 REMAINS UNEXECUTED" in text


def test_swarm_recovery_reserves_f6_port_and_uses_advisory_bridge():
    text = (ROOT / "scripts/automation/swarm_comms.sh").read_text(encoding="utf-8")
    assert 'PORT="${SC_MESH_RECOVERY_PORT:-8770}"' in text
    assert '"$PORT" != "8766"' in text
    bridge = (ROOT / "scripts/automation/mesh_advisory_bridge.py").read_text(encoding="utf-8")
    for forbidden in (".claim(", ".submit_result(", ".execution_admit(", ".heartbeat("):
        assert forbidden not in bridge


def test_log_diagnostics_do_not_pollute_stdout_values():
    text = (ROOT / "scripts/automation/lib.sh").read_text(encoding="utf-8")
    assert 'printf \'[%s] %s\\n\'' in text
    assert '"$*" >&2' in text
