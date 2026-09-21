from __future__ import annotations

from pathlib import Path
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "pr-agent.yml"


class PRAgentAdvisoryGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        start = self.workflow.index('published="$(')
        end = self.workflow.index('if [[ "$published" -lt 1 ]]', start)
        self.query = self.workflow[start:end]

    def test_gate_requires_pr_agent_full_review_marker(self) -> None:
        self.assertIn('github-actions[bot]', self.query)
        self.assertIn('.updated_at >=', self.query)
        self.assertIn('<!-- pr-agent:review:full -->', self.query)

    def test_failure_comment_cannot_satisfy_the_structural_gate(self) -> None:
        failure_comment = "Failed to review PR"
        full_review = "## PR Reviewer Guide\n<!-- pr-agent:review:full -->"
        self.assertNotIn('<!-- pr-agent:review:full -->', failure_comment)
        self.assertIn('<!-- pr-agent:review:full -->', full_review)
        self.assertIn('failure/status comments do not satisfy this gate', self.workflow)

    def test_reviewer_uses_append_only_exact_head_reviews(self) -> None:
        # GITHUB_TOKEN cannot reliably prove the bot identity needed for a safe
        # persistent-comment mutation. Each run therefore publishes a fresh full
        # review; the structural gate below binds it to the current run window.
        start = self.workflow.index("- name: Run advisory PR review")
        end = self.workflow.index("- name: Verify substantive advisory review was published", start)
        review_step = self.workflow[start:end]
        self.assertIn('PR_REVIEWER.PERSISTENT_COMMENT: "false"', review_step)

    def test_bot_issue_comments_cannot_cancel_human_review_runs(self) -> None:
        # Concurrency identity must distinguish pull_request vs issue_comment and
        # User vs Bot senders. This prevents status bots from cancelling the
        # advisory run before its job-level sender filter can reject the bot.
        group_line = next(
            line.strip() for line in self.workflow.splitlines() if line.strip().startswith("group: pr-agent-")
        )
        self.assertIn("github.event_name", group_line)
        self.assertIn("github.event.sender.type", group_line)
        self.assertIn("cancel-in-progress: true", self.workflow)


if __name__ == "__main__":
    unittest.main()
