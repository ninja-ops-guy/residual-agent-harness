#!/usr/bin/env python3
"""Clean-install qualification for the residual-agent-harness (fail-closed).

Builds a wheel from the exact checkout, installs it into a fresh venv with
NO access to the source tree, runs an isolated smoke suite from outside the
checkout, runs the Factory ownership gate against the checkout, and emits a
machine-readable qualification report binding:

  - the source commit and tree SHA,
  - the built wheel name and SHA-256,
  - the Python version,
  - the Factory ownership gate result,
  - the isolated installed-wheel smoke results.

Fail-closed semantics: ANY failing step (git unavailable, wheel build
failure, venv/install failure, pip check failure, smoke failure, ownership
gate failure) marks the report FAIL and yields exit code 1. The report is
still written so evidence is retained on failure.

Non-claims: this is an installed-wheel/package qualification. It is not a
measured evaluation qualification, not an OS-isolation qualification, and
not a substitute for the full source verifier gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]

EXTRAS = "factory,marketplace"

# Modules that must import from the installed wheel only.
SMOKE_MODULES = (
    "residual",
    "residual.factory.runtime",
    "residual.factory.evidence_bus",
    "residual.factory.m4_safety",
    "residual.factory.m4_integrator",
    "residual.marketplace.cli",
    "residual.station.server",
    "ai_providers",
    "observation_layer",
)

SMOKE_RESOURCES = (
    "residual/station/static/index.html",
    "residual/station/static/app.js",
    "residual/station/static/style.css",
    "residual/station/schemas/runtime.json",
    "residual/station/schemas/ldd-base.json",
    "residual/station/schemas/workflow-event.json",
)

SMOKE_COMMANDS = (
    "residual",
    "residual-station",
    "residual-worker",
    "residual-module",
)

# Extra import check: Factory extras must resolve without test tools.
SMOKE_EXTRA_MODULES = ("cryptography", "yaml")

# Isolated smoke program executed by the FRESH VENV python with -I, from a
# temporary directory outside the checkout. Never imports from the checkout.
SMOKE_PROGRAM = r'''
import importlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig

source_root = Path(sys.argv[1]).resolve()
modules = json.loads(sys.argv[2])
resources = json.loads(sys.argv[3])
commands = json.loads(sys.argv[4])
extra_modules = json.loads(sys.argv[5])

if not sys.flags.isolated:
    raise RuntimeError("smoke must run with Python -I")
if sys.prefix == sys.base_prefix:
    raise RuntimeError("smoke must run inside the dedicated venv")
if Path.cwd().resolve().is_relative_to(source_root):
    raise RuntimeError("smoke must run from a directory outside the checkout")

site_packages = Path(sysconfig.get_path("purelib")).resolve()
distribution = metadata.distribution("residual-agent-harness")
if not distribution.files:
    raise RuntimeError("installed distribution has no file manifest")
installed = {Path(distribution.locate_file(p)).resolve() for p in distribution.files}

def validate(origin):
    resolved = Path(origin).resolve()
    if resolved.is_relative_to(source_root):
        raise RuntimeError(f"checkout shadowing detected: {resolved}")
    if not resolved.is_relative_to(site_packages):
        raise RuntimeError(f"origin outside venv site-packages: {resolved}")
    if resolved not in installed or not resolved.is_file():
        raise RuntimeError(f"origin is not a retained distribution file: {resolved}")
    return str(resolved)

report = {"module_origins": {}, "resources": [], "cli": {}}
for name in modules:
    module = importlib.import_module(name)
    if not getattr(module, "__file__", None):
        raise RuntimeError(f"module has no verifiable file origin: {name}")
    report["module_origins"][name] = validate(module.__file__)
for resource in resources:
    report["resources"].append(validate(distribution.locate_file(resource)))
for name in extra_modules:
    importlib.import_module(name)
declared = {ep.name for ep in distribution.entry_points if ep.group == "console_scripts"}
env = dict(os.environ)
env.pop("PYTHONPATH", None)
env.pop("PYTHONHOME", None)
env["PYTHONNOUSERSITE"] = "1"
for name in commands:
    if name not in declared:
        raise RuntimeError(f"missing console-script declaration: {name}")
    executable = Path(sys.executable).parent / (name + (".exe" if os.name == "nt" else ""))
    if not executable.is_file():
        raise RuntimeError(f"missing installed entry point: {executable}")
    completed = subprocess.run(
        [str(executable), "--help"], stdin=subprocess.DEVNULL,
        capture_output=True, text=True, env=env, timeout=30)
    if completed.returncode or not completed.stdout.strip():
        raise RuntimeError(
            f"{name} --help failed ({completed.returncode}): "
            f"{completed.stdout[-500:]}\n{completed.stderr[-500:]}")
    report["cli"][name] = "PASS"
report["distribution_version"] = distribution.version
print(json.dumps(report))
'''


class QualificationError(RuntimeError):
    """A qualification step failed; never means "not applicable"."""


def _run(cmd, *, cwd=None, env=None, timeout=600):
    try:
        result = subprocess.run(
            [str(c) for c in cmd], cwd=cwd, env=env,
            capture_output=True, text=True, errors="surrogateescape",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise QualificationError(f"command unavailable {cmd[0]}: {exc}") from exc
    return result


def _require(result, step):
    if result.returncode:
        detail = ((result.stderr or "") + "\n" + (result.stdout or "")).strip()
        raise QualificationError(
            f"{step} failed (exit {result.returncode}): {detail[-1500:]}")
    return result


def git_sha(root, ref):
    result = _require(
        _run(["git", "--no-replace-objects", "-C", str(root),
              "rev-parse", "--verify", "--end-of-options", ref],
             timeout=30),
        f"git rev-parse {ref}")
    sha = result.stdout.strip()
    if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        raise QualificationError(f"invalid git SHA for {ref}: {sha!r}")
    return sha


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_wheel(root, wheel_dir):
    result = _require(
        _run([sys.executable, "-m", "pip", "wheel", "--no-deps",
              "--wheel-dir", str(wheel_dir), str(root)], timeout=900),
        "wheel build")
    wheels = sorted(Path(wheel_dir).glob("*.whl"))
    if len(wheels) != 1:
        raise QualificationError(
            f"expected exactly one wheel, found {len(wheels)}: {wheels}")
    return wheels[0], result


def create_venv(venv_dir):
    _require(_run([sys.executable, "-m", "venv", str(venv_dir)], timeout=300),
             "venv creation")
    suffix = "Scripts" if os.name == "nt" else "bin"
    exe = "python.exe" if os.name == "nt" else "python"
    python = venv_dir / suffix / exe
    if not python.is_file():
        raise QualificationError(f"venv python missing: {python}")
    return python


def install_wheel(venv_python, wheel):
    _require(
        _run([str(venv_python), "-m", "pip", "install", f"{wheel}[{EXTRAS}]"],
             timeout=900),
        "wheel install into fresh venv")
    _require(_run([str(venv_python), "-m", "pip", "check"], timeout=120),
             "pip check")
    freeze = _require(
        _run([str(venv_python), "-m", "pip", "freeze"], timeout=120),
        "pip freeze")
    return freeze.stdout


def run_isolated_smoke(venv_python, source_root, work_dir):
    smoke_script = Path(work_dir) / "installed_smoke.py"
    smoke_script.write_text(SMOKE_PROGRAM, encoding="utf-8")
    smoke_cwd = Path(work_dir) / "smoke-cwd"
    smoke_cwd.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    result = _run(
        [str(venv_python), "-I", str(smoke_script), str(source_root),
         json.dumps(SMOKE_MODULES), json.dumps(SMOKE_RESOURCES),
         json.dumps(SMOKE_COMMANDS), json.dumps(SMOKE_EXTRA_MODULES)],
        cwd=smoke_cwd, env=env, timeout=300)
    _require(result, "isolated installed-wheel smoke")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise QualificationError(
            f"smoke report unreadable: {exc}: {result.stdout[-500:]}") from exc


def run_ownership_gate(source_root):
    checker = Path(source_root) / "verifier" / "v3" / "check_factory_ownership.py"
    if not checker.is_file():
        raise QualificationError(f"ownership checker missing: {checker}")
    result = _run([sys.executable, str(checker), "--root", str(source_root)],
                  timeout=120)
    output = result.stdout
    try:
        report = json.loads(output[: output.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        report = {"passed": None, "raw_tail": output[-500:]}
    if result.returncode or not report.get("passed"):
        raise QualificationError(
            f"factory ownership gate failed: {(result.stdout + result.stderr)[-1000:]}")
    return report


def qualify(source_root, work_dir, runner=_run):
    """Run the full qualification. Raises QualificationError on any failure."""
    global _run
    if runner is not _run:  # test seam
        original = _run
        _run = runner
    else:
        original = _run
    try:
        return _qualify_inner(source_root, work_dir)
    finally:
        _run = original


def _qualify_inner(source_root, work_dir):
    source_root = Path(source_root).resolve()
    work_dir = Path(work_dir).resolve()
    if work_dir.is_relative_to(source_root) or source_root.is_relative_to(work_dir):
        raise QualificationError(
            "work directory must be outside the checkout: "
            f"{work_dir} vs {source_root}")
    work_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "PASS",
        "scope": "clean-install wheel qualification; not measured evaluation",
        "python": sys.version,
        "commit": git_sha(source_root, "HEAD"),
        "tree": git_sha(source_root, "HEAD^{tree}"),
        "wheel": {},
        "ownership": {},
        "smoke": {},
        "installed": "",
    }
    wheel_dir = work_dir / "wheels"
    wheel_dir.mkdir(exist_ok=True)
    wheel, _ = build_wheel(source_root, wheel_dir)
    report["wheel"] = {"name": wheel.name, "sha256": sha256_file(wheel)}
    venv_dir = work_dir / "installed-venv"
    venv_python = create_venv(venv_dir)
    report["installed"] = install_wheel(venv_python, wheel)
    report["smoke"] = run_isolated_smoke(venv_python, source_root, work_dir)
    report["ownership"] = run_ownership_gate(source_root)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT,
                        help="checkout to qualify (default: inferred)")
    parser.add_argument("--output", type=Path, required=True,
                        help="qualification report JSON path")
    parser.add_argument("--work-dir", type=Path, default=None,
                        help="scratch dir outside the checkout "
                             "(default: fresh temporary directory)")
    args = parser.parse_args(argv)

    def execute(work_dir):
        try:
            report = qualify(args.source_root, work_dir)
        except Exception as exc:
            report = {
                "status": "FAIL",
                "error": f"{type(exc).__name__}: {exc}",
                "python": sys.version,
            }
        encoded = json.dumps(report, indent=2) + "\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
        print(encoded, end="")
        return 0 if report["status"] == "PASS" else 1

    if args.work_dir is not None:
        return execute(args.work_dir)
    with tempfile.TemporaryDirectory(prefix="residual-qualify-") as temp:
        return execute(temp)


if __name__ == "__main__":
    raise SystemExit(main())
