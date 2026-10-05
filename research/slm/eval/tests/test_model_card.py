"""Tests for model_card.py (toy data only)."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import model_card

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "model-card-template.md",
)


def valid_card():
    return model_card.ModelCard(
        model_name="StationLM-150M-toy",
        model_artifact_digest="sha256:" + "ab" * 32,
        intended_use="Advisory decision proposals under Station authority.",
        training_data_classes=["frozen Control Bench train split records"],
        known_limitations=["toy card; no evaluation performed"],
        benchmark_version="control-bench-v0",
        qualification_status="candidate",
        deployment_constraints=["advisory only", "fail-closed Station"],
        quantization="INT8",
        hardware_class="CPU-only test node",
    )


class TestModelCard(unittest.TestCase):
    def test_valid_card_passes(self):
        self.assertEqual(valid_card().validate(), [])

    def test_missing_required_field(self):
        card = valid_card()
        card.model_name = ""
        self.assertTrue(any("model_name" in p for p in card.validate()))

    def test_bad_status_rejected(self):
        card = valid_card()
        card.qualification_status = "shipped"
        self.assertTrue(card.validate())

    def test_staged_requires_quant_and_hardware(self):
        card = valid_card()
        card.qualification_status = "staged"
        card.quantization = ""
        self.assertTrue(any("quantization" in p for p in card.validate()))

    def test_unknown_metadata_field(self):
        with self.assertRaises(ValueError):
            model_card.ModelCard.from_dict({"surprise": 1})

    def test_render_fills_all_placeholders(self):
        with open(TEMPLATE_PATH, encoding="utf-8") as fh:
            template = fh.read()
        rendered = valid_card().render(template)
        self.assertNotIn("{{", rendered)
        self.assertIn("StationLM-150M-toy", rendered)
        self.assertIn("candidate", rendered)

    def test_render_detects_unfilled(self):
        with self.assertRaises(ValueError):
            valid_card().render("status: {{qualification_status}} {{nope}}")

    def test_cli_init_validate_render(self):
        with tempfile.TemporaryDirectory() as td:
            meta = os.path.join(td, "card.json")
            self.assertEqual(model_card.main(["init", "--output", meta]), 0)
            # blank card is invalid
            self.assertEqual(
                model_card.main(["validate", "--metadata", meta]), 1)
            from dataclasses import asdict
            with open(meta, "w", encoding="utf-8") as fh:
                json.dump(asdict(valid_card()), fh)
            self.assertEqual(
                model_card.main(["validate", "--metadata", meta]), 0)
            self.assertEqual(
                model_card.main(["render", "--metadata", meta,
                                 "--template", TEMPLATE_PATH]), 0)

    def test_cli_help(self):
        with self.assertRaises(SystemExit) as ctx:
            model_card.main(["--help"])
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
