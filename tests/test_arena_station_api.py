import json
import tempfile
import threading
import time
import unittest
import urllib.request
from unittest.mock import patch

from residual.station.models import save_settings
from residual.station.server import Server
from residual.station.service import Station


class ArenaStationApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.station = Station(self.temp.name)
        save_settings(self.station.store, {
            "cloud": {
                "kind": "arena",
                "model": "",
                "base_url": "https://api.preview.arena.ai/v1",
                "output_token_field": "max_completion_tokens",
            },
            "provider_credentials": {
                "arena": {"api_key": "ARENA-STATION-SECRET"},
            },
        })
        self.server = Server(("127.0.0.1", 0), self.station)
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            kwargs={"poll_interval": 0.02},
            daemon=True,
        )
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.token = self.station.store.settings()["session_token"]
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temp.cleanup()

    def request(self, path, data=None):
        body = None if data is None else json.dumps(data).encode()
        headers = {"X-Station-Token": self.token}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base + path, data=body, headers=headers)
        with self.opener.open(request, timeout=5) as response:
            return json.loads(response.read())

    def wait_job(self, job_id):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            jobs = self.request("/api/jobs")["jobs"]
            job = next(item for item in jobs if item["id"] == job_id)
            if job["state"] in {"completed", "failed", "interrupted"}:
                return job
            time.sleep(0.02)
        self.fail("Station Arena API job did not finish")

    def test_model_discovery_is_served_with_saved_arena_credentials(self):
        captured = {}

        class FakeArenaAdapter:
            def list_models(self):
                return ["model-a", "model-z"]

        def fake_make_adapter(profile, credentials):
            captured["profile"] = dict(profile)
            captured["credentials"] = dict(credentials)
            return FakeArenaAdapter()

        with patch("residual.station.server.make_adapter", side_effect=fake_make_adapter):
            launch = self.request("/api/providers/models", {"placement": "cloud"})
            job = self.wait_job(launch["job_id"])

        self.assertEqual(job["state"], "completed")
        self.assertEqual(job["result"]["models"], ["model-a", "model-z"])
        self.assertEqual(job["result"]["placement"], "cloud")
        self.assertEqual(captured["profile"]["kind"], "arena")
        self.assertEqual(captured["profile"]["model"], "")
        self.assertEqual(captured["credentials"]["api_key"], "ARENA-STATION-SECRET")
        self.assertNotIn("ARENA-STATION-SECRET", json.dumps(job))

    def test_connection_test_is_served_after_exact_model_selection(self):
        settings = self.station.store.settings()
        cloud = settings["cloud"]
        save_settings(self.station.store, {
            "cloud": {
                "kind": cloud["kind"],
                "model": "model-a",
                "base_url": cloud["base_url"],
                "output_token_field": cloud["output_token_field"],
                "region": cloud.get("region", "us-east-1"),
                "api_version": cloud.get("api_version", "2024-10-21"),
            },
        })
        captured = {}

        def fake_model_call(store, pid, role, packet, system, schema=None, placement="local", tid=None, extensions=None):
            captured.update({
                "pid": pid,
                "role": role,
                "packet": packet,
                "placement": placement,
            })
            return {
                "text": "Station online.",
                "usage": {
                    "input_tokens": 2,
                    "output_tokens": 1,
                    "cached_input_tokens": None,
                    "source": "reported",
                    "cache_write_input_tokens": None,
                },
                "elapsed_ms": 1,
            }

        with patch("residual.station.server.model_call", side_effect=fake_model_call):
            launch = self.request("/api/models/test", {"placement": "cloud"})
            job = self.wait_job(launch["job_id"])

        self.assertEqual(job["state"], "completed")
        self.assertEqual(job["result"]["text"], "Station online.")
        self.assertEqual(captured["placement"], "cloud")
        self.assertEqual(captured["role"], "connection_test")
        self.assertEqual(captured["packet"], {"message": "Reply with: Station online."})


if __name__ == "__main__":
    unittest.main()
