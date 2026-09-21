from __future__ import annotations

import http.cookiejar
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from residual.core import ContractError, canonical
from residual.providers import Reply, Usage
from residual.station.server import Server, validate_exposure
from residual.station.service import Station, demo_spec
from residual.station.worker import WorkerAuthorityLost, WorkerClient


class AUD1HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.station = Station(self.temp.name)
        self.http = Server(("127.0.0.1", 0), self.station, launch_token="launch-capability")
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.http.server_port}"
        self.operator = self.station.store.settings()["session_token"]

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, body=None, *, worker=None, operator=True, opener=None, headers=None):
        supplied = {"Content-Type": "application/json", **(headers or {})}
        if worker is not None:
            supplied["Authorization"] = "Bearer " + worker
        elif operator:
            supplied["X-Station-Token"] = self.operator
        req = urllib.request.Request(
            self.url + path,
            data=canonical(body).encode() if body is not None else None,
            headers=supplied,
        )
        with (opener or urllib.request).open(req) as response:
            raw = response.read()
            return json.loads(raw) if raw else None

    def make_project(self):
        pid = self.station.create(demo_spec(), demo=True)["project_id"]
        self.station.triage(pid)
        return pid

    def issue_worker(self, rotate=False):
        return self.request("/api/workers/access", {"enabled": True, "rotate": rotate})["token"]

    def claim(self, token, pid, runner="runner-a", task="OPS-101"):
        return self.request(
            "/api/worker/claim",
            {"project_id": pid, "task_id": task, "name": runner},
            worker=token,
            operator=False,
        )["work"]

    # AUD-1 regression 1: unauthenticated bootstrap cannot obtain operator authority.
    def test_01_bootstrap_is_metadata_only_and_launch_capability_is_one_time(self):
        body = self.request("/api/bootstrap", operator=False)
        self.assertNotIn("token", body)
        self.assertNotIn(self.operator, canonical(body))
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/projects", operator=False)
        self.assertEqual(error.exception.code, 403)

        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        self.request("/auth/launch-capability", operator=False, opener=opener)
        projects = self.request("/api/projects", operator=False, opener=opener)
        self.assertEqual(projects["projects"], [])
        self.assertTrue(any(cookie.name == "residual_session" and cookie.has_nonstandard_attr("HttpOnly") for cookie in jar))

        fresh = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/auth/launch-capability", operator=False, opener=fresh)
        self.assertEqual(error.exception.code, 403)

    # AUD-1 regressions 2 and 6: worker B cannot use worker A's lease or operator surface.
    def test_02_runner_identity_owns_heartbeat_result_and_not_operator_transitions(self):
        pid = self.make_project()
        token_a = self.issue_worker()
        work = self.claim(token_a, pid, "runner-a")
        token_b = self.issue_worker()
        # Bind B to the same project but another ready task/runner identity.
        self.claim(token_b, pid, "runner-b", "OPS-102")

        for route, body in (
            ("/api/worker/heartbeat", {"project_id": pid, "task_id": "OPS-101", "lease": work["lease"]}),
            ("/api/worker/result", {"project_id": pid, "task_id": "OPS-101", "lease": work["lease"], "submission_id": "b-steal", "response": {"files": {}}}),
        ):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request(route, body, worker=token_b, operator=False)
            self.assertEqual(error.exception.code, 403)

        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request(
                f"/api/projects/{pid}/task",
                {"task_id": "OPS-101", "action": "integrate"},
                worker=token_b,
                operator=False,
                headers={"X-Station-Token": ""},
            )
        self.assertEqual(error.exception.code, 403)

        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/worker/cancel", {"project_id": pid, "task_id": "OPS-101"}, worker=token_b, operator=False)
        self.assertEqual(error.exception.code, 400)

    # AUD-1 regression 3: a project-bound credential cannot exercise authority in another project.
    def test_03_project_bound_credential_cannot_cross_project(self):
        project_a = self.make_project()
        project_b = self.make_project()
        token = self.issue_worker()
        self.claim(token, project_a, "runner-a")
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.claim(token, project_b, "runner-a")
        self.assertEqual(error.exception.code, 403)

    # AUD-1 regression 4: non-loopback exposure fails closed unless every explicit control is present.
    def test_04_non_loopback_bind_requires_explicit_tls_exposure_contract(self):
        with self.assertRaises(ContractError):
            validate_exposure("0.0.0.0", "", False, "")
        with self.assertRaises(ContractError):
            validate_exposure("0.0.0.0", "station.example:443", True, "http://station.example:443")
        with self.assertRaises(ContractError):
            validate_exposure("0.0.0.0", "other.example", True, "https://station.example")
        self.assertEqual(
            validate_exposure("0.0.0.0", "station.example", True, "https://station.example"),
            "https://station.example",
        )
        self.assertIsNone(validate_exposure("127.0.0.1", "", False, ""))

    # AUD-1 regression 5: Host spoofing cannot acquire bootstrap or launch authority.
    def test_05_spoofed_host_cannot_become_local_operator(self):
        for path in ("/api/bootstrap", "/auth/launch-capability"):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request(path, operator=False, headers={"Host": "evil.example"})
            self.assertEqual(error.exception.code, 403)

    # AUD-1 regression 9: stale result remains dead after expiry, recovery and reassignment.
    def test_09_stale_result_rejected_after_recovery_and_reassignment(self):
        pid = self.make_project()
        old_token = self.issue_worker()
        old = self.claim(old_token, pid, "old-runner")
        with self.station.store.transaction() as connection:
            task = self.station.store._task(connection, pid, "OPS-101")
            task["lease_until"] = time.time() - 1
            self.station.store._write_task(connection, pid, task)
        self.station.store.recover()
        self.station.triage(pid)

        new_token = self.issue_worker()
        new = self.claim(new_token, pid, "new-runner")
        self.assertNotEqual(old["lease"], new["lease"])
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request(
                "/api/worker/result",
                {"project_id": pid, "task_id": "OPS-101", "lease": old["lease"], "submission_id": "stale", "response": {"files": {}}},
                worker=old_token,
                operator=False,
            )
        self.assertEqual(error.exception.code, 403)

    # AUD-1 regression 10: rotation invalidates every previously issued runner credential.
    def test_10_rotation_invalidates_old_runner_credentials(self):
        pid = self.make_project()
        old = self.issue_worker()
        self.claim(old, pid, "runner-a")
        fresh = self.issue_worker(rotate=True)
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/worker/projects", worker=old, operator=False)
        self.assertEqual(error.exception.code, 403)
        # A fresh credential remains usable and binds on its first claim.
        other = self.make_project()
        self.assertIsNotNone(self.claim(fresh, other, "runner-new"))


class AUD1WorkerContinuityTests(unittest.TestCase):
    class Provider:
        placement = "local"
        model = "fixture"

        def __init__(self, delay):
            self.delay = delay

        def generate(self, packet, max_tokens):
            time.sleep(self.delay)
            return Reply('{"files":{"station/health.py":"def status(services):\\n    return \'ready\' if all(services.values()) else \'degraded\'\\n"}}', Usage())

        def wire_size(self, packet, max_tokens):
            return 100

    def client(self, delay, *, transient=False):
        client = WorkerClient("http://127.0.0.1:8765", "test-token", heartbeat_interval=0.01, heartbeat_grace=0.04)
        calls = {"heartbeat": 0, "result": 0}
        work = {
            "project_id": "p-test",
            "task_id": "OPS-101",
            "lease": "lease-a",
            "packet": {"task": "fixture"},
            "allow_cloud": False,
        }

        def request(route, data):
            if route == "claim":
                return {"work": work}
            if route == "heartbeat":
                calls["heartbeat"] += 1
                if transient and calls["heartbeat"] == 1:
                    raise OSError("temporary tunnel loss")
                if not transient:
                    raise OSError("persistent tunnel loss")
                return {"ok": True}
            if route == "result":
                calls["result"] += 1
                return {"state": "review_ready"}
            raise AssertionError(route)

        client.request = request
        return client, self.Provider(delay), calls

    # AUD-1 regression 7: an interruption inside the grace window recovers without duplicate authority.
    def test_07_temporary_heartbeat_loss_recovers_inside_grace(self):
        client, provider, calls = self.client(0.035, transient=True)
        self.assertTrue(client.run_once("p-test", "runner-a", provider))
        self.assertGreaterEqual(calls["heartbeat"], 2)
        self.assertEqual(calls["result"], 1)

    # AUD-1 regression 8: persistent heartbeat loss surrenders before a proposal can be submitted.
    def test_08_persistent_heartbeat_loss_surrenders_and_never_submits(self):
        client, provider, calls = self.client(0.20, transient=False)
        with self.assertRaises(WorkerAuthorityLost):
            client.run_once("p-test", "runner-a", provider)
        self.assertGreaterEqual(calls["heartbeat"], 3)
        self.assertEqual(calls["result"], 0)


if __name__ == "__main__":
    unittest.main()
