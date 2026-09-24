"""Synthetic grammar controls; no package resolution or real artifact hashes."""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_release_lock.py"
SPEC = importlib.util.spec_from_file_location("lock_adversarial_target", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
H = "--hash=sha256:" + "a" * 64
H2 = "--hash=sha256:" + "b" * 64


class ReleaseLockAdversarialTests(unittest.TestCase):
    def lock(self, text):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "synthetic.lock"
        path.write_bytes(text.encode("utf-8"))
        return path

    def rejected(self, text):
        with self.assertRaises(module.LockContractError):
            module.validate_lock(self.lock(text))

    def test_wildcard_is_not_an_exact_version(self):
        self.rejected(f"demo==1.* {H}\n")

    def test_dot_alias_is_one_project(self):
        self.rejected(f"demo.pkg==1.0 {H}\ndemo-pkg==1.0 {H}\n")

    def test_trailing_token_is_not_ignored(self):
        self.rejected(f"demo==1.0 arbitrary-trailing-token {H}\n")

    def test_url_in_version_is_rejected(self):
        self.rejected(f"demo==https://example.invalid/demo.whl {H}\n")

    def test_canonical_version_positive_controls(self):
        for version in ("0", "1.2.3", "1!2.0", "2.0a1", "2.0b2", "2.0rc1",
                        "2.0.post1", "2.0.dev1", "2.0rc1.post2.dev3",
                        "2.0+vendor.1", "1!2.0rc1.post2.dev3+linux.1"):
            with self.subTest(version=version):
                result = module.validate_lock(self.lock(f"demo=={version} {H}\n"))
                self.assertEqual(result["status"], "PASS")

    def test_invalid_or_out_of_grammar_versions(self):
        for version in ("*", "1.*", "", "1.0,>=2", "1.0===2", "=1.0",
                        "1.0/evil", "1.0@evil", "1.0#fragment", "v1.0",
                        "1.0RC1", "01.0", "1.0+", "1.0..1", "NaN"):
            with self.subTest(version=version):
                self.rejected(f"demo=={version} {H}\n")

    def test_normalized_project_aliases(self):
        for left, right in (("Demo.Pkg", "demo-pkg"), ("demo__pkg", "demo--pkg"),
                            ("demo._-pkg", "demo-pkg"), ("DEMO", "demo")):
            with self.subTest(left=left, right=right):
                self.rejected(f"{left}==1.0 {H}\n{right}==2.0 {H2}\n")

    def test_name_positive_controls(self):
        for name in ("a", "7", "Demo.Pkg", "demo__pkg", "demo-1"):
            with self.subTest(name=name):
                self.assertEqual(module.validate_lock(self.lock(f"{name}==1.0 {H}"))["status"], "PASS")

    def test_invalid_names(self):
        for name in ("-demo", "_demo", "demo-", "demo.", "demo_", "demo[extra]", "démö"):
            with self.subTest(name=name):
                self.rejected(f"{name}==1.0 {H}")

    def test_options_markers_and_comments_are_not_silently_consumed(self):
        for tail in (f"{H} extra", f"{H} --index-url=https://example.invalid",
                     f"{H} ; python_version > '3'", f"# {H}", f"{H} # annotation",
                     f"{H} https://example.invalid/pkg.whl", f"{H} -r other.lock",
                     f"{H} --trusted-host=example.invalid"):
            with self.subTest(tail=tail):
                self.rejected(f"demo==1.0 {tail}\n")

    def test_hash_token_grammar(self):
        for value in ("--hash=sha256:" + "a"*63, "--hash=sha256:" + "a"*65,
                      "--hash=sha256:" + "g"*64, "--hash=sha256:" + "A"*64,
                      "--hash=sha512:" + "a"*128, "prefix" + H, H + "suffix"):
            with self.subTest(value=value):
                self.rejected(f"demo==1.0 {H} {value}\n")

    def test_missing_separator_before_hash(self):
        self.rejected(f"demo==1.0{H}\n")

    def test_complete_token_continuation_and_comments(self):
        text = "# synthetic only\r\n\r\ndemo==1.0 \\\r\n    " + H + " \\\r\n    " + H2 + "\r\n# end\r\n"
        result = module.validate_lock(self.lock(text))
        self.assertEqual(result["entries"], 1)
        self.assertEqual(result["unique_sha256_hashes"], 2)

    def test_unterminated_continuation(self):
        self.rejected(f"demo==1.0 {H} " + "\\\n")

    def test_interrupted_or_mid_token_continuation(self):
        for text in ("demo==1.0 \\\n# interrupted\n" + H,
                     "demo==1.0 \\\n\n" + H,
                     "demo==1.0\\\n " + H,
                     "\\\n" + f"demo==1.0 {H}"):
            with self.subTest(text=text):
                self.rejected(text)

    def test_non_ascii_and_control_whitespace(self):
        for separator in ("\x00", "\x0b", "\x0c", "\x1c", "\u00a0", "\u2028"):
            with self.subTest(separator=repr(separator)):
                self.rejected(f"demo==1.0{separator}{H}\n")

    def test_regular_whitespace_and_multiple_hashes(self):
        result = module.validate_lock(self.lock(f"\t demo==1.0\t{H}  {H2}\t\n"))
        self.assertEqual(result["unique_sha256_hashes"], 2)

    def test_unreadable_input_is_typed_failure(self):
        path = self.lock(f"demo==1.0 {H}\n")
        with mock.patch.object(Path, "read_bytes", side_effect=PermissionError("denied")), \
             mock.patch.object(Path, "read_text", side_effect=PermissionError("denied")):
            with self.assertRaises(module.LockContractError):
                module.validate_lock(path)

    def test_invalid_utf8_is_typed_failure(self):
        path = self.lock("")
        path.write_bytes(b"\xff")
        with self.assertRaises(module.LockContractError):
            module.validate_lock(path)

    def test_cli_invalid_is_blocked_without_pass(self):
        path = self.lock(f"demo==1.* {H}\n")
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", [str(SCRIPT), str(path)]), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = module.main()
        self.assertEqual(result, 2)
        self.assertNotIn("PASS", out.getvalue())
        self.assertIn("BLOCKED", err.getvalue())

    def test_cli_valid_is_validation_only(self):
        path = self.lock(f"demo==1.0 {H}\n")
        out = io.StringIO()
        with mock.patch.object(sys, "argv", [str(SCRIPT), str(path)]), contextlib.redirect_stdout(out):
            result = module.main()
        self.assertEqual(result, 0)
        self.assertIn("PASS entries=1", out.getvalue())


if __name__ == "__main__":
    unittest.main()
