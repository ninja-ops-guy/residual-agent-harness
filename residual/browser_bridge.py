"""Browser-hosted inference transport for the static WebVM demo.

This provider keeps RESIDUAL execution inside the guest Linux VM while delegating
only model inference to a same-page browser host.  The transport is deliberately
simple and bounded: one request/response line over the VM's PTY, base64 encoded so
model text can never be interpreted as terminal control input.
"""
from __future__ import annotations

import base64
import json
import select
import sys
import time
import uuid

from .core import ContractError, canonical, positive_int, strict_json
from .providers import Provider, ProviderError, Reply, Usage

_REQUEST = "__RESIDUAL_BROWSER_REQUEST__"
_RESPONSE = "__RESIDUAL_BROWSER_RESPONSE__"


def _encode(obj: dict) -> str:
    return base64.urlsafe_b64encode(canonical(obj).encode("utf-8")).decode("ascii")


def _decode(value: str) -> dict:
    try:
        raw = base64.urlsafe_b64decode(value.encode("ascii")).decode("utf-8")
        obj = strict_json(raw)
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProviderError("browser_bridge_invalid_response") from None
    if not isinstance(obj, dict):
        raise ProviderError("browser_bridge_invalid_response")
    return obj


class BrowserBridgeProvider(Provider):
    """Inference provider backed by a browser-side host such as Puter.js.

    The provider writes a single base64 JSON request marker to stdout and waits for
    the host to feed a matching response marker to stdin.  Normal user keystrokes
    are ignored while a request is outstanding.
    """

    placement = "remote"

    def __init__(self, spec: dict):
        spec = dict(spec)
        model = spec.pop("model", "gpt-5.6-luna")
        placement = spec.pop("placement", "remote")
        timeout = spec.pop("timeout_seconds", 90)
        if spec:
            raise ContractError("unsupported browser bridge option")
        if not isinstance(model, str) or not model:
            raise ContractError("browser bridge requires a model")
        if placement != "remote":
            raise ContractError("browser bridge placement must be remote")
        if type(timeout) not in (int, float) or not 0 < timeout <= 600:
            raise ContractError("browser bridge timeout must be within (0, 600]")
        self.model = model
        self.name = f"browser_bridge:{model}"
        self.timeout = float(timeout)

    def generate(self, packet: dict, max_output_tokens: int) -> Reply:
        positive_int(max_output_tokens, "max_output_tokens")
        request_id = uuid.uuid4().hex
        messages = super().payload(packet, max_output_tokens)["messages"]
        request = {
            "id": request_id,
            "model": self.model,
            "messages": messages,
            "max_output_tokens": max_output_tokens,
        }
        marker = f"{_REQUEST}:{request_id}:{_encode(request)}"
        print(marker, flush=True)

        start = time.monotonic()
        deadline = start + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProviderError("browser_bridge_timeout")
            try:
                ready, _, _ = select.select([sys.stdin], [], [], remaining)
            except (OSError, ValueError):
                raise ProviderError("browser_bridge_stdin_unavailable") from None
            if not ready:
                raise ProviderError("browser_bridge_timeout")
            line = sys.stdin.readline()
            if not line:
                raise ProviderError("browser_bridge_closed")
            line = line.rstrip("\r\n")
            prefix = f"{_RESPONSE}:{request_id}:"
            if not line.startswith(prefix):
                continue
            response = _decode(line[len(prefix):])
            if response.get("ok") is not True:
                code = response.get("error")
                if not isinstance(code, str) or not code:
                    code = "browser_bridge_remote_error"
                raise ProviderError(code)
            text = response.get("text")
            if not isinstance(text, str):
                raise ProviderError("browser_bridge_invalid_response")
            usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
            inp = usage.get("input_tokens") if type(usage.get("input_tokens")) is int else None
            out = usage.get("output_tokens") if type(usage.get("output_tokens")) is int else None
            source = "reported" if inp is not None and out is not None else "unavailable"
            return Reply(text, Usage(inp, out, None, source),
                         (time.monotonic() - start) * 1000,
                         response.get("finish_reason") if isinstance(response.get("finish_reason"), str) else None)


def register(registry):
    registry.provider("browser_bridge", BrowserBridgeProvider)
