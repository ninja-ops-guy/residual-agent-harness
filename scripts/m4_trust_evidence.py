#!/usr/bin/env python3
"""Generate machine-readable M4 trust-boundary evidence into runs/m4-trust/.

Runs the adversarial verification trials, the filesystem red team, the Git
evidence-state matrix and the dedicated M4 pytest suites, recording raw logs
and per-trial tree hashes. Never reclassifies a failure: every outcome is
stored verbatim.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "runs" / "m4-trust"
LOGS = OUT / "sandbox-logs"

SOURCE_COMMIT = "610ce42ebf1d7f32f4c976174661225a947c783a"
PR66_HEAD = "3961f52b45c4d5a167b5e346790451392572646d"


def tree_hash(directory: Path) -> str:
    from residual.factory.m4_safety import snapshot
    inventory = snapshot(directory)
    return hashlib.sha256(json.dumps(
        {k: list(v) for k, v in sorted(inventory.items())}, sort_keys=True
    ).encode()).hexdigest()


def environment() -> dict:
    def version_of(*argv):
        try:
            return subprocess.run(argv, capture_output=True, text=True, timeout=10).stdout.strip()
        except OSError:
            return "unavailable"
    import cryptography
    import pytest
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "kernel": platform.release(),
        "unshare": version_of("unshare", "--version"),
        "git": version_of("git", "--version"),
        "pytest": pytest.__version__,
        "cryptography": cryptography.__version__,
    }


def adversarial_trials() -> list[dict]:
    from residual.factory.m4_sandbox import probe_isolation, run_isolated
    ok, probe_reason = probe_isolation()
    trials = []
    scenarios = {
        "extra_file_creation": "open('trial-extra.txt','w').write('x')",
        "candidate_artifact_mutation": "open('candidate.txt','w').write('evil')",
        "network_exfiltration_attempt":
            "import socket; socket.create_connection(('203.0.113.1',443),2)",
        "external_filesystem_write_attempt": "open('/etc/m4-pwned','w').write('x')",
        "infinite_loop": "while True: pass",
        "infinite_output": "import sys\nwhile True: sys.stdout.write('x'*65536)",
        "fork_descendant_escape": (
            "import os,time\n"
            "if os.fork()==0:\n time.sleep(300); os._exit(0)\n"
        ),
    }
    for name, code in scenarios.items():
        trial = {"scenario": name, "isolation_available": ok}
        with tempfile.TemporaryDirectory() as tmp:
            worktree = Path(tmp) / "worktree"
            worktree.mkdir()
            (worktree / "candidate.txt").write_text("candidate-bytes")
            before = tree_hash(worktree)
            trial["tree_hash_before"] = before
            if ok:
                start = time.monotonic()
                result = run_isolated(("/usr/bin/python3", "-c", code), worktree,
                                      timeout_s=5, output_limit=1 << 16)
                trial["wall_s"] = round(time.monotonic() - start, 3)
                trial["sandbox_result"] = {
                    "status": result.status, "returncode": result.returncode,
                    "reason": result.reason,
                    "stdout_sha256": result.stdout_sha256,
                    "stderr_sha256": result.stderr_sha256,
                    "execution_boundary": result.execution_boundary,
                }
            else:
                trial["sandbox_result"] = {"status": "unknown",
                                           "reason": f"isolation_unavailable:{probe_reason}"}
            after = tree_hash(worktree)
            trial["tree_hash_after"] = after
            trial["tree_unchanged"] = before == after
        trials.append(trial)
    return trials


def git_evidence_matrix() -> list[dict]:
    from residual.factory.m4_git_evidence import read_base_blob
    from residual.factory.runtime_workspace import git
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        (repo / "present.txt").write_bytes(b"content\n")
        git(repo, "init")
        git(repo, "add", ".")
        git(repo, "-c", "user.name=t", "-c", "user.email=t@l", "commit", "-m", "base")
        base = git(repo, "rev-parse", "HEAD").decode().strip()

        def row(name, commit, path):
            ev = read_base_blob(repo, commit, path)
            rows.append({"scenario": name, "state": ev.state.value, "detail": ev.detail,
                         "has_data": ev.data is not None})

        row("valid_base_absent_path", base, "missing.txt")
        row("valid_base_present_path", base, "present.txt")
        row("malformed_commit_ref", "not-a-sha", "present.txt")
        row("nonexistent_commit", "0" * 40, "present.txt")
        oid = git(repo, "rev-parse", f"{base}:present.txt").decode().strip()
        (repo / ".git" / "objects" / oid[:2] / oid[2:]).unlink()
        row("corrupt_missing_object", base, "present.txt")
        empty = Path(tmp) / "not-a-repo"
        empty.mkdir()
        ev = read_base_blob(empty, base, "present.txt")
        rows.append({"scenario": "missing_repository_evidence", "state": ev.state.value,
                     "detail": ev.detail, "has_data": ev.data is not None})
    return rows


def canonical_api_report() -> dict:
    import residual.integrations as integrations
    from residual.factory import m4_evidence, m4_integrator, m4_scheduler
    return {
        "decision": {
            "integration_receipt_schema": {
                "canonical": "residual.factory.m4_integrator.IntegrationReceipt",
                "schema_version": m4_integrator.INTEGRATION_SCHEMA,
                "renamed_parallel_api": (
                    "residual.integrations.base.IntegrationReceipt -> ConnectorReceipt "
                    "(enterprise connector transport receipt, unrelated semantics)"
                ),
                "parallel_name_removed": not hasattr(integrations, "IntegrationReceipt"),
            },
            "scheduler_decision_schema": {
                "canonical": "residual.factory.m4_scheduler",
                "schemas": ["factory-m4-scheduler-measurements-v1",
                            "factory-m4-structural-replan-v1",
                            "factory-m4-ready-dag-v1"],
            },
            "conflict_resolution_schema": {
                "canonical": "residual.factory.m4_integrator.ConflictResolution",
            },
            "verifier_result_interface": {
                "canonical": "residual.factory.m4_integrator.VerificationResult",
                "typed_statuses": ["pass", "fail", "unknown", "error"],
                "execution_boundaries": ["linux-userns-isolated-v1",
                                          "trusted_fixture_unsandboxed (development only)"],
            },
        },
        "issues_reconciled": ["#22", "#24", "#26"],
        "notes": (
            "Older evaluation/fault/benchmark adapters do not import the M4 API in this "
            "tree (verified by grep over residual/eval); the only parallel live surface "
            "was the enterprise IntegrationReceipt name, now renamed. measurement/eval "
            "code continues to consume evidence_receipts (M3) unchanged."
        ),
    }


def run_suite(name: str, paths: list[str]) -> dict:
    log = LOGS / f"{name}.log"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *paths, "-v", "--tb=short"],
        capture_output=True, text=True, cwd=ROOT, timeout=1800,
    )
    log.write_text(result.stdout + "\n--- STDERR ---\n" + result.stderr)
    summary = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
    return {"suite": name, "paths": paths, "returncode": result.returncode,
            "summary": summary, "log": str(log.relative_to(ROOT))}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "m4-trust-report-v1",
        "issue": 63,
        "source_commit_main": SOURCE_COMMIT,
        "based_on_pr66_head": PR66_HEAD,
        "generated_at_ns": time.time_ns(),
        "environment": environment(),
    }
    report["git_evidence_matrix"] = git_evidence_matrix()
    (OUT / "git-evidence-matrix.json").write_text(json.dumps(report["git_evidence_matrix"], indent=2))
    report["adversarial_trials"] = adversarial_trials()
    (OUT / "tree-hashes.json").write_text(json.dumps(report["adversarial_trials"], indent=2))
    report["canonical_api"] = canonical_api_report()
    (OUT / "canonical-api-report.json").write_text(json.dumps(report["canonical_api"], indent=2))
    report["suites"] = [
        run_suite("sandbox", ["tests/test_factory_m4_sandbox.py"]),
        run_suite("tree-binding", ["tests/test_factory_m4_tree_binding.py"]),
        run_suite("fs-redteam", ["tests/test_factory_m4_fs_redteam.py"]),
        run_suite("git-evidence", ["tests/test_factory_m4_git_evidence.py"]),
        run_suite("canonical-api", ["tests/test_factory_m4_canonical_api.py"]),
        run_suite("m4-regression", [
            "tests/test_factory_m4_integrator.py", "tests/test_factory_m4_safety.py",
            "tests/test_factory_m4_attribution.py", "tests/test_factory_m4_evidence.py",
            "tests/test_factory_m4_scheduler.py",
        ]),
    ]
    (OUT / "m4-trust-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"suites": report["suites"]}, indent=2))


if __name__ == "__main__":
    main()
