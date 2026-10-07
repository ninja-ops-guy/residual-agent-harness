import io
import os
import sys

import pytest

from residual.browser_bridge import BrowserBridgeProvider, _decode, _encode
from residual.providers import ProviderError


def test_bridge_codec_roundtrip_unicode():
    value = {"ok": True, "text": "hello \u2603\nworld"}
    assert _decode(_encode(value)) == value


def test_bridge_provider_roundtrip(monkeypatch):
    class FixedUUID:
        hex = "abc123"

    monkeypatch.setattr("residual.browser_bridge.uuid.uuid4", lambda: FixedUUID())
    response = _encode({"ok": True, "text": '{"updates":{},"requests":[]}', "finish_reason": "stop"})
    read_fd, write_fd = os.pipe()
    os.write(write_fd, f"__RESIDUAL_BROWSER_RESPONSE__:abc123:{response}\n".encode())
    os.close(write_fd)
    reader = os.fdopen(read_fd, "r", encoding="utf-8")
    output = io.StringIO()
    monkeypatch.setattr(sys, "stdin", reader)
    monkeypatch.setattr(sys, "stdout", output)
    try:
        reply = BrowserBridgeProvider({"model": "gpt-5.6-luna", "timeout_seconds": 1}).generate({}, 32)
    finally:
        reader.close()
    assert reply.text == '{"updates":{},"requests":[]}'
    assert reply.finish_reason == "stop"
    marker = output.getvalue().strip()
    assert marker.startswith("__RESIDUAL_BROWSER_REQUEST__:abc123:")
    request = _decode(marker.split(":", 2)[2])
    assert request["model"] == "gpt-5.6-luna"
    assert request["max_output_tokens"] == 32
    assert len(request["messages"]) == 2


def test_bridge_provider_propagates_safe_remote_error(monkeypatch):
    class FixedUUID:
        hex = "deadbeef"

    monkeypatch.setattr("residual.browser_bridge.uuid.uuid4", lambda: FixedUUID())
    response = _encode({"ok": False, "error": "browser_bridge_auth_required"})
    read_fd, write_fd = os.pipe()
    os.write(write_fd, f"__RESIDUAL_BROWSER_RESPONSE__:deadbeef:{response}\n".encode())
    os.close(write_fd)
    reader = os.fdopen(read_fd, "r", encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", reader)
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    try:
        with pytest.raises(ProviderError, match="browser_bridge_auth_required"):
            BrowserBridgeProvider({"model": "gpt-5.6-luna", "timeout_seconds": 1}).generate({}, 32)
    finally:
        reader.close()
