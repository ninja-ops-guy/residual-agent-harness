"""Unit tests for scripts/m4_runner_preflight.py and the fail-loudly gating
mode in tests/test_factory_m4_sandbox.py (M4_REQUIRE_ISOLATION=1).

Teeth: a mutant that turns a BLOCKED capability into a silent skip — or into
a PASS — fails tests in this file.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_PATH = REPO_ROOT / "scripts" / "m4_runner_preflight.py"
SANDBOX_TEST_PATH = REPO_ROOT / "tests" / "test_factory_m4_sandbox.py"

sys.path.insert(0, str(REPO_ROOT))


def _load_preflight():
    spec = importlib.util.spec_from_file_location("m4_runner_preflight", PREFLIGHT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


preflight = _load_preflight()


class FakeProbe(preflight.Probe):
    """Deterministic, fully in-memory Probe substitute."""

    def __init__(
        self,
        files: dict[str, str] | None = None,
        run_results: dict[tuple[str, ...], tuple[int, str]] | None = None,
        default_run: tuple[int, str] = (0, ""),
        bwrap: bool = True,
        pidfd_ok: bool = True,
        pidfd_call_ok: bool = True,
        free_bytes: int = 1 << 30,
    ):
        self.files = dict(files or {})
        self.run_results = dict(run_results or {})
        self.default_run = default_run
        self.bwrap = bwrap
        self.pidfd_ok = pidfd_ok
        self.pidfd_call_ok = pidfd_call_ok
        self.free_bytes = free_bytes
        self.ran: list[list[str]] = []

    def read_text(self, path: str):
        return self.files.get(path)

    def run(self, argv, timeout: int = 20):
        self.ran.append(list(argv))
        key = tuple(argv)
        for prefix, result in self.run_results.items():
            if list(key[: len(prefix)]) == list(prefix):
                return result
        return self.default_run

    def which(self, name: str):
        if name == "bwrap":
            return "/usr/bin/bwrap" if self.bwrap else None
        return f"/usr/bin/{name}"

    def has_pidfd_open(self) -> bool:
        return self.pidfd_ok

    def pidfd_open_self(self) -> int:
        if not self.pidfd_call_ok:
            raise OSError(38, "Function not implemented")
        return 3

    def unix_socket_probe(self, directory: str):
        return (True, "af_unix_bind_listen_ok")

    def statvfs_free(self, path: str) -> int:
        return self.free_bytes

    def write_and_fsync(self, path: str, payload: bytes) -> None:
        with open(path, "wb") as fh:
            fh.write(payload)


ALL_SYSCTL_FILES = {
    "/proc/sys/kernel/unprivileged_userns_clone": "1\n",
    "/proc/sys/user/max_user_namespaces": "15000\n",
    "/proc/self/status": "Name:\tpython3\nSeccomp:\t2\nSeccomp_filters:\t1\n",
    "/proc/sys/kernel/seccomp/actions_avail": "allow errno trap kill_process kill_thread log trace user_notif filter\n",
    "/sys/fs/cgroup/cgroup.controllers": "cpu memory pids\n",
}


def passing_probe(**overrides) -> FakeProbe:
    kwargs = dict(files=dict(ALL_SYSCTL_FILES))
    kwargs.update(overrides)
    return FakeProbe(**kwargs)


class CapabilityCheckTests(unittest.TestCase):
    def test_all_pass_yields_qualified(self):
        probe = passing_probe()
        with tempfile.TemporaryDirectory() as tmp, patch("os.access", return_value=True):
            report = preflight.run_preflight(probe=probe, runs_dir=tmp)
        self.assertEqual(report["verdict"], "QUALIFIED")
        self.assertEqual(report["blocked"], [])
        self.assertTrue(all(c["status"] == "PASS" for c in report["capabilities"].values()))

    def test_userns_exec_probe_refusal_is_blocked(self):
        probe = passing_probe(
            run_results={(preflight._UNSHARE, "--user", "--map-root-user"): (1, "unshare: unshare failed: Operation not permitted")},
        )
        with tempfile.TemporaryDirectory() as tmp, patch("os.access", return_value=True):
            report = preflight.run_preflight(probe=probe, runs_dir=tmp)
        for ns in ("user_namespace", "mount_namespace", "pid_namespace", "ipc_namespace", "uts_namespace", "net_namespace"):
            self.assertEqual(report["capabilities"][ns]["status"], "BLOCKED", ns)
            self.assertIn("Operation not permitted", report["capabilities"][ns]["detail"])
        self.assertEqual(report["verdict"], "BLOCKED")
        self.assertIn("user_namespace", report["blocked"])

    def test_userns_sysctl_zero_blocks_before_exec_probe(self):
        files = dict(ALL_SYSCTL_FILES)
        files["/proc/sys/user/max_user_namespaces"] = "0\n"
        probe = passing_probe(files=files)
        with tempfile.TemporaryDirectory() as tmp, patch("os.access", return_value=True):
            report = preflight.run_preflight(probe=probe, runs_dir=tmp)
        cap = report["capabilities"]["user_namespace"]
        self.assertEqual(cap["status"], "BLOCKED")
        self.assertEqual(cap["detail"], "max_user_namespaces=0")
        self.assertIn("sysctl", cap["remediation"])
        # No unshare exec probe should have run for userns once the sysctl fails.
        self.assertFalse(any(a[:3] == [preflight._UNSHARE, "--user", "--map-root-user"] and "--mount" not in a
                             and "--pid" not in a and "--ipc" not in a and "--uts" not in a and "--net" not in a
                             for a in probe.ran))

    def test_unprivileged_userns_clone_disabled_blocks(self):
        files = dict(ALL_SYSCTL_FILES)
        files["/proc/sys/kernel/unprivileged_userns_clone"] = "0\n"
        probe = passing_probe(files=files)
        with tempfile.TemporaryDirectory() as tmp, patch("os.access", return_value=True):
            report = preflight.run_preflight(probe=probe, runs_dir=tmp)
        self.assertEqual(report["capabilities"]["user_namespace"]["status"], "BLOCKED")

    def test_cgroups_v1_only_is_blocked_with_delegation_remediation(self):
        files = dict(ALL_SYSCTL_FILES)
        del files["/sys/fs/cgroup/cgroup.controllers"]
        probe = passing_probe(files=files)
        with tempfile.TemporaryDirectory() as tmp, patch("os.access", return_value=True):
            report = preflight.run_preflight(probe=probe, runs_dir=tmp)
        cap = report["capabilities"]["cgroups_v2"]
        self.assertEqual(cap["status"], "BLOCKED")
        self.assertIn("cgroup", cap["remediation"])

    def test_cgroups_present_but_not_delegated_is_blocked(self):
        probe = passing_probe()
        with tempfile.TemporaryDirectory() as tmp, patch("os.access", return_value=False):
            report = preflight.run_preflight(probe=probe, runs_dir=tmp)
        cap = report["capabilities"]["cgroups_v2"]
        self.assertEqual(cap["status"], "BLOCKED")
        self.assertIn("not_delegated", cap["detail"])

    def test_bwrap_missing_is_fail_and_exec_refusal_is_blocked(self):
        probe = passing_probe(bwrap=False)
        with tempfile.TemporaryDirectory() as tmp, patch("os.access", return_value=True):
            report = preflight.run_preflight(probe=probe, runs_dir=tmp)
        self.assertEqual(report["capabilities"]["bubblewrap"]["status"], "FAIL")
        self.assertIn("install bubblewrap", report["capabilities"]["bubblewrap"]["remediation"])

        probe2 = passing_probe(run_results={("/usr/bin/bwrap", "--ro-bind"): (1, "bwrap: No permissions")})
        with tempfile.TemporaryDirectory() as tmp, patch("os.access", return_value=True):
            report2 = preflight.run_preflight(probe=probe2, runs_dir=tmp)
        self.assertEqual(report2["capabilities"]["bubblewrap"]["status"], "BLOCKED")

    def test_pidfd_blocked_and_missing(self):
        probe = passing_probe(pidfd_ok=False)
        with tempfile.TemporaryDirectory() as tmp, patch("os.access", return_value=True):
            report = preflight.run_preflight(probe=probe, runs_dir=tmp)
        self.assertEqual(report["capabilities"]["pidfd"]["status"], "FAIL")

        probe2 = passing_probe(pidfd_call_ok=False)
        with tempfile.TemporaryDirectory() as tmp, patch("os.access", return_value=True):
            report2 = preflight.run_preflight(probe=probe2, runs_dir=tmp)
        self.assertEqual(report2["capabilities"]["pidfd"]["status"], "BLOCKED")

    def test_seccomp_filter_unavailable_is_blocked(self):
        files = dict(ALL_SYSCTL_FILES)
        files["/proc/sys/kernel/seccomp/actions_avail"] = "allow errno trap kill_process kill_thread log trace user_notif\n"
        probe = passing_probe(files=files)
        with tempfile.TemporaryDirectory() as tmp, patch("os.access", return_value=True):
            report = preflight.run_preflight(probe=probe, runs_dir=tmp)
        self.assertEqual(report["capabilities"]["seccomp"]["status"], "BLOCKED")

    def test_insufficient_free_space_blocks_artifact_retention(self):
        probe = passing_probe(free_bytes=1024)
        with tempfile.TemporaryDirectory() as tmp, patch("os.access", return_value=True):
            report = preflight.run_preflight(probe=probe, runs_dir=tmp)
        cap = report["capabilities"]["artifact_retention"]
        self.assertEqual(cap["status"], "BLOCKED")
        self.assertIn("insufficient_free_space", cap["detail"])


class ReportShapeTests(unittest.TestCase):
    def _report(self, tmp):
        with patch("os.access", return_value=True):
            return preflight.run_preflight(probe=passing_probe(), runs_dir=tmp)

    def test_capability_order_is_deterministic(self):
        names = [name for name, _ in preflight.CAPABILITY_CHECKS] + ["artifact_retention"]
        with tempfile.TemporaryDirectory() as tmp:
            report = self._report(tmp)
        self.assertEqual(list(report["capabilities"].keys()), names)

    def test_capability_hash_deterministic_and_content_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            r1 = self._report(tmp)
            r2 = self._report(tmp)
        self.assertEqual(r1["capability_hash"], r2["capability_hash"])
        # The hash must cover capabilities only: flipping one status changes it.
        with tempfile.TemporaryDirectory() as tmp:
            r3 = preflight.run_preflight(
                probe=passing_probe(run_results={("/usr/bin/bwrap", "--ro-bind"): (1, "denied")}),
                runs_dir=tmp,
            )
        self.assertNotEqual(r1["capability_hash"], r3["capability_hash"])
        # No timestamps anywhere in the report.
        blob = json.dumps(r1)
        for token in ("time", "date", "epoch", "timestamp"):
            self.assertNotIn(token, blob.lower())

    def test_report_schema_and_exit_codes(self):
        self.assertEqual(preflight.EXIT_QUALIFIED, 0)
        self.assertEqual(preflight.EXIT_BLOCKED, 3)
        with tempfile.TemporaryDirectory() as tmp:
            report = self._report(tmp)
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["verdict"], "QUALIFIED")

    def test_main_exit_codes_and_json_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            qualified = {"schema_version": 1, "capabilities": {}, "blocked": [],
                         "verdict": "QUALIFIED", "capability_hash": "x"}
            blocked = dict(qualified, verdict="BLOCKED", blocked=["user_namespace"])
            with patch.object(preflight, "run_preflight", return_value=qualified):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    code = preflight.main(["--runs-dir", tmp])
                self.assertEqual(code, 0)
                self.assertEqual(json.loads(buf.getvalue())["verdict"], "QUALIFIED")
            with patch.object(preflight, "run_preflight", return_value=blocked):
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    code = preflight.main(["--runs-dir", tmp])
                self.assertEqual(code, 3)
                parsed = json.loads(buf.getvalue())
                self.assertEqual(parsed["blocked"], ["user_namespace"])

    def test_real_cli_smoke_json_and_exit_code(self):
        """The real probe on any host must emit valid JSON and exit 0 or 3."""
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(PREFLIGHT_PATH), "--runs-dir", tmp],
                capture_output=True, text=True, timeout=180, check=False,
            )
        self.assertIn(result.returncode, (0, 3))
        report = json.loads(result.stdout)
        self.assertIn(report["verdict"], ("QUALIFIED", "BLOCKED"))
        self.assertEqual(
            report["blocked"],
            sorted(n for n, c in report["capabilities"].items() if c["status"] != "PASS"),
        )


def _load_sandbox_tests(require_isolation: bool, isolated: bool):
    """Import tests/test_factory_m4_sandbox.py fresh under a controlled probe."""
    from residual.factory import m4_sandbox

    env = dict(os.environ)
    if require_isolation:
        env["M4_REQUIRE_ISOLATION"] = "1"
    else:
        env.pop("M4_REQUIRE_ISOLATION", None)
    module_name = f"m4_sandbox_tests_req{int(require_isolation)}_iso{int(isolated)}"
    with patch.dict(os.environ, env, clear=True), \
            patch.object(m4_sandbox, "probe_isolation", return_value=(isolated, "fake-probe")):
        spec = importlib.util.spec_from_file_location(module_name, SANDBOX_TEST_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


def _run_class(test_class) -> unittest.TestResult:
    suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
    runner = unittest.TextTestRunner(stream=io.StringIO())
    return runner.run(suite)


class FailLoudlyGatingTests(unittest.TestCase):
    def test_require_mode_blocked_runner_fails_loudly(self):
        """M4_REQUIRE_ISOLATION=1 + BLOCKED runner => failures, not skips.

        Teeth: a mutant that converts this into a silent skip makes this
        assertion fail.
        """
        module = _load_sandbox_tests(require_isolation=True, isolated=False)
        result = _run_class(module.IsolatedRunnerTests)
        self.assertEqual(result.skipped, [], "BLOCKED capability must never read as skip in require mode")
        loud = result.failures + result.errors
        self.assertTrue(loud, "expected a loud failure when isolation is BLOCKED in require mode")
        messages = "\n".join(str(part) for _, text in loud for part in (text,))
        self.assertIn("M4_REQUIRE_ISOLATION", messages)
        self.assertIn("verdict", messages)  # the preflight JSON report is attached

    def test_default_mode_blocked_runner_still_skips(self):
        """Default dev behavior is unchanged: skip with reason, never fail."""
        module = _load_sandbox_tests(require_isolation=False, isolated=False)
        self.assertTrue(getattr(module.IsolatedRunnerTests, "__unittest_skip__", False))
        result = _run_class(module.IsolatedRunnerTests)
        self.assertFalse(result.failures)
        self.assertFalse(result.errors)
        self.assertTrue(result.skipped)

    def test_require_mode_capable_runner_is_not_gated(self):
        module = _load_sandbox_tests(require_isolation=True, isolated=True)
        self.assertFalse(getattr(module.IsolatedRunnerTests, "__unittest_skip__", False))

    def test_preflight_report_helper_returns_json(self):
        module = _load_sandbox_tests(require_isolation=True, isolated=False)
        text = module.isolation_preflight_report()
        self.assertIn("preflight exit=", text)
        json_start = text.index("{")
        report = json.loads(text[json_start:])
        self.assertIn(report["verdict"], ("QUALIFIED", "BLOCKED"))


if __name__ == "__main__":
    unittest.main()
