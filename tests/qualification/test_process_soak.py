from __future__ import annotations

import scripts.qualification_process_soak as soak


class _Response:
    def __init__(self, status: int):
        self.status = status

    def read(self, _limit: int) -> bytes:
        return b"body"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _reasons(**overrides):
    values = {
        "samples": [
            {"elapsed_s": 0.0, "rss_bytes": 1000, "fd_count": 10},
            {"elapsed_s": 300.0, "rss_bytes": 1000, "fd_count": 10},
            {"elapsed_s": 600.0, "rss_bytes": 1000, "fd_count": 10},
        ],
        "probe_failures": [],
        "error": None,
        "elapsed_observed_s": 600.0,
        "duration_requested_s": 600.0,
        "process_alive_at_completion": True,
        "rss_slope": 0.0,
        "fd_slope": 0.0,
        "max_probe_failures": 0,
        "max_rss_growth_mib_per_hour": 32.0,
        "max_fd_growth_per_hour": 8.0,
    }
    values.update(overrides)
    return soak.qualification_reasons(**values)


def test_probe_rejects_4xx_as_unhealthy(monkeypatch):
    monkeypatch.setattr(soak.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response(404))
    ok, detail = soak.probe("http://127.0.0.1/", 1.0)
    assert not ok
    assert detail == "HTTP 404"


def test_probe_accepts_2xx(monkeypatch):
    monkeypatch.setattr(soak.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response(204))
    ok, detail = soak.probe("http://127.0.0.1/", 1.0)
    assert ok
    assert detail == "HTTP 204"


def test_soak_requires_observable_resource_slopes():
    reasons = _reasons(rss_slope=None, fd_slope=None)
    assert "RSS growth slope unavailable" in reasons
    assert "FD growth slope unavailable" in reasons


def test_soak_requires_process_alive_at_completion_boundary():
    reasons = _reasons(process_alive_at_completion=False)
    assert "process was not alive at the completion boundary" in reasons


def test_soak_requires_full_observed_duration():
    reasons = _reasons(elapsed_observed_s=599.0)
    assert any("observed elapsed time" in reason for reason in reasons)


def test_soak_fails_closed_on_metric_sampling_error():
    samples = [
        {"elapsed_s": 0.0, "rss_bytes": None, "fd_count": None, "metric_error": "unavailable"},
        {"elapsed_s": 300.0, "rss_bytes": 1000, "fd_count": 10},
        {"elapsed_s": 600.0, "rss_bytes": 1000, "fd_count": 10},
    ]
    reasons = _reasons(samples=samples)
    assert "resource metric sampling failed 1 time(s)" in reasons


def test_fully_observed_healthy_soak_has_no_reasons():
    assert _reasons() == []
