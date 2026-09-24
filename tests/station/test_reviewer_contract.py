from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

from residual.core import ContractError
from residual.station.service import DEMO_FILES, Station, demo_spec


class ReviewerContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.s = Station(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _live_review_ready(self):
        pid = self.s.create(demo_spec(), commands=True, demo=False)["project_id"]
        self.s.triage(pid)
        work = self.s.prepare(pid, "review-contract", "OPS-101")
        self.s.finish(work, {"files": DEMO_FILES["OPS-101"]})
        self.assertEqual(self.s.store.task(pid, "OPS-101")["state"], "review_ready")
        return pid

    def test_reviewer_cannot_approve_with_blocking_finding(self):
        pid = self._live_review_ready()
        verdict = {"approved": True, "findings": [{"severity": "blocking", "message": "serious semantic defect"}]}
        with patch("residual.station.service.model_call", return_value=verdict):
            with self.assertRaisesRegex(ContractError, "contradictory verdict"):
                self.s.review(pid, "OPS-101")
        self.assertEqual(self.s.store.task(pid, "OPS-101")["state"], "review_ready")
        self.assertFalse(any(e["event_type"] == "review.completed" for e in self.s.store.events(pid)))

    def test_reviewer_approval_allows_only_nonblocking_findings(self):
        pid = self._live_review_ready()
        verdict = {"approved": True, "findings": [{"severity": "warning", "message": "consider a clearer name"}]}
        with patch("residual.station.service.model_call", return_value=verdict):
            self.s.review(pid, "OPS-101")
        task = self.s.store.task(pid, "OPS-101")
        self.assertEqual(task["state"], "approved")
        self.assertEqual(task["findings"], ["consider a clearer name"])
        self.assertEqual(task["review"]["findings"], verdict["findings"])

    def test_reviewer_rejection_requires_blocking_finding(self):
        pid = self._live_review_ready()
        verdict = {"approved": False, "findings": [{"severity": "warning", "message": "style only"}]}
        with patch("residual.station.service.model_call", return_value=verdict):
            with self.assertRaisesRegex(ContractError, "requires at least one blocking"):
                self.s.review(pid, "OPS-101")
        self.assertEqual(self.s.store.task(pid, "OPS-101")["state"], "review_ready")

    def test_legacy_string_finding_is_invalid_reviewer_output(self):
        pid = self._live_review_ready()
        verdict = {"approved": False, "findings": ["serious semantic defect"]}
        with patch("residual.station.service.model_call", return_value=verdict):
            with self.assertRaisesRegex(ContractError, "invalid verdict"):
                self.s.review(pid, "OPS-101")
        self.assertEqual(self.s.store.task(pid, "OPS-101")["state"], "review_ready")


if __name__ == "__main__":
    unittest.main()
