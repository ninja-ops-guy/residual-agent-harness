"""Bounded concurrency/abuse qualification for the Copilot gateway."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from residual.crypto.provider import LocalDevCryptoProvider
from residual.integrations.copilot_studio import EncryptedMissionQueueBackend,SQLiteMissionStore
from tests.enterprise.test_copilot_studio import auth,make_api,make_token,payload,submit


def test_concurrent_unique_submissions_are_lossless(tmp_path):
    state=tmp_path/"state"; state.mkdir(mode=0o700)
    backend=EncryptedMissionQueueBackend(state/"queue.db",LocalDevCryptoProvider(signing_key=b"s"*32,encryption_key=b"e"*32))
    store=SQLiteMissionStore(tmp_path/"ownership.db")
    api,_,_=make_api(backend=backend,store=store)
    def one(i):
        return submit(api,body=payload(request_id=f"load-{i}"))
    with ThreadPoolExecutor(max_workers=12) as pool:
        results=list(pool.map(one,range(40)))
    assert all(r.status==202 for r in results)
    ids={r.body["mission_id"] for r in results}
    assert len(ids)==40
    claimed=[]
    while True:
        work=backend.claim_next("soak_worker",template_ids=frozenset({"firmware-repository-analysis"}))
        if work is None: break
        claimed.append(work.binding.mission_id)
        backend.complete(work.binding.mission_id,work.lease_id,evidence=())
    assert set(claimed)==ids


def test_duplicate_retry_storm_produces_one_mission(tmp_path):
    state=tmp_path/"state"; state.mkdir(mode=0o700)
    backend=EncryptedMissionQueueBackend(state/"queue.db",LocalDevCryptoProvider(signing_key=b"s"*32,encryption_key=b"e"*32))
    store=SQLiteMissionStore(tmp_path/"ownership.db")
    api,_,_=make_api(backend=backend,store=store)
    def replay(_): return submit(api,body=payload(request_id="same-request"))
    with ThreadPoolExecutor(max_workers=16) as pool:
        results=list(pool.map(replay,range(50)))
    assert all(r.status==202 for r in results)
    assert len({r.body["mission_id"] for r in results})==1
    first=backend.claim_next("worker",template_ids=frozenset({"firmware-repository-analysis"}))
    assert first is not None
    assert backend.claim_next("worker2",template_ids=frozenset({"firmware-repository-analysis"})) is None


def test_malformed_token_fuzz_never_reaches_backend():
    api,_,backend=make_api()
    fuzz=["","x","a.b.c","..","Bearer","none.none.none","."*1000,"\x00","é"*50]
    for i,token in enumerate(fuzz):
        r=api.handle("POST","/v1/copilot/missions","Bearer "+token,payload(request_id=f"fuzz-{i}"),now=1_800_000_000)
        assert r.status==401
    assert backend.bindings==[]


def test_mission_id_enumeration_is_nondisclosing():
    api,_,_=make_api()
    owner=auth(make_token())
    for i in range(50):
        guessed="m-"+f"{i:032x}"
        r=api.handle("GET",f"/v1/copilot/missions/{guessed}/evidence",owner,None,now=1_800_000_000)
        assert r.status==404
        assert r.body=={"code":"not_found","message":"unknown mission"}


def test_conflicting_replay_storm_never_replaces_original():
    api,_,backend=make_api()
    original=submit(api,body=payload(request_id="conflict-storm",objective="original"))
    assert original.status==202
    def conflict(i):
        return submit(api,body=payload(request_id="conflict-storm",objective=f"evil-{i}"))
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(conflict,range(20)))
    assert all(r.status==409 for r in results)
    assert len(backend.bindings)==1
    assert backend.requests[0].objective=="original"
