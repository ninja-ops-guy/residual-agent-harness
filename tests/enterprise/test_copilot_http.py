"""Socket-level tests for the bounded Copilot Studio HTTP adapter."""
from __future__ import annotations

import http.client
import json
import threading

import pytest

from residual.core import ContractError
from residual.integrations.copilot_studio import FixedWindowRateLimiter, create_server
from tests.enterprise.test_copilot_studio import make_api, make_token


def _run_server(api, **options):
    server = create_server("127.0.0.1", 0, api, **options)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _request(server, method, path, *, body=None, headers=None):
    host, port = server.server_address[:2]
    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        raw = response.read()
        parsed = json.loads(raw.decode("utf-8")) if raw else None
        return response.status, dict(response.getheaders()), parsed
    finally:
        conn.close()


def _mission_body(request_id="http-1"):
    return json.dumps({
        "request_id": request_id,
        "template_id": "firmware-repository-analysis",
        "objective": "Investigate the firmware failure",
        "inputs": {"repository_id": "firmware_sample"},
    }).encode("utf-8")


def test_valid_http_submission_and_security_headers():
    api, _, _ = make_api()
    server, thread = _run_server(api)
    try:
        status, headers, body = _request(
            server,
            "POST",
            "/v1/copilot/missions",
            body=_mission_body(),
            headers={
                "Authorization": "Bearer " + make_token(),
                "Content-Type": "application/json",
            },
        )
        assert status == 202
        assert body["state"] == "queued"
        assert headers["Cache-Control"] == "no-store"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize(
    ("content_type", "expected"),
    [
        ("text/plain", 415),
        ("application/x-www-form-urlencoded", 415),
        ("", 415),
    ],
)
def test_post_requires_json_content_type(content_type, expected):
    api, _, _ = make_api()
    server, thread = _run_server(api)
    try:
        headers = {"Authorization": "Bearer " + make_token()}
        if content_type:
            headers["Content-Type"] = content_type
        status, _, _ = _request(
            server, "POST", "/v1/copilot/missions",
            body=_mission_body("content-type"), headers=headers,
        )
        assert status == expected
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


def test_body_limit_rejects_before_json_processing():
    api, _, _ = make_api()
    server, thread = _run_server(api, max_body_bytes=1024)
    try:
        status, _, body = _request(
            server, "POST", "/v1/copilot/missions",
            body=b"x" * 2048,
            headers={
                "Authorization": "Bearer " + make_token(),
                "Content-Type": "application/json",
            },
        )
        assert status == 413
        assert body["code"] == "payload_too_large"
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


def test_duplicate_json_keys_are_rejected():
    api, _, _ = make_api()
    server, thread = _run_server(api)
    duplicate = (
        b'{"request_id":"a","request_id":"b",'
        b'"template_id":"firmware-repository-analysis",'
        b'"objective":"x","inputs":{"repository_id":"firmware_sample"}}'
    )
    try:
        status, _, body = _request(
            server, "POST", "/v1/copilot/missions",
            body=duplicate,
            headers={
                "Authorization": "Bearer " + make_token(),
                "Content-Type": "application/json",
            },
        )
        assert status == 400
        assert body["code"] == "invalid_json"
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


def test_query_parameters_are_not_an_unreviewed_input_channel():
    api, _, _ = make_api()
    server, thread = _run_server(api)
    try:
        status, _, body = _request(
            server, "GET", "/v1/copilot/missions/anything?role=admin",
            headers={"Authorization": "Bearer " + make_token()},
        )
        assert status == 400
        assert body["code"] == "invalid_route"
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


def test_local_rate_limiter_fails_closed():
    api, _, _ = make_api()
    limiter = FixedWindowRateLimiter(limit=1, window_s=60)
    server, thread = _run_server(api, limiter=limiter)
    try:
        first, _, _ = _request(
            server, "POST", "/v1/copilot/missions",
            body=_mission_body("rate-1"),
            headers={
                "Authorization": "Bearer " + make_token(),
                "Content-Type": "application/json",
            },
        )
        second, _, body = _request(
            server, "GET", "/v1/copilot/missions/not-a-real-id",
            headers={"Authorization": "Bearer " + make_token()},
        )
        assert first == 202
        assert second == 429
        assert body["code"] == "rate_limited"
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


def test_non_loopback_cleartext_requires_explicit_proxy_trust():
    api, _, _ = make_api()
    with pytest.raises(ContractError, match="TLS|reverse proxy"):
        create_server("0.0.0.0", 0, api)


def test_method_not_allowed_does_not_enter_gateway():
    api, _, backend = make_api()
    server, thread = _run_server(api)
    try:
        status, _, body = _request(
            server, "PUT", "/v1/copilot/missions",
            body=_mission_body("put"),
            headers={
                "Authorization": "Bearer " + make_token(),
                "Content-Type": "application/json",
            },
        )
        assert status == 405
        assert body["code"] == "method_not_allowed"
        assert backend.bindings == []
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)
