"""Hardened stdlib HTTP adapter for the Copilot Studio gateway.

The adapter is deliberately small: it enforces transport-level request bounds
and delegates identity/authorization to CopilotAPI. TLS may terminate here or
at an explicitly trusted reverse proxy; distributed edge throttling remains a
deployment responsibility in addition to the local limiter below.
"""
from __future__ import annotations

import ipaddress
import json
import ssl
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import urlsplit

from ...core import ContractError, canonical, strict_json
from .gateway import APIResponse, CopilotAPI

DEFAULT_MAX_BODY_BYTES = 128 * 1024
DEFAULT_MAX_PATH_BYTES = 512
DEFAULT_REQUEST_TIMEOUT_S = 15.0


class FixedWindowRateLimiter:
    """Thread-safe, process-local defense-in-depth request limiter."""

    def __init__(self, *, limit: int = 120, window_s: float = 60.0,
                 clock: Callable[[], float] = time.monotonic):
        if type(limit) is not int or limit < 1:
            raise ContractError("rate limit must be a positive integer")
        if type(window_s) not in (int, float) or window_s <= 0:
            raise ContractError("rate window must be positive")
        if not callable(clock):
            raise ContractError("rate limiter clock must be callable")
        self.limit = limit
        self.window_s = float(window_s)
        self._clock = clock
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        if not isinstance(key, str) or not key:
            key = "unknown"
        now = float(self._clock())
        cutoff = now - self.window_s
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True


def _loopback(host: str) -> bool:
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class CopilotHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False


def make_handler(
    api: CopilotAPI,
    *,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    max_path_bytes: int = DEFAULT_MAX_PATH_BYTES,
    request_timeout_s: float = DEFAULT_REQUEST_TIMEOUT_S,
    limiter: FixedWindowRateLimiter | None = None,
):
    if not isinstance(api, CopilotAPI):
        raise ContractError("api must be a CopilotAPI")
    if type(max_body_bytes) is not int or not 1024 <= max_body_bytes <= 16 * 1024 * 1024:
        raise ContractError("max_body_bytes is out of bounds")
    if type(max_path_bytes) is not int or not 64 <= max_path_bytes <= 8192:
        raise ContractError("max_path_bytes is out of bounds")
    if type(request_timeout_s) not in (int, float) or not 1 <= request_timeout_s <= 120:
        raise ContractError("request_timeout_s is out of bounds")
    limiter = limiter or FixedWindowRateLimiter()

    class Handler(BaseHTTPRequestHandler):
        server_version = "RESIDUAL-Copilot/1"
        sys_version = ""

        def setup(self):
            super().setup()
            self.connection.settimeout(float(request_timeout_s))

        def log_message(self, format, *args):
            # Do not log Authorization headers or request bodies through the
            # default HTTP handler. Deployment logging belongs in CopilotAPI's
            # redacted audit sink.
            return

        def _send(self, response: APIResponse, *, head_only: bool = False) -> None:
            body = canonical(response.body).encode("utf-8")
            self.send_response(response.status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Pragma", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            if response.status == 401:
                self.send_header("WWW-Authenticate", "Bearer")
            self.end_headers()
            if not head_only:
                self.wfile.write(body)

        def _error(self, status: int, code: str, message: str) -> None:
            self._send(APIResponse(status, {"code": code, "message": message}))

        def _admit_transport(self) -> tuple[str, str] | None:
            if len(self.path.encode("utf-8", errors="ignore")) > max_path_bytes:
                self._error(414, "uri_too_long", "request path is too long")
                return None
            parsed = urlsplit(self.path)
            if parsed.query or parsed.fragment:
                self._error(400, "invalid_route", "query parameters are not supported")
                return None
            key = self.client_address[0] if self.client_address else "unknown"
            if not limiter.allow(str(key)):
                self._send(APIResponse(
                    429,
                    {"code": "rate_limited", "message": "request rate limit exceeded"},
                ))
                return None
            return self.command.upper(), parsed.path

        def _read_json(self) -> dict | None:
            transfer = self.headers.get("Transfer-Encoding")
            if transfer:
                self._error(400, "unsupported_transfer_encoding",
                            "chunked request bodies are not supported")
                return None
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                self._error(411, "length_required", "Content-Length is required")
                return None
            try:
                length = int(raw_length)
            except ValueError:
                self._error(400, "invalid_content_length", "invalid Content-Length")
                return None
            if length < 0:
                self._error(400, "invalid_content_length", "invalid Content-Length")
                return None
            if length > max_body_bytes:
                self._error(413, "payload_too_large", "request body exceeds limit")
                return None
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/json":
                self._error(415, "unsupported_media_type",
                            "Content-Type must be application/json")
                return None
            raw = self.rfile.read(length)
            if len(raw) != length:
                self._error(400, "incomplete_body", "request body was incomplete")
                return None
            try:
                text = raw.decode("utf-8")
                data = strict_json(text)
            except (UnicodeDecodeError, ContractError, ValueError, json.JSONDecodeError):
                self._error(400, "invalid_json", "request body must be strict UTF-8 JSON")
                return None
            if not isinstance(data, dict):
                self._error(400, "invalid_json", "request body must be a JSON object")
                return None
            return data

        def do_GET(self):
            admitted = self._admit_transport()
            if admitted is None:
                return
            method, path = admitted
            response = api.handle(
                method, path, self.headers.get("Authorization"), None,
                now=int(time.time()),
            )
            self._send(response)

        def do_POST(self):
            admitted = self._admit_transport()
            if admitted is None:
                return
            method, path = admitted
            payload = self._read_json()
            if payload is None:
                return
            response = api.handle(
                method, path, self.headers.get("Authorization"), payload,
                now=int(time.time()),
            )
            self._send(response)

        def do_HEAD(self):
            self._error(405, "method_not_allowed", "method not allowed")

        def do_PUT(self):
            self._error(405, "method_not_allowed", "method not allowed")

        def do_PATCH(self):
            self._error(405, "method_not_allowed", "method not allowed")

        def do_DELETE(self):
            self._error(405, "method_not_allowed", "method not allowed")

        def do_OPTIONS(self):
            self._error(405, "method_not_allowed", "method not allowed")

    return Handler


def create_server(
    host: str,
    port: int,
    api: CopilotAPI,
    *,
    ssl_context: ssl.SSLContext | None = None,
    trusted_reverse_proxy: bool = False,
    **handler_options,
) -> CopilotHTTPServer:
    """Create the HTTP server with explicit transport trust.

    Plain HTTP is accepted only on loopback, or when the caller explicitly
    declares that TLS terminates at a trusted reverse proxy. This prevents an
    accidental public clear-text deployment from being the default.
    """
    if not isinstance(host, str) or not host:
        raise ContractError("host is required")
    if type(port) is not int or not 0 <= port <= 65535:
        raise ContractError("port is invalid")
    if type(trusted_reverse_proxy) is not bool:
        raise ContractError("trusted_reverse_proxy must be boolean")
    if ssl_context is None and not (_loopback(host) or trusted_reverse_proxy):
        raise ContractError(
            "non-loopback Copilot HTTP requires TLS or an explicitly trusted reverse proxy"
        )
    handler = make_handler(api, **handler_options)
    server = CopilotHTTPServer((host, port), handler)
    if ssl_context is not None:
        server.socket = ssl_context.wrap_socket(server.socket, server_side=True)
    return server
