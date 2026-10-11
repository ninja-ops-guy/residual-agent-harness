"""Offline argument-boundary tests: no browser, provider, or network is invoked."""
import contextlib
import io
import unittest
from pathlib import Path

from demo.vm.browser_smoke_cli import parse_args


class WebVmFirefoxCliTests(unittest.TestCase):
    def args(self, *extras):
        return ["--url", "http://127.0.0.1:8765/demo/", "--output", "evidence/firefox",
                "--expected-sha", "a" * 40, *extras]

    def test_all_three_browser_engines_use_one_full_acceptance_cli(self):
        for engine in ("chromium", "firefox", "webkit"):
            with self.subTest(engine=engine):
                opts = parse_args(self.args("--browser", engine))
                self.assertEqual(opts.browser, engine)
                self.assertEqual(opts.expected_sha, "a" * 40)
                self.assertEqual(opts.output, Path("evidence/firefox"))
                self.assertFalse(opts.mobile)

    def test_existing_default_and_mobile_behavior_remain(self):
        opts = parse_args(self.args("--mobile", "--boot-timeout", "180"))
        self.assertEqual(opts.browser, "chromium")
        self.assertTrue(opts.mobile)
        self.assertEqual(opts.boot_timeout, 180)

    def test_unsupported_engine_fails_closed(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                parse_args(self.args("--browser", "edge"))
        self.assertEqual(error.exception.code, 2)

    def test_required_provenance_and_artifact_destination_cannot_be_omitted(self):
        for omitted in ("--url", "--output", "--expected-sha"):
            tokens = self.args()
            index = tokens.index(omitted)
            del tokens[index:index + 2]
            with self.subTest(omitted=omitted), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    parse_args(tokens)
                self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
