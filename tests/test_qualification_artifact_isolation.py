"""Offline regression coverage for retained Qualification v1 rerun artifacts."""
from fnmatch import fnmatchcase
from pathlib import Path
import re
import tempfile
import unittest

from residual.qualification.evidence import EvidenceEnvelope, GateResult, write_envelope
from residual.qualification.manifest import aggregate_manifest


EXPECTED_PRODUCERS = {
    "deterministic": "deterministic",
    "discovery": "discovery",
    "m4": "m4",
    "artifacts": "artifacts",
    "browser": "browser-${{ matrix.browser }}",
    "concurrency": "concurrency",
    "protocol-fuzz": "protocol-fuzz",
    "toxic-provider": "toxic-provider",
    "active-workload": "active-workload",
    "browser-adversarial": "browser-adversarial",
    "redteam": "redteam",
    "windows-lifecycle": "windows",
    "fault-injection": "fault-injection",
    "webvm-protocol-fuzz": "webvm-protocol-fuzz",
    "qualification-selftests": "selftests",
    "active-http-soak": "active-http",
    "macos-lifecycle": "macos",
}


class QualificationArtifactIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workflow = (Path(__file__).resolve().parents[1]
                    / ".github/workflows/qualification-v1.yml").read_text(encoding="utf-8")
        producers, aggregate = workflow.split("\n  aggregate:\n")
        cls.pattern, = re.findall(r"^          pattern: (.+)$", aggregate, re.MULTILINE)
        cls.final, = re.findall(r"^          name: (.+)$", aggregate, re.MULTILINE)
        final_uploads = [step for step in re.split(r"^      - ", aggregate, flags=re.MULTILINE)[1:]
                         if re.search(r"^\s*uses: actions/upload-artifact@\S+", step, re.MULTILINE)]
        cls.final_upload, = final_uploads
        cls.producers = []
        # Inspect upload steps, not a subset selected by artifact-name prefix.
        # These boundaries follow this workflow's block-style job/step layout.
        jobs = re.split(r"^  ([\w-]+):\s*$", producers.split("\njobs:\n", 1)[1],
                        flags=re.MULTILINE)
        for job, body in zip(jobs[1::2], jobs[2::2]):
            for step in re.split(r"^      - ", body, flags=re.MULTILINE)[1:]:
                if re.search(r"^\s*uses: actions/upload-artifact@\S+", step, re.MULTILINE):
                    names = re.findall(r"^          name: (.+)$", step, re.MULTILINE)
                    if len(names) != 1:
                        raise AssertionError(f"{job}: upload step must have exactly one artifact name")
                    cls.producers.append((job, names[0]))

    def test_retained_final_attempts_never_match_input_pattern(self):
        self.assertEqual(self.pattern, "qualification-v1-*")
        names = set()
        for run_id in (100, 101):
            for attempt in (1, 2, 3):
                name = (self.final.replace("${{ github.sha }}", "a" * 40)
                        .replace("${{ github.run_id }}", str(run_id))
                        .replace("${{ github.run_attempt }}", str(attempt)))
                self.assertNotIn("${{", name)
                self.assertFalse(fnmatchcase(name, self.pattern), name)
                names.add(name)
        self.assertEqual(len(names), 6)

    def test_every_producer_remains_selectable_across_partial_reruns(self):
        self.assertEqual(len(self.producers), 17)
        self.assertCountEqual(self.producers, [
            (job, "qualification-v1-" + suffix + "-${{ github.event.pull_request.head.sha || github.sha }}-${{ github.run_attempt }}")
            for job, suffix in EXPECTED_PRODUCERS.items()
        ])
        expanded = []
        for job, template in self.producers:
            # Attempt-separated producer artifacts retain prior jobs without overwrite.
            self.assertIn("github.run_attempt", template)
            browsers = ("chromium", "firefox", "webkit") if job == "browser" else (None,)
            for browser in browsers:
                name = (template.replace("${{ github.event.pull_request.head.sha || github.sha }}", "a" * 40)
                        .replace("${{ github.run_attempt }}", "2")
                        .replace("${{ github.run_id }}", "100"))
                if browser is not None:
                    name = name.replace("${{ matrix.browser }}", browser)
                self.assertNotIn("${{", name)
                self.assertTrue(fnmatchcase(name, self.pattern), f"{job}: {name}")
                expanded.append(name)
        self.assertEqual(len(expanded), 19)
        self.assertEqual(len(set(expanded)), 19)

    def test_final_upload_preserves_retained_evidence(self):
        overwrite = re.findall(r"^          overwrite: (.+)$", self.final_upload, re.MULTILINE)
        self.assertIn(overwrite, ([], ["false"]))

    def test_duplicate_dsm_evidence_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for attempt in (1, 2):
                envelope = EvidenceEnvelope(
                    gate_id="dsm-fault-matrix", result=GateResult.PASS,
                    started_at="2026-09-16T00:00:00Z",
                    finished_at="2026-09-16T00:00:01Z",
                    source={"commit": "a" * 40, "tree": "b" * 40,
                            "tracked_source_dirty": False},
                    environment={"ci": {"GITHUB_RUN_ATTEMPT": str(attempt)}},
                )
                paths.append(write_envelope(envelope, Path(directory) / f"{attempt}.evidence.json"))
            self.assertEqual(aggregate_manifest(paths[:1], required_gates=["dsm-fault-matrix"]).result,
                             GateResult.PASS)
            with self.assertRaisesRegex(ValueError, "duplicate evidence for gate 'dsm-fault-matrix'"):
                aggregate_manifest(paths, required_gates=["dsm-fault-matrix"])


if __name__ == "__main__":
    unittest.main()
