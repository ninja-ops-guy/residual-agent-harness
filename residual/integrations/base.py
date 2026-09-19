"""Shared integration connector base.

Implements ENT6-R6 (bidirectional flows: input from and output to
enterprise systems) and ENT6-R7 (every API call to an external system
produces an observation with target system, endpoint, request hash,
response hash, and latency).

All connectors work offline in tests via an injected ``Transport``;
real HTTP is provided by ``UrllibTransport`` behind the same interface.
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, runtime_checkable

from ..core import ContractError, canonical, digest, identifier


@dataclass(frozen=True)
class TransportResponse:
    """HTTP-style response returned by a Transport. Implements ENT6-R7."""

    status: int
    body: Any
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if type(self.status) is not int or not (100 <= self.status <= 599):
            raise ContractError("transport status must be an HTTP status code")

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


@runtime_checkable
class Transport(Protocol):
    """Injectable request transport. Implements ENT6-R7 (offline-testable).

    Implementations must be deterministic in tests; ``UrllibTransport``
    provides real HTTP in production.
    """

    def request(self, method: str, url: str, body: Any = None,
                headers: dict[str, str] | None = None) -> TransportResponse:
        ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Fail closed on redirects so trusted connector origins cannot pivot."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(
            req.full_url, code, "redirect refused", headers, fp
        )


class UrllibTransport:
    """Real HTTP transport built on urllib. Implements ENT6-R7."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        # Ignore ambient proxy configuration and never follow redirects. Both
        # properties matter for SSRF: a connector bound to one reviewed origin
        # must not be silently rerouted through a proxy or 30x target.
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect()
        )

    def request(self, method: str, url: str, body: Any = None,
                headers: dict[str, str] | None = None) -> TransportResponse:
        data = None if body is None else canonical(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method.upper(),
                                     headers=headers or {})
        try:
            with self.opener.open(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                parsed = json.loads(raw) if raw else None
                return TransportResponse(resp.status, parsed,
                                         dict(resp.headers.items()))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8")
            try:
                parsed = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = raw
            return TransportResponse(exc.code, parsed, dict(exc.headers.items()))


@dataclass(frozen=True)
class IntegrationObservation:
    """One observed API call. Implements ENT6-R7 verbatim: target system,
    endpoint, request hash, response hash, and latency."""

    target_system: str
    endpoint: str
    method: str
    request_hash: str
    response_hash: str
    latency_ms: float
    status: int

    def to_dict(self) -> dict:
        return {
            "target_system": self.target_system,
            "endpoint": self.endpoint,
            "method": self.method,
            "request_hash": self.request_hash,
            "response_hash": self.response_hash,
            "latency_ms": self.latency_ms,
            "status": self.status,
        }


@dataclass(frozen=True)
class ConnectorReceipt:
    """Receipt proving an integration outcome (verification, gating,
    evidence). Implements ENT6-R2 (pipeline gating waits for an
    ConnectorReceipt) and ENT6-R7."""

    integration: str
    action: str
    subject_id: str
    verdict: str  # "accepted" | "rejected" | "pending"
    payload_hash: str
    observations: tuple[IntegrationObservation, ...] = ()

    def __post_init__(self):
        identifier(self.integration)
        identifier(self.action)
        if not isinstance(self.subject_id, str) or not self.subject_id:
            raise ContractError("receipt subject_id must be nonempty")
        if self.verdict not in ("accepted", "rejected", "pending"):
            raise ContractError("receipt verdict must be accepted/rejected/pending")

    @property
    def accepted(self) -> bool:
        return self.verdict == "accepted"

    @property
    def receipt_hash(self) -> str:
        return digest({
            "integration": self.integration,
            "action": self.action,
            "subject_id": self.subject_id,
            "verdict": self.verdict,
            "payload_hash": self.payload_hash,
        })

    def to_dict(self) -> dict:
        return {
            "integration": self.integration,
            "action": self.action,
            "subject_id": self.subject_id,
            "verdict": self.verdict,
            "payload_hash": self.payload_hash,
            "receipt_hash": self.receipt_hash,
            "observations": [o.to_dict() for o in self.observations],
        }


class IntegrationConnector:
    """Base connector. Implements ENT6-R6 (bidirectional: ``import_task``
    pulls input, ``post_receipt``/``sync_status`` push output) and
    ENT6-R7 (every external call is observed with request/response
    hashes and latency, recorded in ``observations``).
    """

    system_name = "base"

    def __init__(self, base_url: str, token: str = "",
                 transport: Transport | None = None,
                 clock: Callable[[], float] = time.perf_counter):
        if not isinstance(base_url, str) or not base_url:
            raise ContractError("connector base_url must be nonempty")
        parsed = urllib.parse.urlsplit(base_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or any(ord(ch) < 33 for ch in base_url)
        ):
            raise ContractError(
                "connector base_url must be an HTTP(S) origin/path without "
                "credentials, query, fragment, or control characters"
            )
        self.base_url = urllib.parse.urlunsplit(
            (parsed.scheme.lower(), parsed.netloc, parsed.path.rstrip("/"), "", "")
        )
        self.token = token
        self.transport = transport or UrllibTransport()
        self.clock = clock
        self.observations: list[IntegrationObservation] = []

    # -- ENT6-R7 plumbing -------------------------------------------------

    def call(self, method: str, path: str, body: Any = None,
             headers: dict[str, str] | None = None) -> TransportResponse:
        """Perform one observed API call. Implements ENT6-R7."""
        if (
            not isinstance(path, str)
            or not path.startswith("/")
            or path.startswith("//")
            or "\\" in path
            or any(ord(ch) < 33 for ch in path)
        ):
            raise ContractError("connector endpoint must be a safe origin-relative path")
        endpoint = urllib.parse.urlsplit(path)
        if endpoint.scheme or endpoint.netloc:
            raise ContractError("connector endpoint must not override the configured origin")
        url = self.base_url + path
        merged = {"Content-Type": "application/json"}
        if self.token:
            merged["Authorization"] = f"Bearer {self.token}"
        if headers:
            merged.update(headers)
        start = self.clock()
        resp = self.transport.request(method.upper(), url, body, merged)
        latency_ms = (self.clock() - start) * 1000.0
        obs = IntegrationObservation(
            target_system=self.system_name,
            endpoint=url,
            method=method.upper(),
            request_hash=digest({"method": method.upper(), "url": url, "body": body}),
            response_hash=digest(resp.body),
            latency_ms=latency_ms,
            status=resp.status,
        )
        self.observations.append(obs)
        return resp

    def require_ok(self, resp: TransportResponse, what: str) -> Any:
        if not resp.ok:
            raise ContractError(f"{self.system_name}: {what} failed (status {resp.status})")
        return resp.body

    def receipt(self, action: str, subject_id: str, verdict: str,
                payload: Any) -> ConnectorReceipt:
        """Build an ConnectorReceipt carrying the observations made so far.
        Implements ENT6-R2 and ENT6-R7."""
        return ConnectorReceipt(
            integration=self.system_name,
            action=action,
            subject_id=subject_id,
            verdict=verdict,
            payload_hash=digest(payload),
            observations=tuple(self.observations),
        )

    # -- ENT6-R6 bidirectional surface (overridden per system) ------------

    def import_task(self, external_id: str) -> dict:
        raise NotImplementedError

    def post_receipt(self, external_id: str, receipt: ConnectorReceipt) -> TransportResponse:
        raise NotImplementedError

    def sync_status(self, external_id: str, task_status: str) -> TransportResponse:
        raise NotImplementedError
