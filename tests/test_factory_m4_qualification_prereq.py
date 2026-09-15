"""Regression tests for the M4 qualification prerequisite probe runner.

These tests pin the fail-closed contract: the report is explicit PASS/BLOCKED
with per-capability status, nothing is silently skipped, and any missing
capability (or wrong Python pin / missing dependency) forces BLOCKED.
"""
from __future__ import annotations

import json
import subprocess
import unittest
from unittest import mock

from residual.factory import m4_qualification_prereq as prereq
from residual.factory.m4_sandbox import SANDBOX_PROFILE


def _ok_proc():
    return subprocess.CompletedProcess(args=[], returncode=0, stderr=b"")


def _fail_proc(rc=1):
    return subprocess.CompletedProcess(args=[], returncode=rc, stderr=b"unshare: failed")


_REAL_RUN = subprocess.run


def _raise_timeout(argv, **kw):
    raise subprocess.TimeoutExpired(cmd="unshare", timeout=1)


def _raise_oserror(argv, **kw):
    raise OSError("nope")


def _passthrough(fake):
    """Only intercept unshare probes; delegate everything else to real subprocess.run."""
    def wrapper(argv, **kw):
        if isinstance(argv, (list, tuple)) and argv and "unshare" in str(argv[0]):
            return fake(argv, **kw)
        return _REAL_RUN(argv, **kw)
    return wrapper


def _passing_manifest():
    """Environment-independent manifest for tests that exercise a PASS report.

    The real collect_manifest() remains covered separately, and the explicit
    Python-pin mismatch test proves that a non-3.12 qualification environment
    still fails closed. This helper prevents the repository's ordinary 3.11/
    3.13 unit-test matrices from being mistaken for qualification runs.
    """
    return {
        "schema": "m4-qualification-env-manifest-v1",
        "python": {
            "status": "pass",
            "version": "3.12.0",
            "pinned": ["3.12"],
            "executable": "/usr/bin/python3",
        },
        "dependencies": {
            m: {"status": "pass", "version": "test", "minimum_major": minimum}
            for m, minimum in prereq.REQUIRED_DEPENDENCIES.items()
        },
        "platform": {},
        "kernel": {},
        "resource_limits": {},
    }


class CapabilityProbeTests(unittest.TestCase):
    def test_all_probes_pass_when_kernel_supports_namespaces(self):
        with mock.patch.object(prereq.subprocess, "run", side_effect=_passthrough(lambda a, **k: _ok_proc())), \
             mock.patch.object(prereq, "probe_isolation", return_value=(True, "ok")):
            results = prereq.probe_capabilities()
        names = {r.name: r.status for r in results}
        for name in ("platform_linux", "chroot_available", "unshare_binary",
                     "user_namespace", "mount_namespace", "pid_namespace",
                     "network_namespace", "ipc_namespace", "uts_namespace",
                     "kill_child", "composite_sandbox_profile"):
            self.assertEqual(names[name], "pass", name)
        for r in results:
            if r.name.endswith("_namespace") or r.name == "kill_child":
                self.assertIn("--user", r.probe_argv)
                self.assertIn("--map-root-user", r.probe_argv)

    def test_any_failed_namespace_probe_is_blocked_not_skipped(self):
        def fake_run(argv, **kw):
            return _fail_proc() if "--net" in argv else _ok_proc()
        with mock.patch.object(prereq.subprocess, "run", side_effect=_passthrough(fake_run)), \
             mock.patch.object(prereq, "probe_isolation", return_value=(False, "namespace_probe_failed")):
            report = prereq.build_report(revision="deadbeef")
        self.assertEqual(report["overall"], "BLOCKED")
        self.assertIn("network_namespace", report["blocked_capabilities"])
        net = next(c for c in report["capabilities"] if c["name"] == "network_namespace")
        self.assertEqual(net["status"], "blocked")
        self.assertIn("probe_failed", net["detail"])

    def test_probe_timeout_and_launch_failure_are_blocked(self):
        with mock.patch.object(prereq.subprocess, "run", side_effect=_passthrough(_raise_timeout)), \
             mock.patch.object(prereq, "probe_isolation", return_value=(False, "namespace_probe_failed")):
            results = prereq.probe_capabilities()
        userns = next(r for r in results if r.name == "user_namespace")
        self.assertEqual(userns.status, "blocked")
        self.assertEqual(userns.detail, "probe_timeout")
        with mock.patch.object(prereq.subprocess, "run", side_effect=_passthrough(_raise_oserror)), \
             mock.patch.object(prereq, "probe_isolation", return_value=(False, "namespace_probe_failed")):
            results = prereq.probe_capabilities()
        userns = next(r for r in results if r.name == "user_namespace")
        self.assertEqual(userns.status, "blocked")
        self.assertTrue(userns.detail.startswith("probe_launch_failed:"))

    def test_missing_unshare_blocks_every_namespace_capability(self):
        with mock.patch.object(prereq.shutil, "which", return_value=None), \
             mock.patch.object(prereq, "probe_isolation", return_value=(False, "unshare_binary_missing")):
            report = prereq.build_report()
        self.assertEqual(report["overall"], "BLOCKED")
        for c in report["capabilities"]:
            if c["name"] not in ("platform_linux", "chroot_available"):
                self.assertEqual(c["status"], "blocked", c["name"])

    def test_probe_argv_mirrors_sandbox_flags(self):
        captured = []

        def fake_run(argv, **kw):
            captured.append(argv)
            return _ok_proc()
        with mock.patch.object(prereq.subprocess, "run", side_effect=_passthrough(fake_run)), \
             mock.patch.object(prereq, "probe_isolation", return_value=(True, "ok")):
            prereq.probe_capabilities()
        composite = next(c for c in prereq.probe_capabilities()
                         if c.name == "composite_sandbox_profile")
        for argv in captured:
            self.assertEqual(argv[1:3], ["--user", "--map-root-user"])
        self.assertIn(SANDBOX_PROFILE, composite.detail)


class ManifestAndReportTests(unittest.TestCase):
    def test_manifest_schema_and_required_fields(self):
        manifest = prereq.collect_manifest()
        self.assertEqual(manifest["schema"], "m4-qualification-env-manifest-v1")
        self.assertIn(manifest["platform"]["system"], ("Linux", "Darwin"))
        self.assertIn("max_user_namespaces", manifest["kernel"])
        self.assertEqual(manifest["python"]["pinned"], list(prereq.PINNED_PYTHON))
        self.assertIn("RLIMIT_AS", manifest["resource_limits"])
        for dep in prereq.REQUIRED_DEPENDENCIES:
            self.assertIn(dep, manifest["dependencies"])

    def test_python_pin_mismatch_blocks(self):
        manifest = {"schema": "m4-qualification-env-manifest-v1",
                    "python": {"status": "blocked", "version": "3.11.0",
                               "pinned": ["3.12"], "executable": "/usr/bin/python3"},
                    "dependencies": {m: {"status": "pass"} for m in prereq.REQUIRED_DEPENDENCIES},
                    "platform": {}, "kernel": {}, "resource_limits": {}}
        with mock.patch.object(prereq.subprocess, "run", side_effect=_passthrough(lambda a, **k: _ok_proc())), \
             mock.patch.object(prereq, "probe_isolation", return_value=(True, "ok")), \
             mock.patch.object(prereq, "collect_manifest", return_value=manifest):
            report = prereq.build_report()
        self.assertEqual(report["overall"], "BLOCKED")
        self.assertIn("python_pin", report["blocked_capabilities"])

    def test_missing_dependency_blocks(self):
        with mock.patch.object(prereq, "_dependency_versions",
                               return_value={"cryptography": {"status": "blocked", "version": None,
                                                              "minimum_major": "43"},
                                             "yaml": {"status": "pass", "version": "6.0",
                                                      "minimum_major": "6"}}):
            deps = prereq._dependency_versions()
        self.assertEqual(deps["cryptography"]["status"], "blocked")
        manifest = prereq.collect_manifest()
        manifest["dependencies"]["cryptography"] = {"status": "blocked", "version": None,
                                                    "minimum_major": "43"}
        with mock.patch.object(prereq.subprocess, "run", side_effect=_passthrough(lambda a, **k: _ok_proc())), \
             mock.patch.object(prereq, "probe_isolation", return_value=(True, "ok")), \
             mock.patch.object(prereq, "collect_manifest", return_value=manifest):
            report = prereq.build_report()
        self.assertEqual(report["overall"], "BLOCKED")
        self.assertIn("dependency:cryptography", report["blocked_capabilities"])

    def test_report_is_json_serializable_and_revision_bound(self):
        with mock.patch.object(prereq.subprocess, "run", side_effect=_passthrough(lambda a, **k: _ok_proc())), \
             mock.patch.object(prereq, "probe_isolation", return_value=(True, "ok")), \
             mock.patch.object(prereq, "collect_manifest", return_value=_passing_manifest()):
            report = prereq.build_report(revision="a" * 40)
        self.assertEqual(report["overall"], "PASS")
        self.assertEqual(report["revision"], "a" * 40)
        self.assertEqual(report["schema"], prereq.REPORT_SCHEMA)
        json.dumps(report)

    def test_main_exit_codes_and_output_file(self):
        import tempfile
        from pathlib import Path
        out = Path(tempfile.mkdtemp()) / "report.json"
        with mock.patch.object(prereq.subprocess, "run", side_effect=_passthrough(lambda a, **k: _ok_proc())), \
             mock.patch.object(prereq, "probe_isolation", return_value=(True, "ok")), \
             mock.patch.object(prereq, "collect_manifest", return_value=_passing_manifest()):
            self.assertEqual(prereq.main(["--output", str(out), "--revision", "b" * 40]), 0)
        written = json.loads(out.read_text())
        self.assertEqual(written["overall"], "PASS")
        with mock.patch.object(prereq.subprocess, "run", side_effect=_passthrough(lambda a, **k: _fail_proc())), \
             mock.patch.object(prereq, "probe_isolation", return_value=(False, "namespace_probe_failed")):
            self.assertEqual(prereq.main([]), 1)


if __name__ == "__main__":
    unittest.main()
