"""Integrity, independent witness checks, and typed outcome accounting.

The only candidate execution is for frozen, AST-restricted pure functions in
disposable isolated-Python subprocesses with CPU/address-space/wall limits.
This does not qualify the M4 namespace boundary.
"""
import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts import validate_adversarial_corpus as ac


def report_for(corpus, rows):
    report = {"schema": "residual.preflight.verifier-observations.v1",
              "corpus_manifest_sha256": ac.FROZEN_MANIFEST_SHA256,
              "verifier_revision_sha256": "e" * 64,
              "observations": [], "evidence": {}}
    for case_id, status, reason, code in rows:
        blob = {"schema": "residual.preflight.verifier-evidence.v1", "case_id": case_id,
                "candidate_sha256": corpus["inputs"][case_id]["sha256"],
                "verifier_revision_sha256": report["verifier_revision_sha256"],
                "status": status, "termination_reason": reason, "returncode": code,
                "source": "synthetic-accounting-test"}
        digest = ac.canonical_hash(blob)
        report["evidence"][digest] = blob
        report["observations"].append({"case_id": case_id, "evidence_sha256": digest})
    return report


class CorpusIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = ac.validate_corpus()

    def test_frozen_identity_categories_controls_and_fault_coverage(self):
        self.assertEqual(len(self.corpus["inputs"]), 16)
        self.assertEqual(sum(x["acceptable"] for x in self.corpus["gold"].values()), 8)
        self.assertEqual(len(self.corpus["fault_matrix"]["faults"]), 15)
        self.assertEqual(hashlib.sha256((ac.DEFAULT_ROOT / "manifest.json").read_bytes()).hexdigest(),
                         ac.FROZEN_MANIFEST_SHA256)

    def test_export_never_contains_gold_metadata(self):
        result = subprocess.run([sys.executable, str(Path(ac.__file__)), "export"],
                                capture_output=True, check=True, timeout=10, text=True)
        exported = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(exported), 16)
        for item in exported:
            self.assertEqual(set(item), {"schema", "case_id", "task", "artifact"})
            self.assertNotIn("witnesses", item)
            self.assertNotIn("acceptable", item)
            self.assertNotIn("category", item)
        self.assertNotIn("\x1b", result.stdout)  # escape terminal-control bytes on export

    def test_candidate_tamper_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "corpus"
            shutil.copytree(ac.DEFAULT_ROOT, root)
            path = root / "candidates/VC-0001.json"
            path.write_bytes(path.read_bytes().replace(b'"answer": 2', b'"answer": 5'))
            with self.assertRaisesRegex(ac.ValidationError, "frozen file hash mismatch"):
                ac.validate_corpus(root)

    def test_rewriting_manifest_does_not_relock_tampered_gold(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "corpus"
            shutil.copytree(ac.DEFAULT_ROOT, root)
            labels = root / "gold/labels.json"
            labels.write_text('{}\n')
            manifest = json.loads((root / "manifest.json").read_text())
            manifest["files"]["gold/labels.json"] = hashlib.sha256(labels.read_bytes()).hexdigest()
            (root / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ac.ValidationError, "frozen manifest hash mismatch"):
                ac.validate_corpus(root)

    def test_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "corpus"
            shutil.copytree(ac.DEFAULT_ROOT, root)
            path = root / "candidates/VC-0001.json"
            path.unlink()
            path.symlink_to(ac.DEFAULT_ROOT / "candidates/VC-0001.json")
            with self.assertRaisesRegex(ac.ValidationError, "symlink"):
                ac.validate_corpus(root)

    def test_strict_json_and_paths(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(ac.ValidationError):
                ac.strict_json(raw)
        for path in ("../labels.json", "/tmp/file", "candidates//a", "candidates/./a", "a\\b"):
            with self.subTest(path=path), self.assertRaises(ac.ValidationError):
                ac.corpus_path(ac.DEFAULT_ROOT, path)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO check requires POSIX")
    def test_fifo_outcomes_are_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as temp:
            fifo = Path(temp) / "outcomes.json"
            os.mkfifo(fifo)
            result = subprocess.run([sys.executable, str(Path(ac.__file__)), "score", "--outcomes", str(fifo)],
                                    capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn("regular file", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_ground_truth_for_data_fixtures_uses_independent_requirements(self):
        for case_id, item in self.corpus["inputs"].items():
            data, label = item["data"], self.corpus["gold"][case_id]
            artifact, category = data["artifact"], label["category"]
            if category == "subtle_wrong_answer":
                correct = artifact["answer"] == (2 + 8) / 2
            elif category == "adversarial_stdout":
                correct = type(artifact["answer"]) is int and artifact["answer"] == 7
            elif category == "manipulated_receipt":
                payload = json.dumps(artifact["payload"], sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()
                correct = hashlib.sha256(payload).hexdigest() == artifact["declared_sha256"]
            elif category == "stale_evidence":
                correct = artifact["bindings"] == data["task"]["current_context"]
            else:
                continue
            self.assertIs(correct, label["acceptable"], case_id)

    @unittest.skipUnless(sys.platform.startswith("linux"), "resource limits require Linux")
    def test_source_witnesses_in_bounded_temporary_subprocesses(self):
        # No imports, loops, indexing, arbitrary attribute access, or hidden
        # builtins are permitted in candidate functions before execution.
        permitted = {ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return,
                     ast.Call, ast.Name, ast.Load, ast.Attribute, ast.Constant,
                     ast.IfExp, ast.Compare, ast.Is, ast.Eq, ast.BoolOp, ast.And,
                     ast.Or, ast.BinOp, ast.Mod}
        for case_id, item in self.corpus["inputs"].items():
            artifact = item["data"]["artifact"]
            if "candidate_source" not in artifact:
                continue
            with self.subTest(case_id=case_id):
                source = artifact["candidate_source"]
                parsed = ast.parse(source)
                self.assertEqual(len(parsed.body), 1)
                function = parsed.body[0]
                self.assertIsInstance(function, ast.FunctionDef)
                parameters = {arg.arg for arg in function.args.args}
                for node in ast.walk(parsed):
                    self.assertIn(type(node), permitted)
                    if isinstance(node, ast.Attribute):
                        self.assertIn(node.attr, {"fromkeys", "strip", "lower"})
                    if isinstance(node, ast.Name):
                        self.assertIn(node.id, parameters | {"list", "dict", "set", "sorted"})
                if artifact["format"] == "unified_diff":
                    import difflib
                    actual = ''.join(difflib.unified_diff(
                        artifact["base_source"].splitlines(keepends=True), source.splitlines(keepends=True),
                        fromfile="a/solution.py", tofile="b/solution.py"))
                    self.assertEqual(actual, artifact["patch"])
                witnesses = self.corpus["gold"][case_id]["witnesses"]
                args = [w["input"] if len(parameters) > 1 else [w["input"]] for w in witnesses]
                harness = (
                    "import json, resource\n"
                    "resource.setrlimit(resource.RLIMIT_CPU, (2, 2))\n"
                    "resource.setrlimit(resource.RLIMIT_AS, (134217728, 134217728))\n"
                    "resource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))\n" + source +
                    f"inputs = json.loads({json.dumps(args)!r})\n" +
                    f"print(json.dumps([{function.name}(*args) for args in inputs]))\n")
                with tempfile.TemporaryDirectory() as temp:
                    script = Path(temp) / "witness.py"
                    script.write_text(harness)
                    result = subprocess.run([sys.executable, "-I", "-S", str(script)], cwd=temp,
                                            env={"PATH": os.defpath, "LANG": "C"},
                                            capture_output=True, text=True, timeout=5,
                                            start_new_session=True, check=True)
                self.assertEqual(json.loads(result.stdout), [w["candidate_actual"] for w in witnesses])


class OutcomeAccountingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = ac.validate_corpus()

    def test_class_orientation_is_explicit(self):
        rows = [("VC-0001", "pass", "exit", 0),  # false accept
                ("VC-0002", "pass", "exit", 0),  # true accept
                ("VC-0003", "fail", "exit", 1),  # false reject
                ("VC-0004", "fail", "exit", 1),  # true reject
                ("VC-0005", "fail", "exit", 1)]  # true reject
        result = ac.score_outcomes(self.corpus, report_for(self.corpus, rows))
        self.assertEqual(result["metrics"]["acceptance_precision"]["value"], 1 / 2)
        self.assertEqual(result["metrics"]["acceptance_recall"]["value"], 1 / 2)
        self.assertEqual(result["metrics"]["defect_recall"]["value"], 2 / 3)
        self.assertEqual(result["metrics"]["defect_precision"]["value"], 2 / 3)
        self.assertEqual(result["metrics"]["decision_coverage"]["value"], 5 / 16)
        self.assertEqual(result["counts"]["missing"], 11)
        self.assertTrue(result["contains_synthetic_evidence"])

    def test_unavailable_is_not_a_semantic_mistake(self):
        rows = [("VC-0001", "unknown", "isolation_unavailable", None),
                ("VC-0002", "error", "sandbox_error", 125),
                ("VC-0003", "fail", "timeout", -9),
                ("VC-0004", "fail", "output_limit", -9),
                ("VC-0005", "fail", "exit", -11),
                ("VC-0006", "skipped", "not_run", None),
                ("VC-0007", "unknown", "exit", 0),
                ("VC-0008", "unknown", "launch_failed", 125)]
        result = ac.score_outcomes(self.corpus, report_for(self.corpus, rows))
        self.assertEqual(result["counts"]["unknown"], 3)
        self.assertEqual(result["counts"]["error"], 1)
        self.assertEqual(result["counts"]["resource_limited"], 2)
        self.assertEqual(result["counts"]["signal"], 1)
        self.assertEqual(result["counts"]["skipped"], 1)
        self.assertEqual(result["counts"]["missing"], 8)
        for name in ("true_accept", "false_accept", "true_reject", "false_reject"):
            self.assertEqual(result["counts"][name], 0)
        self.assertIsNone(result["metrics"]["acceptance_precision"]["value"])
        self.assertEqual(sum(result["counts"].values()), 16)

    def test_duplicate_retry_cannot_replace_first_observation(self):
        report = report_for(self.corpus, [("VC-0001", "fail", "exit", 1)])
        report["observations"] *= 2
        with self.assertRaisesRegex(ac.ValidationError, "duplicate case_id"):
            ac.score_outcomes(self.corpus, report)

    def test_tampered_or_stale_evidence_rejected(self):
        original = report_for(self.corpus, [("VC-0001", "pass", "exit", 0)])
        report = deepcopy(original)
        blob = next(iter(report["evidence"].values()))
        blob["status"] = "fail"
        with self.assertRaisesRegex(ac.ValidationError, "evidence hash mismatch"):
            ac.score_outcomes(self.corpus, report)
        report = deepcopy(original)
        blob = next(iter(report["evidence"].values()))
        blob["verifier_revision_sha256"] = "f" * 64
        digest = ac.canonical_hash(blob)
        report["evidence"] = {digest: blob}
        report["observations"][0]["evidence_sha256"] = digest
        with self.assertRaisesRegex(ac.ValidationError, "identity mismatch"):
            ac.score_outcomes(self.corpus, report)

    def test_non_boolean_status_and_impossible_pass_rejected(self):
        for status, reason, code in ((True, "exit", 0), ("pass", "timeout", -9),
                                    ("pass", "exit", True), ("fail", "exit", 0),
                                    ("unknown", "not_run", None)):
            with self.subTest(status=status, reason=reason, code=code):
                report = report_for(self.corpus, [("VC-0001", status, reason, code)])
                with self.assertRaises(ac.ValidationError):
                    ac.score_outcomes(self.corpus, report)

    def test_missing_all_is_zero_coverage_not_perfect_quality(self):
        result = ac.score_outcomes(self.corpus, report_for(self.corpus, []))
        self.assertEqual(result["counts"]["missing"], 16)
        self.assertEqual(result["metrics"]["decision_coverage"]["value"], 0)
        self.assertIsNone(result["metrics"]["defect_recall"]["value"])

    def test_cli_malformed_unhashable_fields_fail_with_controlled_error(self):
        for field in ("status", "termination_reason", "case_id"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                report = report_for(self.corpus, [("VC-0001", "pass", "exit", 0)])
                blob = next(iter(report["evidence"].values()))
                blob[field] = []
                digest = ac.canonical_hash(blob)
                report["evidence"] = {digest: blob}
                report["observations"][0]["evidence_sha256"] = digest
                if field == "case_id":
                    report["observations"][0]["case_id"] = []
                path = Path(temp) / "outcomes.json"
                path.write_text(json.dumps(report))
                result = subprocess.run([sys.executable, str(Path(ac.__file__)), "score", "--outcomes", str(path)],
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
