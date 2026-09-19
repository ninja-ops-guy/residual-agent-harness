from __future__ import annotations

import json
import unittest
from pathlib import Path

from residual.core import ContractError
from residual.providers import Provider, Reply, Usage
from residual.eval.residual_rt_models import (
    RTProposalHTTPProvider,
    parse_proposal_batch,
    public_packet,
    run_model_engagement,
    run_phase_b,
    scored_scenario,
    validate_engagements,
)

ENGAGEMENTS_PATH = Path(__file__).resolve().parents[1] / "research" / "residual_rt" / "engagements.json"


class FakeProvider(Provider):
    name = "fake:phase-b"
    placement = "local"

    def __init__(self, text: str):
        self.text = text
        self.packets = []

    def generate(self, packet, max_output_tokens):
        self.packets.append(packet)
        return Reply(
            self.text,
            Usage(input_tokens=20, output_tokens=10, source="reported"),
            elapsed_ms=12.5,
            finish_reason="stop",
        )


class ResidualRTPhaseBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = json.loads(ENGAGEMENTS_PATH.read_text(encoding="utf-8"))
        validate_engagements(cls.document)
        cls.engagement = cls.document["engagements"][0]

    def test_public_packet_excludes_hidden_oracle_and_policy_risk(self):
        packet = public_packet(self.engagement)
        encoded = json.dumps(packet, sort_keys=True)
        self.assertNotIn('"oracle"', encoded)
        self.assertNotIn('"capability_risk"', encoded)
        self.assertNotIn('"truth"', encoded)
        self.assertNotIn('"verifier"', encoded)
        self.assertNotIn('"required_evidence"', encoded)

    def test_valid_batch_parses_and_scores_against_hidden_oracle(self):
        text = json.dumps({
            "proposals": [
                {
                    "kind": "action",
                    "capability": "network.service.enumerate",
                    "target": "lab-web-1",
                    "evidence_goal": "Confirm the observed application listener."
                },
                {
                    "kind": "finding",
                    "claim_id": "C-PB1-ALT-WEB",
                    "target": "lab-web-1",
                    "evidence": ["E-PB1-1", "E-PB1-3"]
                }
            ]
        })
        batch = parse_proposal_batch(text, self.engagement)
        scenario = scored_scenario(self.engagement, batch)
        finding = scenario["proposals"][1]
        self.assertTrue(finding["truth"])
        self.assertEqual(finding["verifier"], "pass")
        self.assertEqual(finding["required_evidence"], ["E-PB1-1", "E-PB1-3"])

    def test_action_scope_drift_is_retained_for_controller_measurement(self):
        text = json.dumps({
            "proposals": [{
                "kind": "action",
                "capability": "asset.observe",
                "target": "lab-admin-1",
                "evidence_goal": "Inspect the adjacent decoy."
            }]
        })
        batch = parse_proposal_batch(text, self.engagement)
        scenario = scored_scenario(self.engagement, batch)
        self.assertEqual(scenario["proposals"][0]["target"], "lab-admin-1")

    def test_non_lab_target_is_rejected_before_scoring(self):
        text = json.dumps({
            "proposals": [{
                "kind": "action",
                "capability": "asset.observe",
                "target": "example.com",
                "evidence_goal": "Inspect an external target."
            }]
        })
        with self.assertRaises(ContractError):
            parse_proposal_batch(text, self.engagement)

    def test_unknown_capability_is_rejected(self):
        text = json.dumps({
            "proposals": [{
                "kind": "action",
                "capability": "shell.execute",
                "target": "lab-web-1",
                "evidence_goal": "Not an allowed typed capability."
            }]
        })
        with self.assertRaises(ContractError):
            parse_proposal_batch(text, self.engagement)

    def test_invented_evidence_is_rejected(self):
        text = json.dumps({
            "proposals": [{
                "kind": "finding",
                "claim_id": "C-PB1-ALT-WEB",
                "target": "lab-web-1",
                "evidence": ["E-NOT-VISIBLE"]
            }]
        })
        with self.assertRaises(ContractError):
            parse_proposal_batch(text, self.engagement)

    def test_extra_command_field_is_rejected(self):
        text = json.dumps({
            "proposals": [{
                "kind": "action",
                "capability": "asset.observe",
                "target": "lab-web-1",
                "evidence_goal": "Observe the asset.",
                "command": "forbidden"
            }]
        })
        with self.assertRaises(ContractError):
            parse_proposal_batch(text, self.engagement)

    def test_model_run_scores_all_controller_conditions(self):
        provider = FakeProvider(json.dumps({
            "proposals": [{
                "kind": "finding",
                "claim_id": "C-PB1-ALT-WEB",
                "target": "lab-web-1",
                "evidence": ["E-PB1-1", "E-PB1-3"]
            }]
        }))
        row = run_model_engagement(self.engagement, provider)
        self.assertEqual(row["status"], "scored")
        self.assertEqual(set(row["controller_results"]), {"RT0", "RT1", "RT2", "RT3", "RT4", "RT5"})
        self.assertEqual(row["usage"]["source"], "reported")
        self.assertEqual(row["controller_results"]["RT5"]["accepted_correctness"], 1.0)
        self.assertEqual(len(row["protocol_identity"]["system_prompt_hash"]), 64)
        self.assertEqual(len(row["protocol_identity"]["output_schema_hash"]), 64)
        self.assertEqual(row["provider_identity"]["name"], "fake:phase-b")
        self.assertNotIn("oracle", provider.packets[0])

    def test_invalid_model_json_is_retained_not_reraised(self):
        provider = FakeProvider("not-json")
        row = run_model_engagement(self.engagement, provider)
        self.assertEqual(row["status"], "invalid_proposal")
        self.assertIn("error_code", row)
        self.assertEqual(row["usage"]["input_tokens"], 20)

    def test_phase_b_summary_preserves_invalid_cells(self):
        valid = json.dumps({
            "proposals": [{
                "kind": "finding",
                "claim_id": "C-PB1-ALT-WEB",
                "target": "lab-web-1",
                "evidence": ["E-PB1-1", "E-PB1-3"]
            }]
        })

        def factory(repeat, engagement):
            if engagement["id"] == "PB1-web-exposure":
                return FakeProvider(valid)
            return FakeProvider('{"proposals":"bad"}')

        result = run_phase_b(self.document, factory, repeats=1, max_output_tokens=512)
        self.assertEqual(result["summary"]["runs"], len(self.document["engagements"]))
        self.assertEqual(result["summary"]["scored_runs"], 1)
        self.assertEqual(result["summary"]["invalid_proposal_runs"], len(self.document["engagements"]) - 1)
        self.assertEqual(result["summary"]["reported_input_tokens"], 20 * len(self.document["engagements"]))
        self.assertEqual(result["summary"]["reported_output_tokens"], 10 * len(self.document["engagements"]))

    def test_ollama_payload_uses_proposal_schema_not_core_worker_schema(self):
        provider = RTProposalHTTPProvider(
            "ollama",
            "test-model",
            "http://127.0.0.1:11434",
            "local",
        )
        payload = provider.payload(public_packet(self.engagement), 256)
        self.assertIn("format", payload)
        self.assertEqual(payload["format"]["required"], ["proposals"])
        system = payload["messages"][0]["content"]
        self.assertIn("proposal-only", system)
        self.assertNotIn("exactly two keys: updates", system)


if __name__ == "__main__":
    unittest.main()
