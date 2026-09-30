"""Operator CLI tests for substrate qualification evidence."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from residual.core import digest
from residual.substrates.cli import main
from residual.substrates.ledger import SubstrateQualificationLedger
from residual.substrates.qualification import (
    QualificationGate,
    SubstrateQualificationRecord,
    SubstrateQualificationTuple,
    inference_route_digest,
    provider_set_digest,
)


class SubstrateCliTests(unittest.TestCase):
    def make_ledger(self):
        qtuple = SubstrateQualificationTuple(
            substrate_name="openshell",
            substrate_version="0.1.1",
            substrate_source_identity="openshell@fixture",
            driver="docker",
            platform_class="linux-x86_64",
            environment_digest="a" * 64,
            agent_profile="openshell/direct",
            agent_identity="hermes@fixture",
            image_digest="1" * 64,
            requested_policy_digest="2" * 64,
            provider_set_digest=provider_set_digest({"provider-a": "b" * 64}),
            inference_route_digest=inference_route_digest("route-a"),
        )
        record = SubstrateQualificationRecord(
            qualification_tuple=qtuple,
            gates=(
                QualificationGate(
                    gate_id="Q0",
                    status="PASS",
                    evidence_digest="3" * 64,
                ),
            ),
            capabilities=("sandboxed_execution", "filesystem_policy"),
            evidence_root_digest="4" * 64,
            limitations=("gpu_execution:not_qualified",),
        )
        return SubstrateQualificationLedger((record,)), record

    def test_verify_ledger_with_pinned_digest(self):
        ledger, _record = self.make_ledger()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "qualification.json"
            ledger.write(path)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main([
                    "verify-ledger",
                    str(path),
                    "--expected-digest",
                    ledger.ledger_digest,
                    "--json",
                ])
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["status"], "VALID")
            self.assertEqual(payload["ledger_digest"], ledger.ledger_digest)
            self.assertEqual(payload["pass_records"], 1)

    def test_verify_ledger_wrong_digest_fails_without_leaking_content(self):
        ledger, _record = self.make_ledger()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "qualification.json"
            ledger.write(path)
            err = io.StringIO()
            with redirect_stderr(err):
                code = main([
                    "verify-ledger",
                    str(path),
                    "--expected-digest",
                    "9" * 64,
                ])
            self.assertEqual(code, 1)
            self.assertIn("qualification evidence could not be validated", err.getvalue())
            self.assertNotIn("provider-a", err.getvalue())

    def test_status_exposes_only_evidence_backed_capabilities(self):
        ledger, record = self.make_ledger()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "qualification.json"
            ledger.write(path)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["status", str(path), "--json"])
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["records"][0]["overall"], "PASS")
            self.assertEqual(
                payload["records"][0]["qualified_capabilities"],
                ["filesystem_policy", "sandboxed_execution"],
            )
            self.assertEqual(
                payload["records"][0]["record_digest"],
                record.record_digest,
            )

    def test_status_tuple_filter_fails_closed_when_absent(self):
        ledger, _record = self.make_ledger()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "qualification.json"
            ledger.write(path)
            err = io.StringIO()
            with redirect_stderr(err):
                code = main([
                    "status",
                    str(path),
                    "--tuple-digest",
                    digest({"missing": True}),
                ])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
