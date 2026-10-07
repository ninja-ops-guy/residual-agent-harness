#!/usr/bin/env python3
"""Qualify an already-built wheel without rebuilding it.

This complements verifier/v3/qualify_clean_install.py. The caller supplies the
exact wheel bytes that may later be promoted; this script installs those bytes
into a fresh isolated venv and reuses the existing installed-origin, resource,
CLI, pip-check, and Factory ownership qualification logic.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUALIFIER = ROOT / "verifier" / "v3" / "qualify_clean_install.py"


def load_qualifier():
    spec = importlib.util.spec_from_file_location("residual_clean_install_qualifier", QUALIFIER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load clean-install qualifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def qualify(wheel: Path, source_root: Path, work_dir: Path) -> dict:
    q = load_qualifier()
    wheel = wheel.resolve()
    source_root = source_root.resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        raise q.QualificationError(f"wheel does not exist: {wheel}")
    report = {
        "status": "PASS",
        "scope": "exact prebuilt wheel qualification; no rebuild performed",
        "commit": q.git_sha(source_root, "HEAD"),
        "tree": q.git_sha(source_root, "HEAD^{tree}"),
        "wheel": {"name": wheel.name, "sha256": q.sha256_file(wheel)},
        "ownership": {},
        "smoke": {},
        "installed": "",
    }
    venv_python = q.create_venv(work_dir / "installed-venv")
    report["installed"] = q.install_wheel(venv_python, wheel)
    report["smoke"] = q.run_isolated_smoke(venv_python, source_root, work_dir)
    report["ownership"] = q.run_ownership_gate(source_root)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path)
    args = parser.parse_args(argv)

    def execute(work_dir: Path) -> int:
        try:
            report = qualify(args.wheel, args.source_root, work_dir)
        except Exception as exc:
            report = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"] == "PASS" else 1

    if args.work_dir:
        args.work_dir.mkdir(parents=True, exist_ok=True)
        return execute(args.work_dir)
    with tempfile.TemporaryDirectory(prefix="residual-exact-wheel-") as temp:
        return execute(Path(temp))


if __name__ == "__main__":
    raise SystemExit(main())
