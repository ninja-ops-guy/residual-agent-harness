"""Real Station/HTTP/SQLite/client composition proof, not installed-native proof.

No model is called. Demo review is scripted and MUST NOT be described as an
independent verifier or as a Hermes/OpenClaw gateway execution.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from residual.station.mission_client import MissionClient
from residual.station.mission_routes import with_mission_sync
from residual.station.mission_sync import SCHEMA
from residual.station.server import Handler
from residual.station.service import DEMO_FILES, Station, demo_spec


def decode_context(value):
    return json.loads(value.split("\n", 1)[1])


class ComposedMissionAuthority(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.station = Station(self.root / "station")
        self.pid = self.station.create(demo_spec(), demo=True)["project_id"]
        self.station.triage(self.pid)
        self.work = self.station.prepare(self.pid, "composed-worker", "OPS-101")
        self.assertIsNotNone(self.work)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), with_mission_sync(Handler))
        self.server.daemon_threads = True
        self.server.station = self.station
        self.server.allowed_hosts = {f"127.0.0.1:{self.server.server_port}"}
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.opener = build_opener(ProxyHandler({}))
        # Guard against a future demo regression silently invoking a paid provider.
        guard = patch("residual.station.service.model_call", side_effect=AssertionError("provider call forbidden"))
        guard.start()
        self.addCleanup(guard.stop)

    def stop_server(self):
        self.server.shutdown()
        self.thread.join(timeout=10)
        self.server.server_close()
        self.assertFalse(self.thread.is_alive())

    def http(self, path, body=None, headers=None):
        data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
        request = Request(self.url + path, data=data,
                          headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with self.opener.open(request, timeout=5) as response:
                raw = response.read()
                return response.status, json.loads(raw)
        except HTTPError as exc:
            with exc:
                return exc.code, json.loads(exc.read())

    def bind(self, name, *, share=False):
        definition = {"mission_id": self.pid, "task_id": "OPS-101", "harness": name,
                      "instance_id": "software-fixture", "conversation_id": name + "-session",
                      "agent_id": name + "-agent", "share_messages": share}
        status, result = self.http("/api/missions/bind", definition,
                                  {"X-Station-Token": self.station.store.settings()["session_token"]})
        self.assertEqual(status, 200, result)
        private = self.root / name
        private.mkdir(mode=0o700)
        config = {"url": self.url, "binding_id": result["binding"]["binding_id"],
                  "token": result["token"], "conversation_id": definition["conversation_id"],
                  "spool": str(private / "spool.sqlite3")}
        config_path = private / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        config_path.chmod(0o600)
        return config, config_path

    def node(self, config_path, *, report=False):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node >=22.16 is required; this gate must not silently skip")
        adapter = Path(os.environ.get("MISSION_NODE_ADAPTER", "")) if os.environ.get("MISSION_NODE_ADAPTER") else (
            Path(__file__).resolve().parents[1] / "integrations/mission-sync/openclaw/client.mjs")
        self.assertTrue(adapter.is_file(), "exact-candidate Node adapter required")
        program = """
import {readFileSync} from 'node:fs';
const {MissionClient} = await import(process.argv[1]);
const c = new MissionClient(JSON.parse(readFileSync(process.argv[2], 'utf8')));
try {
  await c.context(false);
  if (process.argv[3] === 'report') await c.record('completion_claim', 'NODE_FALSE_ACCEPTED', 'native-repeat-id');
  for (let i=0;i<3;i++) await c.pump();
  console.log(await c.context());
} finally {await c.tail; c.close();}
"""
        run = subprocess.run([node, "--input-type=module", "-e", program, adapter.resolve().as_uri(),
                              str(config_path), "report" if report else "context"],
                             capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stderr)
        return decode_context(run.stdout)

    def assert_state(self, context, state):
        packet = context["station_context"]["packet"]
        self.assertEqual(packet["task"]["state"], state)
        self.assertEqual(packet["task"]["id"], "OPS-101")
        self.assertEqual(packet["acceptance_authority"], "station_only")

    def test_both_clients_follow_real_station_but_cannot_accept(self):
        py_config, _ = self.bind("hermes", share=True)
        _, node_path = self.bind("openclaw", share=True)
        client = MissionClient(py_config)
        before = self.station.store.task(self.pid, "OPS-101")
        client.record("completion_claim", "PYTHON_FALSE_ACCEPTED", native_event_id="python-once")
        client.pump()
        context = self.node(node_path, report=True)
        self.assert_state(context, "running")
        self.assertIn("PYTHON_FALSE_ACCEPTED", json.dumps(context["untrusted_conversation_observations"]))
        self.assertEqual(before, self.station.store.task(self.pid, "OPS-101"))
        # Reopen the Node spool in another process and replay the same native ID.
        self.node(node_path, report=True)
        for _ in range(3):
            client.pump()
        self.assertIn("NODE_FALSE_ACCEPTED", json.dumps(decode_context(client.context())["untrusted_conversation_observations"]))
        self.assertEqual(before, self.station.store.task(self.pid, "OPS-101"))
        result = self.station.finish(self.work, {"files": DEMO_FILES["OPS-101"]})
        self.assertEqual(result["state"], "review_ready")
        self.assert_state(decode_context(client.context()), "review_ready")
        self.assert_state(self.node(node_path), "review_ready")
        self.station.review(self.pid, "OPS-101")  # explicitly scripted demo reviewer
        self.station.integrate(self.pid, "OPS-101")
        self.assert_state(decode_context(client.context()), "integrated")
        self.assert_state(self.node(node_path), "integrated")
        self.assertIsInstance(self.station.store.task(self.pid, "OPS-101")["verification_receipt"], dict)

    def test_message_sharing_requires_both_bindings_to_consent(self):
        config, _ = self.bind("hermes", share=True)
        _, node_path = self.bind("openclaw", share=False)
        client = MissionClient(config)
        client.record("message", "PRIVATE_NONFORWARD_SENTINEL", native_event_id="private-message")
        client.pump()
        context = self.node(node_path)
        self.assert_state(context, "running")
        self.assertNotIn("PRIVATE_NONFORWARD_SENTINEL", json.dumps(context))

    def test_scoped_capability_cannot_cross_operator_or_worker_boundary(self):
        config, _ = self.bind("hermes")
        before = self.station.store.task(self.pid, "OPS-101")
        headers = {"Authorization": "Bearer " + config["token"], "X-Mission-Binding": config["binding_id"]}
        for path, body in (("/api/missions", None), ("/api/worker/projects", None),
                           ("/api/missions/bind", {}), ("/api/worker/result", {})):
            with self.subTest(path=path):
                self.assertEqual(self.http(path, body, headers)[0], 403)
        status, result = self.http("/api/mission-sync/report", {
            "schema": SCHEMA, "event_id": "extra-authority", "source_seq": 1,
            "kind": "completion_claim", "text": "ACCEPTED", "accepted": True}, headers)
        self.assertEqual(status, 400, result)
        self.assertEqual(self.http("/api/mission-sync/context", {}, {**headers, "Origin": "https://example.invalid"})[0], 403)
        self.assertEqual(before, self.station.store.task(self.pid, "OPS-101"))

    def test_existing_routes_and_mission_assets_are_served(self):
        status, bootstrap = self.http("/api/bootstrap")
        self.assertEqual(status, 200)
        self.assertIn("token", bootstrap)
        for path in ("/", "/missions", "/missions.js", "/missions.css"):
            with self.subTest(path=path):
                with self.opener.open(self.url + path, timeout=5) as response:
                    self.assertEqual(response.status, 200)
                    self.assertGreater(len(response.read()), 100)
                    self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_retry_invalidates_previous_attempt_binding(self):
        config, _ = self.bind("hermes")
        result = self.station.finish(self.work, {"files": {"station/health.py": "def status(services):\n    return 'wrong'\n"}})
        self.assertEqual(result["state"], "repair_required")
        retry = self.station.prepare(self.pid, "replacement-worker", "OPS-101")
        self.assertGreater(retry["task"]["attempt"], self.work["task"]["attempt"])
        before = self.station.store.task(self.pid, "OPS-101")
        headers = {"Authorization": "Bearer " + config["token"], "X-Mission-Binding": config["binding_id"]}
        status, _ = self.http("/api/mission-sync/report", {
            "schema": SCHEMA, "event_id": "late", "source_seq": 1,
            "kind": "completion_claim", "text": "STALE_ACCEPTED"}, headers)
        self.assertIn(status, (400, 403))
        self.assertEqual(before, self.station.store.task(self.pid, "OPS-101"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
