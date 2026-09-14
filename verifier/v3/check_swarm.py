#!/usr/bin/env python3
"""8-swarm acceptance gate; committed-tree ownership checks fail closed.

The original swarm baseline still protects the legacy directories. The separate
Factory baseline protects the canonical M2/M3/M4 trust surface. Advance that
baseline only in an explicitly reviewed, authorized Factory-owner change.

--ownership-only runs just the ownership preflight, not full qualification.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "98c12f0"
# Exact synthetic composition of the independently reviewed current-main M2
# lifecycle repair (#68) and M4 accepted-state safety repair (#66). This SHA is
# review evidence, not permission to advance to an arbitrary newer main commit.
OWNERSHIP_BASELINE = "9aa29001c7bb5fc533ae3524017c9b4efdaed837"
REQUIRED_PATHS = [
    "implementation-status.yaml", "scripts/status_check.py",
    "docs/status/IMPLEMENTATION_STATUS.md",
    "residual/sandbox", "tests/redteam",
    "residual/cluster", "residual/orchestrator",
    "residual/eval", "residual/soak",
    "residual/gateway", "residual/lifecycle_glue",
    "residual/crypto", "residual/connectors/conformance",
    "residual/studio_frontend", "examples/onboarding",
]
PROTECTED = (
    "residual/swarm", "residual/evidence",
    "residual/scheduler", "residual/integrator",
)
PROTECTED_FILES = frozenset({
    "residual/factory/_sandbox_child.py",
    "residual/factory/evidence_bus.py",
    "residual/factory/evidence_receipts.py",
    "residual/factory/m4_evidence.py",
    "residual/factory/m4_integrator.py",
    "residual/factory/m4_safety.py",
    "residual/factory/m4_scheduler.py",
    "residual/factory/runtime.py",
    "residual/factory/runtime_journal.py",
    "residual/factory/runtime_workspace.py",
    "residual/factory/station_issuer.py",
    "residual/factory/worker_contract.py",
})


class GitEvidenceError(RuntimeError):
    """History or comparison evidence is unavailable; never means no changes."""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", "--no-replace-objects", "-C", str(root), *args],
            capture_output=True, text=True, errors="surrogateescape", timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitEvidenceError(f"git {args[0]} unavailable: {exc}") from exc
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-2000:]
        raise GitEvidenceError(
            f"git {args[0]} failed (exit {result.returncode}): {detail}"
        )
    return result


def _commit(root: Path, ref: str) -> str:
    return _git(
        root, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}"
    ).stdout.strip()


def _changed_paths(root: Path, baseline: str, head: str) -> list[str]:
    _git(root, "merge-base", "--is-ancestor", baseline, head)
    # NUL delimiters preserve whitespace in filenames. Disabling renames means
    # moving a protected file out of its directory still exposes its deletion.
    result = _git(
        root, "diff", "--no-ext-diff", "--no-textconv", "--no-renames",
        "--name-only", "-z", baseline, head, "--",
    )
    return [path for path in result.stdout.split("\0") if path]


def evaluate_ownership(
    root: Path, baseline: str = BASELINE,
    ownership_baseline: str = OWNERSHIP_BASELINE,
) -> tuple[dict[str, object], list[str]]:
    """Check committed HEAD; missing evidence yields null counts and failure."""
    report: dict[str, object] = {
        "scope": "committed-tree ownership",
        "head": None,
        "reporting_baseline": baseline,
        "ownership_baseline": ownership_baseline,
        "resolved_reporting_baseline": None,
        "resolved_ownership_baseline": None,
        "changed_files": None,
        "ownership_changed_files": None,
        "protected_files": len(PROTECTED_FILES),
    }
    failures: list[str] = []
    try:
        head = _commit(root, "HEAD")
        report["head"] = head
    except GitEvidenceError as exc:
        return report, [f"HEAD evidence unavailable: {exc}"]

    for label, ref, resolved_key, count_key in (
        ("reporting", baseline, "resolved_reporting_baseline", "changed_files"),
        ("Factory ownership", ownership_baseline,
         "resolved_ownership_baseline", "ownership_changed_files"),
    ):
        try:
            resolved = _commit(root, ref)
            report[resolved_key] = resolved
            changed = _changed_paths(root, resolved, head)
            report[count_key] = len(changed)
        except GitEvidenceError as exc:
            failures.append(f"{label} evidence unavailable for {ref}: {exc}")
            continue
        if label == "reporting":
            hits = [p for p in changed if any(
                p == prefix or p.startswith(prefix + "/") for prefix in PROTECTED
            )]
        else:
            hits = sorted(PROTECTED_FILES.intersection(changed))
        if hits:
            failures.append(f"{label} protected paths modified: {', '.join(hits)}")
    return report, failures


def _run_check(root: Path, label: str, command: list[str]) -> tuple[str, str | None]:
    try:
        result = subprocess.run(
            command, cwd=root, capture_output=True, text=True, timeout=900,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "unavailable", f"{label} could not complete: {exc}"
    output = result.stdout.strip()
    summary = output.splitlines()[-1] if output else "no stdout"
    if result.returncode:
        return summary, (
            f"{label} failed (exit {result.returncode})\n"
            f"stdout:\n{result.stdout[-2000:]}\nstderr:\n{result.stderr[-2000:]}"
        )
    return summary, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ownership-only", action="store_true")
    args = parser.parse_args(argv)
    report, failures = evaluate_ownership(ROOT)
    report.update({"pytest": "NOT RUN", "verifier_v2": "NOT RUN"})
    if not args.ownership_only:
        failures.extend(
            f"missing deliverable path: {path}" for path in REQUIRED_PATHS
            if not (ROOT / path).exists()
        )
        if not failures:
            for key, label, command in (
                ("pytest", "pytest", [sys.executable, "-m", "pytest", "tests", "-q"]),
                ("verifier_v2", "verifier v2",
                 [sys.executable, "verifier/v2/check_specs.py"]),
            ):
                report[key], failure = _run_check(ROOT, label, command)
                if failure:
                    failures.append(failure)
    report["passed"] = not failures
    print(json.dumps(report, indent=2))
    if failures:
        print("FAIL:\n - " + "\n - ".join(failures))
        return 1
    if args.ownership_only:
        print("PASS: ownership preflight only; full qualification NOT RUN")
    else:
        print("PASS: 8-swarm acceptance checks green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
