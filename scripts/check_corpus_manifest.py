#!/usr/bin/env python3
"""Fail-closed checker for the consolidated R0-R5 corpus manifest.

Validates, against the repository's own residual.eval_frozen code (merged
PR #86), that the manifest at experiments/corpus/manifest.v1.json:

* has the expected schema and a self-consistent ``manifest_sha256``;
* binds per-item content hashes that match the recomputed FrozenTask
  payload digests (hash mismatch => fail);
* binds the frozen workload hash, name, seed and schema to the code;
* binds every R0-R5 arm id, label, layer stack and config hash;
* assigns every task to exactly one split with no development/held-out
  leakage, and no unknown or missing task ids;
* carries non-empty provenance for every item.

Exit 0 only when every check passes. Exit 2 on any violation. This script
makes no network or model calls and produces no experiment results.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA_VERSION = "residual.corpus-manifest.v1"
EXPECTED_SPLITS = ("development", "held_out")


class ManifestError(ValueError):
    """Any integrity, leakage, or provenance violation."""


def _fail(message: str) -> None:
    raise ManifestError(message)


def check_manifest(manifest_path: Path, root: Path) -> dict:
    if manifest_path.is_symlink() or not manifest_path.is_file():
        _fail("manifest must be a regular non-symlink file")
    try:
        manifest = json.loads(manifest_path.read_bytes())
    except (ValueError, UnicodeDecodeError):
        _fail("manifest is not valid UTF-8 JSON")
    if not isinstance(manifest, dict):
        _fail("manifest must be a JSON object")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        _fail("unsupported manifest schema_version")
    if manifest.get("status") != "frozen_preparation_no_results":
        _fail("manifest must not claim results or launch readiness")

    sys.path.insert(0, str(root))
    try:
        from residual.core import digest
        from residual.eval_frozen.configs import CONFIGURATIONS
        from residual.eval_frozen.workload import development_workload
    except ImportError as exc:  # fail closed if the harness is unavailable
        _fail(f"cannot import residual.eval_frozen: {exc}")

    # Self-hash: digest of the manifest without its own manifest_sha256.
    declared = manifest.get("manifest_sha256")
    body = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    if not isinstance(declared, str) or digest(body) != declared:
        _fail("manifest_sha256 mismatch")

    workload = development_workload()
    frozen = manifest.get("frozen_workload")
    if not isinstance(frozen, dict):
        _fail("missing frozen_workload binding")
    if frozen.get("workload_sha256") != workload.sha256:
        _fail("frozen workload hash mismatch")
    if frozen.get("workload_name") != workload.name:
        _fail("frozen workload name mismatch")
    if frozen.get("schema_version") != workload.schema_version:
        _fail("frozen workload schema mismatch")
    if frozen.get("seed") != workload.seed:
        _fail("frozen workload seed mismatch")

    arms = manifest.get("arms")
    if not isinstance(arms, list) or [a.get("config_id") for a in arms] != [
        c.config_id for c in CONFIGURATIONS
    ]:
        _fail("arms must enumerate R0-R5 exactly once, in order")
    for arm, config in zip(arms, CONFIGURATIONS):
        if arm.get("config_sha256") != config.sha256:
            _fail(f"arm {config.config_id} config hash mismatch")
        if arm.get("control_layers") != list(config.control_layers):
            _fail(f"arm {config.config_id} control-layer stack mismatch")

    items = manifest.get("items")
    if not isinstance(items, list) or not items:
        _fail("manifest requires a non-empty items list")
    code_tasks = {t.task_id: t for t in workload.tasks}
    seen: set[str] = set()
    split_of: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            _fail("manifest item must be an object")
        task_id = item.get("task_id")
        if task_id not in code_tasks:
            _fail(f"unknown task_id {task_id!r}")
        if task_id in seen:
            _fail(f"duplicate task_id {task_id!r}")
        seen.add(task_id)
        task = code_tasks[task_id]
        if item.get("content_sha256") != digest(task.payload()):
            _fail(f"content hash mismatch for {task_id}")
        expected_split = "held_out" if task.slice == "evaluation" else "development"
        if item.get("split") != expected_split:
            _fail(f"split mismatch for {task_id}: manifest disagrees with code")
        if item.get("family") != task.family:
            _fail(f"family mismatch for {task_id}")
        if item.get("fault_label") != task.fault_label:
            _fail(f"fault label mismatch for {task_id}")
        provenance = item.get("provenance")
        if not isinstance(provenance, dict) or not all(
            provenance.get(field) for field in ("authored_in", "introduced_by", "public_exposure")
        ):
            _fail(f"missing provenance for {task_id}")
        split_of[task_id] = item["split"]
    missing = set(code_tasks) - seen
    if missing:
        _fail(f"manifest omits tasks: {sorted(missing)}")

    # Split leakage: split tables must partition the item set exactly.
    splits = manifest.get("splits")
    if not isinstance(splits, dict) or set(splits) != set(EXPECTED_SPLITS):
        _fail("splits must be exactly development and held_out")
    assigned: dict[str, str] = {}
    for split_name, table in splits.items():
        ids = table.get("task_ids") if isinstance(table, dict) else None
        if not isinstance(ids, list) or not ids:
            _fail(f"split {split_name} requires a non-empty task_ids list")
        for task_id in ids:
            if task_id in assigned:
                _fail(f"split leakage: {task_id} in both {assigned[task_id]} and {split_name}")
            if task_id not in code_tasks:
                _fail(f"split {split_name} references unknown task {task_id!r}")
            if split_of[task_id] != split_name:
                _fail(f"split {split_name} assignment contradicts item split for {task_id}")
            assigned[task_id] = split_name
    if set(assigned) != set(code_tasks):
        _fail("splits do not cover every manifest item")

    if not isinstance(manifest.get("leakage_rule"), str) or not manifest["leakage_rule"]:
        _fail("missing leakage rule")
    if not isinstance(manifest.get("amendment_rule"), str) or not manifest["amendment_rule"]:
        _fail("missing amendment rule")
    return {
        "status": "PASS",
        "tasks": len(items),
        "development": len(splits["development"]["task_ids"]),
        "held_out": len(splits["held_out"]["task_ids"]),
        "workload_sha256": workload.sha256,
        "results_produced": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path,
                        default=Path("experiments/corpus/manifest.v1.json"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        report = check_manifest(args.manifest, args.root)
    except ManifestError as exc:
        print(f"corpus manifest REJECTED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
