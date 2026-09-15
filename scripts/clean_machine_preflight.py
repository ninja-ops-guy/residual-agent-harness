#!/usr/bin/env python3
"""Exercise README source onboarding in a fresh venv; this is not a blank VM.

Default operation is offline and uses only scripted providers. Output is a new,
private evidence directory. A real provider smoke requires two explicit flags.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib

SOURCE_PATHS = ("residual", "ai_providers", "observation_layer", "examples/onboarding",
                "README.md", "START-HERE.md", "docs/quickstart.md", "pyproject.toml")
ENV_ALLOWLIST = ("PATH", "LANG", "LC_ALL", "SYSTEMROOT", "WINDIR", "TMPDIR", "TEMP", "TMP")


class PreflightValidationError(ValueError):
    """A predefined diagnostic safe to retain without provider secrets."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clean_environment() -> dict[str, str]:
    """No model keys, Python injection variables, proxy URLs, or Git config."""
    values = {key: os.environ[key] for key in ENV_ALLOWLIST if key in os.environ}
    values.update(PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1")
    return values


def unpack_source(data: bytes, destination: Path) -> None:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        for item in archive:
            path = PurePosixPath(item.name)
            if path.is_absolute() or ".." in path.parts or not (item.isdir() or item.isfile()):
                raise PreflightValidationError("source archive contains an unsafe entry")
            target = destination.joinpath(*path.parts)
            if item.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(item) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)


def provider_environment(path: Path) -> dict[str, str]:
    """Pass only key names requested by built-in provider configuration."""
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    if config.get("plugins"):
        raise PreflightValidationError("onboarding smoke does not load provider plugins")
    values = {}
    for role in ("local", "expert"):
        entry = config.get(role) or {}
        if not isinstance(entry, dict):
            raise PreflightValidationError("invalid provider section")
        key = entry.get("api_key_env")
        if key is not None:
            if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                raise PreflightValidationError("invalid API key environment name")
            if key in ENV_ALLOWLIST or key.startswith(("PYTHON", "LD_", "DYLD_", "GIT_")):
                raise PreflightValidationError("unsafe API key environment name")
            if not os.environ.get(key):
                raise PreflightValidationError("configured API key environment variable is missing")
            values[key] = os.environ[key]
    return values


class PhaseFailure(RuntimeError):
    pass


class Recorder:
    def __init__(self, output: Path, timeout: float):
        self.output, self.timeout = output, timeout
        self.phases: list[dict] = []

    def run(self, name: str, argv: list[str], *, cwd: Path, env: dict[str, str],
            private_output: bool = False) -> bytes:
        started = time.monotonic()
        try:
            result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True,
                                    timeout=self.timeout, check=False)
            code, stdout, stderr = result.returncode, result.stdout, result.stderr
            status = "pass" if code == 0 else "fail"
        except subprocess.TimeoutExpired as exc:
            code, stdout, stderr, status = None, exc.stdout or b"", exc.stderr or b"", "timeout"
        except OSError as exc:
            code, stdout, stderr, status = None, b"", type(exc).__name__.encode(), "fail"
        phase = {"name": name, "status": status, "exit_code": code,
                 "elapsed_seconds": time.monotonic() - started, "command": argv,
                 "stdout_sha256": sha256(stdout), "stderr_sha256": sha256(stderr),
                 "output_withheld": private_output}
        for stream, data in (("stdout", stdout), ("stderr", stderr)):
            retained = b"[output withheld]\n" if private_output else data
            log = self.output / f"{name}.{stream}.log"
            log.write_bytes(retained)
            phase[f"{stream}_log_sha256"] = sha256(retained)
        self.phases.append(phase)
        if status != "pass":
            raise PhaseFailure(name)
        return stdout


def verify_demo_result(value: dict) -> None:
    if value.get("success") is not True or not isinstance(value.get("calls"), list):
        raise PreflightValidationError("scripted demo did not complete with evidence")
    if any(call.get("usage", {}).get("source") != "simulation" for call in value["calls"]):
        raise PreflightValidationError("default onboarding must use simulation only")


def run_preflight(source: Path, output: Path, *, timeout: float = 120,
                  provider_config: Path | None = None, allow_model_call: bool = False) -> dict:
    if bool(provider_config) != allow_model_call:
        raise PreflightValidationError("provider smoke requires both --provider-config and --allow-model-call")
    if not math.isfinite(timeout) or timeout <= 0 or timeout > 600:
        raise PreflightValidationError("timeout must be between 0 and 600 seconds")
    source, output = source.resolve(), output.absolute()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    recorder = Recorder(output, timeout)
    env = clean_environment()
    report = {"schema_version": "residual.onboarding-preflight.v1", "status": "fail",
              "scope": "fresh-venv-source-checkout", "blank_vm_tested": False,
              "installed_distribution_tested": False, "sandbox_qualified": False,
              "real_provider_requested": allow_model_call,
              "started_unix_ns": time.time_ns(), "phase_timeout_seconds": timeout,
              "harness_sha256": sha256(Path(__file__).read_bytes()),
              "environment": {"system": platform.system(), "release": platform.release(),
                              "machine": platform.machine(), "bootstrap_python": platform.python_version()},
              "phases": recorder.phases, "limitations": [
                  "Host OS, interpreter, Git, system libraries, and network policy are inherited.",
                  "No graphical Station interaction or Factory sandbox qualification is performed.",
                  "Source mode is README-supported; wheel installation is a separate release gate."]}
    try:
        report["git_sha"] = recorder.run("git-sha", ["git", "rev-parse", "HEAD"], cwd=source, env=env).decode().strip()
        report["git_tree"] = recorder.run("git-tree", ["git", "rev-parse", "HEAD^{tree}"], cwd=source, env=env).decode().strip()
        report["git_version"] = recorder.run("git-version", ["git", "--version"], cwd=source, env=env).decode().strip()
        # Only committed source is executed. Caller worktree edits cannot alter the fixture.
        with tempfile.TemporaryDirectory(prefix="residual-onboarding-") as temporary:
            root = Path(temporary)
            checkout = root / "checkout"
            checkout.mkdir()
            archive = recorder.run("source-archive", ["git", "archive", report["git_sha"], "--", *SOURCE_PATHS],
                                   cwd=source, env=env, private_output=True)
            report["source_archive_sha256"] = sha256(archive)
            unpack_source(archive, checkout)
            report["instruction_hashes"] = {name: sha256((checkout / name).read_bytes())
                                            for name in ("README.md", "START-HERE.md", "docs/quickstart.md")}
            venv = root / "venv"
            recorder.run("fresh-venv", [sys.executable, "-m", "venv", "--without-pip", str(venv)], cwd=root, env=env)
            python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            diagnostic = "import json,sys,sqlite3,os,signal; print(json.dumps({'python':sys.version.split()[0], 'fresh_venv':sys.prefix != sys.base_prefix, 'sqlite':sqlite3.sqlite_version, 'pidfd_api':hasattr(os,'pidfd_open') and hasattr(signal,'pidfd_send_signal')}))"
            report["diagnostics"] = json.loads(recorder.run("diagnostics", [str(python), "-c", diagnostic], cwd=checkout, env=env))
            if report["diagnostics"]["fresh_venv"] is not True:
                raise PreflightValidationError("interpreter is not isolated in a venv")
            recorder.run("cli-help", [str(python), "-m", "residual", "--help"], cwd=checkout, env=env)
            recorder.run("station-help", [str(python), "-m", "residual", "serve", "--help"], cwd=checkout, env=env)
            demo = root / "demo"
            recorder.run("scripted-demo", [str(python), "-m", "residual", "run",
                         "examples/onboarding/sample_project/task.json", "--config",
                         "examples/onboarding/config.toml", "--output", str(demo)], cwd=checkout, env=env)
            result = json.loads((demo / "result.json").read_text())
            verify_demo_result(result)
            root_hash = json.loads(recorder.run("trace-check", [str(python), "-m", "residual", "verify-trace",
                        str(demo / "trace.jsonl")], cwd=checkout, env=env))["root"]
            recorder.run("result-binding", [str(python), "-m", "residual", "verify-trace",
                         str(demo / "trace.jsonl"), "--expected-root", root_hash,
                         "--result", str(demo / "result.json")], cwd=checkout, env=env)
            report["trace_root"] = root_hash
            report["scripted_artifacts"] = {}
            for name in ("result.json", "trace.jsonl"):
                content = (demo / name).read_bytes()
                (output / name).write_bytes(content)
                report["scripted_artifacts"][name] = sha256(content)
            report["provider_smoke"] = {"status": "not_requested", "model_calls": 0}
            if provider_config:
                provider_config = provider_config.resolve()
                provider_env = {**env, **provider_environment(provider_config)}
                report["provider_config_sha256"] = sha256(provider_config.read_bytes())
                staged = root / "provider.toml"
                staged.write_bytes(provider_config.read_bytes())
                staged.chmod(0o600)
                recorder.run("provider-smoke", [str(python), "-m", "residual", "demo", "--config", str(staged),
                             "--no-cache", "--output", str(root / "provider-run")], cwd=checkout,
                             env=provider_env, private_output=True)
                live = json.loads((root / "provider-run/result.json").read_text())
                report["provider_smoke"] = {"status": "pass", "model_calls": len(live.get("calls", [])),
                    "simulation_only": all(c.get("usage", {}).get("source") == "simulation" for c in live.get("calls", [])),
                    "result_sha256": sha256((root / "provider-run/result.json").read_bytes())}
            report["status"] = "pass"
    except Exception as exc:
        report["failure"] = {"type": type(exc).__name__, "phase": str(exc) if isinstance(exc, PhaseFailure) else "preflight-validation",
                             "reason": str(exc) if isinstance(exc, PreflightValidationError) else "See phase status and safe retained logs.",
                             "next_step": "Inspect the failing phase log; validate host prerequisites and configuration. Do not count this run as a passed onboarding test."}
    finally:
        report["finished_unix_ns"] = time.time_ns()
        data = (json.dumps(report, indent=2, allow_nan=False) + "\n").encode()
        temporary_report = output / "manifest.json.tmp"
        temporary_report.write_bytes(data)
        temporary_report.replace(output / "manifest.json")
        (output / "manifest.sha256").write_text(sha256(data) + "  manifest.json\n")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True, help="New directory; existing evidence is never overwritten")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--provider-config", type=Path)
    parser.add_argument("--allow-model-call", action="store_true", help="Explicitly enable configured provider usage/cost")
    args = parser.parse_args(argv)
    try:
        report = run_preflight(args.source, args.output, timeout=args.timeout,
                               provider_config=args.provider_config, allow_model_call=args.allow_model_call)
    except (ValueError, OSError):
        parser.error("use a new output path and valid options; provider smoke requires both provider flags")
    print(json.dumps({"status": report["status"], "manifest": str(args.output / "manifest.json"),
                      "blank_vm_tested": False, "real_provider_requested": args.allow_model_call}))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
