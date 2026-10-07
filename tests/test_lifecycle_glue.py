"""Track E: auto-indexing, verified retrieval, replay checkpoints."""
import json
import os
import tempfile
import unittest

from residual import CheckResult, VerifierRevision
from residual.core import ContractError, digest
from residual.lifecycle_glue import (
    CheckpointStore,
    auto_index_run,
    retrieve_bound,
)
from residual.loop import RunOutcome
from residual.memory import EpistemicMemoryStore
from residual.receipts import StationReceipt


def revision(tag="v1"):
    return VerifierRevision(digest({"impl": tag}), digest({}), digest({}))


def receipt_for(value, *, verdict=CheckResult.PASS, rev=None, task_id="task-1"):
    rev = rev or revision()
    return StationReceipt(
        task_id=task_id, cache_key=digest("context"), value_hash=digest(value),
        verifier_name="sample:check", verifier_revision=rev.effective_revision,
        verdict=verdict, engine_name="test-engine", engine_version="1.0",
    )


class TestAutoIndexing(unittest.TestCase):
    def test_successful_run_is_indexed(self):
        with tempfile.TemporaryDirectory() as d:
            store = EpistemicMemoryStore(d)
            receipt = receipt_for({"answer": 42})
            entry = auto_index_run(store, "solve the riddle", receipt,
                                   {"answer": 42}, RunOutcome.SUCCESS)
            self.assertIsNotNone(entry)
            self.assertEqual(entry.receipt_hash, receipt.receipt_hash)
            self.assertIsNotNone(store.retrieve("solve the riddle"))

    def test_non_successful_runs_are_not_indexed(self):
        with tempfile.TemporaryDirectory() as d:
            store = EpistemicMemoryStore(d)
            for outcome in (RunOutcome.ESCALATED, RunOutcome.ABORTED, RunOutcome.AMENDED):
                receipt = receipt_for({"answer": 42})
                self.assertIsNone(auto_index_run(store, f"goal-{outcome}", receipt,
                                                 {"answer": 42}, outcome))
                self.assertIsNone(store.retrieve(f"goal-{outcome}"))

    def test_unbound_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            store = EpistemicMemoryStore(d)
            receipt = receipt_for({"answer": 42})
            with self.assertRaises(ContractError):
                auto_index_run(store, "goal", receipt, {"answer": 43}, RunOutcome.SUCCESS)

    def test_failing_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            store = EpistemicMemoryStore(d)
            receipt = receipt_for({"answer": 42}, verdict=CheckResult.FAIL)
            with self.assertRaises(ContractError):
                auto_index_run(store, "goal", receipt, {"answer": 42}, RunOutcome.SUCCESS)


class TestVerifiedRetrieval(unittest.TestCase):
    def _indexed(self, d, value={"answer": 42}, rev=None):
        store = EpistemicMemoryStore(d)
        rev = rev or revision()
        receipt = receipt_for(value, rev=rev)
        auto_index_run(store, "goal", receipt, value, RunOutcome.SUCCESS)
        return store, receipt, rev

    def test_provenance_bound_retrieval(self):
        with tempfile.TemporaryDirectory() as d:
            store, receipt, rev = self._indexed(d)
            artifact = retrieve_bound(store, "goal",
                                      verifier_revision=rev.effective_revision,
                                      verify=lambda r, v: True)
            self.assertIsNotNone(artifact)
            # Provenance binding: artifact hash == receipt value hash, receipt
            # hash == indexed entry hash.
            self.assertEqual(artifact.artifact_hash, receipt.value_hash)
            self.assertEqual(artifact.artifact_hash, digest({"answer": 42}))
            self.assertEqual(artifact.receipt_hash, receipt.receipt_hash)
            self.assertEqual(artifact.entry.receipt_hash, receipt.receipt_hash)

    def test_wrong_verifier_revision_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            store, _receipt, _rev = self._indexed(d)
            self.assertIsNone(retrieve_bound(store, "goal",
                                             verifier_revision=revision("v2").effective_revision,
                                             verify=lambda r, v: True))

    def test_host_verifier_rejection_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            store, _receipt, rev = self._indexed(d)
            self.assertIsNone(retrieve_bound(store, "goal",
                                             verifier_revision=rev.effective_revision,
                                             verify=lambda r, v: False))

    def test_tampered_payload_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            store, _receipt, rev = self._indexed(d)
            key = EpistemicMemoryStore._key("goal")
            path = os.path.join(d, f"{key}.json")
            with open(path) as f:
                data = json.load(f)
            data["artifact_payload"]["value"] = {"answer": 43}
            with open(path, "w") as f:
                json.dump(data, f)
            self.assertIsNone(retrieve_bound(store, "goal",
                                             verifier_revision=rev.effective_revision,
                                             verify=lambda r, v: True))

    def test_unknown_goal_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            store = EpistemicMemoryStore(d)
            self.assertIsNone(retrieve_bound(store, "never seen",
                                             verifier_revision=revision().effective_revision,
                                             verify=lambda r, v: True))


class TestCheckpoints(unittest.TestCase):
    def test_checkpoint_is_content_addressed(self):
        with tempfile.TemporaryDirectory() as d:
            store = CheckpointStore(d)
            a = store.save("run-1", 0, {"cursor": 3, "flags": {"debug": True}})
            b = store.save("run-1", 0, {"flags": {"debug": True}, "cursor": 3})
            self.assertEqual(a.checkpoint_hash, b.checkpoint_hash)  # deterministic
            self.assertEqual(len(a.checkpoint_hash), 64)

    def test_checkpoint_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            store = CheckpointStore(d)
            saved = store.save("run-1", 7, {"cursor": 9})
            loaded = store.load(saved.checkpoint_hash)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.run_id, "run-1")
            self.assertEqual(loaded.step, 7)
            self.assertEqual(loaded.state, {"cursor": 9})
            self.assertEqual(loaded.state_hash, saved.state_hash)

    def test_tampered_checkpoint_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            store = CheckpointStore(d)
            saved = store.save("run-1", 0, {"cursor": 1})
            path = os.path.join(d, f"{saved.checkpoint_hash}.json")
            with open(path) as f:
                data = json.load(f)
            data["state"]["cursor"] = 999
            with open(path, "w") as f:
                json.dump(data, f)
            self.assertIsNone(store.load(saved.checkpoint_hash))

    def test_noncanonical_state_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            store = CheckpointStore(d)
            with self.assertRaises(ContractError):
                store.save("run-1", 0, {"bad": object()})

    def test_history_orders_replay(self):
        with tempfile.TemporaryDirectory() as d:
            store = CheckpointStore(d)
            store.save("run-1", 2, {"cursor": 2})
            store.save("run-1", 0, {"cursor": 0})
            store.save("run-1", 1, {"cursor": 1})
            store.save("run-2", 0, {"cursor": 99})
            history = store.history("run-1")
            self.assertEqual([c.step for c in history], [0, 1, 2])
            self.assertEqual([c.state["cursor"] for c in history], [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
