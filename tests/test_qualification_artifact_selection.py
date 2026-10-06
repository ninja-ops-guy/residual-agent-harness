"""Fail-closed regression coverage for Qualification v1 partial-rerun selection."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "select_qualification_artifacts",
    ROOT / "scripts/select_qualification_artifacts.py",
)
assert SPEC is not None and SPEC.loader is not None
selector = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = selector
SPEC.loader.exec_module(selector)

SOURCE = "a" * 40


def write_candidate(root: Path, producer: str, attempt: int, *, commit: str = SOURCE,
                    evidence_attempt: int | None = None) -> Path:
    path = root / f"qualification-v1-{producer}-{commit}-{attempt}"
    path.mkdir()
    payload = {
        "source": {"commit": commit},
        "environment": {"ci": {"GITHUB_RUN_ATTEMPT":
                               str(attempt if evidence_attempt is None else evidence_attempt)}},
    }
    (path / f"{producer}.evidence.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    return path


def write_full_attempt(root: Path, attempt: int = 1) -> None:
    for producer in selector.EXPECTED_PRODUCERS:
        write_candidate(root, producer, attempt)


class QualificationArtifactSelectionTests(unittest.TestCase):
    def test_partial_rerun_selects_newest_only_for_rerun_producer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_full_attempt(root, 1)
            write_candidate(root, "active-http", 2)

            candidates = selector.discover_candidates(root, SOURCE, 2)
            selected = selector.select_candidates(candidates)

            self.assertEqual(selected["active-http"].attempt, 2)
            self.assertEqual(selected["deterministic"].attempt, 1)
            self.assertEqual(set(selected), set(selector.EXPECTED_PRODUCERS))

    def test_wrong_source_commit_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_full_attempt(root, 1)
            wrong = "b" * 40
            path = root / f"qualification-v1-active-http-{SOURCE}-1"
            path.rename(root / f"qualification-v1-active-http-{wrong}-1")
            with self.assertRaisesRegex(ValueError, "source commit mismatch"):
                selector.discover_candidates(root, SOURCE, 1)

    def test_future_attempt_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_full_attempt(root, 1)
            write_candidate(root, "active-http", 2)
            with self.assertRaisesRegex(ValueError, "future run attempt"):
                selector.discover_candidates(root, SOURCE, 1)

    def test_missing_producer_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_full_attempt(root, 1)
            target = root / f"qualification-v1-macos-{SOURCE}-1"
            for child in target.iterdir():
                child.unlink()
            target.rmdir()
            candidates = selector.discover_candidates(root, SOURCE, 1)
            with self.assertRaisesRegex(ValueError, "missing qualification producers: macos"):
                selector.select_candidates(candidates)

    def test_ambiguous_newest_attempt_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_full_attempt(root, 1)
            candidates = selector.discover_candidates(root, SOURCE, 1)
            candidates.append(selector.ArtifactCandidate(
                producer="active-http",
                attempt=1,
                path=Path("second-active-http"),
                evidence_count=1,
            ))
            with self.assertRaisesRegex(ValueError, "ambiguous qualification producer active-http"):
                selector.select_candidates(candidates)

    def test_evidence_attempt_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_full_attempt(root, 1)
            target = root / f"qualification-v1-active-http-{SOURCE}-1"
            evidence = target / "active-http.evidence.json"
            payload = json.loads(evidence.read_text(encoding="utf-8"))
            payload["environment"]["ci"]["GITHUB_RUN_ATTEMPT"] = "2"
            evidence.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "evidence run attempt mismatch"):
                selector.discover_candidates(root, SOURCE, 2)

    def test_materialization_records_selected_attempts_without_flattening(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "artifacts"
            root.mkdir()
            write_full_attempt(root, 1)
            write_candidate(root, "active-http", 2)
            selected = selector.select_candidates(
                selector.discover_candidates(root, SOURCE, 2)
            )
            output = Path(directory) / "selected"
            record = Path(directory) / "selection.json"

            selector.materialize_selection(selected, output, record)

            self.assertTrue((output / "active-http" / "active-http.evidence.json").is_file())
            self.assertTrue((output / "deterministic" / "deterministic.evidence.json").is_file())
            rows = json.loads(record.read_text(encoding="utf-8"))["selected"]
            attempts = {row["producer"]: row["attempt"] for row in rows}
            self.assertEqual(attempts["active-http"], 2)
            self.assertEqual(attempts["deterministic"], 1)


if __name__ == "__main__":
    unittest.main()
