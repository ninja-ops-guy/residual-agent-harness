from __future__ import annotations

import concurrent.futures
import io
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from residual.core import ContractError, canonical
from residual.station.contracts import event_validate, parse_spec, sha
from residual.station.models import StationProvider, public_settings, save_settings, model_call
from residual.station.server import Server
from residual.station.service import Station, demo_spec, DEMO_FILES
from residual.station.store import Store
from residual.station import workspace as ws


class StationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.s = Station(self.temp.name)
        self.pid = self.s.create(demo_spec(), demo=True)["project_id"]

    def tearDown(self):
        self.temp.cleanup()

    def test_full_demo_real_git_tests_review_and_release(self):
        result = self.s.batch(self.pid)
        self.assertEqual(result["integrated"], 3)
        self.assertEqual(self.s.metrics(self.pid)["calls"], 0)
        p = self.s.store.project(self.pid)
        for task in p["tasks"]:
            self.assertEqual(task["state"], "integrated")
            self.assertTrue(all(c["passed"] for c in task["checks_result"]))
            self.assertEqual(task["review"]["head_commit"], task["head_commit"])
        art = self.s.export(self.pid)
        _, data = self.s.store.artifact(art["id"])
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            self.assertIn("HANDOFF.md", z.namelist())
            self.assertNotIn(".git/config", z.namelist())
        self.assertIn("OPS-101 | integrated", self.s.store.markdown(self.pid))

    def test_invalid_manifest_rejects_cycles_unknown_fields_and_paths(self):
        m = parse_spec(demo_spec())
        mutations = [lambda x: x["tasks"][0].update(depends_on=["OPS-103"]),
                     lambda x: x["tasks"][0].update(files=["../escape"]),
                     lambda x: x["tasks"][0].update(files=[".env"]),
                     lambda x: x["tasks"][0].update(files=[".git/config"]),
                     lambda x: x.update(override_policy=True),
                     lambda x: x["tasks"][0].update(depends_on=["absent"])]
        for mutate in mutations:
            copy = json.loads(canonical(m)); mutate(copy)
            with self.assertRaises(ContractError):
                parse_spec("```json\n" + canonical(copy) + "\n```")

    def test_minimal_log_cannot_be_admitted_as_workflow_event(self):
        with self.assertRaises(ContractError):
            event_validate({"event_type": "task.completed", "timestamp": "2026-09-13T00:00:00Z"})
        event = self.s.store.events(self.pid)[0]
        for key in ("seq", "hash", "prev_hash"):
            event.pop(key)
        event_validate(event)
        event["spec_hash"] = "not-a-hash"
        with self.assertRaises(ContractError):
            event_validate(event)

    def test_event_chain_and_report_cursor_are_deterministic(self):
        self.s.triage(self.pid)
        previous = "0" * 64
        for event in self.s.store.events(self.pid):
            root = event.pop("hash"); event.pop("seq")
            self.assertEqual(event.pop("prev_hash"), previous)
            self.assertEqual(root, sha({"previous": previous, "event": event}))
            previous = root
        first = self.s.store.report(self.pid)
        self.assertTrue(first["changes"])
        self.s.store.acknowledge(self.pid, "cloud-review", first["through_seq"])
        second = self.s.store.report(self.pid)
        self.assertEqual(second["changes"], [])
        self.assertEqual(first["tasks"], second["tasks"])

    def test_concurrent_claims_are_exclusive_and_dependencies_wait(self):
        self.s.triage(self.pid)
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            jobs = list(pool.map(lambda n: self.s.store.claim(self.pid, f"w{n}"), range(6)))
        claimed = [j["id"] for j in jobs if j]
        self.assertEqual(sorted(claimed), ["OPS-101", "OPS-102"])

    def test_lease_expiry_and_restart_recovery_preserve_evidence(self):
        self.s.triage(self.pid)
        work = self.s.prepare(self.pid, "local-runner", "OPS-101")
        reopened = Station(self.temp.name)
        self.assertEqual(reopened.store.task(self.pid, "OPS-101")["state"], "blocked")
        with self.assertRaises(ContractError):
            reopened.finish(work, {"files": DEMO_FILES["OPS-101"]})

    def test_stale_worker_cannot_write_candidate(self):
        self.s.triage(self.pid)
        work = self.s.prepare(self.pid, "remote:one", "OPS-101")
        original = ws.context_files(self.s.store.task(self.pid, "OPS-101")["candidate_dir"], work["task"])
        work["lease"] = "wrong"
        with self.assertRaises(ContractError):
            self.s.finish(work, {"files": DEMO_FILES["OPS-101"]})
        self.assertEqual(original, ws.context_files(self.s.store.task(self.pid, "OPS-101")["candidate_dir"], work["task"]))

    def test_failed_checks_do_not_reach_review(self):
        self.s.triage(self.pid)
        work = self.s.prepare(self.pid, "one", "OPS-101")
        self.s.finish(work, {"files": {"station/health.py": "def status(services):\n    return 'ready'\n"}})
        self.assertEqual(self.s.store.task(self.pid, "OPS-101")["state"], "repair_required")
        with self.assertRaises(ContractError):
            self.s.review(self.pid, "OPS-101")

    def test_write_scope_and_symlink_are_enforced(self):
        self.s.triage(self.pid)
        work = self.s.prepare(self.pid, "one", "OPS-101")
        with self.assertRaises(ContractError):
            self.s.finish(work, {"files": {"secrets.txt": "override"}})
        root = Path(self.temp.name) / "links"; root.mkdir()
        (root / "link").symlink_to(root / "real")
        with self.assertRaises(ContractError):
            ws.safe_file(root, "link/target.py")

    def test_approval_cannot_survive_changed_candidate(self):
        self.s.triage(self.pid); self.s.run_one(self.pid, "OPS-101"); self.s.review(self.pid, "OPS-101")
        task = self.s.store.task(self.pid, "OPS-101")
        Path(task["candidate_dir"], "station/health.py").write_text("broken = True")
        with self.assertRaises(ContractError):
            self.s.integrate(self.pid, "OPS-101")

    def test_moving_base_invalidates_review(self):
        self.s.triage(self.pid)
        self.s.run_one(self.pid, "OPS-101"); self.s.run_one(self.pid, "OPS-102")
        self.s.review(self.pid, "OPS-101"); self.s.review(self.pid, "OPS-102")
        self.s.integrate(self.pid, "OPS-101")
        with self.assertRaises(ContractError):
            self.s.integrate(self.pid, "OPS-102")
        self.assertEqual(self.s.store.task(self.pid, "OPS-102")["state"], "repair_required")

    def test_disjoint_refresh_rechecks_and_reviews_new_commit(self):
        self.s.triage(self.pid)
        self.s.run_one(self.pid, "OPS-101"); self.s.run_one(self.pid, "OPS-102")
        original = self.s.store.task(self.pid, "OPS-102")["head_commit"]
        self.s.review(self.pid, "OPS-101"); self.s.integrate(self.pid, "OPS-101")
        self.s.review(self.pid, "OPS-102")
        task = self.s.store.task(self.pid, "OPS-102")
        self.assertNotEqual(original, task["head_commit"])
        self.assertEqual(task["review"]["head_commit"], task["head_commit"])

    def test_pause_prevents_claim_and_cloud_disabled_prevents_transport(self):
        self.s.triage(self.pid); self.s.store.pause(self.pid, True)
        self.assertIsNone(self.s.prepare(self.pid, "one"))
        with self.assertRaises(ContractError):
            self.s.cloud_report(self.pid)
        with self.assertRaises(ContractError):
            self.s.store.reserve_call(self.pid, "runner", "remote", 100)

    def test_budget_reservation_is_atomic_and_survives_failed_call(self):
        self.s.store.project_update(self.pid, call_limit=1)
        self.s.store.reserve_call(self.pid, "runner", "local", 123)
        with self.assertRaises(ContractError):
            self.s.store.reserve_call(self.pid, "runner", "local", 123)
        self.assertEqual(self.s.store.project(self.pid)["calls_reserved"], 1)

    def test_api_key_is_not_public_or_in_project_exports(self):
        save_settings(self.s.store, {"cloud_key": "sensitive-example-key"})
        self.assertTrue(public_settings(self.s.store)["has_cloud_key"])
        self.assertNotIn("sensitive-example-key", canonical(public_settings(self.s.store)))
        self.assertNotIn("sensitive-example-key", self.s.store.markdown(self.pid))

    def test_runtime_base_schema_is_upstream_copy(self):
        repo = Path(__file__).parents[2]
        self.assertEqual((repo / "vendor/ldd-kit/base.json").read_bytes(), (repo / "residual/station/schemas/ldd-base.json").read_bytes())

    def test_test_commands_require_project_permission(self):
        checks = [{"kind": "command", "argv": ["{python}", "-c", "print('ok')"]}]
        result = ws.run_checks(self.temp.name, checks, False)
        self.assertFalse(result[0]["passed"])

    def test_artifact_tampering_is_rejected(self):
        a = self.s.store.add_artifact(self.pid, "receipt", "original")
        (self.s.store.root / "artifacts" / self.pid / a["sha256"]).write_text("tampered")
        with self.assertRaises(ContractError):
            self.s.store.artifact(a["id"])

    def test_release_rejects_dirty_or_unaccepted_revision(self):
        self.s.batch(self.pid)
        repo = self.s.store.project(self.pid)["repo"]
        target = Path(repo, "HANDOFF.md")
        target.write_text("unverified replacement")
        with self.assertRaises(ContractError):
            self.s.export(self.pid)
        ws.git(repo, "add", "HANDOFF.md"); ws.git(repo, "commit", "-m", "External edit")
        with self.assertRaises(ContractError):
            self.s.export(self.pid)

    def test_live_cloud_enabled_batch_generates_assessment_after_work(self):
        self.s.store.project_update(self.pid, mode="live", allow_cloud=True)
        self.s.store.settings({"cloud": {"model": "configured"}})
        with patch("residual.station.service.model_call") as call, patch.object(self.s, "cloud_report", return_value={"id": "report"}) as report:
            def reply(store, pid, role, packet, system, schema, placement, tid):
                return {"files": DEMO_FILES[tid]} if role == "runner" else {"approved": True, "findings": []}
            call.side_effect = reply
            result = self.s.batch(self.pid)
            self.assertEqual(result["integrated"], 3)
            self.assertEqual(result["assessment"], {"id": "report"})
            report.assert_called_once()


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.s = Station(self.temp.name)
        self.http = Server(("127.0.0.1", 0), self.s)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True); self.thread.start()
        self.url = f"http://127.0.0.1:{self.http.server_port}"
        self.token = self.s.store.settings()["session_token"]

    def tearDown(self):
        self.http.shutdown(); self.http.server_close(); self.thread.join(); self.temp.cleanup()

    def request(self, path, body=None, headers=None):
        req = urllib.request.Request(self.url + path, data=canonical(body).encode() if body is not None else None,
                                    headers={"Content-Type": "application/json", "X-Station-Token": self.token, **(headers or {})})
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())

    def test_csrf_and_origin_and_host_enforced(self):
        for headers in ({"X-Station-Token": "wrong"}, {"Origin": "https://evil.example"}, {"Host": "evil.example"}, {"Sec-Fetch-Site": "cross-site"}):
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.request("/api/demo", {}, headers)
            self.assertEqual(error.exception.code, 403)

    def test_bootstrap_contains_no_api_key(self):
        save_settings(self.s.store, {"cloud_key": "private-key"})
        body = self.request("/api/bootstrap")
        self.assertNotIn("private-key", canonical(body))

    def test_remote_candidate_submission_is_idempotent_and_unable_to_approve(self):
        pid = self.s.create(demo_spec(), demo=True)["project_id"]
        self.s.triage(pid)
        self.s.store.settings({"remote_workers_enabled": True})
        headers = {"Authorization": "Bearer " + self.s.store.settings()["worker_token"]}
        work = self.request("/api/worker/claim", {"project_id": pid, "task_id": "OPS-101", "name": "machine2"}, headers)["work"]
        data = {"project_id": pid, "task_id": "OPS-101", "lease": work["lease"], "submission_id": "submission-1", "response": {"files": DEMO_FILES["OPS-101"]}}
        result = self.request("/api/worker/result", data, headers)
        self.assertEqual(result["state"], "review_ready")
        self.assertEqual(result, self.request("/api/worker/result", data, headers))
        with self.assertRaises(urllib.error.HTTPError):
            self.request("/api/worker/result", {**data, "response": {"files": {}}}, headers)
        with self.assertRaises(urllib.error.HTTPError):
            self.request(f"/api/projects/{pid}/task", {"task_id": "OPS-101", "action": "integrate"}, {**headers, "X-Station-Token": ""})


class ProviderHTTPTests(unittest.TestCase):
    def test_station_uses_actual_ollama_http_framing_and_reported_usage(self):
        requests = []
        class Fake(BaseHTTPRequestHandler):
            def do_POST(self):
                packet = json.loads(self.rfile.read(int(self.headers["Content-Length"]))); requests.append((self.path, packet))
                body = canonical({"message": {"content": '{"files":{"a.py":"x=1"}}'}, "done": True, "done_reason": "stop", "prompt_eval_count": 24, "eval_count": 12}).encode()
                self.send_response(200);self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
            def log_message(self,*a):pass
        http = ThreadingHTTPServer(("127.0.0.1",0),Fake)
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        try:
            provider=StationProvider({"kind":"ollama","model":"test","base_url":f"http://127.0.0.1:{http.server_port}","placement":"local"},"IMPLEMENT",{"type":"object"})
            result=provider.generate({"task":"example"},100)
            self.assertEqual(requests[0][0],"/api/chat")
            self.assertEqual(requests[0][1]["messages"][0]["content"],"IMPLEMENT")
            self.assertEqual(requests[0][1]["options"]["num_predict"],100)
            self.assertEqual(result.usage.input_tokens,24)
        finally:
            http.shutdown();http.server_close();thread.join()
