"""Tests for Tracks 2-8: TUI, Trajectory, Memory, HITL, NetOps, SecOps, Mesh."""
import os
import tempfile
import unittest

from residual.tui import DashboardState, ObservationCollector, StationTUI
from residual.trajectory import (
    Trajectory, TrajectoryRecorder, TrajectoryRegressionEngine, TrajectoryStep,
)
from residual.memory import EpistemicMemoryStore, MemoryEntry
from residual.hitl import HITLChallenge, HITLEscalationGateway, HITLStatus
from residual.modules.netops import NetOpsModule, TelemetryAnomalyBrake, TopologyDriftBrake
from residual.modules.secops import SecOpsModule, SecretExposureBrake, VulnerabilityDeltaBrake
from residual.mesh import MeshChat, MeshIdentity, MeshMessage, MeshMessageKind, MeshNode
from residual.verifier import CheckResult


class TestTUI(unittest.TestCase):
    def test_collector_updates_on_events(self):
        c = ObservationCollector()
        c.on_event("checkpoint", {"event": "run_opened", "run_id": "r1", "token_budget": 1000})
        self.assertEqual(c.state.run_id, "r1")
        self.assertEqual(c.state.token_budget, 1000)
        c.on_event("state.transition", {"to_state": "pass_running", "pass_number": 1})
        self.assertEqual(c.state.pass_number, 1)
        c.on_event("llm.response", {"usage": {"total_tokens": 250}})
        self.assertEqual(c.state.tokens_used, 250)

    def test_collector_brake_tracking(self):
        c = ObservationCollector()
        c.on_event("state.transition", {"to_state": "brake_tripped", "brake_name": "budget"})
        self.assertEqual(c.state.brake_states["budget"], "TRIPPED")

    def test_tui_start_stop(self):
        c = ObservationCollector()
        tui = StationTUI(c, refresh_hz=10)
        tui.start()
        tui.stop()  # must not raise

    def test_tui_invalid_refresh(self):
        with self.assertRaises(Exception):
            StationTUI(ObservationCollector(), refresh_hz=0)


class TestTrajectory(unittest.TestCase):
    def test_record_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            rec = TrajectoryRecorder(d)
            steps = [TrajectoryStep(1, "search", "fp1", "pass", 100.0)]
            traj = rec.record("gs_hash", steps, ["budget"], "success")
            self.assertEqual(len(traj.trajectory_hash), 64)
            loaded = rec.load(traj.trajectory_hash)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["outcome"], "success")

    def test_regression_passes_on_match(self):
        with tempfile.TemporaryDirectory() as d:
            rec = TrajectoryRecorder(d)
            steps = [TrajectoryStep(1, "search", "fp1", "pass")]
            golden = rec.record("gs_hash", steps, [], "success")
            engine = TrajectoryRegressionEngine(rec)
            current = Trajectory(
                trajectory_hash="x", goal_spec_hash="gs_hash",
                steps=steps, brake_trips=(), outcome="success", recorded_at_ns=0,
            )
            passed, reason = engine.evaluate_regression(current, golden.trajectory_hash)
            self.assertTrue(passed)

    def test_regression_fails_on_tool_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            rec = TrajectoryRecorder(d)
            golden = rec.record("gs_hash", [TrajectoryStep(1, "search", "fp1", "pass")], [], "success")
            engine = TrajectoryRegressionEngine(rec)
            current = Trajectory(
                trajectory_hash="x", goal_spec_hash="gs_hash",
                steps=[TrajectoryStep(1, "fetch", "fp2", "pass")],
                brake_trips=(), outcome="success", recorded_at_ns=0,
            )
            passed, _ = engine.evaluate_regression(current, golden.trajectory_hash)
            self.assertFalse(passed)

    def test_regression_fails_on_outcome_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            rec = TrajectoryRecorder(d)
            steps = [TrajectoryStep(1, "search", "fp1", "pass")]
            golden = rec.record("gs_hash", steps, [], "success")
            engine = TrajectoryRegressionEngine(rec)
            current = Trajectory(
                trajectory_hash="x", goal_spec_hash="gs_hash",
                steps=steps, brake_trips=(), outcome="aborted", recorded_at_ns=0,
            )
            passed, _ = engine.evaluate_regression(current, golden.trajectory_hash)
            self.assertFalse(passed)


class TestMemory(unittest.TestCase):
    def test_index_and_retrieve(self):
        with tempfile.TemporaryDirectory() as d:
            store = EpistemicMemoryStore(d)
            entry = store.index("fix BGP flap", "a" * 64, {"config": "ok"}, "v1.0.0")
            self.assertEqual(len(entry.key), 64)
            retrieved = store.retrieve("fix BGP flap")
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.receipt_hash, "a" * 64)

    def test_retrieve_missing(self):
        with tempfile.TemporaryDirectory() as d:
            store = EpistemicMemoryStore(d)
            self.assertIsNone(store.retrieve("nonexistent goal"))

    def test_validate_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            store = EpistemicMemoryStore(d)
            entry = store.index("goal", "b" * 64, {}, "v1")
            self.assertTrue(store.validate_receipt(entry, "b" * 64))
            self.assertFalse(store.validate_receipt(entry, "c" * 64))


class TestHITL(unittest.TestCase):
    def _gateway(self, tmpdir):
        return HITLEscalationGateway(b"test_key_32_bytes_long___________", tmpdir, validity_window_s=60, authenticate=lambda challenge, response, role: response == "authenticated-operator-response")

    def test_generate_and_verify(self):
        with tempfile.TemporaryDirectory() as d:
            gw = self._gateway(d)
            from residual import AmendmentRule, CheckType, GoalSpec, SuccessCriterion
            spec = GoalSpec(
                goal_id="g1", objective="test",
                success_criteria=(SuccessCriterion("c1", CheckType.MECHANICAL, "d", "e"),),
                max_passes=5, token_budget=1000, wall_clock_budget_s=60.0,
                amendment_rule=AmendmentRule(authorized_roles=("operator",)),
            )
            challenge = gw.generate_challenge("task1", {"action": "restart"}, "borderline", spec)
            self.assertEqual(len(challenge.challenge_id), 36)
            # Verify approval
            status = gw.verify_approval(
                challenge.challenge_id, "authenticated-operator-response", "operator", ("operator",),
            )
            self.assertEqual(status, HITLStatus.APPROVED)

    def test_verify_wrong_role(self):
        with tempfile.TemporaryDirectory() as d:
            gw = self._gateway(d)
            from residual import AmendmentRule, CheckType, GoalSpec, SuccessCriterion
            spec = GoalSpec(
                goal_id="g1", objective="test",
                success_criteria=(SuccessCriterion("c1", CheckType.MECHANICAL, "d", "e"),),
                max_passes=5, token_budget=1000, wall_clock_budget_s=60.0,
                amendment_rule=AmendmentRule(authorized_roles=("operator",)),
            )
            challenge = gw.generate_challenge("t", {}, "reason", spec)
            status = gw.verify_approval(
                challenge.challenge_id, challenge.signature, "intruder", ("operator",),
            )
            self.assertEqual(status, HITLStatus.DENIED)

    def test_challenge_durability(self):
        with tempfile.TemporaryDirectory() as d:
            gw = self._gateway(d)
            from residual import AmendmentRule, CheckType, GoalSpec, SuccessCriterion
            spec = GoalSpec(
                goal_id="g1", objective="test",
                success_criteria=(SuccessCriterion("c1", CheckType.MECHANICAL, "d", "e"),),
                max_passes=5, token_budget=1000, wall_clock_budget_s=60.0,
                amendment_rule=AmendmentRule(authorized_roles=("operator",)),
            )
            challenge = gw.generate_challenge("t", {}, "r", spec)
            loaded = gw.get_challenge(challenge.challenge_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["status"], "pending")


class FakeTelemetry:
    def __init__(self, metrics):
        self._metrics = metrics
    def get_current_metrics(self):
        return dict(self._metrics)


class TestNetOps(unittest.TestCase):
    def test_maintenance_window_policy(self):
        tel = FakeTelemetry({"packet_loss_pct": 0.1})
        mod = NetOpsModule(tel, {"packet_loss_pct": 2.0},
                           maintenance_window_validator=lambda r: r == "VALID-123")
        from residual.quarantine import ProposedAction
        # Core without receipt → deny
        action = ProposedAction(action_type="config_change", name="bgp_update",
                                arguments={"tier": "core"})
        policy = mod.quarantine_policies()[0]
        self.assertIsNotNone(policy(action))
        # Core with valid receipt → allow
        action2 = ProposedAction(action_type="config_change", name="bgp_update",
                                 arguments={"tier": "core", "maintenance_receipt": "VALID-123"})
        self.assertIsNone(policy(action2))

    def test_maintenance_window_invalid_receipt(self):
        tel = FakeTelemetry({})
        mod = NetOpsModule(tel, {}, maintenance_window_validator=lambda r: False)
        from residual.quarantine import ProposedAction
        action = ProposedAction(action_type="config_change", name="x",
                                arguments={"tier": "core", "maintenance_receipt": "FAKE"})
        policy = mod.quarantine_policies()[0]
        self.assertIsNotNone(policy(action))

    def test_telemetry_stabilization_pass(self):
        tel = FakeTelemetry({"packet_loss_pct": 0.1})
        mod = NetOpsModule(tel, {"packet_loss_pct": 2.0})
        verifier = mod.verifiers()["telemetry_stabilization"][1]
        result, reason = verifier({}, {"evaluation_window_sec": 0, "poll_interval_sec": 0})
        self.assertEqual(result, CheckResult.PASS)

    def test_telemetry_stabilization_fail(self):
        tel = FakeTelemetry({"packet_loss_pct": 5.0})
        mod = NetOpsModule(tel, {"packet_loss_pct": 2.0})
        verifier = mod.verifiers()["telemetry_stabilization"][1]
        result, reason = verifier({}, {"evaluation_window_sec": 1, "poll_interval_sec": 0})
        self.assertEqual(result, CheckResult.FAIL)
        self.assertIn("packet_loss_pct", reason)

    def test_telemetry_stabilization_unknown(self):
        class BadTelemetry:
            def get_current_metrics(self):
                raise ConnectionError("unreachable")
        mod = NetOpsModule(BadTelemetry(), {"x": 1.0})
        verifier = mod.verifiers()["telemetry_stabilization"][1]
        result, _ = verifier({}, {"evaluation_window_sec": 1, "poll_interval_sec": 0})
        self.assertEqual(result, CheckResult.UNKNOWN)

    def test_config_syntax_valid(self):
        tel = FakeTelemetry({})
        mod = NetOpsModule(tel, {})
        verifier = mod.verifiers()["config_syntax_valid"][1]
        self.assertEqual(verifier({"config": "router bgp 65001 { neighbor 10.0.0.1; }"}, {})[0], CheckResult.PASS)
        self.assertEqual(verifier({"config": "router bgp 65001 { neighbor 10.0.0.1; "}, {})[0], CheckResult.FAIL)

    def test_telemetry_anomaly_brake(self):
        tel = FakeTelemetry({"packet_loss_pct": 5.0})  # 5.0 > 2.0 * 1.5 = 3.0
        brake = TelemetryAnomalyBrake(tel, {"packet_loss_pct": 2.0})
        trip = brake.update({})
        self.assertIsNotNone(trip)
        self.assertEqual(trip.recommended_action.value, "abort")

    def test_telemetry_anomaly_brake_no_trip(self):
        tel = FakeTelemetry({"packet_loss_pct": 2.5})  # 2.5 < 3.0
        brake = TelemetryAnomalyBrake(tel, {"packet_loss_pct": 2.0})
        self.assertIsNone(brake.update({}))

    def test_topology_drift_brake(self):
        tel = FakeTelemetry({"topology_hash": "abc123"})
        brake = TopologyDriftBrake(tel)
        # Set baseline
        brake.update({"kind": "checkpoint", "payload": {"event": "run_opened"}})
        # No drift
        self.assertIsNone(brake.update({"kind": "state.transition", "to_state": "pass_complete"}))
        # Drift
        tel._metrics["topology_hash"] = "xyz789"
        trip = brake.update({"kind": "state.transition", "to_state": "pass_complete"})
        self.assertIsNotNone(trip)
        self.assertEqual(trip.recommended_action.value, "escalate")

    def test_topology_drift_declared_change(self):
        tel = FakeTelemetry({"topology_hash": "abc"})
        brake = TopologyDriftBrake(tel)
        brake.update({"kind": "checkpoint", "payload": {"event": "run_opened"}})
        tel._metrics["topology_hash"] = "xyz"
        trip = brake.update({
            "kind": "state.transition", "to_state": "pass_complete",
            "payload": {"topology_change_declared": True},
        })
        self.assertIsNone(trip)


class TestSecOps(unittest.TestCase):
    def _mod(self):
        return SecOpsModule(
            prohibited_patterns=[r"BEGIN PRIVATE KEY", r"api_secret\s*="],
            allowed_licenses=["MIT", "Apache-2.0"],
        )

    def test_secret_exfiltration_policy(self):
        mod = self._mod()
        from residual.quarantine import ProposedAction
        policy = mod.quarantine_policies()[0]
        action = ProposedAction(action_type="file_write", name="config",
                                arguments={"content": "-----BEGIN PRIVATE KEY-----"})
        self.assertIsNotNone(policy(action))

    def test_secret_exfiltration_nested(self):
        mod = self._mod()
        from residual.quarantine import ProposedAction
        policy = mod.quarantine_policies()[0]
        action = ProposedAction(action_type="provider_call", name="upload",
                                arguments={"data": {"nested": {"key": "api_secret = 'abc123'"}}})
        self.assertIsNotNone(policy(action))

    def test_secret_exfiltration_clean(self):
        mod = self._mod()
        from residual.quarantine import ProposedAction
        policy = mod.quarantine_policies()[0]
        action = ProposedAction(action_type="file_write", name="readme",
                                arguments={"content": "hello world"})
        self.assertIsNone(policy(action))

    def test_dependency_disclosure_policy(self):
        mod = self._mod()
        from residual.quarantine import ProposedAction
        policy = mod.quarantine_policies()[1]
        action = ProposedAction(action_type="provider_call", name="upload",
                                arguments={"payload": {"dependencies": {"flask": "2.0"}}})
        self.assertIsNotNone(policy(action))

    def test_sast_scan_detects_key(self):
        mod = self._mod()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("-----BEGIN PRIVATE KEY-----\nMII...\n")
            path = f.name
        try:
            result, reason = mod.verifiers()["sast_scan"][1]({"modified_files": [path]}, {})
            self.assertEqual(result, CheckResult.FAIL)
            self.assertIn("private key", reason)
        finally:
            os.unlink(path)

    def test_sast_scan_clean(self):
        mod = self._mod()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def hello(): return 'world'\n")
            path = f.name
        try:
            result, _ = mod.verifiers()["sast_scan"][1]({"modified_files": [path]}, {})
            self.assertEqual(result, CheckResult.PASS)
        finally:
            os.unlink(path)

    def test_sast_no_files(self):
        mod = self._mod()
        result, reason = mod.verifiers()["sast_scan"][1]({}, {})
        self.assertEqual(result, CheckResult.UNKNOWN)

    def test_sbom_check(self):
        mod = self._mod()
        manifest = {"flask": {"license": "MIT"}, "requests": {"license": "Apache-2.0"}}
        result, _ = mod.verifiers()["sbom_check"][1]({"dependencies": manifest}, {})
        self.assertEqual(result, CheckResult.PASS)

    def test_sbom_check_violation(self):
        mod = self._mod()
        manifest = {"flask": {"license": "MIT"}, "gpl_lib": {"license": "GPL-3.0"}}
        result, reason = mod.verifiers()["sbom_check"][1]({"dependencies": manifest}, {})
        self.assertEqual(result, CheckResult.FAIL)
        self.assertIn("GPL-3.0", reason)

    def test_policy_as_code_unknown(self):
        mod = self._mod()
        result, reason = mod.verifiers()["policy_as_code_eval"][1]({"config": {}}, {})
        self.assertEqual(result, CheckResult.UNKNOWN)
        self.assertEqual(reason, "policy_engine_unavailable")

    def test_vulnerability_delta_brake(self):
        brake = VulnerabilityDeltaBrake()
        self.assertIsNone(brake.update({"payload": {"vulnerability_count": 5}}))
        trip = brake.update({"payload": {"vulnerability_count": 8}})
        self.assertIsNotNone(trip)
        self.assertEqual(trip.recommended_action.value, "escalate")

    def test_vulnerability_delta_no_regression(self):
        brake = VulnerabilityDeltaBrake()
        brake.update({"payload": {"vulnerability_count": 10}})
        self.assertIsNone(brake.update({"payload": {"vulnerability_count": 10}}))
        self.assertIsNone(brake.update({"payload": {"vulnerability_count": 8}}))

    def test_secret_exposure_brake(self):
        import re
        brake = SecretExposureBrake([re.compile(r"BEGIN PRIVATE KEY")])
        trip = brake.update({"payload": {"output": "found: BEGIN PRIVATE KEY"}})
        self.assertIsNotNone(trip)
        self.assertEqual(trip.recommended_action.value, "abort")

    def test_secret_exposure_brake_clean(self):
        import re
        brake = SecretExposureBrake([re.compile(r"BEGIN PRIVATE KEY")])
        self.assertIsNone(brake.update({"payload": {"output": "clean"}}))


class TestMesh(unittest.TestCase):
    def _identity(self, name):
        return MeshIdentity(
            device_id=f"dev-{name}", display_name=name,
            public_key="pk_" + name, capabilities=("llama3",), address=f"10.0.0.{name}",
            joined_at_ns=0,
        )

    def _node(self, name):
        idd = self._identity(name)
        return MeshNode(
            identity=idd,
            sign_fn=lambda data: "sig_" + data[:20].hex(),
            verify_fn=lambda pk, data, sig: sig.startswith("sig_"),
        )

    def test_chat_chain(self):
        node = self._node("a")
        node.send_message(MeshMessageKind.CHAT, content="hello")
        node.send_message(MeshMessageKind.CHAT, content="world")
        self.assertTrue(node.chat.verify())
        self.assertEqual(len(node.chat.messages), 2)

    def test_message_signing(self):
        node = self._node("a")
        msg = node.send_message(MeshMessageKind.CHAT, content="test")
        self.assertTrue(msg.signature.startswith("sig_"))

    def test_receive_valid_message(self):
        node_a = self._node("a")
        node_b = self._node("b")
        node_b.connect_peer(node_a.identity)
        msg = node_a.send_message(MeshMessageKind.CHAT, content="hi from a")
        self.assertTrue(node_b.receive_message(msg))

    def test_receive_rejects_bad_signature(self):
        node_a = self._node("a")
        node_b = self._node("b")
        node_b.connect_peer(node_a.identity)
        msg = node_a.send_message(MeshMessageKind.CHAT, content="hi")
        # Tamper with signature
        bad_msg = MeshMessage(
            message_id=msg.message_id, author_id=msg.author_id,
            timestamp_ns=msg.timestamp_ns, kind=msg.kind, content=msg.content,
            payload=msg.payload, signature="bad_sig", prev_hash=msg.prev_hash,
        )
        self.assertFalse(node_b.receive_message(bad_msg))

    def test_revoked_device_rejected(self):
        node_a = self._node("a")
        node_b = self._node("b")
        node_b.connect_peer(node_a.identity)
        node_b.revoke_device("dev-a", "sig_revoke")
        msg = node_a.send_message(MeshMessageKind.CHAT, content="hi")
        self.assertFalse(node_b.receive_message(msg))

    def test_task_proposal(self):
        node = self._node("a")
        msg = node.propose_task({"goal_id": "g1", "objective": "fix network"})
        self.assertEqual(msg.kind, MeshMessageKind.TASK_PROPOSAL)
        self.assertIn("goal_spec_hash", msg.payload)

    def test_model_offer(self):
        node = self._node("a")
        msg = node.offer_model("task-1", "llama3.3", 0.95, load_time_s=5.0)
        self.assertEqual(msg.kind, MeshMessageKind.MODEL_OFFER)
        self.assertEqual(msg.payload["model_name"], "llama3.3")
        self.assertEqual(msg.payload["capability_score"], 0.95)

    def test_broadcast_result(self):
        node = self._node("a")
        msg = node.broadcast_result("task-1", "config applied", "abc123", "v1.0.0", "success")
        self.assertEqual(msg.kind, MeshMessageKind.TASK_RESULT)
        self.assertEqual(msg.payload["receipt_hash"], "abc123")

    def test_dispute_result(self):
        node = self._node("a")
        msg = node.dispute_result("task-1", "receipt verification failed", "expected_hash")
        self.assertEqual(msg.kind, MeshMessageKind.TASK_RESULT_DISPUTE)
        self.assertEqual(msg.payload["reason"], "receipt verification failed")


if __name__ == "__main__":
    unittest.main()
