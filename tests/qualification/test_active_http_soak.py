from __future__ import annotations

import socket

from scripts.qualification_active_http_soak import run_campaign


def free_port():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def test_active_http_soak_exercises_real_server_jobs_without_orphans(tmp_path):
    report = run_campaign(cycles=2, port=free_port(), root=tmp_path / "http-soak")
    assert report["result"] == "PASS", report
    assert report["cycles_completed"] == 2
    assert report["station_alive_at_completion"] is True
    assert report["fd_delta"] <= 12
    assert report["rss_delta_bytes"] <= 96 * 1024 * 1024
