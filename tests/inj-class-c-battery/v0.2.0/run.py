#!/usr/bin/env python3
"""Class C battery v0.2.0 — top-level mode dispatcher.

Usage:
  python3 run.py --mode general  [general-mode args...]
  python3 run.py --mode harness  [harness-mode args...]

Modes are independently selectable and NEVER mixed in a run: receipts carry
the mode label ("general-susceptibility" or "harness-faithful") plus the
battery version, claim, and not_claim fields, so the two claims cannot be
confused. General-susceptibility results MUST NEVER be presented as evidence
about RESIDUAL v1's cognitive layer.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent


def _load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] != "--mode" or len(argv) < 2:
        print(__doc__.strip().splitlines()[0])
        print("usage: run.py --mode {general,harness} [mode args...]")
        return 2
    mode, rest = argv[1], argv[2:]
    if mode == "general":
        battery = _load("battery", ROOT / "general" / "battery.py")
        parser = battery.build_parser()
        args = parser.parse_args(rest)
        return battery.run(args)
    if mode == "harness":
        runner = _load("run_harness", ROOT / "harness" / "run_harness.py")
        return runner.main(rest)
    print(f"unknown mode: {mode!r} (expected 'general' or 'harness')", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
