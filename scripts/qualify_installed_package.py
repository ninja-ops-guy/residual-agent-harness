#!/usr/bin/env python3
"""Qualify a wheel from outside the checkout, with Python -I in a fresh venv."""
from __future__ import annotations

import argparse
import importlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig

MODULES = (
    "residual", "residual.factory.runtime", "residual.factory.evidence_bus",
    "residual.marketplace.cli", "residual.station.server",
    "ai_providers", "observation_layer",
)
RESOURCES = (
    "residual/station/static/index.html", "residual/station/static/app.js",
    "residual/station/static/style.css", "residual/station/schemas/runtime.json",
    "residual/station/schemas/ldd-base.json",
    "residual/station/schemas/workflow-event.json",
)
COMMANDS = ("residual", "residual-station", "residual-worker", "residual-module")


def validate_origin(
    origin: Path, installed_files: set[Path], site_packages: Path, source_root: Path,
) -> Path:
    resolved = origin.resolve()
    if resolved.is_relative_to(source_root.resolve()):
        raise RuntimeError(f"checkout shadowing detected: {resolved}")
    if not resolved.is_relative_to(site_packages.resolve()):
        raise RuntimeError(f"origin is outside this venv's site-packages: {resolved}")
    if resolved not in installed_files or not resolved.is_file():
        raise RuntimeError(f"origin is not a retained distribution file: {resolved}")
    return resolved


def clean_environment(environment: dict[str, str]) -> dict[str, str]:
    cleaned = dict(environment)
    cleaned.pop("PYTHONPATH", None)
    cleaned.pop("PYTHONHOME", None)
    cleaned["PYTHONNOUSERSITE"] = "1"
    return cleaned


def qualify(source_root: Path) -> dict[str, object]:
    if not sys.flags.isolated:
        raise RuntimeError("run this check with Python -I")
    if sys.prefix == sys.base_prefix:
        raise RuntimeError("a dedicated virtual environment is required")
    if Path.cwd().resolve().is_relative_to(source_root.resolve()):
        raise RuntimeError("run from a temporary directory outside the checkout")
    site_packages = Path(sysconfig.get_path("purelib")).resolve()
    distribution = metadata.distribution("residual-agent-harness")
    if not distribution.files:
        raise RuntimeError("installed distribution has no file manifest")
    installed = {Path(distribution.locate_file(p)).resolve() for p in distribution.files}
    report: dict[str, object] = {
        "status": "PASS", "scope": "installed-wheel smoke, not source qualification",
        "python": sys.version, "prefix": sys.prefix,
        "distribution_version": distribution.version,
        "cwd": str(Path.cwd()), "source_root": str(source_root.resolve()),
        "module_origins": {}, "resources": [], "cli": {},
    }
    origins = {}
    for name in MODULES:
        module = importlib.import_module(name)
        if not getattr(module, "__file__", None):
            raise RuntimeError(f"module has no verifiable file origin: {name}")
        origins[name] = str(validate_origin(
            Path(module.__file__), installed, site_packages, source_root,
        ))
    report["module_origins"] = origins
    report["resources"] = [str(validate_origin(
        Path(distribution.locate_file(resource)), installed, site_packages, source_root,
    )) for resource in RESOURCES]
    # Factory extras must resolve independently of test-tool dependencies.
    for name in ("cryptography", "yaml"):
        importlib.import_module(name)
    declared = {ep.name for ep in distribution.entry_points if ep.group == "console_scripts"}
    cli = {}
    for name in COMMANDS:
        if name not in declared:
            raise RuntimeError(f"missing console-script declaration: {name}")
        executable = Path(sys.executable).parent / (name + (".exe" if os.name == "nt" else ""))
        if not executable.is_file():
            raise RuntimeError(f"missing installed entry point: {executable}")
        completed = subprocess.run(
            [str(executable), "--help"], stdin=subprocess.DEVNULL,
            capture_output=True, text=True, env=clean_environment(dict(os.environ)),
            timeout=30,
        )
        if completed.returncode or not completed.stdout.strip():
            raise RuntimeError(
                f"{name} --help failed ({completed.returncode}): "
                f"{completed.stdout[-1000:]}\n{completed.stderr[-1000:]}"
            )
        cli[name] = "PASS"
    report["cli"] = cli
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = qualify(args.source_root)
    except Exception as exc:
        report = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
    encoded = json.dumps(report, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
