"""Governance gate index: enforced gates must exist, keep their names, and
remain fail-closed; no workflow may shadow a required job name.

Deleting a gate workflow, renaming its job, dropping its fail-closed
invocation, or adding a second workflow that declares the same job name
(a shadow that could replace a required check's status context) must all
fail this test. The checkout credential invariant (#330) is owned by
tests/test_checkout_credentials.py and only referenced here.
"""
from __future__ import annotations

import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

# workflow file -> (required job name, required run-step substrings)
REQUIRED_GATES = {
    "maintainer-approval.yml": (
        "maintainer-approval",
        ("scripts/check_maintainer_approval.py", "--publish-status"),
    ),
    "factory-ownership.yml": (
        "factory-ownership",
        ("verifier/v3/check_factory_ownership.py",),
    ),
    "clean-install-qualification.yml": (
        "qualify",
        ("verifier/v3/qualify_clean_install.py",),
    ),
    "measured-eval-binding.yml": (
        "measured-eval-binding",
        ("tests/test_eval_frozen_acceptance_binding.py",),
    ),
}

ADVISORY_WORKFLOW = "pr-agent.yml"
ADVISORY_VERIFY_STEP_NAME = "Verify substantive advisory review was published"


def load_workflows() -> dict[str, dict]:
    docs: dict[str, dict] = {}
    for path in sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml"))):
        docs[path.name] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return docs


def run_steps(job: dict) -> list[str]:
    return [step.get("run", "") for step in job.get("steps", []) if isinstance(step, dict)]


class GovernanceGateIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflows = load_workflows()

    def test_every_required_gate_is_present_with_expected_job_and_invocation(self):
        for filename, (job_name, needles) in REQUIRED_GATES.items():
            with self.subTest(gate=filename):
                self.assertIn(
                    filename, self.workflows,
                    f"required gate workflow {filename} was deleted or renamed",
                )
                jobs = self.workflows[filename].get("jobs") or {}
                self.assertIn(
                    job_name, jobs,
                    f"{filename}: required job {job_name!r} was renamed or removed",
                )
                runs = run_steps(jobs[job_name])
                for needle in needles:
                    self.assertTrue(
                        any(needle in run for run in runs),
                        f"{filename}: no fail-closed step invokes {needle}",
                    )

    def test_maintainer_approval_publishes_status_fail_closed(self):
        # --publish-status is what makes the gate a blocking check; the flag
        # must appear in the same step that runs the checker.
        jobs = self.workflows["maintainer-approval.yml"]["jobs"]
        for job in jobs.values():
            for run in run_steps(job):
                if "scripts/check_maintainer_approval.py" in run:
                    self.assertIn(
                        "--publish-status", run,
                        "maintainer-approval gate lost its published blocking status",
                    )

    def test_pr_agent_advisory_verify_step_present(self):
        self.assertIn(ADVISORY_WORKFLOW, self.workflows)
        names = [
            step.get("name", "")
            for job in (self.workflows[ADVISORY_WORKFLOW].get("jobs") or {}).values()
            for step in job.get("steps", [])
            if isinstance(step, dict)
        ]
        self.assertIn(
            ADVISORY_VERIFY_STEP_NAME, names,
            "pr-agent workflow lost its advisory verification step",
        )

    # Pre-existing non-gate duplication found by this test on main:
    # `sleep-canary-live-main` is declared by both the standalone canary
    # workflow and the superset diagnostic workflow. Neither is a required
    # check, so the shadow risk is limited to status confusion on that
    # canary. It is recorded here as a known finding for owner follow-up
    # (fixing it requires .github/ changes, which this lane may not make);
    # ANY new duplicate, and any duplicate touching a required gate job,
    # fails closed.
    KNOWN_LEGACY_DUPLICATES = {
        "sleep-canary-live-main": {
            "webvm-runtime-diagnostic.yml",
            "webvm-runtime-sleep-canary.yml",
        },
    }

    def _job_owners(self) -> dict[str, list[str]]:
        owners: dict[str, list[str]] = {}
        for filename, doc in self.workflows.items():
            for job_name in (doc.get("jobs") or {}):
                owners.setdefault(job_name, []).append(filename)
        return owners

    def test_no_duplicate_job_names_across_workflows(self):
        owners = self._job_owners()
        duplicates = {job: set(files) for job, files in owners.items() if len(files) > 1}
        self.assertEqual(
            duplicates, self.KNOWN_LEGACY_DUPLICATES,
            "duplicate job-name set changed: new shadow jobs must be removed, "
            "and the legacy canary pair must be fixed in .github/ (owner task)",
        )

    def test_required_gate_jobs_cannot_be_shadowed(self):
        owners = self._job_owners()
        for filename, (job_name, _needles) in REQUIRED_GATES.items():
            with self.subTest(gate=job_name):
                self.assertEqual(
                    owners.get(job_name), [filename],
                    f"required gate job {job_name!r} is shadowed by {owners.get(job_name)}",
                )

    def test_checkout_credential_invariant_is_owned(self):
        # The #330 persist-credentials invariant lives in
        # tests/test_checkout_credentials.py; reference it rather than
        # duplicate its logic here.
        owner = ROOT / "tests" / "test_checkout_credentials.py"
        self.assertTrue(owner.is_file(), "checkout credential invariant test is missing")
        self.assertIn("persist-credentials: false", owner.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
