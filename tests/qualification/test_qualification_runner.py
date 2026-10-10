from __future__ import annotations

import argparse
import sys
import tempfile
import unittest
from pathlib import Path

import scripts.qualification_v1 as qualification
from residual.qualification.evidence import GateResult, load_envelope


class QualificationRunnerEvidenceTests(unittest.TestCase):
    def _args(self, root: Path, *, evidence_paths=None, junit=None, command=None):
        return argparse.Namespace(
            command=command or [sys.executable, "-c", "pass"],
            log=root / "gate.log",
            junit=junit,
            zero_skips=False,
            unknown_count=0,
            evidence_path=list(evidence_paths or []),
            gate_id="test-gate",
            output=root / "gate.evidence.json",
            non_claim=[],
        )

    def test_missing_declared_evidence_forces_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            missing = root / "missing-report.json"
            args = self._args(root, evidence_paths=[missing])
            rc = qualification.command_run(args)
            envelope = load_envelope(args.output)
            self.assertEqual(rc, 1)
            self.assertEqual(envelope.result, GateResult.FAIL)
            self.assertTrue(any("required evidence missing" in note for note in envelope.notes))
            self.assertNotIn(str(missing), envelope.evidence)

    def test_missing_declared_junit_forces_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            junit = root / "missing.xml"
            args = self._args(root, junit=junit)
            rc = qualification.command_run(args)
            envelope = load_envelope(args.output)
            self.assertEqual(rc, 1)
            self.assertEqual(envelope.result, GateResult.FAIL)
            self.assertTrue(any(str(junit) in note for note in envelope.notes))

    def test_present_declared_evidence_can_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / "report.json"
            command = [
                sys.executable,
                "-c",
                f"from pathlib import Path; Path({str(report)!r}).write_text('ok', encoding='utf-8')",
            ]
            args = self._args(root, evidence_paths=[report], command=command)
            rc = qualification.command_run(args)
            envelope = load_envelope(args.output)
            self.assertEqual(rc, 0)
            self.assertEqual(envelope.result, GateResult.PASS)
            self.assertIn(str(report), envelope.evidence)


if __name__ == "__main__":
    unittest.main()
