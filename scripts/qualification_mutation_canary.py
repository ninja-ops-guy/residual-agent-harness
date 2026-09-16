#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Mutation:
    name: str
    path: str
    old: str
    new: str
    tests: tuple[str, ...]


MUTATIONS = (
    Mutation(
        "revoked-candidate-acceptance",
        "residual/factory/runtime_journal.py",
        """            if state == 'CANDIDATE' and row[1]:
                raise JournalError("revoked attempt cannot produce a candidate")""",
        """            if state == 'CANDIDATE' and not row[1]:
                raise JournalError("revoked attempt cannot produce a candidate")""",
        ("tests/qualification/test_trust_boundary_canaries.py::test_revoked_attempt_can_never_publish_candidate",),
    ),
    Mutation(
        "candidate-lease-resurrection",
        "residual/factory/runtime_journal.py",
        "and not row[2] and row[3] in ('RESERVED', 'RUNNING')\n                    and row[4] == contract.contract_hash)",
        "and not row[2] and row[3] in ('RESERVED', 'RUNNING', 'CANDIDATE')\n                    and row[4] == contract.contract_hash)",
        ("tests/qualification/test_trust_boundary_canaries.py::test_candidate_is_no_longer_an_authoritative_current_lease",),
    ),
    Mutation(
        "git-path-policy-bypass",
        "residual/factory/worker_contract.py",
        """        if any(part.lower() == ".git" for part in path.split("/")):
            return False
        if any(_matches(path, item) for item in self.forbidden):""",
        """        if any(part.lower() == ".git" for part in path.split("/")):
            return True
        if any(_matches(path, item) for item in self.forbidden):""",
        ("tests/qualification/test_trust_boundary_canaries.py::test_git_metadata_is_never_permitted_by_worker_path_policy",),
    ),
    Mutation(
        "forbidden-prefix-bypass",
        "residual/factory/worker_contract.py",
        """        if any(part.lower() == ".git" for part in path.split("/")):
            return False
        if any(_matches(path, item) for item in self.forbidden):
            return False
        return any(_matches(path, item) for item in (self.allowed_outputs if write else self.inputs))""",
        """        if any(part.lower() == ".git" for part in path.split("/")):
            return False
        if any(_matches(path, item) for item in self.forbidden):
            return True
        return any(_matches(path, item) for item in (self.allowed_outputs if write else self.inputs))""",
        ("tests/qualification/test_trust_boundary_canaries.py::test_forbidden_prefix_wins_over_read_allowlist",),
    ),
)


def mutation_site_count(mutation: Mutation, *, root: Path = ROOT) -> int:
    return (root / mutation.path).read_text(encoding="utf-8").count(mutation.old)


def validate_mutation_sites(*, root: Path = ROOT) -> list[dict[str, object]]:
    """Return every mutation whose source selector is not exactly unique.

    Mutation qualification is meaningful only when the intended semantic site is
    unambiguous. A source refactor therefore fails this harness explicitly instead
    of mutating whichever textual occurrence happens to come first.
    """
    invalid = []
    for mutation in MUTATIONS:
        count = mutation_site_count(mutation, root=root)
        if count != 1:
            invalid.append({"name": mutation.name, "path": mutation.path, "site_count": count})
    return invalid


def run_mutation(mutation: Mutation) -> dict:
    path = ROOT / mutation.path
    original = path.read_text(encoding="utf-8")
    count = original.count(mutation.old)
    if count != 1:
        return {
            "name": mutation.name,
            "path": mutation.path,
            "result": "ERROR",
            "reason": f"expected one scoped mutation site, found {count}",
        }
    mutated = original.replace(mutation.old, mutation.new, 1)
    try:
        path.write_text(mutated, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", *mutation.tests],
            cwd=ROOT, capture_output=True, text=True, timeout=180, check=False,
        )
    finally:
        path.write_text(original, encoding="utf-8")
    killed = proc.returncode != 0
    return {
        "name": mutation.name,
        "path": mutation.path,
        "tests": list(mutation.tests),
        "result": "KILLED" if killed else "SURVIVED",
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic trust-boundary mutation canaries")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    invalid = validate_mutation_sites()
    if invalid:
        report = {
            "schema": "residual.qualification.mutation.v1",
            "mutants": len(MUTATIONS),
            "killed": 0,
            "survived_or_error": len(MUTATIONS),
            "mutation_score": 0.0,
            "result": "FAIL",
            "harness_errors": invalid,
            "results": [],
        }
    else:
        results = [run_mutation(m) for m in MUTATIONS]
        survivors = [r for r in results if r["result"] != "KILLED"]
        report = {
            "schema": "residual.qualification.mutation.v1",
            "mutants": len(results),
            "killed": len(results) - len(survivors),
            "survived_or_error": len(survivors),
            "mutation_score": (len(results) - len(survivors)) / len(results) if results else 0.0,
            "result": "PASS" if not survivors else "FAIL",
            "results": results,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
