"""AUD-1 F3 regression: programmatic Server construction must share CLI exposure policy.

Disposable temporary directories and loopback-only positive controls. Non-loopback
cases intercept before any OS bind and do not touch live hosts, R4/R4.1, canary, or F6.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from http.server import ThreadingHTTPServer
from unittest import mock

from residual.core import ContractError
from residual.station.server import Server
from residual.station.service import Station


class AUD1ProgrammaticExposureTests(unittest.TestCase):
    def test_direct_constructor_rejects_default_nonloopback_before_bind(self):
        attempts = []

        def intercepted(instance):
            attempts.append(instance.server_address)
            raise AssertionError("non-loopback bind boundary must not be reached")

        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
                ThreadingHTTPServer, "server_bind", intercepted
            ):
                with self.assertRaises(ContractError):
                    Server(("0.0.0.0", 0), Station(temp))
        self.assertEqual(attempts, [])

    def test_direct_constructor_rejects_incomplete_remote_opt_in_before_bind(self):
        attempts = []

        def intercepted(instance):
            attempts.append(instance.server_address)
            raise AssertionError("incomplete exposure contract reached bind boundary")

        env = {"RESIDUAL_REMOTE_EXPOSURE": "1"}
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
                ThreadingHTTPServer, "server_bind", intercepted
            ):
                with self.assertRaises(ContractError):
                    Server(("0.0.0.0", 0), Station(temp))
        self.assertEqual(attempts, [])

    def test_loopback_constructor_remains_available_without_remote_opt_in(self):
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.dict(os.environ, {}, clear=True):
                server = Server(("127.0.0.1", 0), Station(temp))
                try:
                    self.assertFalse(server.secure_cookie)
                finally:
                    server.server_close()


if __name__ == "__main__":
    unittest.main()
