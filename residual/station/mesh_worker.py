"""Host-side client for the scoped Shared Communications Mesh API.

This client does not grant authority locally. It persists outbound intent before
transport, synchronizes Station generation before authority-bearing calls, and
keeps application acknowledgement distinct from transport acknowledgement.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from residual.core import ContractError, canonical, strict_json
from residual.providers import NoRedirect
from .mesh import new_envelope
from .mesh_outbox import MeshOutbox


class MeshWorkerClient:
    def __init__(self, station, token, *, worker_id, outbox_path=None):
        url = urllib.parse.urlsplit(station)
        if url.scheme != "https" and not (url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}):
            raise ContractError("Use HTTPS for remote stations or a loopback SSH tunnel")
        if url.username or url.password or url.query or url.fragment:
            raise ContractError("Station URL must not contain credentials, query, or fragment")
        if not token:
            raise ContractError("A mesh enrollment token is required")
        if not worker_id:
            raise ContractError("worker_id is required")
        self.base = station.rstrip("/")
        self.token = token
        self.worker_id = worker_id
        self.outbox = MeshOutbox(outbox_path) if outbox_path else None
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.snapshots = {}

    def _headers(self, body=False):
        result = {"Authorization": "Bearer " + self.token}
        if body:
            result["Content-Type"] = "application/json"
        return result

    def request(self, route, data):
        req = urllib.request.Request(
            self.base + "/api/mesh/worker/" + route,
            data=canonical(data).encode("utf-8"),
            headers=self._headers(body=True),
        )
        with self.opener.open(req, timeout=600) as response:
            raw = response.read(500_001)
            if len(raw) > 500_000:
                raise ContractError("Mesh response exceeds 500 KB")
            return strict_json(raw.decode("utf-8"))

    def fetch(self, route, params):
        suffix = "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            self.base + "/api/mesh/worker/" + route + suffix,
            headers=self._headers(),
        )
        with self.opener.open(req, timeout=60) as response:
            raw = response.read(500_001)
            if len(raw) > 500_000:
                raise ContractError("Mesh response exceeds 500 KB")
            return strict_json(raw.decode("utf-8"))

    def sync(self, project_id):
        value = self.fetch("sync", {"project_id": project_id})["snapshot"]
        self.snapshots[project_id] = value
        return value

    def _snapshot(self, project_id):
        value = self.snapshots.get(project_id)
        if not value:
            raise ContractError("Synchronize the project before authority-bearing operations")
        return value

    def presence(self, project_id=None):
        return self.request("presence", {"project_id": project_id} if project_id else {})

    def messages(self, project_id, *, after=0, limit=100):
        return self.fetch("messages", {"project_id": project_id, "after": after, "limit": limit})

    def acknowledge(self, project_id, seq):
        result = self.request("ack", {"project_id": project_id, "seq": seq})
        if self.outbox is not None:
            # The Station cursor and local cursor intentionally advance independently;
            # inbox apply controls the local cursor.
            pass
        return result

    def _deliver_envelope(self, envelope):
        key = envelope["idempotency_key"]
        try:
            receipt = self.request("message", envelope)
        except (OSError, TimeoutError, urllib.error.URLError):
            lookup = self.fetch("receipt", {
                "project_id": envelope["project_id"],
                "idempotency_key": key,
                "kind": envelope["kind"],
            }).get("receipt")
            if lookup is None:
                raise
            receipt = lookup
        if self.outbox is not None:
            self.outbox.ack(key, receipt)
        return receipt

    def send(self, project_id, *, recipient, kind="message", payload=None, artifact_ref=None,
             correlation_id=None, causation_id=None, task=None, idempotency_key=None):
        snap = self._snapshot(project_id)
        bound = task or {}
        envelope = new_envelope(
            project_id=project_id,
            sender=self.worker_id,
            recipient=recipient,
            kind=kind,
            generation=snap["generation"],
            payload=payload,
            artifact_ref=artifact_ref,
            correlation_id=correlation_id,
            causation_id=causation_id,
            task_id=bound.get("task_id"),
            attempt=bound.get("attempt"),
            lease_id=bound.get("lease_id"),
            fencing_token=bound.get("fencing_token"),
            idempotency_key=idempotency_key,
        )
        if self.outbox is not None:
            self.outbox.enqueue(envelope["idempotency_key"], envelope)
        return self._deliver_envelope(envelope)

    def recover_outbox(self, *, max_attempts=8):
        if self.outbox is None:
            return {"acked": 0, "pending": 0}
        acked = 0
        for item in self.outbox.due(limit=50):
            try:
                self._deliver_envelope(item["value"])
                acked += 1
            except (OSError, TimeoutError, urllib.error.URLError):
                if item["attempts"] < max_attempts:
                    self.outbox.fail(item["operation_id"])
        return {"acked": acked, "pending": self.outbox.pending(),
                "oldest_age_s": self.outbox.oldest_age_s()}

    def claim(self, project_id, task_id=None):
        snap = self._snapshot(project_id)
        body = {"project_id": project_id, "generation": snap["generation"]}
        if task_id:
            body["task_id"] = task_id
        value = self.request("claim", body).get("work")
        return value

    def execution_admit(self, work, attempts):
        return self.request("execution-admit", {
            "project_id": work["project_id"],
            "generation": work["generation"],
            "task_id": work["task_id"],
            "lease_id": work["lease_id"],
            "fencing_token": work["fencing_token"],
            "attempts": attempts,
        })

    def heartbeat(self, work):
        return self.request("heartbeat", {
            "project_id": work["project_id"],
            "task_id": work["task_id"],
            "lease_id": work["lease_id"],
            "fencing_token": work["fencing_token"],
        })

    def admit_provider_attempt(self, work, *, placement, request_bytes):
        return self.request("admit", {
            "project_id": work["project_id"],
            "task_id": work["task_id"],
            "lease_id": work["lease_id"],
            "fencing_token": work["fencing_token"],
            "placement": placement,
            "request_bytes": request_bytes,
        })

    def submit_result(self, work, *, submission_id, response, usage=None, provider_attempts=None):
        data = {
            "project_id": work["project_id"],
            "generation": work["generation"],
            "task_id": work["task_id"],
            "attempt": work["attempt"],
            "lease_id": work["lease_id"],
            "fencing_token": work["fencing_token"],
            "submission_id": submission_id,
            "response": response,
        }
        if usage is not None:
            data["usage"] = usage
        if provider_attempts is not None:
            data["provider_attempts"] = provider_attempts
        return self.request("result", data)
