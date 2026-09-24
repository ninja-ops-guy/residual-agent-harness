#!/usr/bin/env python3
"""Read-only AUD-1 helper/candidate reconciliation preflight.

This tool never edits either checkout. It exists so the eventual #403 successor
retarget is explicit, exact-SHA bound, and reviewable after candidate selection.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess

FROZEN_HELPER_SHA = "118ec3c795ae11c88b68278717fb781f4b059559"
FROZEN_TARGET_SHA = "8df77b832b3839ccd2a6944a65760ce3ab10dc9c"

CODE_BINDINGS = {
    "tools/aud1/f6_collect.py": f'TARGET_SHA = "{FROZEN_TARGET_SHA}"',
    "tools/aud1/Run-F6-Physical.ps1": f'$Target = "{FROZEN_TARGET_SHA}"',
}
TRANSITIVE_BINDINGS = {
    "tools/aud1/f6_case_guard.py": "TARGET_SHA = base.TARGET_SHA",
    "tests/tools/test_aud1_f6_guard.py": "guard.TARGET_SHA",
}
DOCUMENT_BINDING = "tools/aud1/README.md"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git(repo, *args):
    p = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def repo_identity(repo):
    repo = pathlib.Path(repo).resolve()
    rc_head, head, err_head = git(repo, "rev-parse", "HEAD")
    rc_tree, tree, err_tree = git(repo, "rev-parse", "HEAD^{tree}")
    rc_status, status, err_status = git(repo, "status", "--porcelain=v1")
    return {
        "path": str(repo),
        "head_sha": head if rc_head == 0 else "",
        "tree_sha": tree if rc_tree == 0 else "",
        "clean_worktree": rc_status == 0 and not status,
        "git_errors": [x for x in (err_head, err_tree, err_status) if x],
    }


def valid_sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{40}", value) is not None


def inspect_bindings(helper_repo, proposed_target):
    helper_repo = pathlib.Path(helper_repo).resolve()
    errors = []
    bindings = []
    hashes_before = {}

    for relative, marker in CODE_BINDINGS.items():
        path = helper_repo / relative
        if not path.is_file():
            errors.append(f"missing required helper binding file: {relative}")
            continue
        hashes_before[relative] = sha256_file(path)
        text = path.read_text(encoding="utf-8")
        count = text.count(marker)
        if count != 1:
            errors.append(f"{relative}: expected exactly one frozen target binding, found {count}")
        if proposed_target != FROZEN_TARGET_SHA and proposed_target in text:
            errors.append(f"{relative}: proposed target is already embedded before selection")
        bindings.append({
            "path": relative,
            "kind": "direct-code",
            "frozen_marker_count": count,
            "current_target": FROZEN_TARGET_SHA,
            "proposed_target": proposed_target,
            "change_required_after_selection": proposed_target != FROZEN_TARGET_SHA,
        })

    for relative, marker in TRANSITIVE_BINDINGS.items():
        path = helper_repo / relative
        if not path.is_file():
            errors.append(f"missing required transitive binding file: {relative}")
            continue
        hashes_before[relative] = sha256_file(path)
        text = path.read_text(encoding="utf-8")
        count = text.count(marker)
        if count < 1:
            errors.append(f"{relative}: target-binding invariant marker is missing")
        bindings.append({
            "path": relative,
            "kind": "transitive-guard",
            "marker": marker,
            "marker_count": count,
            "change_required_after_selection": False,
        })

    readme = helper_repo / DOCUMENT_BINDING
    if not readme.is_file():
        errors.append(f"missing helper documentation: {DOCUMENT_BINDING}")
    else:
        hashes_before[DOCUMENT_BINDING] = sha256_file(readme)
        text = readme.read_text(encoding="utf-8")
        count = text.count(FROZEN_TARGET_SHA)
        if count < 1:
            errors.append("README no longer documents the frozen #399 target")
        bindings.append({
            "path": DOCUMENT_BINDING,
            "kind": "documentation",
            "frozen_target_occurrences": count,
            "change_required_after_selection": proposed_target != FROZEN_TARGET_SHA,
        })

    hashes_after = {
        relative: sha256_file(helper_repo / relative)
        for relative in hashes_before
    }
    if hashes_after != hashes_before:
        errors.append("helper files changed during read-only preflight")

    return bindings, hashes_before, errors


def preflight(helper_repo, candidate_repo, proposed_target):
    if not valid_sha(proposed_target):
        raise ValueError("proposed target must be an exact 40-character hexadecimal commit SHA")
    proposed_target = proposed_target.lower()

    helper = repo_identity(helper_repo)
    candidate = repo_identity(candidate_repo)
    errors = []

    if helper["head_sha"] != FROZEN_HELPER_SHA:
        errors.append(
            f"helper checkout is {helper['head_sha']!r}; expected frozen #403 head {FROZEN_HELPER_SHA}"
        )
    if not helper["clean_worktree"]:
        errors.append("helper checkout is dirty")
    if helper["git_errors"]:
        errors.append("helper git identity could not be read cleanly")

    if candidate["head_sha"].lower() != proposed_target:
        errors.append(
            f"candidate checkout is {candidate['head_sha']!r}; expected proposed target {proposed_target}"
        )
    if not candidate["clean_worktree"]:
        errors.append("candidate checkout is dirty")
    if candidate["git_errors"]:
        errors.append("candidate git identity could not be read cleanly")

    bindings, hashes, binding_errors = inspect_bindings(helper_repo, proposed_target)
    errors.extend(binding_errors)

    if errors:
        status = "REFUSE"
    elif proposed_target == FROZEN_TARGET_SHA:
        status = "CURRENT_TARGET_MATCH"
    else:
        status = "PREPARED_NOT_AUTHORIZED"

    return {
        "schema": "residual.aud1.helper-retarget-preflight.v1",
        "status": status,
        "mutated": False,
        "frozen_helper": {
            "expected_head": FROZEN_HELPER_SHA,
            **helper,
        },
        "candidate": {
            "proposed_target": proposed_target,
            **candidate,
        },
        "current_helper_target": FROZEN_TARGET_SHA,
        "bindings": bindings,
        "helper_file_sha256": hashes,
        "required_after_selection": [
            "record explicit owner candidate selection bound to one exact SHA",
            "create a new helper successor from frozen #403; do not rewrite #403",
            "atomically update both direct code bindings and helper documentation to the selected SHA",
            "retain exact-head/clean-worktree, Station-process provenance, stale-result, and closed-world evidence guards",
            "run fresh exact-head helper CI before any physical F6 execution",
        ],
        "errors": errors,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only preflight for a future AUD-1 #403 helper reconciliation"
    )
    parser.add_argument("--helper-repo", required=True)
    parser.add_argument("--candidate-repo", required=True)
    parser.add_argument("--proposed-target", required=True)
    args = parser.parse_args(argv)

    try:
        result = preflight(args.helper_repo, args.candidate_repo, args.proposed_target)
    except ValueError as exc:
        result = {
            "schema": "residual.aud1.helper-retarget-preflight.v1",
            "status": "REFUSE",
            "mutated": False,
            "errors": [str(exc)],
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"CURRENT_TARGET_MATCH", "PREPARED_NOT_AUTHORIZED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
