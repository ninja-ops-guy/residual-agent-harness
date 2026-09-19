"""Qualification tests for the encrypted Copilot mission queue backend."""
from __future__ import annotations

import os
import sqlite3
import stat

import pytest

from residual.core import ContractError
from residual.crypto.provider import LocalDevCryptoProvider
from residual.integrations.copilot_studio.backend import EncryptedMissionQueueBackend
from tests.enterprise.test_copilot_studio import (
    auth,
    make_api,
    make_token,
    payload,
    submit,
)


class Clock:
    def __init__(self, now=1000.0):
        self.now = float(now)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += float(seconds)


def _backend(tmp_path, *, clock=None):
    if os.name == "posix":
        os.chmod(tmp_path, 0o700)
    crypto = LocalDevCryptoProvider(
        signing_key=b"s" * 32,
        encryption_key=b"e" * 32,
    )
    return EncryptedMissionQueueBackend(
        tmp_path / "missions.db",
        crypto,
        clock=clock or Clock(),
    )


def test_gateway_submits_encrypted_durable_mission_and_worker_claims_exact_plan(tmp_path):
    backend = _backend(tmp_path)
    api, _, _ = make_api(backend=backend)
    response = submit(
        api,
        body=payload(
            request_id="queue-submit",
            objective="Investigate a bootloader regression",
            inputs={"repository_id": "firmware_secure"},
        ),
    )
    assert response.status == 202
    mission_id = response.body["mission_id"]
    assert backend.status(mission_id)["state"] == "queued"

    work = backend.claim_next("firmware_worker")
    assert work is not None
    assert work.binding.mission_id == mission_id
    assert work.binding.plan_hash == work.plan.graph_hash
    assert work.binding.request_hash == work.request.request_hash
    assert work.request.inputs == {"repository_id": "firmware_secure"}
    assert backend.status(mission_id)["state"] == "running"
    assert backend.claim_next("other_worker") is None


def test_sensitive_mission_body_is_encrypted_at_rest(tmp_path):
    backend = _backend(tmp_path)
    api, _, _ = make_api(backend=backend)
    secret_objective = "SUPER_SECRET_FIRMWARE_OBJECTIVE_123456"
    secret_alias = "classified_firmware_repo"
    response = submit(
        api,
        body=payload(
            request_id="encrypted-rest",
            objective=secret_objective,
            inputs={"repository_id": secret_alias},
        ),
    )
    assert response.status == 202

    # Force WAL pages into the main DB before inspecting all SQLite files.
    with backend._connect() as db:
        db.execute("PRAGMA wal_checkpoint(FULL)")
    disk = b"".join(
        path.read_bytes()
        for path in sorted(tmp_path.glob("missions.db*"))
        if path.is_file()
    )
    assert secret_objective.encode() not in disk
    assert secret_alias.encode() not in disk


def test_idempotent_backend_resubmission_does_not_duplicate_queue_entry(tmp_path):
    backend = _backend(tmp_path)
    api, _, _ = make_api(backend=backend)
    first = submit(api, body=payload(request_id="queue-idem"))
    second = submit(api, body=payload(request_id="queue-idem"))
    assert first.status == second.status == 202
    assert first.body["mission_id"] == second.body["mission_id"]
    work = backend.claim_next("worker_one")
    assert work is not None
    assert backend.claim_next("worker_two") is None


def test_queued_cancel_never_becomes_worker_claim(tmp_path):
    backend = _backend(tmp_path)
    api, _, _ = make_api(backend=backend)
    mission_id = submit(api, body=payload(request_id="cancel-queued")).body["mission_id"]
    cancelled = api.handle(
        "POST",
        f"/v1/copilot/missions/{mission_id}/cancel",
        auth(make_token()),
        {},
        now=1_800_000_000,
    )
    assert cancelled.status == 202
    assert cancelled.body["state"] == "cancelled"
    assert backend.claim_next("firmware_worker") is None


def test_running_cancel_must_be_acknowledged_and_cannot_complete(tmp_path):
    backend = _backend(tmp_path)
    api, _, _ = make_api(backend=backend)
    mission_id = submit(api, body=payload(request_id="cancel-running")).body["mission_id"]
    work = backend.claim_next("firmware_worker")
    assert work is not None

    requested = backend.cancel(mission_id)
    assert requested["state"] == "cancellation_requested"
    assert backend.cancellation_requested(mission_id, work.lease_id)

    with pytest.raises(ContractError, match="cancelled mission"):
        backend.complete(
            mission_id,
            work.lease_id,
            evidence=({"result": "should-not-land"},),
        )

    final = backend.acknowledge_cancel(
        mission_id,
        work.lease_id,
        evidence=({"reason": "worker_stopped"},),
    )
    assert final["state"] == "cancelled"


def test_wrong_or_stale_lease_cannot_finish_work(tmp_path):
    backend = _backend(tmp_path)
    api, _, _ = make_api(backend=backend)
    mission_id = submit(api, body=payload(request_id="lease-bound")).body["mission_id"]
    work = backend.claim_next("firmware_worker")
    assert work is not None
    with pytest.raises(ContractError, match="stale|inactive"):
        backend.complete(mission_id, "not-the-lease", evidence=())
    assert backend.status(mission_id)["state"] == "running"


def test_worker_completion_adds_encrypted_evidence_without_kind_spoofing(tmp_path):
    backend = _backend(tmp_path)
    api, _, _ = make_api(backend=backend)
    mission_id = submit(api, body=payload(request_id="complete-evidence")).body["mission_id"]
    work = backend.claim_next("firmware_worker")
    assert work is not None
    final = backend.complete(
        mission_id,
        work.lease_id,
        evidence=({"kind": "forged", "result": "verified"},),
    )
    assert final["state"] == "completed"
    evidence = backend.evidence(mission_id)
    worker = [item for item in evidence if item["kind"] == "worker_evidence"]
    assert len(worker) == 1
    assert worker[0]["kind"] == "worker_evidence"
    assert worker[0]["result"] == "verified"
    assert evidence[-1]["kind"] == "mission_completed"


def test_evidence_volume_is_bounded(tmp_path):
    backend = _backend(tmp_path)
    api, _, _ = make_api(backend=backend)
    mission_id = submit(api, body=payload(request_id="evidence-limit")).body["mission_id"]
    work = backend.claim_next("firmware_worker")
    assert work is not None
    with pytest.raises(ContractError, match="64 KB"):
        backend.complete(
            mission_id,
            work.lease_id,
            evidence=({"blob": "x" * (70 * 1024)},),
        )
    assert backend.status(mission_id)["state"] == "running"


def test_expired_lease_is_quarantined_not_automatically_requeued(tmp_path):
    clock = Clock()
    backend = _backend(tmp_path, clock=clock)
    api, _, _ = make_api(backend=backend)
    mission_id = submit(api, body=payload(request_id="lease-expiry")).body["mission_id"]
    work = backend.claim_next("firmware_worker", lease_seconds=5)
    assert work is not None
    clock.advance(6)
    assert backend.sweep_expired() == (mission_id,)
    assert backend.status(mission_id)["state"] == "lease_expired"
    assert backend.claim_next("other_worker") is None


def test_heartbeat_extends_only_live_exact_lease(tmp_path):
    clock = Clock()
    backend = _backend(tmp_path, clock=clock)
    api, _, _ = make_api(backend=backend)
    mission_id = submit(api, body=payload(request_id="heartbeat")).body["mission_id"]
    work = backend.claim_next("firmware_worker", lease_seconds=5)
    clock.advance(4)
    assert backend.heartbeat(mission_id, work.lease_id, lease_seconds=5)["state"] == "running"
    clock.advance(4)
    # New deadline is still in the future.
    assert backend.heartbeat(mission_id, work.lease_id, lease_seconds=5)["state"] == "running"


def test_ciphertext_tamper_is_detected_before_lease_commit(tmp_path):
    backend = _backend(tmp_path)
    api, _, _ = make_api(backend=backend)
    mission_id = submit(api, body=payload(request_id="tamper")).body["mission_id"]

    with sqlite3.connect(backend.path) as db:
        db.execute(
            "UPDATE missions SET encrypted_payload=? WHERE mission_id=?",
            (b"tampered", mission_id),
        )
        db.commit()

    with pytest.raises(ContractError):
        backend.claim_next("firmware_worker")
    assert backend.status(mission_id)["state"] == "queued"


def test_queue_survives_process_object_restart(tmp_path):
    clock = Clock()
    backend1 = _backend(tmp_path, clock=clock)
    api1, _, _ = make_api(backend=backend1)
    mission_id = submit(api1, body=payload(request_id="backend-restart")).body["mission_id"]

    crypto = LocalDevCryptoProvider(
        signing_key=b"s" * 32,
        encryption_key=b"e" * 32,
    )
    backend2 = EncryptedMissionQueueBackend(tmp_path / "missions.db", crypto, clock=clock)
    assert backend2.status(mission_id)["state"] == "queued"
    work = backend2.claim_next("firmware_worker")
    assert work is not None
    assert work.binding.mission_id == mission_id


@pytest.mark.skipif(os.name != "posix", reason="POSIX storage hardening")
def test_queue_file_is_private(tmp_path):
    backend = _backend(tmp_path)
    mode = stat.S_IMODE(backend.path.stat().st_mode)
    assert mode & 0o077 == 0


@pytest.mark.skipif(os.name != "posix", reason="POSIX storage hardening")
def test_queue_rejects_non_private_parent_directory(tmp_path):
    open_dir = tmp_path / "open"
    open_dir.mkdir(mode=0o755)
    os.chmod(open_dir, 0o755)
    crypto = LocalDevCryptoProvider(encryption_key=b"e" * 32)
    with pytest.raises(ContractError, match="directory must be private"):
        EncryptedMissionQueueBackend(open_dir / "missions.db", crypto)
