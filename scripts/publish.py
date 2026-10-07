#!/usr/bin/env python3
"""Publish the committed prototype to a new PRIVATE GitHub repository.

Requires Git and an authenticated GitHub CLI. No tokens are read by this script.
The downloadable archive contains history.bundle; an existing git checkout does
not need that bundle. --dry-run prints the commands without executing anything.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


def publish_commands(root: Path, owner: str, name: str, restore: bool):
    for value in (owner, name):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", value):
            raise ValueError("owner and repository name must be simple GitHub identifiers")
    commands = []
    if restore:
        commands += [["git", "init", "--initial-branch=main", str(root)],
                     ["git", "-C", str(root), "fetch", str(root / "history.bundle"), "main"],
                     ["git", "-C", str(root), "reset", "--mixed", "FETCH_HEAD"]]
    commands += [["gh", "repo", "create", f"{owner}/{name}", "--private", "--source", str(root),
                  "--remote", "origin", "--push", "--description",
                  "Hybrid agent harness for counterexample-directed residual delegation; Ollama and BYO LLMs."]]
    return commands


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", default="ninja-ops-guy")
    parser.add_argument("--name", default="residual-agent-harness")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    restore = not (root / ".git").exists()
    try:
        commands = publish_commands(root, args.owner, args.name, restore)
        if args.dry_run:
            print(json.dumps({"visibility": "private", "commands": commands}, indent=2))
            return 0
        if not shutil.which("git") or not shutil.which("gh"):
            raise ValueError("Install Git and GitHub CLI, then authenticate with gh auth login.")
        subprocess.run(["gh", "auth", "status"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if restore:
            if not (root / "history.bundle").is_file():
                raise ValueError("history.bundle is missing; run from the committed checkout or distributed ZIP.")
            for command in commands[:-1]:
                subprocess.run(command, check=True)
        actual_root = subprocess.check_output(["git", "-C", str(root), "rev-parse", "--show-toplevel"], text=True).strip()
        if Path(actual_root).resolve() != root:
            raise ValueError("Refusing to publish a different enclosing repository.")
        if subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"], capture_output=True).returncode == 0:
            raise ValueError("An origin already exists. Use the normal git push workflow for that repository.")
        if subprocess.check_output(["git", "-C", str(root), "branch", "--show-current"], text=True).strip() != "main":
            raise ValueError("Switch to the intended main branch before publishing.")
        if subprocess.run(["git", "-C", str(root), "diff-index", "--quiet", "HEAD", "--"]).returncode:
            raise ValueError("Commit tracked changes before publishing.")
        subprocess.run(commands[-1], check=True)
        return 0
    except (ValueError, subprocess.CalledProcessError) as exc:
        message = str(exc) if isinstance(exc, ValueError) else "Git/GitHub CLI failed; check authentication and repository permissions."
        print(message)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
