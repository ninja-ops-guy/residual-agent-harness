from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import pathlib
import tempfile
import unittest
import urllib.error
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "f6_stale_probe", ROOT / "tools" / "aud1" / "f6_stale_result_probe.py"
)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class StaleResultProbeTests(unittest.TestCase):
    def test_probe_redacts_echoed_lease_and_token_from_response_excerpt(self):
        lease = "abcdefghijklmnopqrstuvwxyzABCDEF"
        token = "worker-secret-token-value"

        class Opener:
            def open(self, request, timeout=15):
                echoed = json.dumps({
                    "error": "Task authority belongs to another runner",
                    "lease": lease,
                    "authorization": token,
                }).encode("utf-8")
                raise urllib.error.HTTPError(
                    request.full_url, 403, "Forbidden", {}, io.BytesIO(echoed)
                )

        with tempfile.TemporaryDirectory() as temp, \
             mock.patch.dict(os.environ, {"RESIDUAL_WORKER_TOKEN": token}, clear=False), \
             mock.patch.object(probe.urllib.request, "build_opener", return_value=Opener()):
            output = pathlib.Path(temp) / "stale.json"
            with contextlib.redirect_stdout(io.StringIO()):
                result = probe.main([
                    "--station-url", "http://127.0.0.1:8766",
                    "--project", "p-test",
                    "--task", "OPS-101",
                    "--lease", lease,
                    "--attempt", "3",
                    "--owner", "remote:old",
                    "--output", str(output),
                ])

            self.assertEqual(result, 0)
            record = json.loads(output.read_text(encoding="utf-8"))
            rendered = json.dumps(record)
            self.assertNotIn(lease, rendered)
            self.assertNotIn(token, rendered)
            self.assertEqual(
                record["response_excerpt"],
                "Task authority belongs to another runner",
            )

    def test_probe_discards_json_escaped_secret_echoes(self):
        lease = "abcdefghijklmnopqrstuvwxyzABCDEF"
        token = "worker-secret-token-value"
        escaped_lease = "".join("\\u%04x" % ord(ch) for ch in lease)
        escaped_token = "".join("\\u%04x" % ord(ch) for ch in token)

        class Opener:
            def open(self, request, timeout=15):
                echoed = (
                    '{"error":"Task authority belongs to another runner",'
                    '"lease":"' + escaped_lease + '",'
                    '"authorization":"' + escaped_token + '"}'
                ).encode("utf-8")
                raise urllib.error.HTTPError(
                    request.full_url, 403, "Forbidden", {}, io.BytesIO(echoed)
                )

        with tempfile.TemporaryDirectory() as temp, \
             mock.patch.dict(os.environ, {"RESIDUAL_WORKER_TOKEN": token}, clear=False), \
             mock.patch.object(probe.urllib.request, "build_opener", return_value=Opener()):
            output = pathlib.Path(temp) / "stale.json"
            with contextlib.redirect_stdout(io.StringIO()):
                result = probe.main([
                    "--station-url", "http://127.0.0.1:8766",
                    "--project", "p-test",
                    "--task", "OPS-101",
                    "--lease", lease,
                    "--attempt", "3",
                    "--owner", "remote:old",
                    "--output", str(output),
                ])
            self.assertEqual(result, 0)
            record = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                record["response_excerpt"],
                "Task authority belongs to another runner",
            )
            rendered = json.dumps(record)
            self.assertNotIn(lease, rendered)
            self.assertNotIn(token, rendered)
            self.assertNotIn(escaped_lease, rendered)
            self.assertNotIn(escaped_token, rendered)

    def test_probe_sends_raw_lease_but_retains_only_fingerprint_and_authority_binding(self):
        lease = "abcdefghijklmnopqrstuvwxyzABCDEF"
        captured = {}

        class Opener:
            def open(self, request, timeout=15):
                captured["body"] = json.loads(request.data.decode("utf-8"))
                raise urllib.error.HTTPError(
                    request.full_url,
                    403,
                    "Forbidden",
                    {},
                    io.BytesIO(b'{"error":"Task authority belongs to another runner"}'),
                )

        with tempfile.TemporaryDirectory() as temp, \
             mock.patch.dict(os.environ, {"RESIDUAL_WORKER_TOKEN": "worker-secret"}, clear=False), \
             mock.patch.object(probe.urllib.request, "build_opener", return_value=Opener()):
            output = pathlib.Path(temp) / "stale.json"
            with contextlib.redirect_stdout(io.StringIO()):
                result = probe.main([
                    "--station-url", "http://127.0.0.1:8766",
                    "--project", "p-test",
                    "--task", "OPS-101",
                    "--lease", lease,
                    "--attempt", "3",
                    "--owner", "remote:old",
                    "--output", str(output),
                ])

            self.assertEqual(result, 0)
            self.assertEqual(captured["body"]["lease"], lease)
            self.assertNotIn("lease_fingerprint", captured["body"])
            self.assertNotIn("owner", captured["body"])
            self.assertNotIn("attempt", captured["body"])

            record = json.loads(output.read_text(encoding="utf-8"))
            rendered = json.dumps(record)
            self.assertNotIn(lease, rendered)
            self.assertNotIn("worker-secret", rendered)
            self.assertEqual(record["schema"], "residual.aud1.f6.stale-probe.v2")
            self.assertTrue(record["lease_fingerprint"].startswith("sha256:"))
            self.assertEqual(record["attempt"], 3)
            self.assertEqual(record["owner"], "remote:old")
            self.assertEqual(record["observed_status"], 403)
            self.assertIs(record["rejected"], True)
            self.assertIs(record["accepted"], False)
            self.assertIs(record["credential_value_retained"], False)


if __name__ == "__main__":
    unittest.main()
