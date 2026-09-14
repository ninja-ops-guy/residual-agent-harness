"""Prevent duplicate Pages publishers and regressions in the reviewed workflow."""
from copy import deepcopy
from pathlib import Path
import re
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ".github/workflows/pages.yml"
DEPLOY_IF = "github.ref == 'refs/heads/main' && github.event_name != 'pull_request'"


def validate_publishers(documents):
    """Review-controlled workflow contract, not detection of arbitrary hidden egress."""
    publishers = []
    for filename, document in documents.items():
        if not isinstance(document, dict):
            raise ValueError(f"workflow must be a mapping: {filename}")
        for job_name, job in document.get("jobs", {}).items():
            for step in job.get("steps", []):
                if str(step.get("uses", "")).startswith("actions/deploy-pages@"):
                    publishers.append((filename, job_name))
            if job.get("permissions", {}).get("pages") == "write" and (filename, job_name) != (WORKFLOW, "deploy"):
                raise ValueError("Pages write permission outside the sole deployment job")
    if publishers != [(WORKFLOW, "deploy")]:
        raise ValueError("exactly one Pages publisher is required")
    doc = documents[WORKFLOW]
    if doc.get("permissions") != {"contents": "read"}:
        raise ValueError("default workflow permission must be contents:read only")
    build, deploy = doc["jobs"]["build"], doc["jobs"]["deploy"]
    if "permissions" in build and build["permissions"] != {"contents": "read"}:
        raise ValueError("build must be read-only")
    if deploy.get("if") != DEPLOY_IF or deploy.get("needs") != "build":
        raise ValueError("deployment must require successful build on main, never a PR")
    if deploy.get("permissions") != {"pages": "write", "id-token": "write"}:
        raise ValueError("deployment requires only Pages and OIDC permissions")
    if deploy.get("environment", {}).get("name") != "github-pages":
        raise ValueError("deployment must honor the github-pages environment")
    for job in doc["jobs"].values():
        for step in job.get("steps", []):
            if "uses" in step and not re.fullmatch(r"actions/[a-z-]+@[0-9a-f]{40}", step["uses"]):
                raise ValueError("top-level actions must be pinned to full SHAs")
    checkout = [s for s in build["steps"] if s.get("uses", "").startswith("actions/checkout@")]
    if len(checkout) != 1 or str(checkout[0].get("with", {}).get("persist-credentials")).lower() != "false":
        raise ValueError("checkout must not persist credentials")
    uploads = [s for s in build["steps"] if s.get("uses", "").startswith("actions/upload-pages-artifact@")]
    if len(uploads) != 1 or uploads[0].get("with", {}).get("path") != "_site":
        raise ValueError("only the validated public _site may be uploaded")
    for event in ("push", "pull_request"):
        if ".github/workflows/**" not in doc.get("on", {}).get(event, {}).get("paths", []):
            raise ValueError("workflow changes must trigger publisher validation")
    return True


class PagesPublisherTests(unittest.TestCase):
    def setUp(self):
        self.documents = {
            path.relative_to(ROOT).as_posix(): yaml.load(path.read_text(), Loader=yaml.BaseLoader)
            for path in sorted((ROOT / ".github/workflows").glob("*"))
            if path.suffix in (".yml", ".yaml")
        }
        self.document = self.documents[WORKFLOW]

    def test_repository_has_one_guarded_publisher(self):
        self.assertTrue(validate_publishers(self.documents))

    def test_second_publisher_file_rejected(self):
        self.documents[".github/workflows/pages-demo.yml"] = deepcopy(self.document)
        with self.assertRaises(ValueError):
            validate_publishers(self.documents)

    def test_second_deployment_job_rejected(self):
        self.document["jobs"]["duplicate"] = deepcopy(self.document["jobs"]["deploy"])
        with self.assertRaises(ValueError):
            validate_publishers(self.documents)

    def test_default_write_permission_rejected(self):
        self.document["permissions"]["pages"] = "write"
        with self.assertRaises(ValueError):
            validate_publishers(self.documents)

    def test_missing_build_dependency_rejected(self):
        self.document["jobs"]["deploy"].pop("needs")
        with self.assertRaises(ValueError):
            validate_publishers(self.documents)

    def test_pr_deployment_rejected(self):
        self.document["jobs"]["deploy"]["if"] = "always()"
        with self.assertRaises(ValueError):
            validate_publishers(self.documents)

    def test_repository_upload_rejected(self):
        for step in self.document["jobs"]["build"]["steps"]:
            if step.get("uses", "").startswith("actions/upload-pages-artifact@"):
                step["with"]["path"] = "."
        with self.assertRaises(ValueError):
            validate_publishers(self.documents)

    def test_persisted_checkout_token_rejected(self):
        self.document["jobs"]["build"]["steps"][0]["with"]["persist-credentials"] = "true"
        with self.assertRaises(ValueError):
            validate_publishers(self.documents)

    def test_mutable_action_reference_rejected(self):
        self.document["jobs"]["build"]["steps"][0]["uses"] = "actions/checkout@v4"
        with self.assertRaises(ValueError):
            validate_publishers(self.documents)

    def test_workflow_blind_trigger_rejected(self):
        self.document["on"]["pull_request"]["paths"] = ["demo/**"]
        with self.assertRaises(ValueError):
            validate_publishers(self.documents)


if __name__ == "__main__":
    unittest.main()
