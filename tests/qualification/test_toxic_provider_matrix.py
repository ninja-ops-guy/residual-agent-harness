from __future__ import annotations

import json
import tempfile
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from ai_providers import ProviderError
from residual.core import ContractError, canonical
from residual.station.models import model_call, save_settings
from residual.station.service import Station, demo_spec


class ToxicHandler(BaseHTTPRequestHandler):
    scenario = "valid"
    seen: list[dict] = []

    def log_message(self, *_args):
        pass

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(size))
        type(self).seen.append(body)
        scenario = type(self).scenario
        model = body.get("model")

        if scenario == "failover" and model == "primary":
            self.send_response(503); self.end_headers(); self.wfile.write(b"TOPSECRET upstream body"); return
        if scenario == "rate_limit":
            self.send_response(429); self.send_header("Retry-After", "0"); self.end_headers(); return
        if scenario == "server_error":
            self.send_response(503); self.end_headers(); self.wfile.write(b"TOPSECRET upstream body"); return
        if scenario == "malformed":
            payload = b'{"choices":['
        elif scenario == "duplicate_key":
            payload = b'{"choices":[],"choices":[]}'
        elif scenario == "oversized":
            payload = b'{"padding":"' + (b"x" * 2_100_000) + b'"}'
        else:
            finish = "length" if scenario == "truncated" else "stop"
            content = '{"answer":"ok"}' if body.get("response_format") else "Station online."
            payload = canonical({
                "id": "toxic-response",
                "model": model,
                "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": finish}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


@contextmanager
def toxic_provider(scenario: str):
    ToxicHandler.scenario = scenario
    ToxicHandler.seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), ToxicHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1"
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


def station_with_provider(url: str, *, failover: bool = False):
    temp = tempfile.TemporaryDirectory(prefix="residual-toxic-provider-")
    station = Station(temp.name)
    pid = station.create(demo_spec(), demo=True)["project_id"]
    settings = {
        "local": {
            "kind": "openai_compatible",
            "model": "primary",
            "base_url": url,
            "output_token_field": "max_tokens",
        },
        "local_credentials": {"api_key": "TEST-LOCAL-SECRET"},
    }
    if failover:
        settings["local_failover"] = ["fallback"]
    save_settings(station.store, settings)
    return temp, station, pid


@pytest.mark.parametrize("scenario,expected_code", [
    ("rate_limit", "rate_limit"),
    ("server_error", "server_error"),
    ("malformed", "invalid_response"),
    ("duplicate_key", "invalid_response"),
    ("oversized", "response_too_large"),
])
def test_toxic_provider_failures_are_bounded_and_secret_free(scenario: str, expected_code: str):
    with toxic_provider(scenario) as url:
        temp, station, pid = station_with_provider(url)
        try:
            with pytest.raises(ProviderError) as error:
                model_call(station.store, pid, "playground", {"message": "hello"}, "Be concise.", placement="local")
            assert error.value.code == expected_code
            retained = station.store.observation_export(pid)
            assert "TOPSECRET" not in retained
            assert "TEST-LOCAL-SECRET" not in retained
            assert expected_code in retained
        finally:
            temp.cleanup()


def test_toxic_provider_truncation_fails_closed_for_structured_output():
    with toxic_provider("truncated") as url:
        temp, station, pid = station_with_provider(url)
        try:
            with pytest.raises(ContractError, match="truncated"):
                model_call(
                    station.store, pid, "runner", {"task": "x"}, "Return JSON.",
                    schema={"type": "object"}, placement="local", tid="OPS-101",
                )
            assert "length" in station.store.observation_export(pid)
        finally:
            temp.cleanup()


def test_retryable_primary_failure_uses_counted_local_failover_and_records_both_attempts():
    with toxic_provider("failover") as url:
        temp, station, pid = station_with_provider(url, failover=True)
        try:
            reply = model_call(station.store, pid, "playground", {"message": "hello"}, "Be concise.", placement="local")
            assert reply["text"] == "Station online."
            assert [request["model"] for request in ToxicHandler.seen] == ["primary", "fallback"]
            retained = station.store.observation_export(pid)
            assert "primary" in retained and "fallback" in retained
            assert "TOPSECRET" not in retained
        finally:
            temp.cleanup()
