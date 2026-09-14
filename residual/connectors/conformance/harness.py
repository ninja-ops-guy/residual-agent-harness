"""Connector contract conformance suite (Track M).

Implements M-R1..M-R4. ``ScriptedTransport`` simulates a remote system
(auth expiry, rate limits, flaky 5xx, malformed bodies, pagination) entirely
offline; ``ResilientConnector`` is the reference connector under
certification; ``ConformanceSuite`` runs the contract checks and emits a
``CertificationMatrix``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from ...core import ContractError, digest
from ...integrations.base import IntegrationConnector, TransportResponse


# ---------------------------------------------------------------------------
# Scripted transport (M-R1)
# ---------------------------------------------------------------------------

class ScriptedTransport:
    """Deterministic offline transport. Implements M-R1.

    ``script`` maps (method, path-suffix) to a list of responses consumed in
    order; when the list is exhausted the last response repeats. A response
    may also be a callable receiving the request context. Every request is
    recorded for evidence.
    """

    def __init__(self):
        self.script: dict[tuple[str, str], list] = {}
        self.requests: list[dict] = []

    def add(self, method: str, path: str, *responses) -> "ScriptedTransport":
        self.script.setdefault((method.upper(), path), []).extend(responses)
        return self

    def request(self, method: str, url: str, body: Any = None,
                headers: dict[str, str] | None = None) -> TransportResponse:
        self.requests.append({"method": method.upper(), "url": url,
                              "body": body, "headers": dict(headers or {})})
        bare_url = url.split("?", 1)[0]
        for (m, path), responses in self.script.items():
            if method.upper() == m and bare_url.endswith(path):
                if not responses:
                    break
                item = responses.pop(0) if len(responses) > 1 else responses[0]
                resp = item(self.requests[-1]) if callable(item) else item
                if isinstance(resp, Exception):
                    raise resp
                return resp
        return TransportResponse(404, {"error": "no scripted response"}, {})

    def count(self, method: str, path: str) -> int:
        return sum(1 for r in self.requests
                   if r["method"] == method.upper() and r["url"].endswith(path))


# ---------------------------------------------------------------------------
# Reference connector under certification
# ---------------------------------------------------------------------------

class ResilientConnector(IntegrationConnector):
    """Reference connector implementing the M-R2 contract behaviors:
    re-auth on 401, cursor pagination, bounded retry with backoff on 5xx,
    Retry-After handling on 429, stable idempotency keys on mutations, and
    webhook deduplication.
    """

    system_name = "resilient-reference"

    def __init__(self, base_url: str, token: str = "",
                 transport=None, max_attempts: int = 4,
                 clock=lambda: 0.0, sleep: Callable[[float], None] | None = None):
        super().__init__(base_url, token=token, transport=transport, clock=clock)
        self.max_attempts = max_attempts
        self._sleep = sleep or (lambda seconds: None)
        self.waits: list[float] = []
        self._seen_webhooks: set[str] = set()
        self.reauths = 0

    # -- retry / backoff / 429 / idempotency ------------------------------

    def call_resilient(self, method: str, path: str, body: Any = None,
                       idempotency_key: str | None = None) -> TransportResponse:
        """Call with bounded retry, exponential backoff, Retry-After support,
        re-auth on 401, and a stable Idempotency-Key header on mutations."""
        headers = {}
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        reauthed = False
        for attempt in range(self.max_attempts):
            resp = self.call(method, path, body, headers or None)
            if resp.status == 401 and not reauthed:
                self.reauth()
                reauthed = True
                continue
            if resp.status == 429:
                wait = float(resp.headers.get("Retry-After", 2 ** attempt))
                self.waits.append(wait)
                self._sleep(wait)
                continue
            if resp.status >= 500:
                wait = float(2 ** attempt) / 10.0
                self.waits.append(wait)
                self._sleep(wait)
                continue
            return resp
        raise ContractError(
            f"{self.system_name}: exhausted {self.max_attempts} attempts for {method} {path}")

    def reauth(self) -> None:
        resp = self.call("POST", "/auth/token", {"grant_type": "client_credentials"})
        body = self.require_ok(resp, "re-authentication")
        token = body.get("access_token") if isinstance(body, dict) else None
        if not isinstance(token, str) or not token:
            raise ContractError("re-authentication returned no access token")
        self.token = token
        self.reauths += 1

    # -- pagination --------------------------------------------------------

    def fetch_all(self, path: str, items_key: str = "items",
                  cursor_key: str = "next_cursor") -> list:
        """Follow cursor pagination until no next cursor is returned."""
        items: list = []
        cursor: str | None = None
        while True:
            paged = path + (("?cursor=" + cursor) if cursor else "")
            resp = self.call_resilient("GET", paged)
            body = self.require_ok(resp, f"paginated fetch of {path}")
            if not isinstance(body, dict) or not isinstance(body.get(items_key), list):
                raise ContractError(f"malformed page body for {path}")
            items.extend(body[items_key])
            cursor = body.get(cursor_key)
            if not cursor:
                return items

    # -- webhooks ----------------------------------------------------------

    def handle_webhook(self, delivery_id: str, payload: Any) -> bool:
        """Process a webhook exactly once per delivery_id. Returns True when
        the delivery was new, False for duplicates."""
        if not isinstance(delivery_id, str) or not delivery_id:
            raise ContractError("webhook delivery_id must be nonempty")
        if delivery_id in self._seen_webhooks:
            return False
        self._seen_webhooks.add(delivery_id)
        return True

    # -- IntegrationConnector bidirectional surface ------------------------

    def import_task(self, external_id: str) -> dict:
        resp = self.call_resilient("GET", f"/tasks/{external_id}")
        return self.require_ok(resp, "import_task")

    def post_receipt(self, receipt: dict) -> str:
        key = digest({"action": "post_receipt", "receipt": receipt})
        resp = self.call_resilient("POST", "/receipts", receipt, idempotency_key=key)
        body = self.require_ok(resp, "post_receipt")
        return body.get("id", "") if isinstance(body, dict) else ""


# ---------------------------------------------------------------------------
# Suite + certification matrix (M-R2..M-R4)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CheckResult:
    """Outcome of one contract check. Implements M-R3."""

    check_id: str
    requirement: str
    passed: bool
    evidence: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"check_id": self.check_id, "requirement": self.requirement,
                "passed": self.passed, "evidence": self.evidence}


@dataclass(frozen=True)
class CertificationMatrix:
    """Aggregate certification result. Implements M-R4."""

    connector: str
    results: tuple[CheckResult, ...]

    @property
    def certified(self) -> bool:
        return all(r.passed for r in self.results)

    def to_json(self) -> str:
        return json.dumps({
            "connector": self.connector,
            "certified": self.certified,
            "checks": [r.to_dict() for r in self.results],
        }, indent=2, sort_keys=True)

    def to_markdown(self) -> str:
        lines = [
            f"# Connector Certification Matrix — {self.connector}",
            "",
            f"**Certified:** {'YES' if self.certified else 'NO'}",
            "",
            "| Check | Requirement | Result |",
            "| --- | --- | --- |",
        ]
        for r in self.results:
            lines.append(f"| {r.check_id} | {r.requirement} | "
                         f"{'PASS' if r.passed else 'FAIL'} |")
        return "\n".join(lines) + "\n"


class ConformanceSuite:
    """Runs the M-R2 contract checks against a fresh connector per check so
    failures cannot contaminate each other (M-R3)."""

    def __init__(self, connector_factory: Callable[[ScriptedTransport], ResilientConnector]):
        self.connector_factory = connector_factory

    # -- individual checks --------------------------------------------------

    def check_auth_expiry(self) -> CheckResult:
        t = ScriptedTransport()
        t.add("GET", "/tasks/t1", TransportResponse(401, {"error": "token expired"}, {}),
              TransportResponse(200, {"id": "t1"}, {}))
        t.add("POST", "/auth/token", TransportResponse(200, {"access_token": "fresh"}, {}))
        conn = self.connector_factory(t)
        try:
            body = conn.import_task("t1")
            ok = body == {"id": "t1"} and conn.reauths == 1 and conn.token == "fresh"
            return CheckResult("auth_expiry", "M-R2.auth-expiry", ok,
                               {"reauths": conn.reauths, "token": conn.token})
        except ContractError as exc:
            return CheckResult("auth_expiry", "M-R2.auth-expiry", False, {"error": str(exc)})

    def check_pagination(self) -> CheckResult:
        t = ScriptedTransport()
        t.add("GET", "/items",
              TransportResponse(200, {"items": [1, 2], "next_cursor": "c2"}, {}),
              TransportResponse(200, {"items": [3], "next_cursor": None}, {}))
        conn = self.connector_factory(t)
        try:
            items = conn.fetch_all("/items")
            return CheckResult("pagination", "M-R2.pagination",
                               items == [1, 2, 3], {"items": items})
        except ContractError as exc:
            return CheckResult("pagination", "M-R2.pagination", False, {"error": str(exc)})

    def check_retry_backoff(self) -> CheckResult:
        t = ScriptedTransport()
        t.add("GET", "/tasks/flaky",
              TransportResponse(500, {"error": "boom"}, {}),
              TransportResponse(500, {"error": "boom"}, {}),
              TransportResponse(200, {"id": "flaky"}, {}))
        conn = self.connector_factory(t)
        try:
            body = conn.import_task("flaky")
            waits = conn.waits
            ok = (body == {"id": "flaky"} and len(waits) == 2
                  and waits[0] < waits[1])  # backoff must increase
            return CheckResult("retry_backoff", "M-R2.retry-backoff", ok, {"waits": waits})
        except ContractError as exc:
            return CheckResult("retry_backoff", "M-R2.retry-backoff", False, {"error": str(exc)})

    def check_http_429(self) -> CheckResult:
        t = ScriptedTransport()
        t.add("GET", "/tasks/limited",
              TransportResponse(429, {"error": "rate limited"}, {"Retry-After": "7"}),
              TransportResponse(200, {"id": "limited"}, {}))
        conn = self.connector_factory(t)
        try:
            body = conn.import_task("limited")
            ok = body == {"id": "limited"} and conn.waits and conn.waits[0] >= 7.0
            return CheckResult("http_429", "M-R2.http-429", ok, {"waits": conn.waits})
        except ContractError as exc:
            return CheckResult("http_429", "M-R2.http-429", False, {"error": str(exc)})

    def check_duplicate_webhooks(self) -> CheckResult:
        conn = self.connector_factory(ScriptedTransport())
        first = conn.handle_webhook("delivery-1", {"event": "x"})
        second = conn.handle_webhook("delivery-1", {"event": "x"})
        third = conn.handle_webhook("delivery-2", {"event": "y"})
        ok = first is True and second is False and third is True
        return CheckResult("duplicate_webhooks", "M-R2.duplicate-webhooks", ok,
                           {"first": first, "duplicate": second, "distinct": third})

    def check_malformed_responses(self) -> CheckResult:
        t = ScriptedTransport()
        t.add("GET", "/items", TransportResponse(200, "not-a-page-object", {}))
        conn = self.connector_factory(t)
        try:
            conn.fetch_all("/items")
            return CheckResult("malformed_responses", "M-R2.malformed-responses", False,
                               {"error": "connector accepted malformed body"})
        except ContractError as exc:
            # Must fail cleanly with ContractError, not an unhandled exception.
            return CheckResult("malformed_responses", "M-R2.malformed-responses",
                               True, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - any other exception is a defect
            return CheckResult("malformed_responses", "M-R2.malformed-responses",
                               False, {"error": f"unhandled {type(exc).__name__}: {exc}"})

    def check_idempotency_keys(self) -> CheckResult:
        t = ScriptedTransport()
        t.add("POST", "/receipts",
              TransportResponse(500, {"error": "boom"}, {}),
              TransportResponse(200, {"id": "r1"}, {}))
        conn = self.connector_factory(t)
        try:
            conn.post_receipt({"receipt_hash": "abc"})
            posts = [r for r in t.requests if r["method"] == "POST"
                     and r["url"].endswith("/receipts")]
            keys = [r["headers"].get("Idempotency-Key") for r in posts]
            ok = len(posts) == 2 and keys[0] and keys[0] == keys[1]
            return CheckResult("idempotency_keys", "M-R2.idempotency-keys", ok,
                               {"attempts": len(posts), "keys": keys})
        except ContractError as exc:
            return CheckResult("idempotency_keys", "M-R2.idempotency-keys", False,
                               {"error": str(exc)})

    def run(self) -> CertificationMatrix:
        """Run every check; a failing check MUST NOT abort the rest (M-R3)."""
        checks = [
            self.check_auth_expiry, self.check_pagination, self.check_retry_backoff,
            self.check_http_429, self.check_duplicate_webhooks,
            self.check_malformed_responses, self.check_idempotency_keys,
        ]
        results: list[CheckResult] = []
        for check in checks:
            try:
                results.append(check())
            except Exception as exc:  # noqa: BLE001 - suite must never crash
                results.append(CheckResult(check.__name__.removeprefix("check_"),
                                           "M-R2", False,
                                           {"error": f"suite error: {type(exc).__name__}: {exc}"}))
        probe = self.connector_factory(ScriptedTransport())
        return CertificationMatrix(connector=probe.system_name, results=tuple(results))


def run_conformance_suite(base_url: str = "https://conformance.local") -> CertificationMatrix:
    """Certify the reference ResilientConnector. Implements M-R1..M-R4."""
    suite = ConformanceSuite(
        lambda transport: ResilientConnector(base_url, token="initial", transport=transport))
    return suite.run()
