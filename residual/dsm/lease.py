"""Lease manager with monotonic fencing tokens (DSM-R5).

A lease grants a holder exclusive write eligibility for a resource until an
expiry instant. Every acquisition/renewal bumps a per-resource fencing
token. Any write presenting a token lower than the resource's current token
is a stale-lease write and MUST fail closed.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager

from residual.core import ContractError


class FencingError(ContractError):
    pass


class LeaseManager:
    def __init__(self):
        # resource -> {"holder": str, "until": int, "token": int}
        self._leases = {}
        self._tokens = {}
        self._lock = threading.RLock()

    def acquire(self, resource, holder, ttl_ms, now_ms):
        with self._lock:
            lease = self._leases.get(resource)
            if lease and lease["holder"] != holder and now_ms < lease["until"]:
                raise FencingError(
                    f"resource {resource!r} is leased to {lease['holder']!r} until {lease['until']}"
                )
            token = self._tokens.get(resource, 0) + 1
            self._tokens[resource] = token
            self._leases[resource] = {"holder": holder, "until": now_ms + ttl_ms, "token": token}
            return {"resource": resource, "holder": holder, "fencing_token": token,
                    "expires_at_ms": now_ms + ttl_ms}

    def renew(self, resource, holder, fencing_token, ttl_ms, now_ms):
        with self._lock:
            self.check(resource, holder, fencing_token, now_ms)
            token = self._tokens[resource] + 1
            self._tokens[resource] = token
            self._leases[resource] = {"holder": holder, "until": now_ms + ttl_ms, "token": token}
            return {"resource": resource, "holder": holder, "fencing_token": token,
                    "expires_at_ms": now_ms + ttl_ms}

    def release(self, resource, holder, fencing_token):
        with self._lock:
            lease = self._leases.get(resource)
            if lease and lease["holder"] == holder and lease["token"] == fencing_token:
                del self._leases[resource]

    def check(self, resource, holder, fencing_token, now_ms):
        """Fail closed for stale, expired, or foreign tokens (DSM-R5)."""
        with self._lock:
            current = self._tokens.get(resource, 0)
            if fencing_token < current:
                raise FencingError(
                    f"stale fencing token {fencing_token} for {resource!r} (current: {current})"
                )
            lease = self._leases.get(resource)
            if lease is None:
                raise FencingError(f"no active lease for {resource!r}")
            if lease["holder"] != holder or lease["token"] != fencing_token:
                raise FencingError(f"fencing token does not match active lease for {resource!r}")
            if now_ms >= lease["until"]:
                raise FencingError(f"lease for {resource!r} expired at {lease['until']}")
            return True

    @contextmanager
    def commit_guard(self, resource, holder, fencing_token, now_ms):
        """Hold the local lease lock from validation through authoritative commit."""
        with self._lock:
            self.check(resource, holder, fencing_token, now_ms)
            yield

    def current_token(self, resource):
        with self._lock:
            return self._tokens.get(resource, 0)
