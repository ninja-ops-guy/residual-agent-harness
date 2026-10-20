#!/usr/bin/env python3
"""Offline seam-layer checker for the proposed MS-00..08 seam DAG.

Self-contained (stdlib-only) AST import scan. It expresses the same layering
as the import-linter contracts in `.importlinter` so the rules can be checked
locally and in CI without installing dependencies.

Exit 0: no violations. Exit 1: violations found (each printed as a finding).

This checker is ADVISORY tooling added by the G0 seam-graph PR. Wiring it into
CI (required-status) is a maintainer step; see docs/architecture/SEAM-DAG.md.

Layer order (low -> high; a layer may import only from layers at or below
itself, plus the shared kernel):

    MS-00  durable ledger core        residual.factory.runtime_journal, residual.dsm.journal
    MS-08  admission & fencing        residual.dsm.* (except journal)
    MS-02  resolution & registry      ai_providers.*, residual.extensions
    MS-01  lifecycle orchestration    residual.station.*, residual.factory.runtime,
                                      residual.factory.worker_contract

Shared kernel (importable by every layer, may import none of the layers):
residual.core, observation_layer.*, stdlib/third-party.

Protected modules (Factory/M4, verifier/receipt authority) are flagged as
FINDINGS when imported from a seam layer, per the exclusion boundary.
"""
from __future__ import annotations

import ast
import fnmatch
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

# --- layer membership (module prefixes) --------------------------------------
LAYERS = {
    "MS-00": ["residual.factory.runtime_journal", "residual.dsm.journal"],
    "MS-08": ["residual.dsm"],  # journal excluded by MS-00 precedence below
    "MS-02": ["ai_providers", "residual.extensions"],
    "MS-01": ["residual.station", "residual.factory.runtime", "residual.factory.worker_contract"],
}
ORDER = {"MS-00": 0, "MS-08": 1, "MS-02": 1, "MS-01": 2}  # MS-08 and MS-02 are parallel
KERNEL = ["residual.core", "residual"]
PROTECTED = ["residual.factory.m4_", "residual.verifier", "verifier"]


def layer_of(mod: str):
    # most specific match wins (runtime_journal before factory.runtime)
    best, blen = None, -1
    for layer, prefixes in LAYERS.items():
        for p in prefixes:
            if mod == p or mod.startswith(p + "."):
                if len(p) > blen:
                    best, blen = layer, len(p)
    return best


def is_kernel(mod: str) -> bool:
    return mod == "residual.core" or mod == "residual" or mod.startswith("observation_layer")


def protected_hit(mod: str) -> str | None:
    for p in PROTECTED:
        if mod.startswith(p):
            return mod
    return None


def module_name(path: pathlib.Path) -> str:
    rel = path.relative_to(REPO).with_suffix("")
    return ".".join(rel.parts)


def imports_of(path: pathlib.Path) -> list[str]:
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)  # third-party file quirks
        tree = ast.parse(path.read_text(encoding="utf-8"))
    mods: list[str] = []
    pkg = module_name(path).rsplit(".", 1)[0]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative -> resolve against package
                base = pkg.split(".")[: len(pkg.split(".")) - (node.level - 1)]
                mods.append(".".join(base + ([node.module] if node.module else [])))
            elif node.module:
                mods.append(node.module)
    return mods


def main() -> int:
    violations, findings = [], set()
    for path in sorted(REPO.rglob("*.py")):
        if any(part in {".git", "vendor", "node_modules"} for part in path.parts):
            continue
        src_mod = module_name(path)
        src_layer = layer_of(src_mod)
        src_kernel = is_kernel(src_mod)
        for imp in imports_of(path):
            dst_layer = layer_of(imp)
            if src_kernel and dst_layer:
                findings.add(f"KERNEL-IMPORT   {src_mod} (kernel) imports {imp} ({dst_layer})")
                continue
            hit = protected_hit(imp)
            if hit and src_layer:
                findings.add(f"PROTECTED-IMPORT  {src_mod} ({src_layer}) imports {hit}")
            if src_layer is None or dst_layer is None or dst_layer == src_layer:
                continue
            if ORDER[dst_layer] > ORDER[src_layer]:
                violations.append(
                    f"LAYER-VIOLATION {src_mod} ({src_layer}) imports {imp} ({dst_layer})"
                )
    for f in sorted(findings):
        print("FINDING  ", f)
    for v in violations:
        print("VIOLATION", v)
    print(f"\n{len(violations)} violation(s), {len(findings)} finding(s).")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
