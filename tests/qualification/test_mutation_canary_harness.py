from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "qualification_mutation_canary.py"


def load_module():
    spec = importlib.util.spec_from_file_location("qualification_mutation_canary", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_mutation_selector_identifies_exactly_one_semantic_site():
    module = load_module()
    assert module.validate_mutation_sites(root=ROOT) == []
    assert len(module.MUTATIONS) >= 4
    assert {m.name for m in module.MUTATIONS} >= {
        "revoked-candidate-acceptance",
        "candidate-lease-resurrection",
        "git-path-policy-bypass",
        "forbidden-prefix-bypass",
    }
