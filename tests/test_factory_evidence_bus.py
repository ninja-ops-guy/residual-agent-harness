from __future__ import annotations
import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from residual.core import digest
from residual.factory.evidence_bus import (EvidenceBus, EvidenceError,
    FactoryStationIssuer, StationIdentity, VerificationDecision, WorkerReceipt)
from residual.factory.runtime import RuntimeResult
from residual.factory.runtime_workspace import CandidateTree
from residual.factory.worker_contract import WorkerContract

H = "a"*64
C = "b"*40


def contract(root):
    return WorkerContract(task_id="task1", worker_id="worker1", swarm_id="swarm1",
        execution_plan_hash=H, attempt_id="attempt1", lease_id="lease1", lease_generation=1,
        input_commit=C, workspace_root=str(root), inputs=("in.txt",), allowed_outputs=("out.txt",),
        forbidden=(), requirements=("REQ1",), acceptance=("check1",), dependencies=(),
        allowed_tools=("read","write"), forbidden_tools=(), token_budget=10,
        wall_clock_budget_s=10, max_tool_calls=10, max_file_writes=10, memory_limit_mb=64)


def decision(verdict="pass"):
    return VerificationDecision((("REQ1", True),), (("check1", "pass"),), verdict,
                                "station:test", digest({"rev": 1}))


class EvidenceBusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)/"workspace"; self.root.mkdir()
        self.c = contract(self.root); (self.root/"out.txt").write_bytes(b"hello")
        sha = hashlib.sha256(b"hello").hexdigest()
        candidate = CandidateTree(C, "d"*40, "e"*40, (("out.txt", sha),))
        self.result = RuntimeResult("attempt1","CANDIDATE",self.c.contract_hash,H,0,True,{},candidate,
                                    "awaiting_station_verification")
        self.identity = StationIdentity.generate()
        self.db = str(Path(self.tmp.name)/"bus.sqlite")
        self.events=[]; self.bus=EvidenceBus(self.db, observe=self.events.append)
        self.issuer=FactoryStationIssuer(self.identity,self.bus)

    def tearDown(self): self.tmp.cleanup()

    def issue(self, **kw):
        return self.issuer.issue(contract=self.c,result=self.result,workspace_root=self.root,
                                 decision=decision(),**kw)

    def test_issue_and_local_verify(self):
        r=self.issue(); self.assertTrue(StationIdentity.verify(r,self.identity.public_bytes()))
        self.assertEqual(self.bus.artifact(r.receipt_hash,"out.txt",station_public_key=self.identity.public_bytes()),b"hello")
        self.assertEqual(self.bus.consumable(r.receipt_hash,station_public_key=self.identity.public_bytes()).receipt_hash,r.receipt_hash)

    def test_tampered_signature_rejected(self):
        r=self.issue(); bad=replace(r,station_signature="00"*64)
        self.assertFalse(StationIdentity.verify(bad,self.identity.public_bytes()))

    def test_wrong_key_rejected(self):
        r=self.issue(); other=StationIdentity.generate()
        with self.assertRaises(EvidenceError): self.bus.consumable(r.receipt_hash,station_public_key=other.public_bytes())

    def test_raw_artifact_not_stored_on_failed_verification(self):
        with self.assertRaises(EvidenceError):
            self.issuer.issue(contract=self.c,result=self.result,workspace_root=self.root,
                              decision=decision("fail"))
        with self.bus._connect() as db:
            self.assertEqual(db.execute("select count(*) from artifacts").fetchone()[0],0)
            self.assertEqual(db.execute("select count(*) from receipts").fetchone()[0],0)

    def test_changed_candidate_rejected_before_store(self):
        (self.root/"out.txt").write_bytes(b"tampered")
        with self.assertRaises(EvidenceError): self.issue()
        with self.bus._connect() as db: self.assertEqual(db.execute("select count(*) from artifacts").fetchone()[0],0)

    def test_acceptance_must_pass(self):
        bad=VerificationDecision((("REQ1",True),),(("check1","unknown"),),"pass","station:test",digest({"r":2}))
        with self.assertRaises(EvidenceError):
            self.issuer.issue(contract=self.c,result=self.result,workspace_root=self.root,decision=bad)

    def test_requirements_must_pass(self):
        bad=VerificationDecision((("REQ1",False),),(("check1","pass"),),"pass","station:test",digest({"r":2}))
        with self.assertRaises(EvidenceError):
            self.issuer.issue(contract=self.c,result=self.result,workspace_root=self.root,decision=bad)

    def test_append_only_trigger(self):
        r=self.issue()
        with self.assertRaises(Exception):
            with self.bus._tx() as db: db.execute("update receipts set task_id='x' where receipt_hash=?",(r.receipt_hash,))

    def test_queries(self):
        r=self.issue(); sha=r.artifacts[0].sha256
        for kwargs in ({"task_id":"task1"},{"requirement_id":"REQ1"},{"artifact_hash":sha},
                       {"engine_name":"brokered-python"},{"verification_status":"pass"},{"swarm_id":"swarm1"}):
            self.assertEqual([x.receipt_hash for x in self.bus.query(**kwargs)],[r.receipt_hash])

    def test_supersession_marks_self_and_descendant_stale(self):
        r1=self.issue()
        c2=replace(self.c,worker_id="worker2",attempt_id="attempt2",lease_id="lease2",lease_generation=2)
        result2=replace(self.result,attempt_id="attempt2",contract_hash=c2.contract_hash)
        r2=self.issuer.issue(contract=c2,result=result2,workspace_root=self.root,decision=decision(),supersedes=r1.receipt_hash)
        self.assertTrue(self.bus.is_stale(r1.receipt_hash)); self.assertFalse(self.bus.is_stale(r2.receipt_hash))
        with self.assertRaises(EvidenceError): self.bus.consumable(r1.receipt_hash,station_public_key=self.identity.public_bytes())
        self.bus.approve_stale(r1.receipt_hash,approved_by="human",reason="audit replay")
        self.assertEqual(self.bus.consumable(r1.receipt_hash,station_public_key=self.identity.public_bytes()).receipt_hash,r1.receipt_hash)

    def test_parent_must_exist(self):
        with self.assertRaises(EvidenceError): self.issue(parent_receipts=("f"*64,))

    def test_deleted_artifact_has_no_blob(self):
        (self.root/"out.txt").unlink()
        candidate=CandidateTree(C,"d"*40,"e"*40,(("out.txt",None),))
        result=replace(self.result,candidate=candidate)
        r=self.issuer.issue(contract=self.c,result=result,workspace_root=self.root,decision=decision())
        self.assertTrue(r.artifacts[0].deleted)
        with self.bus._connect() as db: self.assertEqual(db.execute("select count(*) from artifacts").fetchone()[0],0)

    def test_receipt_roundtrip_hash(self):
        r=self.issue(); copy=WorkerReceipt.from_dict(r.to_dict()); self.assertEqual(copy,r)

    def test_corrupt_artifact_detected(self):
        r=self.issue()
        with self.bus._tx() as db: db.execute("update artifacts set bytes=? where sha256=?",(b"bad",r.artifacts[0].sha256))
        with self.assertRaises(EvidenceError): self.bus.consumable(r.receipt_hash,station_public_key=self.identity.public_bytes())

    def test_events_cover_issue_store_query_reject(self):
        r=self.issue(); self.bus.query(task_id="task1")
        names={x["event"] for x in self.events}; self.assertTrue({"WorkerReceiptIssued","ArtifactStored","EvidenceQueryExecuted"}<=names)

    def test_queue_chain_and_time_query(self):
        r=self.issue()
        state=self.bus.verify_queue(); self.assertEqual(state["receipts"],1)
        self.assertEqual([x.receipt_hash for x in self.bus.query(start_ns=r.issued_at_ns-1,end_ns=r.issued_at_ns+1)],[r.receipt_hash])

    def test_dependency_admission_requires_exact_tasks_and_plan(self):
        r=self.issue()
        dependent=replace(self.c,task_id="task2",worker_id="worker2",attempt_id="attempt2",lease_id="lease2",
                          dependencies=("task1",),requirements=("REQ1",))
        admitted=self.bus.admit_dependencies(dependent,(r.receipt_hash,),station_public_key=self.identity.public_bytes())
        self.assertEqual(admitted[0].task_id,"task1")
        wrong=replace(dependent,dependencies=("other",))
        with self.assertRaises(EvidenceError):
            self.bus.admit_dependencies(wrong,(r.receipt_hash,),station_public_key=self.identity.public_bytes())

    def test_private_key_roundtrip_and_exclusive_create(self):
        path=Path(self.tmp.name)/"station.pem"; self.identity.save_private(path)
        loaded=StationIdentity.load_private(path); self.assertEqual(loaded.public_bytes(),self.identity.public_bytes())
        with self.assertRaises(FileExistsError): self.identity.save_private(path)

    def test_stale_approval_is_immutable(self):
        r1=self.issue()
        c2=replace(self.c,worker_id="worker2",attempt_id="attempt2",lease_id="lease2",lease_generation=2)
        result2=replace(self.result,attempt_id="attempt2",contract_hash=c2.contract_hash)
        self.issuer.issue(contract=c2,result=result2,workspace_root=self.root,decision=decision(),supersedes=r1.receipt_hash)
        self.bus.approve_stale(r1.receipt_hash,approved_by="human",reason="first")
        with self.assertRaises(EvidenceError): self.bus.approve_stale(r1.receipt_hash,approved_by="human",reason="second")


if __name__ == "__main__": unittest.main()
