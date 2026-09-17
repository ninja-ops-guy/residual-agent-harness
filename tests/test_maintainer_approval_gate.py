import unittest

from scripts.check_maintainer_approval import (
    APPROVE_PREFIX,
    REVOKE_PREFIX,
    _command,
    candidate_logins,
    current_head_approvers,
    evaluate,
)

HEAD = "abc123"


def comment(cid, login, body, user_type="User"):
    return {
        "id": cid,
        "body": body,
        "user": {"login": login, "type": user_type},
    }


class MaintainerApprovalGateTests(unittest.TestCase):
    def test_exact_command_parsing(self):
        self.assertEqual(_command(f"{APPROVE_PREFIX} {HEAD}"), ("approve", HEAD))
        self.assertEqual(_command(f"{REVOKE_PREFIX} {HEAD}"), ("revoke", HEAD))
        self.assertIsNone(_command("looks good"))

    def test_write_maintainer_can_approve_own_pr_head(self):
        comments = [comment(10, "solo", f"{APPROVE_PREFIX} {HEAD}")]
        self.assertEqual(current_head_approvers(HEAD, comments, {"solo": "write"}), ["solo"])

    def test_admin_maintainer_qualifies(self):
        comments = [comment(10, "solo", f"{APPROVE_PREFIX} {HEAD}")]
        self.assertEqual(current_head_approvers(HEAD, comments, {"solo": "admin"}), ["solo"])

    def test_read_only_user_does_not_qualify(self):
        comments = [comment(10, "reader", f"{APPROVE_PREFIX} {HEAD}")]
        self.assertEqual(current_head_approvers(HEAD, comments, {"reader": "read"}), [])

    def test_bot_does_not_qualify(self):
        comments = [comment(10, "residual-bot[bot]", f"{APPROVE_PREFIX} {HEAD}", "Bot")]
        self.assertEqual(current_head_approvers(HEAD, comments, {"residual-bot[bot]": "write"}), [])

    def test_stale_head_does_not_qualify(self):
        comments = [comment(10, "solo", f"{APPROVE_PREFIX} oldsha")]
        self.assertEqual(current_head_approvers(HEAD, comments, {"solo": "write"}), [])

    def test_later_revoke_wins_for_same_head(self):
        comments = [
            comment(10, "solo", f"{APPROVE_PREFIX} {HEAD}"),
            comment(11, "solo", f"{REVOKE_PREFIX} {HEAD}"),
        ]
        self.assertEqual(current_head_approvers(HEAD, comments, {"solo": "write"}), [])

    def test_later_approval_after_revoke_restores(self):
        comments = [
            comment(10, "solo", f"{REVOKE_PREFIX} {HEAD}"),
            comment(11, "solo", f"{APPROVE_PREFIX} {HEAD}"),
        ]
        self.assertEqual(current_head_approvers(HEAD, comments, {"solo": "write"}), ["solo"])

    def test_candidate_logins_only_include_exact_head_humans(self):
        comments = [
            comment(1, "solo", f"{APPROVE_PREFIX} {HEAD}"),
            comment(2, "other", f"{APPROVE_PREFIX} oldsha"),
            comment(3, "bot[bot]", f"{APPROVE_PREFIX} {HEAD}", "Bot"),
        ]
        self.assertEqual(candidate_logins(comments, HEAD), ["solo"])

    def test_evaluate_explains_required_exact_comment(self):
        ok, detail = evaluate(HEAD, [], {})
        self.assertFalse(ok)
        self.assertIn(f"{APPROVE_PREFIX} {HEAD}", detail)

    def test_evaluate_passes_with_exact_head_attestation(self):
        comments = [comment(1, "solo", f"{APPROVE_PREFIX} {HEAD}")]
        ok, detail = evaluate(HEAD, comments, {"solo": "write"})
        self.assertTrue(ok)
        self.assertIn("solo", detail)


if __name__ == "__main__":
    unittest.main()
