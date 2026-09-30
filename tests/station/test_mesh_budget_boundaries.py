"""Attempt authority, durable crash boundaries and safe runner rejection receipts."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
from unittest.mock import Mock, patch

from residual.core import ContractError, canonical
from residual.station.contracts import ExecutionAdmissionError, sha
from residual.station.mesh_cli import worker_main
from residual.station.mesh_runner import MeshClawRunner
from residual.station.mesh_worker import MeshAdmissionRejected, MeshWorkerClient
from residual.station.server import Server
from residual.station.service import DEMO_FILES, Station, demo_spec
from residual.station.store import MAX_TASK_ATTEMPTS, Store
from tests.station.test_sc_mesh_001 import enrollment

PLAN = [{"placement": "local", "model": "fixture/model", "request_bytes": 100}]
OBSERVED = [{**PLAN[0], "request_bytes": 90, "status": "completed", "usage_known": True}]


class BudgetBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.station = Station(self.temp.name)
        self.pid = self.station.create(demo_spec(), demo=True)["project_id"]
        self.station.triage(self.pid)
        self.store = self.station.store
        self.tid = "OPS-101"

    def claim(self):
        return self.store.claim(self.pid, "mesh:fixture", self.tid, reserve_budget=True)

    def admit(self, task, store=None):
        return (store or self.store).reserve_mesh_execution(
            self.pid, self.tid, task["lease"], task["fencing_token"], 1, PLAN)

    def reconcile(self, task, observed=OBSERVED, store=None):
        return (store or self.store).reconcile_mesh_execution(
            self.pid, self.tid, task["lease"], task["fencing_token"], observed)

    def recover(self, task):
        with patch("residual.station.store.time.time", return_value=task["lease_until"] + 1):
            self.store.recover()
        self.station.triage(self.pid)

    def counters(self):
        p = self.store.project(self.pid)
        return tuple(p.get(k, 0) for k in (
            "calls_reserved", "cloud_calls_reserved", "request_bytes_reserved",
            "mesh_assignments_reserved", "mesh_cloud_assignments_reserved"))

    def test_budget_is_bound_and_duplicate_rejected_even_after_reconciliation(self):
        first = self.claim()
        budget = self.admit(first)
        self.assertEqual((budget["attempt"], budget["fencing_token"], budget["generation"]), (1, 1, 1))
        before = self.counters()
        with self.assertRaises(ExecutionAdmissionError) as raised:
            self.admit(first)
        self.assertEqual(raised.exception.reason_code, "EXECUTION_BUDGET_ALREADY_ADMITTED")
        self.assertEqual(self.counters(), before)
        self.reconcile(first)
        after = self.counters()
        with self.assertRaises(ExecutionAdmissionError):
            self.admit(first)
        with self.assertRaises(ContractError):
            self.reconcile(first, [])
        self.assertEqual(self.counters(), after)

    def test_successor_preserves_old_budget_and_event_chain_without_refund(self):
        first = self.claim()
        old = self.admit(first)
        self.recover(first)
        second = self.claim()
        self.assertIsNone(second["mesh_execution_budget"])
        self.admit(second)
        events = self.store.events(self.pid)
        fenced = [e for e in events if e["event_type"] == "mesh.execution.fenced"]
        self.assertEqual(len(fenced), 1)
        self.assertEqual(fenced[0]["attempt"], 1)
        self.assertEqual(fenced[0]["data"]["budget"], old)
        self.assertEqual(self.counters()[:3], (2, 0, 200))
        previous = "0" * 64
        for event in copy.deepcopy(events):
            digest = event.pop("hash"); event.pop("seq")
            self.assertEqual(event.pop("prev_hash"), previous)
            self.assertEqual(digest, sha({"previous": previous, "event": event}))
            previous = digest

    def test_reconciled_failure_also_gets_a_new_budget(self):
        first = self.claim(); self.admit(first); self.reconcile(first)
        self.store.transition(self.pid, self.tid, "repair_required", lease=first["lease"])
        second = self.claim(); self.admit(second)
        self.assertEqual(second["attempt"], 2)
        self.assertEqual(self.counters()[:3], (2, 0, 190))
        archive = next(e for e in self.store.events(self.pid) if e["event_type"] == "mesh.execution.fenced")
        self.assertTrue(archive["data"]["budget"]["reconciled"])

    def test_old_lease_fence_generation_and_expired_reconciliation_are_rejected(self):
        first = self.claim(); self.admit(first)
        with patch("residual.station.store.time.time", return_value=first["lease_until"] + 1):
            for evidence in (OBSERVED, None, []):
                with self.assertRaises(ContractError):
                    self.reconcile(first, evidence)
        self.recover(first)
        second = self.claim(); self.admit(second)
        before = self.counters()
        with self.assertRaises(ContractError): self.admit(first)
        with self.assertRaises(ContractError): self.reconcile(first, [])
        forged_fence = {**second, "fencing_token": first["fencing_token"]}
        with self.assertRaises(ContractError): self.admit(forged_fence)
        self.store.advance_generation(self.pid, "fixture")
        with self.assertRaises(ContractError): self.admit(second)
        with self.assertRaises(ContractError): self.reconcile(second, [])
        self.assertEqual(self.counters(), before)

    def test_triage_and_retry_cannot_mint_authority_or_exceed_attempt_limit(self):
        for number in range(1, MAX_TASK_ATTEMPTS + 1):
            task = self.claim()
            self.assertEqual(task["attempt"], number)
            self.admit(task)
            before = self.counters()
            for _ in range(3):
                self.station.triage(self.pid)
                self.assertIsNone(self.claim())
                with self.assertRaises(ContractError): self.admit(task)
            self.assertEqual(self.counters(), before)
            self.recover(task)
            for _ in range(3): self.station.triage(self.pid)
            self.assertEqual(self.store.task(self.pid, self.tid)["attempt"], number)
        self.assertIsNone(self.claim())
        self.assertEqual(self.counters()[:3], (MAX_TASK_ATTEMPTS, 0, MAX_TASK_ATTEMPTS * 100))

    def test_project_budget_is_not_reset_by_new_attempt(self):
        self.store.project_update(self.pid, call_limit=1)
        first = self.claim(); self.admit(first); self.recover(first)
        self.assertIsNone(self.claim())
        self.assertEqual(self.counters()[:3], (1, 0, 100))

    def test_reopen_keeps_duplicate_rejection_and_recovery_keeps_consumption(self):
        first = self.claim(); old = self.admit(first)
        reopened = Store(self.temp.name)
        self.assertEqual(reopened.task(self.pid, self.tid)["mesh_execution_budget"], old)
        with self.assertRaises(ContractError): self.admit(first, reopened)
        self.station = Station(self.temp.name)  # Real startup recovery blocks mesh leases.
        self.store = self.station.store
        self.assertEqual(self.store.task(self.pid, self.tid)["state"], "blocked")
        self.assertEqual(self.counters()[:3], (1, 0, 100))
        self.station.triage(self.pid)
        second = self.claim(); self.admit(second)
        self.assertEqual(self.counters()[:3], (2, 0, 200))

    def test_legacy_unbound_budget_is_fenced_without_fabricated_generation(self):
        first = self.claim(); legacy = self.admit(first)
        for key in ("attempt", "fencing_token", "generation"): legacy.pop(key)
        # Migration fixture for data written by the pinned pre-fix implementation.
        self.store.update_task(self.pid, self.tid, mesh_execution_budget=legacy)
        with self.assertRaises(ContractError): self.admit(first)
        with self.assertRaises(ContractError): self.reconcile(first, [])
        self.recover(first)
        second = self.claim(); self.admit(second)
        archive = next(e for e in self.store.events(self.pid) if e["event_type"] == "mesh.execution.fenced")
        self.assertEqual(archive["attempt"], 1)
        self.assertEqual(archive["data"]["budget"], legacy)
        self.assertNotIn("generation", archive["data"]["budget"])
        self.assertEqual(self.counters()[:3], (2, 0, 200))

    def test_concurrent_admission_has_one_effective_reservation(self):
        task = self.claim()
        def admit(_):
            try:
                self.admit(task, Store(self.temp.name)); return True
            except ExecutionAdmissionError: return False
        with ThreadPoolExecutor(max_workers=6) as pool:
            self.assertEqual(sum(pool.map(admit, range(6))), 1)
        self.assertEqual(self.counters()[:3], (1, 0, 100))

    def test_claim_archive_and_fresh_state_rollback_together(self):
        first = self.claim(); old = self.admit(first); self.recover(first)
        before = self.counters()
        original = self.store._event
        def fail(c, p, kind, *args, **kwargs):
            value = original(c, p, kind, *args, **kwargs)
            if kind == "task.claimed": raise RuntimeError("fixture crash before claim commit")
            return value
        with patch.object(self.store, "_event", side_effect=fail):
            with self.assertRaises(RuntimeError): self.claim()
        task = Store(self.temp.name).task(self.pid, self.tid)
        self.assertEqual(task["attempt"], 1)
        self.assertEqual(task["mesh_execution_budget"], old)
        self.assertEqual(self.counters(), before)
        self.assertFalse(any(e["event_type"] == "mesh.execution.fenced" for e in self.store.events(self.pid)))
        self.assertEqual(self.claim()["attempt"], 2)

    def test_real_process_crash_before_and_after_admission_commit(self):
        task = self.claim()
        script = '''
import json, os, sys
from residual.station.store import Store
v = json.load(sys.stdin)
s = Store(v["root"])
if v["before_commit"]:
    original = s._event
    def crash(*args, **kwargs):
        result = original(*args, **kwargs)
        if args[2] == "mesh.execution.admitted": os._exit(79)
        return result
    s._event = crash
s.reserve_mesh_execution(v["pid"], v["tid"], v["lease"], v["fence"], 1, v["plan"])
os._exit(79)
'''
        for before_commit in (True, False):
            with self.subTest(before_commit=before_commit):
                result = subprocess.run([sys.executable, "-c", script], input=json.dumps({
                    "root": self.temp.name, "pid": self.pid, "tid": self.tid,
                    "lease": task["lease"], "fence": task["fencing_token"],
                    "plan": PLAN, "before_commit": before_commit}), text=True,
                    capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 79, result.stderr)
                reopened = Store(self.temp.name)
                active = reopened.task(self.pid, self.tid)["mesh_execution_budget"]
                if before_commit:
                    self.assertIsNone(active)
                    self.assertEqual(self.counters(), (0, 0, 0, 1, 0))
                else:
                    self.assertFalse(active["reconciled"])
                    self.assertEqual(self.counters(), (1, 0, 100, 0, 0))
                    with self.assertRaises(ContractError): self.admit(task, reopened)
        self.assertEqual(sum(e["event_type"] == "mesh.execution.admitted" for e in self.store.events(self.pid)), 1)

    def test_reconciliation_rollback_and_restart_do_not_double_credit(self):
        task = self.claim(); self.admit(task)
        original = self.store._event
        def crash(c, p, kind, *args, **kwargs):
            result = original(c, p, kind, *args, **kwargs)
            if kind == "mesh.execution.reconciled": raise RuntimeError("fixture crash")
            return result
        with patch.object(self.store, "_event", side_effect=crash):
            with self.assertRaises(RuntimeError): self.reconcile(task)
        self.assertEqual(self.counters(), (1, 0, 100, 0, 0))
        reopened = Store(self.temp.name)
        self.reconcile(task, store=reopened)
        self.assertEqual(self.counters(), (1, 0, 90, 0, 0))
        with self.assertRaises(ContractError): self.reconcile(task, [], Store(self.temp.name))
        self.assertEqual(self.counters(), (1, 0, 90, 0, 0))


class HTTPBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.station = Station(self.temp.name)
        self.pid = self.station.create(demo_spec(), demo=True)["project_id"]
        self.station.triage(self.pid)
        created = self.station.mesh.enroll(enrollment(self.pid), allowed_capabilities=
                                          self.station.store.settings()["mesh_allowed_capabilities"])
        self.server = Server(("127.0.0.1", 0), self.station)
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True)
        self.thread.start()
        self.client = MeshWorkerClient(f"http://127.0.0.1:{self.server.server_port}",
                                       created["token"], worker_id="claw-a")
        self.client.sync(self.pid)

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2)
        self.temp.cleanup()

    def test_first_attempt_executes_and_real_result_is_reconciled(self):
        adapter = Mock()
        def execute(assignment):
            plan = assignment["provider_plan"][0]
            return Mock(text=canonical({"files": DEMO_FILES["OPS-101"]}),
                        model="fixture/model", provider="fixture", usage={"input": 1, "output": 1},
                        provider_attempts=({**plan, "status": "completed", "usage_known": True},))
        adapter.execute.side_effect = execute
        runner = MeshClawRunner(self.client, adapter, project_id=self.pid,
                                provider_routes=[{"placement": "local", "model": "fixture/model"}])
        self.assertEqual(runner.run_once()["state"], "review_ready")
        self.assertEqual(adapter.execute.call_count, 1)
        self.assertTrue(self.station.store.task(self.pid, "OPS-101")["mesh_execution_budget"]["reconciled"])
        self.assertIsNone(runner.current)

    def test_failed_result_is_reconciled_and_successor_runs_with_fresh_budget(self):
        adapter = Mock()
        def execute(assignment):
            plan = assignment["provider_plan"][0]
            files = ({"station/health.py": "def status(services): return 'wrong'\n"}
                     if adapter.execute.call_count == 1 else DEMO_FILES["OPS-101"])
            return Mock(text=canonical({"files": files}), model="fixture/model", provider="fixture",
                        usage={"input": 1, "output": 1},
                        provider_attempts=({**plan, "status": "completed", "usage_known": True},))
        adapter.execute.side_effect = execute
        runner = MeshClawRunner(self.client, adapter, project_id=self.pid,
                                provider_routes=[{"placement": "local", "model": "fixture/model"}])
        self.assertEqual(runner.run_once()["state"], "repair_required")
        old = self.station.store.task(self.pid, "OPS-101")["mesh_execution_budget"]
        self.assertTrue(old["reconciled"])
        self.assertEqual(runner.run_once()["state"], "review_ready")
        self.assertEqual(adapter.execute.call_count, 2)
        task = self.station.store.task(self.pid, "OPS-101")
        self.assertEqual(task["attempt"], 2)
        self.assertEqual(task["mesh_execution_budget"]["attempt"], 2)
        archive = next(e for e in self.station.store.events(self.pid)
                       if e["event_type"] == "mesh.execution.fenced")
        self.assertEqual(archive["data"]["budget"], old)
        self.assertEqual(self.station.store.project(self.pid)["calls_reserved"], 2)

    def test_station_error_reaches_runner_and_cli_without_openclaw_execution(self):
        work = self.client.claim(self.pid, "OPS-101")
        self.client.execution_admit(work, PLAN)
        with patch.object(self.client, "claim", return_value=work):
            adapter = Mock()
            runner = MeshClawRunner(self.client, adapter, project_id=self.pid,
                                    provider_routes=[{"placement": "local", "model": "fixture/model"}])
            with self.assertRaises(MeshAdmissionRejected) as raised:
                runner.run_once()
            receipt = raised.exception.to_dict()
            self.assertEqual(receipt["code"], "EXECUTION_ADMISSION_REJECTED")
            self.assertEqual(receipt["reason_code"], "EXECUTION_BUDGET_ALREADY_ADMITTED")
            self.assertEqual(receipt["http_status"], 400)
            self.assertEqual(receipt["http_status_class"], "4xx")
            for key in ("project_id", "task_id", "attempt", "fencing_token", "generation"):
                self.assertEqual(receipt[key], work[key])
            self.assertEqual(receipt["message"], "Execution budget was already admitted for this task attempt")
            adapter.execute.assert_not_called(); adapter.cancel.assert_not_called()
            self.assertIsNone(runner.current); self.assertIsNone(runner.current_assignment_id)
            cfg = {"adapter": {"config_path": "unused", "workspace": "unused", "expected_version": "", "timeout_s": 1},
                   "station": self.client.base, "project_id": self.pid, "worker_id": "claw-a",
                   "outbox_path": None, "provider_routes": [{"placement": "local", "model": "fixture/model"}]}
            stderr = io.StringIO()
            with patch("residual.station.mesh_cli.load_worker_config", return_value=cfg), \
                    patch("residual.station.mesh_cli.OpenClawExecAdapter", return_value=adapter), \
                    patch("residual.station.mesh_cli.MeshWorkerClient", return_value=self.client), \
                    patch("residual.station.mesh_cli._token", return_value="fixture-token"), \
                    patch("residual.station.mesh_cli.signal.signal"), contextlib.redirect_stderr(stderr):
                self.assertEqual(worker_main(["--config", "unused", "--once"]), 3)
            logged = json.loads(stderr.getvalue())
            self.assertEqual(logged, receipt)
            self.assertNotIn(work["lease_id"], stderr.getvalue())
            self.assertNotIn(self.client.token, stderr.getvalue())
            adapter.execute.assert_not_called(); adapter.cancel.assert_not_called()
            adapter.connect.assert_not_called()

    def test_old_admission_and_result_are_fenced_after_successor(self):
        first = self.client.claim(self.pid, "OPS-101"); self.client.execution_admit(first, PLAN)
        task = self.station.store.task(self.pid, "OPS-101")
        with patch("residual.station.store.time.time", return_value=task["lease_until"] + 1):
            self.station.store.recover()
        self.station.triage(self.pid)
        second = self.client.claim(self.pid, "OPS-101"); self.client.execution_admit(second, PLAN)
        before = self.station.store.project(self.pid)
        with self.assertRaises(MeshAdmissionRejected) as wrong_attempt:
            self.client.execution_admit({**second, "attempt": first["attempt"]}, PLAN)
        self.assertEqual(wrong_attempt.exception.reason_code, "STALE_TASK_ATTEMPT")
        with self.assertRaises(MeshAdmissionRejected) as raised: self.client.execution_admit(first, PLAN)
        self.assertEqual(raised.exception.reason_code, "STALE_TASK_LEASE")
        for stale in (first, {**second, "attempt": first["attempt"]}):
            with self.assertRaises(urllib.error.HTTPError):
                self.client.submit_result(stale, submission_id="stale", response={"files": {}}, provider_attempts=[])
        self.assertEqual(self.station.store.project(self.pid), before)

    def test_false_or_missing_admission_cannot_start_execution(self):
        for value in ({"admitted": False}, {}, None, {"admitted": 1}):
            with self.subTest(value=value):
                client = Mock(snapshots={self.pid: {"generation": 1}})
                client.claim.return_value = {"project_id": self.pid, "task_id": "OPS-101", "attempt": 1,
                                             "fencing_token": 1, "route": "local", "packet": {}}
                client.execution_admit.return_value = value
                adapter = Mock()
                runner = MeshClawRunner(client, adapter, project_id=self.pid,
                                        provider_routes=[{"placement": "local", "model": "fixture/model"}])
                with self.assertRaises(ContractError): runner.run_once()
                adapter.execute.assert_not_called(); adapter.cancel.assert_not_called()
                self.assertIsNone(runner.current)


class ErrorRedactionTests(unittest.TestCase):
    def test_malformed_unknown_and_secret_bodies_keep_only_safe_diagnostics(self):
        known = {"code": "EXECUTION_ADMISSION_REJECTED", "reason_code": "EXECUTION_BUDGET_ALREADY_ADMITTED",
                 "message": "SECRET provider prompt", "token": "SECRET"}
        for raw in (b"SECRET", b"[1]", b"{", b"\xff", b"x" * 9000, b"[" * 2000 + b"]" * 2000,
                    canonical({"error": "SECRET"}).encode(),
                    canonical({"execution_error": {**known, "reason_code": "SECRET"}}).encode(),
                    canonical({"execution_error": {**known, "reason_code": []}}).encode(),
                    canonical({"execution_error": {**known, "reason_code": {}}}).encode(),
                    canonical({"execution_error": known, "prompt": "SECRET"}).encode()):
            with self.subTest(raw=raw[:30]):
                client = MeshWorkerClient("http://localhost", "SECRET-token", worker_id="fixture")
                error = urllib.error.HTTPError("http://localhost/SECRET", 400, "SECRET", {}, io.BytesIO(raw))
                client.opener = Mock(); client.opener.open.side_effect = error
                with self.assertRaises(MeshAdmissionRejected) as raised:
                    client.request("execution-admit", {"project_id": "p-1", "task_id": "T-1",
                                                       "attempt": 1, "lease_id": "SECRET"})
                receipt = raised.exception.to_dict()
                self.assertNotIn("SECRET", json.dumps(receipt))
                self.assertNotIn("SECRET", str(raised.exception))
                self.assertEqual(receipt["http_status"], 400)
                self.assertEqual(receipt["reason_code"], "EXECUTION_BUDGET_ALREADY_ADMITTED"
                                 if raw.endswith(b'"prompt":"SECRET"}') else "STATION_HTTP_ERROR")

    def test_http_status_class_is_retained_without_unsafe_legacy_message(self):
        for status in (400, 403, 429, 500, 503):
            with self.subTest(status=status):
                client = MeshWorkerClient("http://localhost", "fixture", worker_id="fixture")
                client.opener = Mock()
                client.opener.open.side_effect = urllib.error.HTTPError(
                    "http://localhost", status, "SECRET", {}, io.BytesIO(b'{"error":"SECRET"}'))
                with self.assertRaises(MeshAdmissionRejected) as raised:
                    client.request("execution-admit", {})
                self.assertEqual(raised.exception.to_dict()["http_status"], status)
                self.assertEqual(raised.exception.to_dict()["http_status_class"], f"{status // 100}xx")
                self.assertNotIn("SECRET", str(raised.exception))

    def test_explicit_cli_preflight_still_probes_without_claiming(self):
        cfg = {"adapter": {"config_path": "unused", "workspace": "unused",
                           "expected_version": "", "timeout_s": 1},
               "project_id": "p-1", "worker_id": "fixture"}
        adapter = Mock(); adapter.connect.return_value = {"supported": True}
        output = io.StringIO()
        with patch("residual.station.mesh_cli.load_worker_config", return_value=cfg), \
                patch("residual.station.mesh_cli.OpenClawExecAdapter", return_value=adapter), \
                patch("residual.station.mesh_cli.MeshWorkerClient") as client, \
                contextlib.redirect_stdout(output):
            self.assertEqual(worker_main(["--config", "unused", "--preflight"]), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "PREFLIGHT_PASS")
        adapter.connect.assert_called_once(); adapter.execute.assert_not_called()
        client.assert_not_called()

    def test_unrelated_mesh_transport_error_behavior_is_unchanged(self):
        client = MeshWorkerClient("http://localhost", "fixture", worker_id="fixture")
        error = urllib.error.HTTPError("http://localhost", 503, "unavailable", {}, io.BytesIO(b"{}"))
        client.opener = Mock(); client.opener.open.side_effect = error
        with self.assertRaises(urllib.error.HTTPError) as raised: client.request("message", {})
        self.assertIs(raised.exception, error)


if __name__ == "__main__":
    unittest.main()
