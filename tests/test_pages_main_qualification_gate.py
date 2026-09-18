"""Structural regression gate for issue #267.

Proves a CI/config/docs-only merge to main cannot bypass the authoritative
production Pages qualification gate. This is a static wiring assertion, not a
substitute for the live production Pages attempt itself.

Checks the push trigger of .github/workflows/pages.yml:
1. fires for every main SHA (no `paths:`/`paths-ignore:` filter that can skip
   a CI/config-only merge);
2. keeps production concurrency non-cancelling (a later merge cannot erase an
   earlier failing attempt);
3. retains the proof/deploy/artifact steps that make the attempt authoritative.

Text-parsed (no PyYAML dependency) so it runs on the bare workflow runners.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / '.github' / 'workflows' / 'pages.yml'
WORKFLOW = WORKFLOW_PATH.read_text()


def _trigger_block(name: str) -> str:
    """Return the indented body of one `on:` trigger key."""
    marker = f'  {name}:\n'
    assert WORKFLOW.count(marker) == 1, f'missing/duplicated {name} trigger'
    body = WORKFLOW.split(marker, 1)[1]
    # The trigger body ends at the next two-space-indented key (another
    # trigger or the end of the `on:` mapping).
    end = re.search(r'\n  \S', body)
    return body[: end.start()] if end else body


class MainPushTriggerTests(unittest.TestCase):
    def test_push_trigger_targets_main(self):
        push = _trigger_block('push')
        self.assertIn('branches: [main]', push)

    def test_push_trigger_has_no_paths_filter(self):
        push = _trigger_block('push')
        self.assertNotRegex(
            push,
            re.compile(r'^\s+paths(-ignore)?:', re.MULTILINE),
            'production push trigger must not skip main merges by path: '
            'a CI/config-only merge would advance main with no Pages attempt '
            '(issue #267)',
        )

    def test_ci_config_only_merge_cannot_bypass_gate(self):
        """Simulate #197-style merge: only CI/config/docs files change."""
        push = _trigger_block('push')
        changed_files = [
            '.github/workflows/pr-agent.yml',
            'docs/runbook.md',
            'pyproject.toml.example-note',
        ]
        filters = re.findall(r"^\s+-\s+'([^']+)'", push, flags=re.MULTILINE)
        # With no paths list every changed file trivially matches the gate.
        # If a paths list ever returns, assert these files would be excluded
        # (the regression) so the test fails loudly.
        if filters:
            import fnmatch

            matched = any(
                fnmatch.fnmatchcase(path, pattern)
                for path in changed_files
                for pattern in filters
            )
            self.fail(
                f'paths filter {filters} would let a CI/config-only main merge '
                f'bypass production Pages qualification; matched={matched}'
            )

    def test_workflow_dispatch_retained_for_manual_repair(self):
        self.assertIn('  workflow_dispatch:', WORKFLOW)


class ProductionConcurrencyTests(unittest.TestCase):
    def test_production_attempt_is_non_cancelling(self):
        self.assertIn(
            "cancel-in-progress: ${{ github.event_name == 'pull_request' }}",
            WORKFLOW,
            'production cancel-in-progress must stay false so a later merge '
            'cannot erase an earlier failing attempt',
        )

    def test_production_concurrency_group_is_stable(self):
        self.assertIn(
            "github.event.pull_request.number || 'production' }}", WORKFLOW
        )


class AuthoritativeContentTests(unittest.TestCase):
    """The attempt must remain authoritative: proof, deploy, retention."""

    def test_attempt_specific_artifact_identity_retained(self):
        self.assertIn('id: pages-artifact', WORKFLOW)
        self.assertIn('$GITHUB_RUN_ID', WORKFLOW)
        self.assertIn('$GITHUB_RUN_ATTEMPT', WORKFLOW)

    def test_generated_browser_proof_retained(self):
        self.assertIn('browser_smoke.py --url "$URL" --expected-sha "$GITHUB_SHA" --output browser-evidence/desktop', WORKFLOW)
        self.assertIn('--output browser-evidence/narrow --mobile', WORKFLOW)

    def test_deploy_gated_to_main_and_proof_job(self):
        self.assertIn(
            "if: github.event_name != 'pull_request' && github.ref == 'refs/heads/main'",
            WORKFLOW,
        )
        self.assertIn('needs: build-and-browser-proof', WORKFLOW)
        self.assertIn('actions/deploy-pages@v4', WORKFLOW)

    def test_published_revision_reverified_after_deploy(self):
        self.assertIn('live-browser-evidence/desktop', WORKFLOW)
        self.assertIn('live-browser-evidence/narrow', WORKFLOW)
        self.assertIn('Retain live acceptance proof', WORKFLOW)
        self.assertIn('if: always()', WORKFLOW)

    def test_exact_revision_identity_binding(self):
        # Both pre-deploy and post-deploy proofs bind the exact merged SHA.
        self.assertGreaterEqual(WORKFLOW.count('--expected-sha "$GITHUB_SHA"'), 3)


class ActivationCleanupTests(unittest.TestCase):
    """The temporary staging copy must disappear once the workflow is active."""

    def test_obsolete_staging_copy_is_absent(self):
        self.assertFalse(
            (ROOT / 'ci' / 'pages.yml').exists(),
            'ci/pages.yml is a stale duplicate after activation under .github/workflows',
        )


if __name__ == '__main__':
    unittest.main()
