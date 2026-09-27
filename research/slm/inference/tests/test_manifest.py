"""Manifest schema tests: provenance fields and qualification label."""

import json
import os

from research.slm.inference.export.export import (
    build_model_from_config,
    export_model,
)
from research.slm.inference.export.manifest import (
    QUALIFICATION_TEST_ARTIFACT,
    sha256_file,
)

TINY_CONFIG = os.path.join(os.path.dirname(__file__), "tiny-config.yaml")


def test_manifest_schema_fields(tmp_path):
    model, raw = build_model_from_config(TINY_CONFIG, seed=7)
    manifest_path = export_model(
        model=model,
        source_config=raw.get("model") or raw,
        training_config=None,
        dtype="fp32",
        output_dir=str(tmp_path),
        code_commit="abc123",
        seed=7,
        model_card_name="tiny-test",
    )
    with open(manifest_path, "r", encoding="utf-8") as fh:
        m = json.load(fh)

    # Schema-on-branch provenance fields.
    for key in (
        "schema_version",
        "backend",
        "artifacts",
        "model_hash",
        "tokenizer_hash",
        "dataset_manifest_hash",
        "source_config",
        "training_config",
        "code_commit",
        "seed",
        "qualification_receipt",
        "model_card",
    ):
        assert key in m, f"missing manifest field {key}"

    assert m["model_hash"] == sha256_file(os.path.join(str(tmp_path), "model.bin"))
    assert m["model_hash"].startswith("sha256:")
    assert m["code_commit"] == "abc123"
    assert m["seed"] == 7
    assert m["qualification_receipt"]["qualification"] == (
        QUALIFICATION_TEST_ARTIFACT
    )
    assert m["model_card"]["name"] == "tiny-test"
    assert m["model_card"]["architecture"].startswith("NanoLM")
    # No tokenizer/dataset artifacts exist pre-freeze.
    assert m["tokenizer_hash"] is None
    assert m["dataset_manifest_hash"] is None


def test_tokenizer_hash_recorded(tmp_path):
    model, raw = build_model_from_config(TINY_CONFIG, seed=7)
    tok = tmp_path / "tokenizer.json"
    tok.write_text("{}", encoding="utf-8")
    manifest_path = export_model(
        model=model,
        source_config=raw.get("model") or raw,
        training_config=None,
        dtype="fp32",
        output_dir=str(tmp_path),
        code_commit="abc123",
        seed=7,
        tokenizer_file=str(tok),
    )
    with open(manifest_path, "r", encoding="utf-8") as fh:
        m = json.load(fh)
    assert m["tokenizer_hash"] == sha256_file(str(tok))
