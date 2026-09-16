from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "qualification_mutation_canary.py"


def load_module():
    name = "qualification_mutation_canary_testload"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
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
