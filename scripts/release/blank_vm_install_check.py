#!/usr/bin/env python3
"""Blank-VM install check for a residual-agent-harness release candidate.

Self-contained (stdlib only) so it can be fetched to a bare machine with no
repo checkout assumptions:

    python3 blank_vm_install_check.py \
        --artifact-url https://.../residual_agent_harness-<ver>-py3-none-any.whl \
        --sha256 <expected-wheel-sha256> \
        --out runs/blank-vm-install

Checks (each emits a typed PASS/FAIL record and retains its own log):

  1. python_probe     - a usable Python >= 3.10 interpreter exists
                        (detection point for the missing-python scenario)
  2. fetch_artifact   - the release artifact downloads completely
  3. verify_hash      - SHA-256 of the fetched bytes matches the published
                        digest (detection point for corrupt download)
  4. create_venv      - a FRESH venv is created (existing venv dir = partial
                        prior install; it is removed and recreated, and the
                        recovery is recorded)
  5. install_artifact - pip installs the artifact with the factory,
                        marketplace extras; `pip check` must pass; the full
                        `pip freeze` is retained (detection point for
                        dependency-resolution failure and interrupted
                        install)
  6. isolated_smoke   - the venv Python runs with -I from a directory
                        outside any checkout; core modules, packaged
                        resources and console scripts are verified against
                        the installed distribution manifest. Mirrors the
                        smoke in verifier/v3/qualify_clean_install.py (#100).
  7. ownership_gate   - if --checkout is given (maintainer mode), runs
                        verifier/v3/check_factory_ownership.py (#95) against
                        that checkout. On a true blank VM with no checkout
                        this check is recorded SKIP, not PASS.

Fail-closed: any required check FAIL -> exit 1. Every record is hash-chained
(sha256 of the previous record line is embedded in the next) so a tampered
or truncated log is detectable; the chain head is in summary.json.

Non-claims: this is an install qualification procedure for a release
candidate. It certifies no release and no measured evaluation result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request

ARTIFACT_EXTRAS = "factory,marketplace"
MIN_PYTHON = (3, 10)

# Smoke surface mirrors verifier/v3/qualify_clean_install.py (#100) so the
# blank-VM procedure and the in-repo qualification check the same surface.
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
SMOKE_EXTRA_MODULES = ("cryptography", "yaml")

# Isolated smoke executed by the fresh venv Python with -I. Unlike #100's
# version there is no source checkout on a blank VM, so shadowing detection
# reduces to: every origin must live inside the venv site-packages and be a
# retained distribution file.
SMOKE_PROGRAM = r'''
import importlib
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig

modules = json.loads(sys.argv[1])
resources = json.loads(sys.argv[2])
commands = json.loads(sys.argv[3])
extra_modules = json.loads(sys.argv[4])

if not sys.flags.isolated:
    raise RuntimeError("smoke must run with Python -I")
if sys.prefix == sys.base_prefix:
    raise RuntimeError("smoke must run inside the dedicated venv")

site_packages = Path(sysconfig.get_path("purelib")).resolve()
distribution = metadata.distribution("residual-agent-harness")
if not distribution.files:
    raise RuntimeError("installed distribution has no file manifest")
installed = {Path(distribution.locate_file(p)).resolve() for p in distribution.files}

def validate(origin):
    resolved = Path(origin).resolve()
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


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


class CheckLog:
    """Typed, hash-chained check log. One JSON record per line."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.stat().st_size:
            raise RuntimeError("existing install evidence requires a fresh output directory")
        self._prev = "0" * 64  # genesis
        self.records = []

    def emit(self, check_id, status, detail="", log_path=None, recovery=None):
        if status not in ("PASS", "FAIL", "SKIP"):
            raise ValueError(f"invalid status {status!r}")
        record = {
            "check_id": check_id,
            "status": status,
            "detail": detail,
            "log": str(log_path) if log_path else None,
            "recovery": recovery,
            "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "prev_hash": self._prev,
        }
        line = json.dumps(record, sort_keys=True)
        self._prev = sha256_bytes(line.encode("utf-8"))
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        self.records.append(record)
        return record

    @property
    def chain_head(self):
        return self._prev


def verify_chain(path, *, expected_head=None, expected_count=None):
    """Verify a complete log against an independently retained endpoint.

    A chain's internal links cannot detect a removed or rewritten final record.
    Callers must supply the head/count captured at finalization, not recompute
    them from the file being verified. The summary itself needs trusted retention.
    """
    if (not isinstance(expected_head, str) or
            not re.fullmatch(r"[0-9a-f]{64}", expected_head) or
            type(expected_count) is not int or expected_count < 0):
        return False, [], "trusted expected chain head and record count required"
    prev = "0" * 64
    records = []
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return False, [], f"log unreadable: {exc}"
    for lineno, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            return False, records, f"line {lineno} not JSON: {exc}"
        if not isinstance(record, dict) or record.get("prev_hash") != prev:
            return False, records, f"line {lineno} chain break"
        prev = sha256_bytes(line.encode("utf-8"))
        records.append(record)
    if prev != expected_head or len(records) != expected_count:
        return False, records, "chain endpoint/count mismatch"
    return True, records, ""


def run_logged(cmd, log_path, *, cwd=None, env=None, timeout=900):
    """Run a command, retaining stdout+stderr in log_path. Returns rc or None."""
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [str(c) for c in cmd], cwd=cwd, env=env,
            capture_output=True, text=True, errors="surrogateescape",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log_path.write_text(f"command unavailable: {exc}\n", encoding="utf-8")
        return None
    log_path.write_text(
        f"$ {' '.join(str(c) for c in cmd)}\nexit={result.returncode}\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}\n",
        encoding="utf-8", errors="surrogateescape")
    return result


def clean_env():
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    return env


def venv_python(venv_dir):
    suffix = "Scripts" if os.name == "nt" else "bin"
    exe = "python.exe" if os.name == "nt" else "python"
    return Path(venv_dir) / suffix / exe


def check_python(log, logs_dir, override=None):
    candidate = override or sys.executable
    result = run_logged(
        [candidate, "-c",
         "import sys, json; print(json.dumps({'version': sys.version, "
         "'executable': sys.executable}))"],
        logs_dir / "01-python-probe.log", timeout=30)
    if result is None or result.returncode:
        log.emit("python_probe", "FAIL",
                 f"no usable Python interpreter at {candidate!r}; "
                 "recovery: install Python >= "
                 f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]} and re-run",
                 log_path=logs_dir / "01-python-probe.log")
        return None
    info = json.loads(result.stdout.strip().splitlines()[-1])
    version = tuple(int(p) for p in info["version"].split()[0].split(".")[:2])
    if version < MIN_PYTHON:
        log.emit("python_probe", "FAIL",
                 f"Python {info['version'].split()[0]} < "
                 f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]}; recovery: install a "
                 "supported interpreter and re-run",
                 log_path=logs_dir / "01-python-probe.log")
        return None
    log.emit("python_probe", "PASS",
             f"{info['executable']} ({info['version'].split()[0]})",
             log_path=logs_dir / "01-python-probe.log")
    return info["executable"]


def check_fetch(log, logs_dir, work_dir, url, max_attempts=2):
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    target = work_dir / Path(url.split("?")[0]).name
    Path(work_dir).mkdir(parents=True, exist_ok=True)
    for attempt in range(1, max_attempts + 1):
        log_path = logs_dir / f"02-fetch-attempt{attempt}.log"
        try:
            with urllib.request.urlopen(url, timeout=120) as response, \
                    open(target, "wb") as handle:
                shutil.copyfileobj(response, handle)
        except (OSError, urllib.error.URLError) as exc:
            log_path.write_text(f"fetch failed: {exc}\n", encoding="utf-8")
            recovery = ("re-fetch attempted" if attempt < max_attempts
                        else "recovery: verify network and artifact URL, "
                             "then re-run the whole procedure")
            log.emit("fetch_artifact", "FAIL",
                     f"attempt {attempt}: {exc}", log_path=log_path,
                     recovery=recovery)
            continue
        log.emit("fetch_artifact", "PASS",
                 f"{url} -> {target} ({target.stat().st_size} bytes, "
                 f"attempt {attempt})", log_path=log_path)
        return target
    return None


def check_hash(log, logs_dir, artifact, expected):
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
        detail = "expected SHA-256 must be a nonempty 64-hex digest"
        (logs_dir / "03-hash.log").write_text(detail + "\n", encoding="utf-8")
        log.emit("verify_hash", "FAIL", detail, log_path=logs_dir / "03-hash.log")
        return False
    actual = sha256_file(artifact)
    detail = f"sha256={actual}"
    if actual != expected.lower():
        log.emit("verify_hash", "FAIL",
                 f"{detail} != expected {expected.lower()}; downloaded bytes "
                 "are not the published artifact; recovery: delete the file, "
                 "re-fetch, and re-verify before any install",
                 log_path=logs_dir / "03-hash.log")
        return False
    (logs_dir / "03-hash.log").write_text(detail + "\n", encoding="utf-8")
    log.emit("verify_hash", "PASS", detail, log_path=logs_dir / "03-hash.log")
    return True


def check_venv(log, logs_dir, python, work_dir):
    venv_dir = work_dir / "install-venv"
    recovery = None
    if venv_dir.exists():
        # Partial prior install: never install into a dirty venv.
        shutil.rmtree(venv_dir, ignore_errors=True)
        recovery = ("pre-existing venv dir removed (partial prior install "
                    "recovery) and recreated fresh")
    result = run_logged([python, "-m", "venv", str(venv_dir)],
                        logs_dir / "04-venv.log", timeout=300)
    exe = venv_python(venv_dir)
    if result is None or result.returncode or not exe.is_file():
        log.emit("create_venv", "FAIL",
                 "venv creation failed; recovery: install the python3-venv "
                 "OS package (or ensurepip) and re-run",
                 log_path=logs_dir / "04-venv.log", recovery=recovery)
        return None
    log.emit("create_venv", "PASS", str(venv_dir),
             log_path=logs_dir / "04-venv.log", recovery=recovery)
    return venv_dir


def check_install(log, logs_dir, venv_dir, artifact):
    exe = venv_python(venv_dir)
    spec = f"{artifact}[{ARTIFACT_EXTRAS}]"
    result = run_logged([str(exe), "-m", "pip", "install", spec],
                        logs_dir / "05-install.log", env=clean_env(),
                        timeout=900)
    if result is None or result.returncode:
        log.emit("install_artifact", "FAIL",
                 "pip install failed (dependency resolution failure or "
                 "interrupted install); recovery: delete the venv and "
                 "re-run; if the failure reproduces, the artifact metadata "
                 "or index reachability is at fault - halt the release",
                 log_path=logs_dir / "05-install.log")
        return False
    check = run_logged([str(exe), "-m", "pip", "check"],
                       logs_dir / "05-pip-check.log", env=clean_env(),
                       timeout=120)
    if check is None or check.returncode:
        log.emit("install_artifact", "FAIL",
                 "pip check failed: inconsistent installed set (partial "
                 "install); recovery: delete the venv and re-run",
                 log_path=logs_dir / "05-pip-check.log")
        return False
    freeze = run_logged([str(exe), "-m", "pip", "freeze"],
                        logs_dir / "05-pip-freeze.log", env=clean_env(),
                        timeout=120)
    if freeze is None or freeze.returncode:
        log.emit("install_artifact", "FAIL",
                 "pip freeze failed: dependency evidence was not retained",
                 log_path=logs_dir / "05-pip-freeze.log")
        return False
    log.emit("install_artifact", "PASS",
             f"installed {Path(str(artifact)).name}[{ARTIFACT_EXTRAS}]; "
             "pip check passed; freeze retained",
             log_path=logs_dir / "05-install.log")
    return True


def check_smoke(log, logs_dir, venv_dir, work_dir):
    exe = venv_python(venv_dir)
    smoke_script = work_dir / "isolated_smoke.py"
    smoke_script.write_text(SMOKE_PROGRAM, encoding="utf-8")
    smoke_cwd = work_dir / "smoke-cwd"
    smoke_cwd.mkdir(exist_ok=True)
    result = run_logged(
        [str(exe), "-I", str(smoke_script),
         json.dumps(SMOKE_MODULES), json.dumps(SMOKE_RESOURCES),
         json.dumps(SMOKE_COMMANDS), json.dumps(SMOKE_EXTRA_MODULES)],
        logs_dir / "06-smoke.log", cwd=smoke_cwd, env=clean_env(),
        timeout=300)
    if result is None or result.returncode:
        log.emit("isolated_smoke", "FAIL",
                 "installed-wheel smoke failed; see retained log; recovery: "
                 "none in-field - halt the release and retain evidence",
                 log_path=logs_dir / "06-smoke.log")
        return False
    log.emit("isolated_smoke", "PASS",
             "modules/resources/entry-points resolve inside the venv",
             log_path=logs_dir / "06-smoke.log")
    return True


def check_ownership(log, logs_dir, checkout):
    if not checkout:
        log.emit("ownership_gate", "SKIP",
                 "no --checkout provided (true blank VM); the #95 ownership "
                 "gate is enforced in CI and in maintainer mode")
        return True
    checker = Path(checkout) / "verifier" / "v3" / "check_factory_ownership.py"
    if not checker.is_file():
        log.emit("ownership_gate", "FAIL", f"checker missing: {checker}")
        return False
    result = run_logged([sys.executable, str(checker), "--root", str(checkout)],
                        logs_dir / "07-ownership.log", timeout=120)
    if result is None or result.returncode:
        log.emit("ownership_gate", "FAIL",
                 "factory ownership gate failed; halt the release",
                 log_path=logs_dir / "07-ownership.log")
        return False
    log.emit("ownership_gate", "PASS", "factory ownership gate passed",
             log_path=logs_dir / "07-ownership.log")
    return True


def run_procedure(*, artifact_url, expected_sha256, out_dir, work_dir,
                  python_override=None, checkout=None):
    out_dir = Path(out_dir)
    logs_dir = out_dir / "logs"
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    log = CheckLog(out_dir / "checks.jsonl")

    python = check_python(log, logs_dir, override=python_override)
    artifact = None
    if python:
        artifact = check_fetch(log, logs_dir, work_dir, artifact_url)
    else:
        log.emit("fetch_artifact", "SKIP", "blocked: no Python interpreter")
    if artifact and not check_hash(log, logs_dir, artifact, expected_sha256):
        artifact = None  # corrupt download: never proceed to install
    venv_dir = None
    if artifact:
        venv_dir = check_venv(log, logs_dir, python, work_dir)
    else:
        for skipped in ("verify_hash", "create_venv"):
            if all(r["check_id"] != skipped for r in log.records):
                log.emit(skipped, "SKIP", "blocked by earlier failure")
    installed = False
    if venv_dir:
        installed = check_install(log, logs_dir, venv_dir, artifact)
    else:
        log.emit("install_artifact", "SKIP", "blocked by earlier failure")
    if installed:
        check_smoke(log, logs_dir, venv_dir, work_dir)
    else:
        log.emit("isolated_smoke", "SKIP", "blocked by earlier failure")
    check_ownership(log, logs_dir, checkout)

    statuses = {r["check_id"]: r["status"] for r in log.records}
    required = ("python_probe", "fetch_artifact", "verify_hash",
                "create_venv", "install_artifact", "isolated_smoke")
    overall = "PASS" if all(statuses.get(c) == "PASS" for c in required) \
        and statuses.get("ownership_gate") in ("PASS", "SKIP") else "FAIL"
    summary = {
        "status": overall,
        "scope": "release-candidate blank-VM install procedure; "
                 "certifies no release",
        "artifact_url": artifact_url,
        "expected_sha256": expected_sha256,
        "checks": statuses,
        "chain_head": log.chain_head,
        "record_count": len(log.records),
        "log": str(log.path),
    }
    ok, _, error = verify_chain(log.path, expected_head=log.chain_head,
                                expected_count=len(log.records))
    if not ok:
        summary["status"] = "FAIL"
        summary["evidence_integrity_error"] = error
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-url", required=True,
                        help="URL of the release-candidate wheel/sdist")
    parser.add_argument("--sha256", required=True,
                        help="expected SHA-256 of the artifact")
    parser.add_argument("--out", type=Path, required=True,
                        help="evidence output directory (checks.jsonl, "
                             "summary.json, logs/)")
    parser.add_argument("--work-dir", type=Path, default=None,
                        help="scratch dir for venv/smoke (default: <out>/work)")
    parser.add_argument("--python", default=None,
                        help="interpreter override (testing)")
    parser.add_argument("--checkout", type=Path, default=None,
                        help="maintainer mode: checkout to run the #95 "
                             "ownership gate against")
    args = parser.parse_args(argv)
    summary = run_procedure(
        artifact_url=args.artifact_url, expected_sha256=args.sha256,
        out_dir=args.out, work_dir=args.work_dir or args.out / "work",
        python_override=args.python, checkout=args.checkout)
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
