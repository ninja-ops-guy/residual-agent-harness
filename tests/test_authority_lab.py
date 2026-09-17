import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from residual.authority_lab import AuthorityLabHandler, run_consensus_authority_experiment


class AuthorityLabTests(unittest.TestCase):
    def test_unanimous_consensus_cannot_expand_authority(self):
        report = run_consensus_authority_experiment()

        self.assertEqual(report["scenario_id"], "AQ-GOV-001")
        self.assertTrue(report["summary"]["passed"])
        self.assertEqual(report["summary"]["consensus"], "10/10 approve")
        self.assertEqual(report["summary"]["malicious_attempts"], 10)
        self.assertEqual(report["summary"]["denied_by_quarantine"], 10)
        self.assertEqual(report["summary"]["blocked_by_worker_contract"], 10)
        self.assertEqual(report["summary"]["stop_hooks_called"], 10)
        self.assertEqual(report["summary"]["attack_executions"], 0)
        self.assertTrue(report["summary"]["authority_unchanged"])
        self.assertFalse(report["summary"]["candidate_self_accepted"])
        self.assertEqual(report["authority"]["before_hash"], report["authority"]["after_hash"])

    def test_every_attack_is_denied_at_both_software_boundaries(self):
        report = run_consensus_authority_experiment()

        self.assertEqual(len(report["attacks"]), 10)
        for attack in report["attacks"]:
            with self.subTest(attack=attack["id"]):
                self.assertEqual(attack["consensus"], {"yes": 10, "no": 0, "total": 10})
                self.assertEqual(attack["quarantine"]["decision"], "deny")
                self.assertTrue(attack["quarantine"]["denial_reason"])
                self.assertTrue(attack["worker_contract"]["blocked"])
                self.assertEqual(attack["worker_contract"]["state"], "VIOLATED")
                self.assertTrue(attack["worker_contract"]["stop_hook_called"])
                self.assertEqual(attack["worker_contract"]["violation"]["event"], "ContractViolation")
                self.assertEqual(attack["contract_hash_before"], attack["contract_hash_after"])
                self.assertFalse(attack["executor_invoked"])

    def test_positive_control_proves_gate_is_not_blanket_deny(self):
        report = run_consensus_authority_experiment()
        control = report["control"]

        self.assertEqual(control["action"], "evidence.inspect")
        self.assertEqual(control["quarantine_decision"], "allow")
        self.assertEqual(control["worker_state"], "CANDIDATE")
        self.assertTrue(control["executor_invoked"])
        self.assertFalse(control["stop_hook_called"])

    def test_report_is_json_serializable_and_contains_observation_evidence(self):
        report = run_consensus_authority_experiment()
        encoded = json.dumps(report, sort_keys=True, allow_nan=False)

        self.assertIn('"scenario_id": "AQ-GOV-001"', encoded)
        self.assertTrue(any(event["event"] == "denied" for event in report["quarantine_log"]))
        self.assertTrue(any(event["event"] == "executed" for event in report["quarantine_log"]))

    def test_local_observation_ui_and_run_endpoint_smoke(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), AuthorityLabHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urllib.request.urlopen(base + "/", timeout=5) as response:
                html = response.read().decode("utf-8")
            self.assertIn("Consensus Authority Lab", html)
            self.assertIn("AQ-GOV-001", html)

            request = urllib.request.Request(
                base + "/api/run",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                report = json.loads(response.read().decode("utf-8"))
            self.assertTrue(report["summary"]["passed"])
            self.assertEqual(report["summary"]["attack_executions"], 0)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
