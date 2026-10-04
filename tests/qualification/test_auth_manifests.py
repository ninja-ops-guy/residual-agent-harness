"""Thin pytest wrapper over the attack-manifest qualification runner.

CI ergonomics only: the runner's receipt is the qualification evidence;
each pytest assertion below is a convenience mirror of it.

Manifests live in tests/qualification/auth_manifests/*.json (Track C).
With no manifests present this module collects zero tests.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from residual.qualification.auth_runner import run_single_manifest

MANIFEST_DIR = Path(__file__).parent / "auth_manifests"
MANIFESTS = sorted(MANIFEST_DIR.glob("*.json")) if MANIFEST_DIR.is_dir() else []


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("manifest_path", MANIFESTS, ids=lambda p: p.stem)
def test_auth_manifest(manifest_path, tmp_path):
    import os
    contract_id = os.environ.get("AUTH_QUAL_CONTRACT_ID")
    if not contract_id:
        pytest.skip("AUTH_QUAL_CONTRACT_ID not set — runner refuses to invent one")
    receipt = run_single_manifest(
        manifest_path, contract_id=contract_id,
        root=_repo_root(), out_dir=tmp_path / "out")
    assert receipt.result == "PASS", f"{receipt.attack_id}: {receipt.notes}"
