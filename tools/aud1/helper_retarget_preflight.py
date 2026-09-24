#!/usr/bin/env python3
"""Fail-closed reconciliation validator for the selected AUD-1 F6 helper."""
from __future__ import annotations

import argparse, hashlib, json, pathlib, re, subprocess

FROZEN_399_SHA = "8df77b832b3839ccd2a6944a65760ce3ab10dc9c"
FROZEN_HELPER_SHA = "118ec3c795ae11c88b68278717fb781f4b059559"
PREPARATION_SHA = "2edee868c30c0a349adb45bff8fbded102fb783c"
STALE_438_SHA = "e815f33484352f100e11b8d075bb954a815244cc"
SELECTED_SHA = "7001bdf68355b7e5288a8cea3f4c827061aca37d"
SELECTED_TREE = "6d60dd39d8c3af8d900843eb5661ca974d9a91b5"

CODE_BINDINGS = {
    "tools/aud1/f6_collect.py": f'TARGET_SHA = "{SELECTED_SHA}"',
    "tools/aud1/Run-F6-Physical.ps1": f'$Target = "{SELECTED_SHA}"',
    "tools/aud1/f6_bound_station.py": f'TARGET_SHA = "{SELECTED_SHA}"',
}
TRANSITIVE_BINDINGS = {
    "tools/aud1/f6_case_guard.py": "TARGET_SHA = base.TARGET_SHA",
    "tests/tools/test_aud1_f6_guard.py": "guard.TARGET_SHA",
}
DOCUMENT_BINDINGS = {
    "tools/aud1/README.md": SELECTED_SHA,
    "tools/aud1/STRICT-PHYSICAL-GATE.md": SELECTED_SHA,
}
SCAN_ROOTS = ("tools/aud1", "tests/tools")
EXTRA_SCAN_FILES = ("docs/security/AUD1_POST_REVIEW_EXECUTION_PACKET.md", "docs/security/AUD1_MASON_REAUDIT_PACKET.md")
SHA_RE = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{40}(?![0-9a-fA-F])")
HISTORICAL_LITERALS = {
    ("tools/aud1/STRICT-PHYSICAL-GATE.md", "03a89dfe0c76e4eaea1406304e9f41a78255a402"): "historical helper-review evidence",
    ("tools/aud1/helper_retarget_preflight.py", FROZEN_399_SHA): "frozen #399 evidence identity",
    ("tools/aud1/helper_retarget_preflight.py", FROZEN_HELPER_SHA): "frozen #403 ancestry identity",
    ("tools/aud1/helper_retarget_preflight.py", PREPARATION_SHA): "unchanged #439 preparation reference",
    ("tools/aud1/helper_retarget_preflight.py", STALE_438_SHA): "stale #438 negative-test identity",
    ("tools/aud1/helper_retarget_preflight.py", SELECTED_TREE): "selected candidate tree binding",
    ("tools/aud1/helper_retarget_preflight.py", "03a89dfe0c76e4eaea1406304e9f41a78255a402"): "historical helper-review evidence allowlist",
    ("tools/aud1/helper_retarget_preflight.py", "2f9dda3882f39c28a1c766859b1bf9579eea7911"): "original audit baseline evidence allowlist",
    ("tools/aud1/helper_retarget_preflight.py", "ee0009145f0dcc8207eceda98719db04a9af46cf"): "historical #438 tree evidence allowlist",
    ("tests/tools/test_aud1_helper_retarget_preflight.py", FROZEN_399_SHA): "frozen #399 negative-test fixture",
    ("tests/tools/test_aud1_helper_retarget_preflight.py", FROZEN_HELPER_SHA): "frozen #403 negative-test fixture",
    ("tests/tools/test_aud1_helper_retarget_preflight.py", STALE_438_SHA): "stale #438 negative-test fixture",
    ("docs/security/AUD1_POST_REVIEW_EXECUTION_PACKET.md", FROZEN_399_SHA): "frozen #399 evidence identity",
    ("docs/security/AUD1_POST_REVIEW_EXECUTION_PACKET.md", FROZEN_HELPER_SHA): "frozen #403 ancestry identity",
    ("docs/security/AUD1_POST_REVIEW_EXECUTION_PACKET.md", STALE_438_SHA): "historical #438 review evidence",
    ("docs/security/AUD1_MASON_REAUDIT_PACKET.md", FROZEN_399_SHA): "frozen #399 evidence identity",
    ("docs/security/AUD1_MASON_REAUDIT_PACKET.md", STALE_438_SHA): "historical #438 review evidence",
    ("docs/security/AUD1_MASON_REAUDIT_PACKET.md", "2f9dda3882f39c28a1c766859b1bf9579eea7911"): "original audit baseline evidence",
    ("docs/security/AUD1_MASON_REAUDIT_PACKET.md", "ee0009145f0dcc8207eceda98719db04a9af46cf"): "historical #438 tree evidence",
}


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(repo, *args):
    proc = subprocess.run(["git", "-C", str(repo), *args], text=True, capture_output=True, timeout=15, check=False)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def repo_identity(repo):
    repo = pathlib.Path(repo).resolve()
    rh, head, eh = git(repo, "rev-parse", "HEAD")
    rt, tree, et = git(repo, "rev-parse", "HEAD^{tree}")
    rs, status, es = git(repo, "status", "--porcelain=v1")
    ra, _, ea = git(repo, "merge-base", "--is-ancestor", FROZEN_HELPER_SHA, "HEAD")
    return {"path": str(repo), "head_sha": head if rh == 0 else "", "tree_sha": tree if rt == 0 else "", "clean_worktree": rs == 0 and not status, "frozen_403_ancestor": ra == 0, "git_errors": [x for x in (eh, et, es) if x] + ([] if ra in (0, 1) else [ea])}


def text_files(helper_repo):
    root = pathlib.Path(helper_repo).resolve()
    for root_name in SCAN_ROOTS:
        scan_root = root / root_name
        if scan_root.exists():
            yield from (
                path for path in sorted(scan_root.rglob("*"))
                if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
            )
    for relative in EXTRA_SCAN_FILES:
        path = root / relative
        if path.is_file():
            yield path


def scoped_hashes(helper_repo):
    root = pathlib.Path(helper_repo).resolve()
    return {p.relative_to(root).as_posix(): sha256_file(p) for p in text_files(root)}


def inspect_bindings(helper_repo):
    root = pathlib.Path(helper_repo).resolve()
    errors, bindings, literals = [], [], []
    before = scoped_hashes(root)
    for relative, marker in CODE_BINDINGS.items():
        path = root / relative
        body = path.read_text(encoding="utf-8") if path.is_file() else ""
        count = body.count(marker)
        if count != 1:
            errors.append(f"{relative}: expected exactly one selected executable pin, found {count}")
        bindings.append({"path": relative, "kind": "executable", "count": count})
    for relative, marker in TRANSITIVE_BINDINGS.items():
        path = root / relative
        body = path.read_text(encoding="utf-8") if path.is_file() else ""
        count = body.count(marker)
        if count < 1:
            errors.append(f"{relative}: target-binding invariant marker is missing")
        bindings.append({"path": relative, "kind": "transitive", "count": count})
    for relative, marker in DOCUMENT_BINDINGS.items():
        path = root / relative
        body = path.read_text(encoding="utf-8") if path.is_file() else ""
        count = body.count(marker)
        if count < 1:
            errors.append(f"{relative}: selected documentation pin is missing")
        bindings.append({"path": relative, "kind": "documentation", "count": count})
    for path in text_files(root):
        relative = path.relative_to(root).as_posix()
        try:
            body = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for sha in SHA_RE.findall(body):
            classification = "selected-candidate" if sha == SELECTED_SHA else HISTORICAL_LITERALS.get((relative, sha))
            literals.append({"path": relative, "sha": sha, "classification": classification})
            if classification is None:
                errors.append(f"unaccounted target-like literal {sha} in {relative}")
    if scoped_hashes(root) != before:
        errors.append("helper files changed during read-only preflight")
    return bindings, literals, before, errors


def preflight(helper_repo, candidate_repo, expected_helper_head):
    if not re.fullmatch(r"[0-9a-fA-F]{40}", expected_helper_head or ""):
        raise ValueError("expected helper head must be an exact 40-character hexadecimal commit SHA")
    helper, candidate = repo_identity(helper_repo), repo_identity(candidate_repo)
    errors = []
    if helper["head_sha"] != expected_helper_head.lower(): errors.append(f"helper checkout is {helper['head_sha']!r}; expected helper identity {expected_helper_head.lower()}")
    if not helper["clean_worktree"]: errors.append("helper checkout is dirty")
    if not helper["frozen_403_ancestor"]: errors.append(f"helper is not derived from frozen #403 {FROZEN_HELPER_SHA}")
    if helper["git_errors"]: errors.append("helper git identity could not be read cleanly")
    if candidate["head_sha"] != SELECTED_SHA: errors.append(f"candidate checkout is {candidate['head_sha']!r}; expected selected candidate {SELECTED_SHA}")
    if candidate["tree_sha"] != SELECTED_TREE: errors.append(f"candidate tree is {candidate['tree_sha']!r}; expected selected tree {SELECTED_TREE}")
    if not candidate["clean_worktree"]: errors.append("candidate checkout is dirty")
    if candidate["git_errors"]: errors.append("candidate git identity could not be read cleanly")
    bindings, literals, hashes, scan_errors = inspect_bindings(helper_repo)
    errors.extend(scan_errors)
    return {"schema": "residual.aud1.helper-reconciliation.v2", "status": "PASS" if not errors else "REFUSE", "mutated": False, "frozen_helper_sha": FROZEN_HELPER_SHA, "preparation_reference": PREPARATION_SHA, "selected_sha": SELECTED_SHA, "selected_tree": SELECTED_TREE, "helper": helper, "candidate": candidate, "bindings": bindings, "literal_inventory": literals, "helper_scope_sha256": hashes, "errors": errors, "physical_f6_executed": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate selected AUD-1 helper reconciliation without physical execution")
    parser.add_argument("--helper-repo", required=True)
    parser.add_argument("--candidate-repo", required=True)
    parser.add_argument("--expected-helper-head", required=True)
    args = parser.parse_args(argv)
    try: result = preflight(args.helper_repo, args.candidate_repo, args.expected_helper_head)
    except ValueError as exc: result = {"schema": "residual.aud1.helper-reconciliation.v2", "status": "REFUSE", "mutated": False, "errors": [str(exc)]}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
