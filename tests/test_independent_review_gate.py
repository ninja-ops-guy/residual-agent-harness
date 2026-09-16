import unittest

from scripts.check_independent_review import (
    current_head_human_approvals,
    evaluate,
    qualifying_reviewers,
)

HEAD = "a" * 40
OLD = "b" * 40


def payload(author="author", head=HEAD):
    return {"pull_request": {"number": 7, "user": {"login": author}, "head": {"sha": head}}}


def review(login, state="APPROVED", commit=HEAD, submitted="2026-09-16T17:00:00Z", user_type="User"):
    return {
        "state": state,
        "commit_id": commit,
        "submitted_at": submitted,
        "user": {"login": login, "type": user_type},
    }


class IndependentReviewGateTests(unittest.TestCase):
    def test_independent_current_head_write_approval_passes(self):
        ok, detail = evaluate(payload(), [review("alice")], {"alice": "write"})
        self.assertTrue(ok)
        self.assertIn("alice", detail)

    def test_admin_approval_passes(self):
        self.assertEqual(
            qualifying_reviewers("author", HEAD, [review("alice")], {"alice": "admin"}),
            ["alice"],
        )

    def test_read_only_outside_style_approval_does_not_qualify(self):
        ok, _ = evaluate(payload(), [review("alice")], {"alice": "read"})
        self.assertFalse(ok)

    def test_missing_permission_fails_closed(self):
        ok, _ = evaluate(payload(), [review("alice")], {})
        self.assertFalse(ok)

    def test_self_approval_does_not_become_candidate(self):
        self.assertEqual(current_head_human_approvals("author", HEAD, [review("author")]), [])

    def test_bot_approval_does_not_become_candidate(self):
        self.assertEqual(
            current_head_human_approvals(
                "author",
                HEAD,
                [review("copilot-pull-request-reviewer[bot]", user_type="Bot")],
            ),
            [],
        )

    def test_stale_head_approval_does_not_qualify(self):
        ok, _ = evaluate(payload(), [review("alice", commit=OLD)], {"alice": "write"})
        self.assertFalse(ok)

    def test_later_changes_requested_revokes_current_head_approval(self):
        reviews = [
            review("alice", "APPROVED", submitted="2026-09-16T17:00:00Z"),
            review("alice", "CHANGES_REQUESTED", submitted="2026-09-16T17:01:00Z"),
        ]
        ok, _ = evaluate(payload(), reviews, {"alice": "write"})
        self.assertFalse(ok)

    def test_later_approval_supersedes_changes_requested(self):
        reviews = [
            review("alice", "CHANGES_REQUESTED", submitted="2026-09-16T17:00:00Z"),
            review("alice", "APPROVED", submitted="2026-09-16T17:01:00Z"),
        ]
        ok, _ = evaluate(payload(), reviews, {"alice": "write"})
        self.assertTrue(ok)

    def test_comment_does_not_revoke_approval(self):
        reviews = [
            review("alice", "APPROVED", submitted="2026-09-16T17:00:00Z"),
            review("alice", "COMMENTED", submitted="2026-09-16T17:01:00Z"),
        ]
        ok, _ = evaluate(payload(), reviews, {"alice": "write"})
        self.assertTrue(ok)

    def test_missing_identity_fails_closed(self):
        ok, detail = evaluate({"pull_request": {}}, [], {})
        self.assertFalse(ok)
        self.assertIn("missing", detail)


if __name__ == '__main__':
    unittest.main()
