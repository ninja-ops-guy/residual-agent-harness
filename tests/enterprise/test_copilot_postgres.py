"""PostgreSQL multi-instance qualification for Copilot Studio persistence."""
from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from residual.crypto.provider import LocalDevCryptoProvider
from residual.integrations.copilot_studio.postgres import (
    PostgresEncryptedMissionQueueBackend,
    PostgresMissionStore,
)
from tests.enterprise.test_copilot_studio import make_api, payload, submit


DSN = os.environ.get("RESIDUAL_TEST_POSTGRES_DSN")


pytestmark = pytest.mark.skipif(not DSN, reason="PostgreSQL test DSN not configured")


def _prefix():
    return "cp" + uuid.uuid4().hex[:20]


def _crypto():
    return LocalDevCryptoProvider(signing_key=b"s" * 32, encryption_key=b"e" * 32)


def _stack(prefix=None):
    prefix = prefix or _prefix()
    return (
        PostgresMissionStore(DSN, table_prefix=prefix),
        PostgresEncryptedMissionQueueBackend(DSN, _crypto(), table_prefix=prefix),
        prefix,
    )


def test_postgres_health_and_gateway_round_trip():
    store, backend, _ = _stack()
    assert backend.ping()
    api, _, _ = make_api(store=store, backend=backend)
    created = submit(api, body=payload(request_id="pg-round-trip"))
    assert created.status == 202
    mission_id = created.body["mission_id"]
    assert backend.status(mission_id)["state"] == "queued"
    work = backend.claim_next(
        "pg_worker", template_ids=frozenset({"firmware-repository-analysis"})
    )
    assert work is not None and work.binding.mission_id == mission_id
    final = backend.complete(
        mission_id, work.lease_id, evidence=({"result": "qualified"},)
    )
    assert final["state"] == "completed"
    assert any(e.get("result") == "qualified" for e in backend.evidence(mission_id))


def test_two_gateway_instances_share_idempotency_and_queue():
    store1, queue1, prefix = _stack()
    store2 = PostgresMissionStore(DSN, table_prefix=prefix)
    queue2 = PostgresEncryptedMissionQueueBackend(
        DSN, _crypto(), table_prefix=prefix
    )
    api1, _, _ = make_api(store=store1, backend=queue1)
    api2, _, _ = make_api(store=store2, backend=queue2)

    def replay(i):
        api = api1 if i % 2 == 0 else api2
        return submit(api, body=payload(request_id="pg-shared-idempotency"))

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(replay, range(40)))
    assert all(r.status == 202 for r in results)
    assert len({r.body["mission_id"] for r in results}) == 1

    claimed = []
    for queue, worker in ((queue1, "worker_a"), (queue2, "worker_b")):
        work = queue.claim_next(
            worker, template_ids=frozenset({"firmware-repository-analysis"})
        )
        if work:
            claimed.append(work)
    assert len(claimed) == 1


def test_skip_locked_distributes_unique_missions_across_workers():
    store, queue, prefix = _stack()
    api, _, _ = make_api(store=store, backend=queue)
    ids = set()
    for i in range(30):
        response = submit(api, body=payload(request_id=f"pg-load-{i}"))
        assert response.status == 202
        ids.add(response.body["mission_id"])

    def claim(i):
        backend = PostgresEncryptedMissionQueueBackend(
            DSN, _crypto(), table_prefix=prefix
        )
        work = backend.claim_next(
            f"worker_{i}",
            template_ids=frozenset({"firmware-repository-analysis"}),
            lease_seconds=120,
        )
        return work

    claimed = []
    with ThreadPoolExecutor(max_workers=16) as pool:
        while len(claimed) < len(ids):
            batch = [w for w in pool.map(claim, range(16)) if w is not None]
            if not batch:
                break
            claimed.extend(batch)

    claimed_ids = [w.binding.mission_id for w in claimed]
    assert len(claimed_ids) == 30
    assert len(set(claimed_ids)) == 30
    assert set(claimed_ids) == ids


def test_shared_cancel_fences_other_worker_instance():
    store, queue1, prefix = _stack()
    queue2 = PostgresEncryptedMissionQueueBackend(
        DSN, _crypto(), table_prefix=prefix
    )
    api, _, _ = make_api(store=store, backend=queue1)
    mission_id = submit(api, body=payload(request_id="pg-cancel")).body["mission_id"]
    work = queue1.claim_next(
        "worker_a", template_ids=frozenset({"firmware-repository-analysis"})
    )
    assert work is not None
    assert queue2.cancel(mission_id)["state"] == "cancellation_requested"
    assert queue1.cancellation_requested(mission_id, work.lease_id)
    with pytest.raises(Exception):
        queue1.complete(mission_id, work.lease_id, evidence=())


def test_postgres_keeps_mission_plaintext_encrypted():
    store, queue, prefix = _stack()
    api, _, _ = make_api(store=store, backend=queue)
    secret = "POSTGRES-SENSITIVE-FIRMWARE-OBJECTIVE"
    response = submit(
        api,
        body=payload(
            request_id="pg-encrypted",
            objective=secret,
            inputs={"repository_id": "firmware_sample"},
        ),
    )
    assert response.status == 202

    with queue._connect() as db:
        row = db.execute(
            f"SELECT encrypted_payload FROM {queue.missions} WHERE mission_id=%s",
            (response.body["mission_id"],),
        ).fetchone()
    assert secret.encode() not in bytes(row["encrypted_payload"])
