#!/usr/bin/env python3
"""Prepare and evaluate the bounded RESIDUAL independent first-install handoff.

`prepare` runs in the candidate checkout and freezes an immutable handoff by SHA-256.
`evaluate` is designed to run from the copied handoff without the source checkout.
Repository-controlled CI may exercise the evaluator, but it can never emit an
independent PASS: only an explicitly external, independence-attested evaluator can.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time

SCHEMA_HANDOFF = "residual.independent-install-handoff.v1"
SCHEMA_RECEIPT = "residual.independent-install-receipt.v1"
VERIFIED = "INDEPENDENT_INSTALL_VERIFIED"
UNVERIFIED = "INDEPENDENT_INSTALL_UNVERIFIED"
FAILED = "INDEPENDENT_INSTALL_FAILED"
PACKAGE = "residual-agent-harness"
SUPPORTED_PYTHON = (3, 11)
SUPPORTED_SYSTEM = "Linux"
SUPPORTED_MACHINES = {"x86_64", "amd64"}
EXTERNAL_CLASS = "external"
EVALUATOR_CLASSES = (EXTERNAL_CLASS, "repository_ci", "maintainer", "development_swarm")

INVENTORY = {
    "site": "independent-install-fixture",
    "readings": {
        "temperatures_c": [21.5, 22.0, 21.75],
        "fan_rpms": [2400, 2450, 2380],
    },
}
TASK = {
    "id": "independent-install-0",
    "goal": "Sum the recorded fan RPMs and temperatures from the site inventory.",
    "artifacts": [{"id": "inventory", "path": "inventory.json", "cloud": False}],
    "obligations": [
        {
            "id": "total_fan_rpm",
            "instruction": "Return the sum of /readings/fan_rpms from the inventory artifact.",
            "check": "json_sum",
            "evidence": ["inventory"],
            "depends_on": [],
            "parameters": {"artifact": "inventory", "pointer": "/readings/fan_rpms"},
            "solver": "json_sum",
            "cloud": False,
        },
        {
            "id": "total_temperature",
            "instruction": "Return the sum of /readings/temperatures_c from the inventory artifact.",
            "check": "json_sum",
            "evidence": ["inventory"],
            "depends_on": [],
            "parameters": {"artifact": "inventory", "pointer": "/readings/temperatures_c"},
            "solver": "json_sum",
            "cloud": False,
        },
    ],
}
CONFIG = """# Frozen offline evaluator configuration; no model calls or credentials.\n[local]\nkind = \"demo\"\nrole = \"local\"\n\n[expert]\nkind = \"demo\"\nrole = \"expert\"\n\n[limits]\nlocal_rounds = 1\n\n[cache]\nenabled = false\n"""
ORIGIN_PROGRAM = r'''
from importlib import metadata
import json
from pathlib import Path
import residual
import sysconfig

site = Path(sysconfig.get_path("purelib")).resolve()
dist = metadata.distribution("residual-agent-harness")
origin = Path(residual.__file__).resolve()
files = {Path(dist.locate_file(p)).resolve() for p in (dist.files or [])}
if not origin.is_relative_to(site):
    raise RuntimeError(f"residual origin outside venv site-packages: {origin}")
if origin not in files:
    raise RuntimeError(f"residual origin absent from installed distribution: {origin}")
entry_points = sorted(ep.name for ep in dist.entry_points if ep.group == "console_scripts")
required = ["residual", "residual-module", "residual-station", "residual-worker"]
missing = sorted(set(required) - set(entry_points))
if missing:
    raise RuntimeError(f"missing console scripts: {missing}")
print(json.dumps({"origin": str(origin), "version": dist.version, "entry_points": entry_points}))
'''


class GateError(RuntimeError):
    pass


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)


def _run(cmd, *, cwd=None, env=None, timeout=900):
    try:
        return subprocess.run(
            [str(x) for x in cmd], cwd=cwd, env=env, capture_output=True,
            text=True, errors="surrogateescape", timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GateError(f"command unavailable or timed out: {cmd[0]}: {exc}") from exc


def _require(proc, label: str):
    if proc.returncode:
        detail = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
        raise GateError(f"{label} failed ({proc.returncode}): {detail[-1800:]}")
    return proc


def git_sha(root: Path, ref: str) -> str:
    proc = _require(_run(["git", "--no-replace-objects", "-C", root, "rev-parse", "--verify", ref], timeout=30), f"git {ref}")
    value = proc.stdout.strip()
    if not _is_sha(value):
        raise GateError(f"invalid git identity for {ref}: {value!r}")
    return value


def prepare_handoff(source_root: Path, wheel: Path, dependency_wheels: list[Path], terms: Path,
                    output: Path, repository: str) -> dict:
    source_root = source_root.resolve()
    wheel = wheel.resolve()
    terms = terms.resolve()
    output = output.resolve()
    if output.exists():
        raise GateError(f"handoff output already exists: {output}")
    if not wheel.is_file() or wheel.suffix != ".whl":
        raise GateError(f"candidate wheel missing or invalid: {wheel}")
    if not terms.is_file():
        raise GateError(f"evaluation terms missing: {terms}")
    deps = [p.resolve() for p in dependency_wheels]
    if not deps or any(not p.is_file() or p.suffix != ".whl" for p in deps):
        raise GateError("at least one valid dependency wheel is required for an offline handoff")
    commit = git_sha(source_root, "HEAD")
    tree = git_sha(source_root, "HEAD^{tree}")
    output.mkdir(parents=True)

    members: list[dict] = []
    def retain(src: Path, name: str, role: str):
        dst = output / name
        shutil.copyfile(src, dst)
        members.append({"name": name, "role": role, "sha256": sha256_file(dst), "size": dst.stat().st_size})

    retain(wheel, wheel.name, "candidate-wheel")
    for dep in sorted(deps, key=lambda p: p.name.lower()):
        retain(dep, dep.name, "dependency-wheel")
    retain(Path(__file__).resolve(), "evaluate.py", "evaluator")
    retain(terms, "TERMS.md", "evaluation-terms")

    manifest = {
        "schema": SCHEMA_HANDOFF,
        "candidate": {"repository": repository, "commit": commit, "tree": tree},
        "artifact": {"package": PACKAGE, "wheel": wheel.name, "sha256": sha256_file(output / wheel.name)},
        "supported_configuration": {
            "system": SUPPORTED_SYSTEM,
            "machine": "x86_64",
            "python": "3.11",
            "network_during_evaluation": "forbidden",
            "provider": "offline demo only",
            "source_checkout": "forbidden",
        },
        "members": members,
        "claims": {
            "release_authority": False,
            "repository_ci_is_external": False,
            "successful_external_receipt_required": True,
        },
    }
    write_json(output / "handoff.json", manifest)
    manifest_hash = sha256_file(output / "handoff.json")
    (output / "handoff.sha256").write_text(f"{manifest_hash}  handoff.json\n", encoding="utf-8")
    return {**manifest, "manifest_sha256": manifest_hash}


def validate_handoff(bundle: Path) -> tuple[dict, str]:
    bundle = bundle.resolve()
    manifest_path = bundle / "handoff.json"
    if not manifest_path.is_file():
        raise GateError("handoff.json missing")
    manifest_hash = sha256_file(manifest_path)
    checksum = bundle / "handoff.sha256"
    if not checksum.is_file():
        raise GateError("handoff.sha256 missing")
    fields = checksum.read_text(encoding="utf-8").strip().split()
    if len(fields) != 2 or fields[0] != manifest_hash or fields[1] != "handoff.json":
        raise GateError("handoff manifest checksum mismatch")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"handoff manifest unreadable: {exc}") from exc
    if manifest.get("schema") != SCHEMA_HANDOFF:
        raise GateError("unsupported handoff schema")
    candidate = manifest.get("candidate", {})
    if not _is_sha(candidate.get("commit")) or not _is_sha(candidate.get("tree")):
        raise GateError("handoff candidate identity is invalid")
    members = manifest.get("members")
    if not isinstance(members, list) or not members:
        raise GateError("handoff member list missing")
    seen = set()
    for member in members:
        name = member.get("name")
        if not isinstance(name, str) or not name or Path(name).name != name or name in seen:
            raise GateError(f"invalid handoff member name: {name!r}")
        seen.add(name)
        path = bundle / name
        if not path.is_file():
            raise GateError(f"handoff member missing: {name}")
        if path.stat().st_size != member.get("size") or sha256_file(path) != member.get("sha256"):
            raise GateError(f"handoff member hash/size mismatch: {name}")
    artifact = manifest.get("artifact", {})
    wheel_name = artifact.get("wheel")
    if wheel_name not in seen or artifact.get("sha256") != sha256_file(bundle / wheel_name):
        raise GateError("candidate wheel is not bound to retained handoff bytes")
    return manifest, manifest_hash


def supported_host() -> dict:
    system = platform.system()
    machine = platform.machine().lower()
    py = sys.version_info[:2]
    if system != SUPPORTED_SYSTEM or machine not in SUPPORTED_MACHINES or py != SUPPORTED_PYTHON:
        raise GateError(
            f"unsupported evaluator host: system={system!r} machine={machine!r} "
            f"python={sys.version_info.major}.{sys.version_info.minor}; "
            "supported=Linux x86_64 Python 3.11")
    raw = f"{platform.node()}|{platform.platform()}|{platform.machine()}|{sys.version}".encode()
    return {
        "system": system,
        "machine": platform.machine(),
        "python": platform.python_version(),
        "fingerprint_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _console_script(venv: Path, name: str) -> Path:
    return venv / (("Scripts/" + name + ".exe") if os.name == "nt" else ("bin/" + name))


def _clean_env() -> dict:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    env["PIP_NO_INDEX"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    return env


def _log_run(checks: list[dict], evidence: Path, label: str, cmd: list[str], *, cwd: Path,
             env: dict, expected: int = 0, timeout: int = 300):
    proc = _run(cmd, cwd=cwd, env=env, timeout=timeout)
    log = evidence / f"{label}.log"
    log.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8")
    passed = proc.returncode == expected
    checks.append({"name": label, "status": "PASS" if passed else "FAIL", "exit_code": proc.returncode,
                   "expected_exit_code": expected, "log_sha256": sha256_file(log)})
    if not passed:
        raise GateError(f"{label} returned {proc.returncode}; expected {expected}; see {log.name}")
    return proc


def create_negative_control(root: Path) -> None:
    (root / "residual").mkdir(parents=True)
    (root / "residual/__init__.py").write_text(
        "raise RuntimeError('SOURCE_CHECKOUT_DEPENDENCY_TRIPWIRE')\n", encoding="utf-8")
    sample = root / "examples/onboarding/sample_project"
    sample.mkdir(parents=True)
    write_json(sample / "inventory.json", {"readings": {"fan_rpms": [-999999], "temperatures_c": [-999999]}})
    (root / "examples/onboarding/config.toml").write_text("this = 'must never be read'\n", encoding="utf-8")
    write_json(root / "inventory.json", INVENTORY)
    write_json(root / "task.json", TASK)
    (root / "config.toml").write_text(CONFIG, encoding="utf-8")


def run_technical_evaluation(bundle: Path, manifest: dict, evidence: Path) -> dict:
    evidence = evidence.resolve()
    if evidence.exists():
        raise GateError(f"evidence directory already exists: {evidence}")
    evidence.mkdir(parents=True)
    checks: list[dict] = []
    env = _clean_env()
    with tempfile.TemporaryDirectory(prefix="residual-independent-install-") as temp:
        temp_root = Path(temp).resolve()
        poison = temp_root / "poisoned-source-shadow"
        poison.mkdir()
        create_negative_control(poison)
        checks.append({"name": "negative-control-poison-created", "status": "PASS"})

        venv = temp_root / "venv"
        _log_run(checks, evidence, "create-venv", [sys.executable, "-m", "venv", str(venv)], cwd=temp_root, env=env)
        python = _venv_python(venv)
        if not python.is_file():
            raise GateError("fresh venv python missing")
        wheel = bundle / manifest["artifact"]["wheel"]
        _log_run(
            checks, evidence, "install-offline",
            [str(python), "-m", "pip", "install", "--no-index", "--find-links", str(bundle), str(wheel)],
            cwd=poison, env=env, timeout=600,
        )
        _log_run(checks, evidence, "pip-check", [str(python), "-m", "pip", "check"], cwd=poison, env=env)
        freeze = _log_run(checks, evidence, "pip-freeze", [str(python), "-m", "pip", "freeze", "--all"], cwd=poison, env=env)
        (evidence / "installed.txt").write_text(freeze.stdout, encoding="utf-8")

        origin = _log_run(checks, evidence, "installed-origin", [str(python), "-I", "-c", ORIGIN_PROGRAM], cwd=poison, env=env)
        try:
            origin_report = json.loads(origin.stdout)
        except json.JSONDecodeError as exc:
            raise GateError(f"installed-origin output unreadable: {exc}") from exc
        checks.append({"name": "source-shadow-not-imported", "status": "PASS", "origin": origin_report["origin"]})

        residual = _console_script(venv, "residual")
        if not residual.is_file():
            raise GateError(f"installed residual CLI missing: {residual}")
        _log_run(checks, evidence, "first-run", [str(residual), "run", "task.json", "--config", "config.toml", "--output", "accepted"], cwd=poison, env=env)
        result_path = poison / "accepted/result.json"
        trace_path = poison / "accepted/trace.jsonl"
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise GateError(f"first-run result unreadable: {exc}") from exc
        if (result.get("success") is not True
                or result.get("values") != {"total_fan_rpm": 7230, "total_temperature": 65.25}
                or result.get("metrics", {}).get("calls") != 0):
            raise GateError("first-run result did not match the frozen zero-model fixture")
        checks.append({"name": "first-run-values", "status": "PASS", "model_calls": 0})
        _log_run(checks, evidence, "verify-result", [str(residual), "verify-trace", "accepted/trace.jsonl", "--result", "accepted/result.json"], cwd=poison, env=env)

        altered = json.loads(result_path.read_text(encoding="utf-8"))
        altered["values"]["total_fan_rpm"] = 0
        write_json(poison / "altered-result.json", altered)
        _log_run(checks, evidence, "reject-altered", [str(residual), "verify-trace", "accepted/trace.jsonl", "--result", "altered-result.json"], cwd=poison, env=env, expected=1)
        _log_run(checks, evidence, "verify-original-again", [str(residual), "verify-trace", "accepted/trace.jsonl", "--result", "accepted/result.json"], cwd=poison, env=env)

        retained = {}
        for src, name in ((result_path, "result.json"), (trace_path, "trace.jsonl"), (poison / "altered-result.json", "altered-result.json")):
            dst = evidence / name
            shutil.copyfile(src, dst)
            retained[name] = {"sha256": sha256_file(dst), "size": dst.stat().st_size}
        return {
            "status": "PASS",
            "checks": checks,
            "retained": retained,
            "installed": {"version": origin_report["version"], "origin": origin_report["origin"]},
            "negative_control": {
                "poison_package": "residual/__init__.py raises SOURCE_CHECKOUT_DEPENDENCY_TRIPWIRE",
                "poison_examples": "examples/onboarding contains deliberately invalid values",
                "cwd": "poisoned source shadow",
                "result": "PASS without reading/importing poisoned source artifacts",
            },
        }


def classify(technical_status: str, evaluator_class: str, attested: bool) -> str:
    if technical_status != "PASS":
        return FAILED
    if evaluator_class == EXTERNAL_CLASS and attested:
        return VERIFIED
    return UNVERIFIED


def evaluate_handoff(bundle: Path, receipt_path: Path, evidence_dir: Path, evaluator_id: str,
                     evaluator_class: str, attested: bool) -> dict:
    started = time.time()
    manifest = None
    manifest_hash = None
    host = None
    technical = {"status": "FAIL", "checks": []}
    error = None
    try:
        manifest, manifest_hash = validate_handoff(bundle)
        host = supported_host()
        technical = run_technical_evaluation(bundle.resolve(), manifest, evidence_dir)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    status = classify(technical.get("status", "FAIL"), evaluator_class, attested)
    receipt = {
        "schema": SCHEMA_RECEIPT,
        "status": status,
        "technical_status": technical.get("status", "FAIL"),
        "candidate": (manifest or {}).get("candidate"),
        "artifact": (manifest or {}).get("artifact"),
        "handoff_manifest_sha256": manifest_hash,
        "supported_configuration": (manifest or {}).get("supported_configuration"),
        "evaluator": {
            "id": evaluator_id,
            "class": evaluator_class,
            "independence_attested": bool(attested),
            "independence_rule": "only class=external plus explicit attestation can verify the independent gate",
        },
        "host": host,
        "technical": technical,
        "error": error,
        "release_authority": False,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    canonical = _json_bytes(receipt)
    receipt["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    write_json(receipt_path.resolve(), receipt)
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="freeze a candidate-bound handoff")
    prepare.add_argument("--source-root", type=Path, required=True)
    prepare.add_argument("--wheel", type=Path, required=True)
    prepare.add_argument("--dependency-wheel", type=Path, action="append", default=[])
    prepare.add_argument("--terms", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--repository", default="ninja-ops-guy/residual-agent-harness")

    evaluate = sub.add_parser("evaluate", help="evaluate only the frozen handoff")
    evaluate.add_argument("--handoff", type=Path, required=True, help="directory containing handoff.json")
    evaluate.add_argument("--receipt", type=Path, required=True)
    evaluate.add_argument("--evidence-dir", type=Path, required=True)
    evaluate.add_argument("--evaluator-id", required=True, help="pseudonymous or organization-approved evaluator identifier")
    evaluate.add_argument("--evaluator-class", choices=EVALUATOR_CLASSES, required=True)
    evaluate.add_argument("--attest-independent", action="store_true", help="assert evaluator/host is independent and no source checkout was supplied")
    evaluate.add_argument("--require-independent", action="store_true", help="exit nonzero unless the final status is INDEPENDENT_INSTALL_VERIFIED")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        try:
            report = prepare_handoff(args.source_root, args.wheel, args.dependency_wheel, args.terms, args.output, args.repository)
        except Exception as exc:
            print(f"handoff preparation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    receipt = evaluate_handoff(args.handoff, args.receipt, args.evidence_dir, args.evaluator_id, args.evaluator_class, args.attest_independent)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if receipt["technical_status"] != "PASS":
        return 1
    if args.require_independent and receipt["status"] != VERIFIED:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
