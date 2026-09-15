#!/usr/bin/env python3
"""Retain independent preflight evidence for a pinned, unmodified target checkout.

Exit 0 = all selected tests pass with no skips or known gaps; 1 = failure;
2 = incomplete (skip/xfail). Never describes partial evidence as qualification.
This does not run a model, update Git refs, modify source, or close an issue.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


def git(target, *args):
    return subprocess.check_output(["git", "-C", str(target), *args], text=True).strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(target):
    """Inventory actual import inputs, including directory names and file modes."""
    entries = {}
    for root, directories, files in os.walk(target, followlinks=False):
        if Path(root) == target:
            directories[:] = [d for d in directories if d != ".git"]
            files = [f for f in files if f != ".git"]
        for name in sorted(directories + files):
            path = Path(root) / name
            relative = str(path.relative_to(target))
            if path.is_symlink():
                raise ValueError(f"source symlink is outside this preflight profile: {relative}")
            entries[relative] = {"kind": "directory" if path.is_dir() else "file",
                                 "mode": path.stat().st_mode & 0o777,
                                 "sha256": None if path.is_dir() else sha(path)}
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sandbox", action="store_true", help="enable bounded real-namespace probes")
    parser.add_argument("--dependency-path", type=Path, action="append", default=[],
                        help="explicit additional Python dependency directory; inherited PYTHONPATH is ignored")
    parser.add_argument("--timeout-s", type=int, default=300, help="whole pytest process-group deadline (1..900 seconds)")
    args = parser.parse_args()
    target = args.target.resolve()
    suite_root = Path(__file__).resolve().parents[1]
    suite = suite_root / "tests/preflight_trust"
    output = args.output.resolve()
    if output == target or target in output.parents:
        parser.error("evidence output must be outside the immutable target checkout")
    commit = git(target, "rev-parse", "HEAD")
    if commit != args.expected_commit:
        parser.error(f"target commit mismatch: observed {commit}")
    if not 1 <= args.timeout_s <= 900:
        parser.error("timeout must be in 1..900 seconds")
    initial_status = git(target, "status", "--porcelain", "--untracked-files=all")
    if initial_status:
        parser.error("target contains tracked modifications or untracked files; use a fresh detached checkout")
    if git(target, "ls-files", "--others", "--ignored", "--exclude-standard"):
        parser.error("target contains ignored files; use a fresh detached checkout")
    try:
        source_inventory = inventory(target)
    except ValueError as exc:
        parser.error(str(exc))
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        parser.error("use an empty output directory to avoid overwriting evidence")
    xml_path = output / "junit.xml"
    command = [sys.executable, "-m", "pytest", str(suite), "--import-mode=importlib", "-ra", "-q",
               "-p", "no:cacheprovider", "-o", "junit_family=legacy", f"--junitxml={xml_path}"]
    if args.sandbox:
        command += ["--run-bounded-sandbox"]
    dependency_paths = [str(p.resolve()) for p in args.dependency_path]
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
           "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONNOUSERSITE": "1",
           "PYTHONHASHSEED": "0", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    env["PYTHONPATH"] = os.pathsep.join([str(target), *dependency_paths])
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # Artifacts and Hypothesis transient cache stay outside the source checkout.
    env["HYPOTHESIS_STORAGE_DIRECTORY"] = str(output / "hypothesis")
    imported = subprocess.check_output([sys.executable, "-c", "import residual; print(residual.__file__)"],
                                       cwd=output, env=env, text=True).strip()
    if Path(imported).resolve() != target / "residual/__init__.py":
        parser.error(f"wrong runtime imported: {imported}")
    start = time.monotonic()
    timed_out = False
    with (output / "stdout.txt").open("wb") as stdout, (output / "stderr.txt").open("wb") as stderr:
        process = subprocess.Popen(command, cwd=output, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            process.wait(timeout=args.timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
    cases = []
    xml_error = None
    try:
        nodes = list(ET.parse(xml_path).getroot().iter("testcase")) if xml_path.exists() else []
    except ET.ParseError as exc:
        nodes = []
        xml_error = str(exc)
    if nodes:
        for node in nodes:
            status = "PASS"
            detail = ""
            for kind, verdict in (("failure", "FAIL"), ("error", "ERROR"), ("skipped", "UNKNOWN")):
                child = node.find(kind)
                if child is not None:
                    status, detail = verdict, child.attrib.get("message", "")
                    if kind == "skipped" and child.attrib.get("type") == "pytest.xfail":
                        status = "KNOWN_GAP"
                    break
            props = {p.attrib["name"]: p.attrib.get("value", "") for p in node.findall("properties/property")}
            cases.append({"name": node.attrib.get("name"), "class": node.attrib.get("classname"),
                          "status": status, "detail": detail, "properties": props})
    source_stable = git(target, "rev-parse", "HEAD") == commit and inventory(target) == source_inventory
    counts = {state: sum(c["status"] == state for c in cases) for state in ("PASS", "FAIL", "ERROR", "UNKNOWN", "KNOWN_GAP")}
    verdict = "FAIL" if not source_stable or (not timed_out and process.returncode not in (0, 5)) else "INCOMPLETE" if timed_out or xml_error or not cases or counts["UNKNOWN"] or counts["KNOWN_GAP"] else "PASS"
    packages = {}
    for name in ("pytest", "hypothesis", "cryptography"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    for package in importlib.metadata.distributions(path=dependency_paths):
        name = package.metadata.get("Name", "").lower()
        if name in packages:
            packages[name] = package.version
    document = {
        "schema_version": "residual-trust-preflight-v1", "verdict": verdict,
        "target_commit": commit, "target_tree": git(target, "rev-parse", "HEAD^{tree}"),
        "target_source_unchanged": source_stable, "target_path": str(target),
        "imported_runtime": imported,
        "source_inventory_sha256": hashlib.sha256(json.dumps(source_inventory, sort_keys=True).encode()).hexdigest(),
        "source_inventory": source_inventory,
        "controlled_environment": env, "dependency_paths": dependency_paths,
        "suite_commit": git(suite_root, "rev-parse", "HEAD"),
        "suite_files": {str(p.relative_to(suite_root)): sha(p) for p in sorted(suite.glob("*.py"))},
        "runner_sha256": sha(Path(__file__)), "command": command,
        "python": sys.version, "platform": platform.platform(), "packages": packages,
        "finished_at": datetime.now(timezone.utc).isoformat(), "elapsed_s": time.monotonic() - start,
        "pytest_exit_code": process.returncode, "counts": counts, "cases": cases,
        "whole_run_timeout_s": args.timeout_s, "termination": "timeout" if timed_out else "exit", "junit_parse_error": xml_error,
        "artifacts": {p.name: sha(p) for p in (output / "stdout.txt", output / "stderr.txt", xml_path) if p.exists()},
        "claim_limit": "Engineering preflight only; incomplete sandbox or strict xfail blocks trust qualification and issue #63 closure.",
    }
    (output / "manifest.json").write_text(json.dumps(document, indent=2) + "\n")
    print(json.dumps({"verdict": verdict, "counts": counts, "manifest": str(output / "manifest.json")}, indent=2))
    return 1 if verdict == "FAIL" else 2 if verdict == "INCOMPLETE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
