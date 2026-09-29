from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import residual.marketplace.install as install
from residual.sandbox import NetworkPolicy


class _Backend:
    def __init__(self, *, enforcement="kernel", ok=True):
        self.result = SimpleNamespace(
            enforcement=enforcement,
            ok=ok,
            stdout=install._VALIDATION_PREFIX + json.dumps({
                "name": "demo.module", "version": "1.0.0",
                "policies": 0, "verifiers": 0, "brakes": 0,
            }) + "\n",
        )
        self.spec = None
        self.argv = None
        self.stdin = None
        self.stopped = False

    def start(self, spec):
        self.spec = spec

    def exec(self, argv, *, stdin=""):
        self.argv = argv
        self.stdin = stdin
        return self.result

    def stop(self):
        self.stopped = True


class MarketplaceInstallSecurityTests(unittest.TestCase):
    def test_validation_requires_kernel_sandbox_with_network_denied(self):
        backend = _Backend()
        with tempfile.TemporaryDirectory() as td, mock.patch.object(
            install, "select_backend", return_value=backend
        ) as select:
            stage = Path(td).resolve()
            report = install.ModuleInstaller._validate_stage(stage)
        select.assert_called_once_with(require_kernel=True)
        self.assertEqual(backend.spec.network, NetworkPolicy.DENY)
        self.assertIn(str(stage), backend.spec.fs.read)
        self.assertEqual(backend.argv[1:3], ["-I", "-S"])
        self.assertTrue(backend.stopped)
        self.assertEqual(report["name"], "demo.module")

    def test_validation_refuses_non_kernel_result(self):
        backend = _Backend(enforcement="best_effort")
        with tempfile.TemporaryDirectory() as td, mock.patch.object(
            install, "select_backend", return_value=backend
        ):
            with self.assertRaises(RuntimeError, msg="kernel"):
                install.ModuleInstaller._validate_stage(Path(td).resolve())

    def test_sdist_is_rejected_before_signature_or_build_execution(self):
        with tempfile.TemporaryDirectory() as td:
            package = Path(td) / "module.tar.gz"
            package.write_bytes(b"not-a-package")
            installer = install.ModuleInstaller(Path(td) / "modules")
            with mock.patch.object(install, "verify_signature") as verify:
                with self.assertRaisesRegex(RuntimeError, "prebuilt .whl"):
                    installer.install(
                        package, public_key_b64="ignored", signature_b64="ignored"
                    )
            verify.assert_not_called()


if __name__ == "__main__":
    unittest.main()
