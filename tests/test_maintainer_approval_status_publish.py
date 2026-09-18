"""Offline regression tests for issue #268 status publication.

Simulates the approval evaluation and commit-status publication against
recorded event payloads with the GitHub HTTP layer stubbed out. Covers:
initial no-attestation FAIL, valid current-head approval PASS, stale-head
approval FAIL, revoke-after-approve FAIL, bot-author rejection, and that the
published status is associated with the exact PR head SHA used by branch
protection (not the default-branch event SHA of an issue_comment run).
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from scripts import check_maintainer_approval as gate

HEAD = "fadf493f5231f90860889f812471d5d2da644216"
MOVED_HEAD = "0" * 40
DEFAULT_BRANCH_EVENT_SHA = "3cff6bcd52e352a6ba048c958949a7bbb2a039eb"
REPO = "ninja-ops-guy/residual-agent-harness"


def comment(cid, login, body, user_type="User"):
    return {"id": cid, "body": body, "user": {"login": login, "type": user_type}}


class PublishHeadStatusUnitTests(unittest.TestCase):
    def test_posts_status_to_exact_head_with_protected_context(self):
        calls = []

        def fake_request(url, token, payload=None):
            calls.append((url, payload))
            return {"state": payload["state"]}

        gate.publish_head_status(REPO, HEAD, "success", "approved", "tok", request_fn=fake_request)
        self.assertEqual(len(calls), 1)
        url, payload = calls[0]
        self.assertEqual(url, f"https://api.github.com/repos/{REPO}/statuses/{HEAD}")
        self.assertEqual(payload["context"], "maintainer-approval")
        self.assertEqual(payload["state"], "success")

    def test_refuses_non_sha_target(self):
        with self.assertRaises(RuntimeError):
            gate.publish_head_status(REPO, "refs/heads/main", "failure", "x", "tok")

    def test_refuses_invalid_state(self):
        with self.assertRaises(RuntimeError):
            gate.publish_head_status(REPO, HEAD, "green", "x", "tok")


class GatePublishEndToEndTests(unittest.TestCase):
    """Drive main() offline with recorded payloads and a stubbed HTTP layer."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        event = {
            "repository": {"full_name": REPO},
            "issue": {"number": 260, "pull_request": {"url": "https://api/..."}},
            # issue_comment events carry the default-branch SHA here, not the PR head.
            "sha": DEFAULT_BRANCH_EVENT_SHA,
        }
        self.event_path = self._write("event.json", event)
        self.calls = []

        def fake_request(url, token, payload=None):
            self.calls.append((url, payload))
            return {}

        patcher = mock.patch.object(gate, "_github_request", side_effect=fake_request)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.env = mock.patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def _write(self, name, data):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return path

    def _run(self, comments, permissions, head_sha=HEAD):
        argv = [
            "--event", self.event_path,
            "--comments-json", self._write("comments.json", comments),
            "--permissions-json", self._write("perms.json", permissions),
            "--head-sha", head_sha,
            "--publish-status",
        ]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = gate.main(argv)
        return code, out.getvalue(), err.getvalue()

    def _published(self):
        self.assertEqual(len(self.calls), 1, "exactly one status must be published")
        return self.calls[0]

    def test_initial_no_attestation_fails_and_publishes_failure_on_head(self):
        code, _, err = self._run([], {})
        self.assertEqual(code, 1)
        self.assertIn("BLOCKED", err)
        url, payload = self._published()
        self.assertEqual(url, f"https://api.github.com/repos/{REPO}/statuses/{HEAD}")
        self.assertEqual(payload["state"], "failure")
        self.assertEqual(payload["context"], "maintainer-approval")

    def test_valid_current_head_approval_passes_and_publishes_success(self):
        comments = [comment(10, "solo", f"{gate.APPROVE_PREFIX} {HEAD}")]
        code, out, _ = self._run(comments, {"solo": "write"})
        self.assertEqual(code, 0)
        self.assertIn("PASS", out)
        url, payload = self._published()
        self.assertTrue(url.endswith(f"/statuses/{HEAD}"))
        self.assertEqual(payload["state"], "success")

    def test_stale_head_approval_fails_on_moved_head(self):
        comments = [comment(10, "solo", f"{gate.APPROVE_PREFIX} {HEAD}")]
        code, _, _ = self._run(comments, {"solo": "write"}, head_sha=MOVED_HEAD)
        self.assertEqual(code, 1)
        url, payload = self._published()
        self.assertTrue(url.endswith(f"/statuses/{MOVED_HEAD}"))
        self.assertEqual(payload["state"], "failure")

    def test_revoke_after_approve_fails(self):
        comments = [
            comment(10, "solo", f"{gate.APPROVE_PREFIX} {HEAD}"),
            comment(11, "solo", f"{gate.REVOKE_PREFIX} {HEAD}"),
        ]
        code, _, _ = self._run(comments, {"solo": "write"})
        self.assertEqual(code, 1)
        _, payload = self._published()
        self.assertEqual(payload["state"], "failure")

    def test_bot_attestation_never_counts(self):
        comments = [comment(10, "residual-bot[bot]", f"{gate.APPROVE_PREFIX} {HEAD}", "Bot")]
        code, _, _ = self._run(comments, {"residual-bot[bot]": "write"})
        self.assertEqual(code, 1)
        _, payload = self._published()
        self.assertEqual(payload["state"], "failure")

    def test_status_associated_with_pr_head_not_default_branch_event_sha(self):
        comments = [comment(10, "solo", f"{gate.APPROVE_PREFIX} {HEAD}")]
        code, _, _ = self._run(comments, {"solo": "admin"})
        self.assertEqual(code, 0)
        url, _ = self._published()
        self.assertIn(HEAD, url)
        self.assertNotIn(DEFAULT_BRANCH_EVENT_SHA, url)


if __name__ == "__main__":
    unittest.main()
