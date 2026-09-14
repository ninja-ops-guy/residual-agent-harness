"""Track G tests: CLI smoke tests for `residual node join|leave` and
`residual cluster status` with --json output."""
from __future__ import annotations

import json

import pytest

from residual.cli import main


@pytest.fixture
def state_file(tmp_path):
    return str(tmp_path / "cluster.json")


def run_cli(argv, capsys):
    code = main(argv)
    out = capsys.readouterr()
    return code, out


def test_node_join_json(state_file, capsys):
    code, out = run_cli([
        "node", "join", "--json", "--cluster-key", "k",
        "--state-file", state_file,
        "--model", "llama3", "--tokens-per-second", "42",
        "--context-window", "8192", "--gpus", "1",
    ], capsys)
    assert code == 0
    payload = json.loads(out.out)
    assert payload["joined"] is True
    assert payload["capability"]["models"] == ["llama3"]
    assert payload["capacity"]["total_gpus"] == 1


def test_cluster_status_json(state_file, capsys):
    assert main(["node", "join", "--json", "--cluster-key", "k",
                 "--state-file", state_file, "--model", "m",
                 "--memory-bytes", "1024", "--workers", "2"]) == 0
    capsys.readouterr()
    code, out = run_cli(["cluster", "status", "--json",
                         "--state-file", state_file], capsys)
    assert code == 0
    payload = json.loads(out.out)
    cap = payload["capacity"]
    assert cap["nodes"] == 1 and cap["total_memory_bytes"] == 1024
    assert cap["total_workers"] == 2 and cap["total_models"] == 1


def test_node_leave_json(state_file, capsys):
    assert main(["node", "join", "--json", "--cluster-key", "k",
                 "--state-file", state_file, "--node-id", "n1"]) == 0
    capsys.readouterr()
    code, out = run_cli(["node", "leave", "--json", "--cluster-key", "k",
                         "--state-file", state_file, "--node-id", "n1"], capsys)
    assert code == 0
    payload = json.loads(out.out)
    assert payload["left"] is True
    assert payload["capacity"]["nodes"] == 0


def test_leave_unknown_node_fails(state_file, capsys):
    code, out = run_cli(["node", "leave", "--json", "--cluster-key", "k",
                         "--state-file", state_file, "--node-id", "ghost"], capsys)
    assert code == 1
    assert "not in the cluster" in out.err


def test_status_empty_cluster(state_file, capsys):
    code, out = run_cli(["cluster", "status", "--json",
                         "--state-file", state_file], capsys)
    assert code == 0
    assert json.loads(out.out)["capacity"]["nodes"] == 0


def test_status_human_output(state_file, capsys):
    code, out = run_cli(["cluster", "status", "--state-file", state_file], capsys)
    assert code == 0
    assert "cluster:" in out.out
