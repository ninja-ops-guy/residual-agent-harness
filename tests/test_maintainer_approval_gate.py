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

    def test_maintain_role_qualifies(self):
        comments = [comment(10, "solo", f"{APPROVE_PREFIX} {HEAD}")]
        self.assertEqual(current_head_approvers(HEAD, comments, {"solo": "maintain"}), ["solo"])

    def test_admin_maintainer_qualifies(self):
        comments = [comment(10, "solo", f"{APPROVE_PREFIX} {HEAD}")]
        self.assertEqual(current_head_approvers(HEAD, comments, {"solo": "admin"}), ["solo"])

    def test_triage_and_read_only_users_do_not_qualify(self):
        comments = [
            comment(10, "triager", f"{APPROVE_PREFIX} {HEAD}"),
            comment(11, "reader", f"{APPROVE_PREFIX} {HEAD}"),
        ]
        self.assertEqual(
            current_head_approvers(
                HEAD,
                comments,
                {"triager": "triage", "reader": "read"},
            ),
            [],
        )

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


class MaintainerApprovalParserHardeningTests(unittest.TestCase):
    """Parser evasion and fail-closed hardening cases (extension; the cases
    above remain the authoritative baseline)."""

    def test_command_with_trailing_lines_is_rejected(self):
        body = f"{APPROVE_PREFIX} {HEAD}\ninject extra instructions"
        self.assertIsNone(_command(body))

    def test_command_on_second_line_is_rejected(self):
        body = f"looks good to me\n{APPROVE_PREFIX} {HEAD}"
        self.assertIsNone(_command(body))

    def test_comment_edited_from_approve_to_revoke_fails_closed(self):
        # An edited comment keeps its id; the latest content for that id must
        # win, so an approve edited into a revoke leaves no approval.
        comments = [
            comment(7, "solo", f"{APPROVE_PREFIX} {HEAD}"),
            comment(7, "solo", f"{REVOKE_PREFIX} {HEAD}"),
        ]
        self.assertEqual(current_head_approvers(HEAD, comments, {"solo": "write"}), [])
        ok, _detail = evaluate(HEAD, comments, {"solo": "write"})
        self.assertFalse(ok)

    def test_approver_demoted_between_evaluations_fails_closed(self):
        comments = [comment(1, "solo", f"{APPROVE_PREFIX} {HEAD}")]
        ok_before, _ = evaluate(HEAD, comments, {"solo": "write"})
        self.assertTrue(ok_before)
        ok_after, detail = evaluate(HEAD, comments, {"solo": "read"})
        self.assertFalse(ok_after)
        self.assertIn("write", detail)

    def test_command_with_extra_token_is_rejected(self):
        self.assertIsNone(_command(f"{APPROVE_PREFIX} {HEAD} extra-token"))
        self.assertIsNone(_command(f"{APPROVE_PREFIX} {HEAD}\textra-token"))

    def test_approval_for_different_head_is_not_counted(self):
        comments = [
            comment(1, "solo", f"{APPROVE_PREFIX} staleheadsha"),
            comment(2, "other", f"{APPROVE_PREFIX} {HEAD}"),
        ]
        self.assertEqual(candidate_logins(comments, HEAD), ["other"])
        ok, detail = evaluate(HEAD, comments, {"solo": "write", "other": "read"})
        self.assertFalse(ok)
        self.assertIn(f"{APPROVE_PREFIX} {HEAD}", detail)


if __name__ == "__main__":
    unittest.main()
