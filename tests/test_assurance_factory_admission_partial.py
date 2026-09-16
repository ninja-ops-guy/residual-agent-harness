from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from residual.assurance.factory_admission import FactoryM3Admission
from residual.core import digest
from residual.factory.evidence_bus import EvidenceBus
from residual.factory.evidence_receipts import EvidenceError, StationIdentity, VerificationDecision
from residual.factory.runtime import RuntimeResult
from residual.factory.runtime_workspace import CandidateTree
from residual.factory.station_issuer import FactoryStationIssuer
from residual.factory.worker_contract import WorkerContract


class PurgeRecorder:
    def __init__(self):
        self.purged = []

    def purge(self, contract):
        self.purged.append(contract.attempt_id)


class PartialAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.identity = StationIdentity.generate()
        self.bus = EvidenceBus(self.root / "bus.sqlite")
        self.issuer = FactoryStationIssuer(self.identity, self.bus)
        self.runtime = PurgeRecorder()

    def tearDown(self):
        self.tmp.cleanup()

    def pair(self, index):
        workspace = self.root / f"workspace{index}"
        workspace.mkdir()
        output = f"out{index}.txt"
        data = f"value-{index}".encode()
        (workspace / output).write_bytes(data)
        contract = WorkerContract(
            task_id=f"task{index}", worker_id=f"worker{index}", swarm_id="swarm1",
            execution_plan_hash="f" * 64, attempt_id=f"attempt{index}", lease_id=f"lease{index}",
            lease_generation=index, input_commit="a" * 40, workspace_root=str(workspace), inputs=(),
            allowed_outputs=(output,), forbidden=(), requirements=(f"REQ{index}",),
            acceptance=("unit",), dependencies=(), allowed_tools=("write_file",), forbidden_tools=(),
            token_budget=10, wall_clock_budget_s=5, max_tool_calls=2, max_file_writes=1, memory_limit_mb=64,
        )
        candidate = CandidateTree(
            contract.input_commit, "b" * 40, "c" * 40,
            ((output, hashlib.sha256(data).hexdigest()),),
        )
        result = RuntimeResult(
            contract.attempt_id, "CANDIDATE", contract.contract_hash, contract.execution_plan_hash,
            0, True, {}, candidate, "awaiting_station_verification",
        )
        return contract, result

    def test_later_rejection_keeps_earlier_signed_receipt_but_purges_nothing(self):
        c1, r1 = self.pair(1)
        c2, r2 = self.pair(2)

        def decide(contract, result):
            passed = contract.attempt_id == "attempt1"
            return VerificationDecision(
                ((contract.requirements[0], passed),),
                (("unit", "pass" if passed else "fail"),),
                "pass" if passed else "fail",
                "station:test",
                digest({"verifier": 2}),
            )

        admission = FactoryM3Admission(self.runtime, self.issuer, decide)
        with self.assertRaises(EvidenceError):
            admission.admit((c1, c2), (r1, r2))

        # M3 is append-only per worker: the first valid receipt remains authoritative.
        self.assertEqual(self.bus.verify_queue()["receipts"], 1)
        receipt = self.bus.query(task_id="task1")[0]
        self.assertTrue(StationIdentity.verify(receipt, self.identity.public_bytes()))
        # Purge is batch-strict: retain every worktree when any requested admission fails.
        self.assertEqual(self.runtime.purged, [])


if __name__ == "__main__":
    unittest.main()
