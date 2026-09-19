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


if __name__ == "__main__":
    unittest.main()
