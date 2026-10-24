"""Policy-bounded whole-attempt provider continuity from the R3.4 contract."""
from __future__ import annotations

import urllib.parse

from ai_providers import ProviderError
from residual.core import ContractError


def _endpoint(provider):
    profile = getattr(provider, "profile", {}) or {}
    raw = profile.get("base_url", "")
    if raw:
        try:
            u = urllib.parse.urlsplit(raw)
            host = (u.hostname or "").lower()
            port = u.port or (443 if u.scheme == "https" else 80)
            return (u.scheme.lower(), host, port)
        except (ValueError, TypeError):
            raise ContractError("Provider continuity route has an invalid endpoint") from None
    return ("provider", str(getattr(provider, "kind", getattr(provider, "name", "unknown"))), 0)


def _placement(provider):
    value = getattr(provider, "placement", None)
    if value not in {"local", "remote"}:
        raise ContractError("Continuity provider must declare local or remote placement")
    return value


def _route_placement(route):
    if route == "local":
        return "local"
    if route == "cloud":
        return "remote"
    raise ContractError("Task route must be local or cloud")


class ContinuityProvider:
    """Try complete provider attempts in a fixed policy order.

    Partial streams are deliberately outside this interface: each provider must
    return a complete Reply or raise. The same endpoint cannot appear twice as
    an independent failure domain merely by changing model IDs.
    """

    def __init__(self, providers, *, cross_placement=False):
        values = list(providers)
        if not values or len(values) > 5:
            raise ContractError("Continuity requires one to five bounded provider routes")
        domains = set()
        for provider in values:
            domain = (_placement(provider), _endpoint(provider))
            if domain in domains:
                raise ContractError("Continuity routes must use independent endpoint failure domains")
            domains.add(domain)
        self.providers = tuple(values)
        self.cross_placement = bool(cross_placement)

    @property
    def accepted_routes(self):
        placements = {_placement(p) for p in self.providers}
        result = set()
        if "local" in placements:
            result.add("local")
        if "remote" in placements:
            result.add("cloud")
        return result

    def generate(self, packet, max_tokens, task_route, *, before_attempt=None, after_attempt=None):
        wanted = _route_placement(task_route)
        same = [p for p in self.providers if _placement(p) == wanted]
        cross = [p for p in self.providers if _placement(p) != wanted] if self.cross_placement else []
        candidates = same + cross
        if not candidates:
            raise ContractError("No approved provider route matches the task placement")
        last = None
        for attempt, provider in enumerate(candidates, 1):
            if before_attempt is not None:
                before_attempt(provider, packet, max_tokens)
            try:
                reply = provider.generate(packet, max_tokens)
            except ProviderError as error:
                last = error
                if after_attempt is not None:
                    after_attempt(provider, attempt, None, error)
                if not error.failover_allowed:
                    raise
                continue
            if after_attempt is not None:
                after_attempt(provider, attempt, reply, None)
            return provider, reply
        raise last or ContractError("Provider continuity exhausted without a complete response")
