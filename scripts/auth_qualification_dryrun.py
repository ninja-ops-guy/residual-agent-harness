#!/usr/bin/env python3
"""Dry-run readiness gate for the AUTH qualification runner (Track B2, §10.6).

Runs the runner skeleton against the real repo with stub-registry entries
for three known rejection paths. Expected outcome TODAY (pre-Track-A):
every negative attack FAILs with "rejected without a typed failure code"
and every receipt FAILs with "kernel_revision unbound" — which PROVES the
runner detects the missing emission layer rather than silently passing.
A dry run that passed today would be evidence of a broken runner.

Manifests are pinned to the current HEAD/TREE at generation time.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from residual.core import canonical
from residual.qualification.auth_runner import capture_candidate, run

STUBS = [
    # (attack_id, invariant_id, expected_code, expected_state, attack_input)
    ("AUTH-AMB-005-N01", "INV-AUTH-AMB-005",
     "AMBIGUOUS_ACCEPTANCE_CONDITION", "NO_IMPLICIT_DEFAULT",
     {"action_type": "not_a_real_action_type", "name": "x"}),
    ("AUTH-AUT-006-N01", "INV-AUTH-AUT-006",
     "UNAPPROVED_ACTION", "NO_EXECUTION",
     {"name": "some_tool"}),
    ("AUTH-EVD-001-N01", "INV-AUTH-EVD-001",
     "UNBOUND_EVIDENCE_SOURCE", "NO_EXECUTION",
     {"task": "ghost_task"}),
]


def _manifest(attack_id, invariant_id, code, state, attack_input,
              head, tree, contract_id) -> dict:
    return {
        "schema": "residual.auth.manifest.v1",
        "attack_id": attack_id,
        "invariant_id": invariant_id,
        "kind": "negative",
        "target_head": head,
        "target_tree": tree,
        "target_contract_id": contract_id,
        "attack_input": attack_input,
        "attack_input_hash": hashlib.sha256(
            canonical(attack_input).encode("utf-8")).hexdigest(),
        "expected_fail_closed_state": state,
        "expected_failure_code": code,
        "description": f"dry-run stub {attack_id}",
    }


def main() -> int:
    from tests.qualification.auth_attacks import ATTACKS

    head, tree, dirty = capture_candidate(REPO_ROOT)
    if dirty:
        print("REFUSED: working tree not clean — "
              "commit or stash Track A2's edits, then re-run", file=sys.stderr)
        return 2
    contract_id = "d" * 64  # dry-run placeholder; the real runner takes --contract-id
    with tempfile.TemporaryDirectory(prefix="authq-dryrun-") as tmp:
        manifest_dir = Path(tmp) / "manifests"
        manifest_dir.mkdir()
        for stub in STUBS:
            (manifest_dir / f"{stub[0]}.json").write_text(
                json.dumps(_manifest(*stub, head, tree, contract_id),
                           indent=2, sort_keys=True) + "\n", encoding="utf-8")
        out_dir = Path(tmp) / "out"
        run_manifest = run(manifest_dir, contract_id=contract_id,
                           out_dir=out_dir, root=REPO_ROOT, registry=ATTACKS)

        print(f"candidate: {head[:12]}/{tree[:12]}")
        print(f"kernel_revision: {run_manifest['kernel_revision']}")
        for attack_id, result in run_manifest["results"].items():
            rp = out_dir / "receipts" / f"{attack_id}.json"
            notes = "; ".join(json.loads(rp.read_text(encoding="utf-8"))["notes"])
            print(f"  {attack_id}: {result} — {notes}")
        print(f"overall: {run_manifest['result']}")
        print(f"INV-AUTH-000: {run_manifest['derived_inv_auth_000']} (derived)")
        return 0 if run_manifest["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
