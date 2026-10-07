from __future__ import annotations

import concurrent.futures
import io
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import secrets
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
from residual.station.service import Station, demo_spec, DEMO_FILES, _repair_detail
from residual.station.store import Store
from residual.station import workspace as ws


class StationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.s = Station(self.temp.name)
        self.pid = self.s.create(demo_spec(), demo=True)["project_id"]

    def tearDown(self):
        self.s.close()
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
        # A restart is a lifecycle transition, not a second live owner.
        self.s.close()
        reopened = Station(self.temp.name)
        self.addCleanup(reopened.close)
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

    def test_repair_attempt_receives_previous_candidate_without_mutating_fresh_baseline(self):
        self.s.triage(self.pid)
        work = self.s.prepare(self.pid, "one", "OPS-101")
        failed = "def status(services):\n    return 'ready'\n"
        self.s.finish(work, {"files": {"station/health.py": failed}})
        self.assertEqual(self.s.store.task(self.pid, "OPS-101")["state"], "repair_required")

        repair = self.s.prepare(self.pid, "two", "OPS-101")
        self.assertEqual(repair["packet"]["prior_candidate_files"]["station/health.py"], failed)
        self.assertEqual(
            repair["packet"]["files"]["station/health.py"],
            'def status(services):\n    return "unknown"\n',
        )
        self.assertTrue(repair["packet"]["repair_findings"])
        findings = [e for e in self.s.store.events(self.pid) if e["event_type"] == "task.finding"]
        self.assertTrue(any(e["data"].get("message") == "Repair context bound to prior candidate" for e in findings))

    def test_repair_detail_retains_terminal_root_cause_within_bound(self):
        detail = "Traceback context " + ("x" * 1200) + "\nTypeError: non-default argument 'acceptance' follows default argument"
        summary = _repair_detail(detail)
        self.assertLessEqual(len(summary), 500)
        self.assertIn("middle omitted", summary)
        self.assertIn("TypeError: non-default argument 'acceptance' follows default argument", summary)

    def test_repeated_failed_patch_is_explicit_repair_finding(self):
        self.s.triage(self.pid)
        failed = {"files": {"station/health.py": "def status(services):\n    return 'ready'\n"}}
        first = self.s.prepare(self.pid, "one", "OPS-101")
        self.s.finish(first, failed)
        second = self.s.prepare(self.pid, "two", "OPS-101")
        self.s.finish(second, failed)
        task = self.s.store.task(self.pid, "OPS-101")
        self.assertEqual(task["state"], "repair_required")
        self.assertTrue(any("exactly repeated a previously failed patch" in finding for finding in task["findings"]))
        events = [e for e in self.s.store.events(self.pid) if e["event_type"] == "task.finding"]
        repeated = [e for e in events if e["data"].get("message") == "Repeated failed candidate detected"]
        self.assertEqual(len(repeated), 1)
        self.assertRegex(repeated[0]["data"]["patch_sha256"], r"^[a-f0-9]{64}$")

    def test_batch_can_repair_on_fourth_attempt_without_weakening_checks(self):
        manifest = {
            "schema_version": 1,
            "name": "Bounded repair regression",
            "goal": "Exercise the full bounded task repair allowance.",
            "tasks": [{
                "id": "REPAIR-001",
                "title": "Implement answer",
                "instruction": "Create answer.py with answer() returning 42.",
                "files": ["answer.py"],
                "context": [],
                "depends_on": [],
                "route": "local",
                "checks": [
                    {"kind": "python_compile", "path": "answer.py"},
                    {"kind": "command", "argv": ["{python}", "-c", "from answer import answer; assert answer() == 42"], "timeout": 30},
                ],
            }],
        }
        fence = "\x60" * 3
        pid = self.s.create(fence + "json\n" + json.dumps(manifest) + "\n" + fence, commands=True)["project_id"]
        self.s.store.settings({"batch_max_passes": 5})
        runner_responses = iter([
            {"files": {"answer.py": "def answer():\n    return 0\n"}},
            {"files": {"answer.py": "def answer():\n    return 1\n"}},
            {"files": {"answer.py": "def answer():\n    return 41\n"}},
            {"files": {"answer.py": "def answer():\n    return 42\n"}},
        ])
        with patch("residual.station.service.model_call") as call:
            def reply(store, project_id, role, packet, system, schema, placement, tid, *, extensions=None):
                if role == "runner":
                    return next(runner_responses)
                return {"approved": True, "findings": []}
            call.side_effect = reply
            result = self.s.batch(pid)

        task = self.s.store.task(pid, "REPAIR-001")
        self.assertEqual(result["integrated"], 1)
        self.assertEqual(task["state"], "integrated")
        self.assertEqual(task["attempt"], 4)
        self.assertTrue(task["verification_receipt"])
        self.assertTrue(all(check["passed"] for check in task["checks_result"]))

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

        # An amended candidate commit with a clean worktree and passing checks
        # evades the review-receipt comparison, the accumulated-check rerun and
        # the dirty-tree recheck; only the candidate-binding guard in
        # integrate() can catch it.
        pid2 = self.s.create(demo_spec(), demo=True)["project_id"]
        self.s.triage(pid2); self.s.run_one(pid2, "OPS-101"); self.s.review(pid2, "OPS-101")
        task2 = self.s.store.task(pid2, "OPS-101")
        health = Path(task2["candidate_dir"], "station/health.py")
        health.write_text(health.read_text() + "\n# amended after review\n")
        ws.git(task2["candidate_dir"], "add", "station/health.py")
        ws.git(task2["candidate_dir"], "commit", "--amend", "--no-edit")
        self.assertEqual(ws.git(task2["candidate_dir"], "status", "--porcelain"), "")
        self.assertNotEqual(ws.git(task2["candidate_dir"], "rev-parse", "HEAD"), task2["head_commit"])
        with self.assertRaises(ContractError):
            self.s.integrate(pid2, "OPS-101")

    def test_moving_base_invalidates_review(self):
        self.s.triage(self.pid)
        self.s.run_one(self.pid, "OPS-101"); self.s.run_one(self.pid, "OPS-102")
        self.s.review(self.pid, "OPS-101"); self.s.review(self.pid, "OPS-102")
        self.s.integrate(self.pid, "OPS-101")
        with self.assertRaises(ContractError):
            self.s.integrate(self.pid, "OPS-102")
        self.assertEqual(self.s.store.task(self.pid, "OPS-102")["state"], "repair_required")

        # A base that moved yet still permits a fast-forward merge evades the
        # non-ff merge failure and the review-receipt comparison; only the
        # stale-base guard in integrate() can catch it.
        pid2 = self.s.create(demo_spec(), demo=True)["project_id"]
        self.s.triage(pid2)
        self.s.run_one(pid2, "OPS-101"); self.s.review(pid2, "OPS-101")
        p2 = self.s.store.project(pid2)
        t2 = self.s.store.task(pid2, "OPS-101")
        ws.git(p2["repo"], "merge", "--ff-only", t2["head_commit"])
        self.assertNotEqual(ws.git(p2["repo"], "rev-parse", "HEAD"), t2["base_commit"])
        with self.assertRaises(ContractError):
            self.s.integrate(pid2, "OPS-101")
        self.assertEqual(self.s.store.task(pid2, "OPS-101")["state"], "repair_required")

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

    def test_receipt_kernel_v3_binding_and_discriminating_cases(self):
        """RECEIPT-KERNEL-V3: receipt validation binds to Station-supplied current
        kernel_revision; legacy v1/v2 receipts are readable but cannot establish
        current-kernel acceptance."""
        from residual.receipts import (
            RECEIPT_SCHEMA, V2_RECEIPT_SCHEMA, LEGACY_RECEIPT_SCHEMA,
            StationReceipt, ReceiptReference,
        )
        from residual.station.extensions import kernel_revision, _revision, _binding
        from residual.verifier import CheckResult
        from residual.core import digest, canonical

        # Build a fully integrated demo project so we have a real receipt to work with
        self.s.batch(self.pid)
        p = self.s.store.project(self.pid)
        task = p["tasks"][0]
        self.assertEqual(task["state"], "integrated")

        # The stored receipt must be v3 with a kernel_revision
        stored = task["verification_receipt"]
        receipt = StationReceipt.from_dict(stored["receipt"])
        self.assertEqual(receipt._schema_version, RECEIPT_SCHEMA)
        self.assertTrue(receipt.kernel_revision)
        self.assertRegex(receipt.kernel_revision, r"^[a-f0-9]{64}$")

        # Validate against current kernel — must pass
        from residual.station.extensions import validate_task_receipt
        validated, value = validate_task_receipt(self.s, p, task)
        self.assertEqual(validated.receipt_hash, receipt.receipt_hash)

        # --- Discriminating cases ---

        # 1. Legacy v1 receipt: readable via from_dict, rejected by validate_task_receipt
        #    Construct with valid dummy kernel_revision (required by v3 __post_init__),
        #    then set schema to v1 for payload serialization.
        v1_receipt_obj = StationReceipt(
            task["id"], receipt.cache_key, receipt.value_hash,
            receipt.verifier_name, receipt.verifier_revision,
            CheckResult.PASS, receipt.parent_receipts,
            engine_name=receipt.engine_name, engine_version=receipt.engine_version,
            kernel_revision="0" * 64,
        )
        object.__setattr__(v1_receipt_obj, "_schema_version", LEGACY_RECEIPT_SCHEMA)
        v1_envelope = v1_receipt_obj.to_dict()
        v1_receipt = StationReceipt.from_dict(v1_envelope)
        self.assertEqual(v1_receipt._schema_version, LEGACY_RECEIPT_SCHEMA)
        self.assertEqual(v1_receipt.engine_name, "unknown")
        # Now try to use it for current-kernel acceptance — must be rejected
        task_with_v1 = dict(task)
        task_with_v1["verification_receipt"] = {"receipt": v1_envelope, "value": stored["value"]}
        with self.assertRaises(ContractError) as ctx:
            validate_task_receipt(self.s, p, task_with_v1)
        self.assertIn("Legacy receipt schema", str(ctx.exception))

        # 2. Legacy v2 receipt: readable, rejected for current-kernel acceptance
        v2_receipt_obj = StationReceipt(
            task["id"], receipt.cache_key, receipt.value_hash,
            receipt.verifier_name, receipt.verifier_revision,
            CheckResult.PASS, receipt.parent_receipts,
            engine_name=receipt.engine_name, engine_version=receipt.engine_version,
            kernel_revision="0" * 64,
        )
        object.__setattr__(v2_receipt_obj, "_schema_version", V2_RECEIPT_SCHEMA)
        v2_envelope = v2_receipt_obj.to_dict()
        v2_receipt = StationReceipt.from_dict(v2_envelope)
        self.assertEqual(v2_receipt._schema_version, V2_RECEIPT_SCHEMA)
        task_with_v2 = dict(task)
        task_with_v2["verification_receipt"] = {"receipt": v2_envelope, "value": stored["value"]}
        with self.assertRaises(ContractError) as ctx:
            validate_task_receipt(self.s, p, task_with_v2)
        self.assertIn("Legacy receipt schema", str(ctx.exception))

        # 3. Empty kernel_revision on v3 receipt: must fail validation
        #    Construct with valid dummy, then clear it and force v3 schema
        empty_kernel_receipt = StationReceipt(
            receipt.task_id, receipt.cache_key, receipt.value_hash,
            receipt.verifier_name, receipt.verifier_revision,
            CheckResult.PASS, receipt.parent_receipts,
            engine_name=receipt.engine_name, engine_version=receipt.engine_version,
            kernel_revision="0" * 64,
        )
        object.__setattr__(empty_kernel_receipt, "kernel_revision", "")
        task_empty_kernel = dict(task)
        task_empty_kernel["verification_receipt"] = {
            "receipt": empty_kernel_receipt.to_dict(), "value": stored["value"],
        }
        with self.assertRaises(ContractError):
            validate_task_receipt(self.s, p, task_empty_kernel)

        # 4. Stale kernel_revision (simulating kernel update after receipt issuance):
        #    must fail validation
        stale_kernel = "a" * 64
        stale_receipt = StationReceipt(
            receipt.task_id, receipt.cache_key, receipt.value_hash,
            receipt.verifier_name, receipt.verifier_revision,
            CheckResult.PASS, receipt.parent_receipts,
            engine_name=receipt.engine_name, engine_version=receipt.engine_version,
            kernel_revision=stale_kernel,
        )
        task_stale = dict(task)
        task_stale["verification_receipt"] = {"receipt": stale_receipt.to_dict(), "value": stored["value"]}
        with self.assertRaises(ContractError):
            validate_task_receipt(self.s, p, task_stale)

        # 5. Mismatched kernel_revision (different from current): must fail
        mismatched_kernel = "b" * 64
        mismatched_receipt = StationReceipt(
            receipt.task_id, receipt.cache_key, receipt.value_hash,
            receipt.verifier_name, receipt.verifier_revision,
            CheckResult.PASS, receipt.parent_receipts,
            engine_name=receipt.engine_name, engine_version=receipt.engine_version,
            kernel_revision=mismatched_kernel,
        )
        task_mismatched = dict(task)
        task_mismatched["verification_receipt"] = {
            "receipt": mismatched_receipt.to_dict(), "value": stored["value"],
        }
        with self.assertRaises(ContractError):
            validate_task_receipt(self.s, p, task_mismatched)

        # 6. Valid v3 receipt with correct current kernel_revision: must pass
        #    (already proven above — the stored receipt is v3 and validates)

    def test_receipt_kernel_v3_station_supplies_not_caller(self):
        """RECEIPT-KERNEL-V3: the validator supplies kernel_revision from Station
        state, never trusting a revision carried by the receipt or caller."""
        from residual.station.extensions import kernel_revision
        # kernel_revision is computed from the live station state
        kr = kernel_revision(self.s, self.pid)
        self.assertRegex(kr, r"^[a-f0-9]{64}$")
        # It is deterministic for the same station state
        kr2 = kernel_revision(self.s, self.pid)
        self.assertEqual(kr, kr2)

    def test_receipt_kernel_v3_matches_rejects_legacy_for_kernel_check(self):
        """RECEIPT-KERNEL-V3: matches() with kernel_revision parameter returns
        False for legacy receipts even if all other fields match."""
        from residual.receipts import RECEIPT_SCHEMA, LEGACY_RECEIPT_SCHEMA, StationReceipt
        from residual.verifier import CheckResult
        from residual.core import digest

        # Build a v1 receipt (construct with valid dummy kernel_revision, then set v1 schema)
        test_value = {"x": 1}
        test_value_hash = digest(test_value)
        v1_receipt = StationReceipt(
            "T1", "a" * 64, test_value_hash,
            "station:integration", "c" * 64,
            CheckResult.PASS, (),
            engine_name="residual-station", engine_version="3.0.0",
            kernel_revision="0" * 64,
        )
        object.__setattr__(v1_receipt, "_schema_version", LEGACY_RECEIPT_SCHEMA)
        # matches() with kernel_revision must return False for v1
        self.assertFalse(v1_receipt.matches(
            value=test_value, cache_key="a" * 64,
            verifier_name="station:integration", verifier_revision="c" * 64,
            parents=(), kernel_revision="d" * 64,
        ))
        # matches() without kernel_revision (None) works for v1 (backward compat)
        self.assertTrue(v1_receipt.matches(
            value=test_value, cache_key="a" * 64,
            verifier_name="station:integration", verifier_revision="c" * 64,
            parents=(),
        ))

        # Build a v3 receipt with matching kernel_revision
        v3_receipt = StationReceipt(
            "T1", "a" * 64, test_value_hash,
            "station:integration", "c" * 64,
            CheckResult.PASS, (),
            engine_name="residual-station", engine_version="3.0.0",
            kernel_revision="d" * 64,
        )
        self.assertTrue(v3_receipt.matches(
            value=test_value, cache_key="a" * 64,
            verifier_name="station:integration", verifier_revision="c" * 64,
            parents=(), kernel_revision="d" * 64,
        ))
        # v3 with wrong kernel_revision must fail
        self.assertFalse(v3_receipt.matches(
            value=test_value, cache_key="a" * 64,
            verifier_name="station:integration", verifier_revision="c" * 64,
            parents=(), kernel_revision="e" * 64,
        ))

    def test_runtime_base_schema_is_upstream_copy(self):
        repo = Path(__file__).parents[2]
        self.assertEqual((repo / "vendor/ldd-kit/base.json").read_bytes(), (repo / "residual/station/schemas/ldd-base.json").read_bytes())

    def test_test_commands_require_project_permission(self):
        checks = [{"kind": "command", "argv": ["{python}", "-c", "print('ok')"]}]
        result = ws.run_checks(self.temp.name, checks, False)
        self.assertFalse(result[0]["passed"])

    def test_run_checks_preserves_systemdrive_in_subprocess_env(self):
        # Regression (QD-1): the check-subprocess env whitelist stripped SystemDrive,
        # so on Windows a child Python expanded %SystemDrive% literally and wrote
        # cache .db files into the candidate tree (dirty-tree ContractError).
        fake = {k: os.environ[k] for k in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP") if k in os.environ}
        fake["SystemDrive"] = "C:\\"  # mixed-case spelling must still be preserved
        # QD-2: the expansion probe must match platform semantics — POSIX
        # expandvars never expands %VAR%, so the original probe failed on every
        # Linux runner regardless of the fix. On POSIX prove functional
        # visibility via $SystemDrive instead; both forms fail when the
        # variable is stripped (predecessor behavior).
        probe_ref = "%SystemDrive%\\\\probe" if sys.platform == "win32" else "$SystemDrive/probe"
        probe = ("import os; ok = 'SYSTEMDRIVE' in {k.upper() for k in os.environ}; "
                 "p = os.path.expandvars(" + repr(probe_ref) + "); "
                 "unexpanded = p.startswith('%') or '$SystemDrive' in p; "
                 "print('PRESENT' if ok and not unexpanded else 'ABSENT:' + p)")
        checks = [{"kind": "command", "argv": ["{python}", "-c", probe]}]
        with patch.dict(os.environ, fake, clear=True):
            result = ws.run_checks(self.temp.name, checks, True)
        self.assertTrue(result[0]["passed"], result[0]["detail"])
        self.assertIn("PRESENT", result[0]["detail"])

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
            def reply(store, pid, role, packet, system, schema, placement, tid, *, extensions=None):
                self.assertIsNotNone(extensions)
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

    def test_remote_execution_evidence_is_attempt_bound_and_non_authoritative(self):
        pid = self.s.create(demo_spec(), demo=True)["project_id"]
        self.s.triage(pid)
        self.s.store.settings({"remote_workers_enabled": True})
        headers = {"Authorization": "Bearer " + self.s.store.settings()["worker_token"]}
        work = self.request("/api/worker/claim", {"project_id": pid, "task_id": "OPS-101", "name": "openclaw-bridge"}, headers)["work"]
        response = {"files": DEMO_FILES["OPS-101"]}
        evidence = {
            "schema": "residual.remote_execution_evidence.v1",
            "engine_name": "openclaw-control",
            "engine_version": "0.2.0",
            "host_version": "2026.6.1",
            "runtime_id": "oc-canary",
            "instance_id": "instance-1",
            "operation_id": "operation-1",
            "project_id": pid,
            "task_id": "OPS-101",
            "attempt": work["attempt"],
            "station_packet_sha256": sha(work["packet"]),
            "command_input_sha256": "1" * 64,
            "station_response_sha256": sha(response),
            "runtime_output_sha256": "2" * 64,
            "plugin_source_sha256": "3" * 64,
            "config_digest": "4" * 64,
            "evidence_tip_sha256": "5" * 64,
            "evidence_sequence": 7,
            "state": "COMPLETED",
            "acceptance": "NOT_EVALUATED",
            "qualification": "NOT_ESTABLISHED",
            "trust": "CONTROLLER_OBSERVED_RUNTIME_REPORTED",
        }
        submission = {
            "project_id": pid, "task_id": "OPS-101", "lease": work["lease"],
            "submission_id": "openclaw-evidence-1", "response": response,
            "execution_evidence": evidence,
        }
        try:
            result = self.request("/api/worker/result", submission, headers)
        except urllib.error.HTTPError as error:
            task_debug = self.s.store.task(pid, "OPS-101")
            events_debug = [event["event_type"] for event in self.s.store.events(pid)]
            self.fail(f"remote execution evidence submission failed HTTP {error.code}; state={task_debug['state']}; findings={task_debug.get('findings')}; artifact_kinds={[a.get('kind') for a in task_debug.get('artifacts', [])]}; events={events_debug}")
        self.assertEqual(result["state"], "review_ready")
        task = self.s.store.task(pid, "OPS-101")
        execution_artifacts = [item for item in task["artifacts"] if item["kind"] == "execution"]
        self.assertEqual(len(execution_artifacts), 1)
        _, stored = self.s.store.artifact(execution_artifacts[0]["id"])
        self.assertEqual(json.loads(stored), evidence)
        events = [event for event in self.s.store.events(pid) if event["event_type"] == "worker.execution"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["data"]["acceptance"], "NOT_EVALUATED")

        # A worker cannot turn runtime self-report into Station acceptance.
        # SECURITY: use a separate credential for the second project — #476's
        # credential-scoped model rejects cross-project credential reuse.
        pid2 = self.s.create(demo_spec(), demo=True)["project_id"]
        self.s.triage(pid2)
        # Issue a fresh credential via the server API (proper cid.secret format)
        cred2 = self.http.issue_worker_credential(rotate=True)
        headers2 = {"Authorization": "Bearer " + cred2}
        work2 = self.request("/api/worker/claim", {"project_id": pid2, "task_id": "OPS-101", "name": "openclaw-bridge"}, headers2)["work"]
        bad = {**evidence, "project_id": pid2, "attempt": work2["attempt"],
               "station_packet_sha256": sha(work2["packet"]), "acceptance": "ACCEPTED"}
        bad_submission = {
            "project_id": pid2, "task_id": "OPS-101", "lease": work2["lease"],
            "submission_id": "openclaw-evidence-bad", "response": response,
            "execution_evidence": bad,
        }
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/worker/result", bad_submission, headers2)
        self.assertEqual(error.exception.code, 400)
        self.assertEqual(self.s.store.task(pid2, "OPS-101")["state"], "repair_required")
        self.assertFalse(any(event["event_type"] == "worker.execution" for event in self.s.store.events(pid2)))

    def test_cross_project_credential_reuse_rejected(self):
        """#476 security constraint: a credential bound to project A cannot claim project B."""
        pid_a = self.s.create(demo_spec(), demo=True)["project_id"]
        self.s.triage(pid_a)
        pid_b = self.s.create(demo_spec(), demo=True)["project_id"]
        self.s.triage(pid_b)
        self.s.store.settings({"remote_workers_enabled": True})
        headers = {"Authorization": "Bearer " + self.s.store.settings()["worker_token"]}
        # Claim project A — credential binds to pid_a
        work_a = self.request("/api/worker/claim", {"project_id": pid_a, "task_id": "OPS-101", "name": "machine-a"}, headers)["work"]
        self.assertIsNotNone(work_a)
        # Attempt to claim project B with the same credential — must be rejected
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/worker/claim", {"project_id": pid_b, "task_id": "OPS-101", "name": "machine-a"}, headers)
        self.assertEqual(error.exception.code, 403)
    def test_failure_path_preserves_evidence_references(self):
        """#509 failure-path evidence references preserved: when finish() raises
        after evidence was recorded, the external_artifacts must survive into
        the failure_fields so the evidence chain is not lost."""
        pid = self.s.create(demo_spec(), demo=True)["project_id"]
        self.s.triage(pid)
        # Use a fresh credential (previous tests may have rotated)
        self.s.store.settings({"remote_workers_enabled": True})
        cred = self.http.issue_worker_credential(rotate=True)
        headers = {"Authorization": "Bearer " + cred}
        work = self.request("/api/worker/claim", {"project_id": pid, "task_id": "OPS-101", "name": "openclaw-bridge"}, headers)["work"]
        response = {"files": DEMO_FILES["OPS-101"]}
        evidence = {
            "schema": "residual.remote_execution_evidence.v1",
            "engine_name": "openclaw-control",
            "engine_version": "0.2.0",
            "host_version": "2026.6.1",
            "runtime_id": "oc-canary",
            "instance_id": "instance-1",
            "operation_id": "operation-1",
            "project_id": pid,
            "task_id": "OPS-101",
            "attempt": work["attempt"],
            "station_packet_sha256": sha(work["packet"]),
            "command_input_sha256": "1" * 64,
            "station_response_sha256": sha(response),
            "runtime_output_sha256": "2" * 64,
            "plugin_source_sha256": "3" * 64,
            "config_digest": "4" * 64,
            "evidence_tip_sha256": "5" * 64,
            "evidence_sequence": 7,
            "state": "COMPLETED",
            "acceptance": "NOT_EVALUATED",
            "qualification": "NOT_ESTABLISHED",
            "trust": "CONTROLLER_OBSERVED_RUNTIME_REPORTED",
        }
        # Submit with valid evidence but response that will fail checks
        # (writable file with a syntax error to trigger check failure)
        bad_response = {"files": {"station/health.py": "def status(services:\n    pass"}}
        bad_submission = {
            "project_id": pid, "task_id": "OPS-101", "lease": work["lease"],
            "submission_id": "openclaw-evidence-fail", "response": bad_response,
            "execution_evidence": evidence,
        }
        with self.assertRaises(urllib.error.HTTPError):
            self.request("/api/worker/result", bad_submission, headers)
        task = self.s.store.task(pid, "OPS-101")
        # Evidence artifact must be preserved in failure fields
        artifact_kinds = [a.get("kind") for a in task.get("artifacts", [])]
        self.assertIn("execution", artifact_kinds)


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
