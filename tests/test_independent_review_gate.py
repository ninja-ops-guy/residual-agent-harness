import unittest
from unittest.mock import call, patch

from scripts.check_independent_review import (
    current_head_human_approvals,
    evaluate,
    github_reviews,
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

    @patch("scripts.check_independent_review._github_json")
    def test_review_pagination_observes_later_change_request(self, github_json):
        first_page = [
            review("alice", submitted="2026-09-16T17:00:00Z"),
            *[
                review(
                    f"commenter-{index}",
                    state="COMMENTED",
                    submitted=f"2026-09-16T17:{index % 60:02d}:00Z",
                )
                for index in range(99)
            ],
        ]
        github_json.side_effect = [
            first_page,
            [review("alice", state="CHANGES_REQUESTED", submitted="2026-09-16T18:00:00Z")],
        ]

        reviews = github_reviews("owner/repo", 7, "token")
        ok, _ = evaluate(payload(), reviews, {"alice": "write"})

        self.assertFalse(ok)
        self.assertEqual(len(reviews), 101)
        self.assertEqual(
            github_json.call_args_list,
            [
                call("https://api.github.com/repos/owner/repo/pulls/7/reviews?per_page=100&page=1", "token"),
                call("https://api.github.com/repos/owner/repo/pulls/7/reviews?per_page=100&page=2", "token"),
            ],
        )

    @patch("scripts.check_independent_review._github_json")
    def test_review_pagination_stops_after_short_page(self, github_json):
        github_json.return_value = [review("alice")]

        self.assertEqual(github_reviews("owner/repo", 7, "token"), [review("alice")])
        github_json.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/pulls/7/reviews?per_page=100&page=1",
            "token",
        )

    @patch("scripts.check_independent_review._github_json")
    def test_review_pagination_rejects_malformed_later_page(self, github_json):
        github_json.side_effect = [[review(f"reviewer-{index}") for index in range(100)], {"oops": True}]

        with self.assertRaisesRegex(RuntimeError, "page 2 is not a list"):
            github_reviews("owner/repo", 7, "token")

    @patch("scripts.check_independent_review.MAX_REVIEW_PAGES", 2)
    @patch("scripts.check_independent_review._github_json")
    def test_review_pagination_limit_fails_closed(self, github_json):
        github_json.return_value = [review(f"reviewer-{index}") for index in range(100)]

        with self.assertRaisesRegex(RuntimeError, "exceeded 2 pages"):
            github_reviews("owner/repo", 7, "token")


if __name__ == '__main__':
    unittest.main()
