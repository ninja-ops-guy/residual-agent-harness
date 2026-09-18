"""Safe self-update support for the RESIDUAL CLI."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path

DISTRIBUTION = "residual-agent-harness"


class UpdateError(RuntimeError):
    """An update could not be completed without weakening safety guarantees."""


def detect_source_checkout(module_file: str | Path | None = None) -> Path | None:
    """Return the repository root when this package is running from a Git checkout."""
    package_file = Path(module_file or __file__).resolve()
    root = package_file.parents[1]
    if (root / ".git").exists() and (root / "pyproject.toml").is_file():
        return root
    return None


def _run_process(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise UpdateError("could not start the update subprocess") from exc


def _git_output(root: Path, args: list[str], error: str) -> str:
    proc = _run_process(["git", *args], cwd=root)
    if proc.returncode != 0:
        raise UpdateError(error)
    return proc.stdout.strip()


def _git_exec(root: Path, args: list[str], error: str) -> None:
    proc = _run_process(["git", *args], cwd=root)
    if proc.returncode != 0:
        raise UpdateError(error)


def update_source(root: Path, *, dry_run: bool = False) -> dict[str, object]:
    """Safely fast-forward a clean source checkout to its configured upstream."""
    root = Path(root).resolve()
    if shutil.which("git") is None:
        raise UpdateError("Git is required to update a source checkout")

    branch = _git_output(
        root,
        ["symbolic-ref", "--quiet", "--short", "HEAD"],
        "source checkout is detached; check out a tracking branch before updating",
    )
    dirty = _git_output(
        root,
        ["status", "--porcelain=v1", "--untracked-files=normal"],
        "could not inspect source checkout state",
    )
    if dirty:
        raise UpdateError("source checkout has uncommitted changes; commit or stash them before updating")

    upstream = _git_output(
        root,
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        "source branch has no configured upstream; configure one before updating",
    )
    before = _git_output(root, ["rev-parse", "HEAD"], "could not identify current source revision")

    if dry_run:
        return {
            "method": "source",
            "status": "ready",
            "branch": branch,
            "upstream": upstream,
            "revision": before,
        }

    _git_exec(
        root,
        ["fetch", "--quiet", "--prune"],
        "could not fetch the configured upstream",
    )
    _git_exec(
        root,
        ["merge", "--ff-only", "@{upstream}"],
        "source branch cannot fast-forward to its upstream; resolve the branch manually",
    )
    after = _git_output(root, ["rev-parse", "HEAD"], "could not identify updated source revision")

    return {
        "method": "source",
        "status": "updated" if after != before else "current",
        "branch": branch,
        "upstream": upstream,
        "from_revision": before,
        "to_revision": after,
    }


def _package_version() -> str | None:
    try:
        return metadata.version(DISTRIBUTION)
    except metadata.PackageNotFoundError:
        return None


def update_package(*, pre: bool = False, dry_run: bool = False) -> dict[str, object]:
    """Upgrade the installed distribution with the interpreter running this CLI."""
    before = _package_version()
    if dry_run:
        return {
            "method": "package",
            "status": "ready",
            "distribution": DISTRIBUTION,
            "version": before,
            "pre": pre,
        }

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
        "--upgrade",
    ]
    if pre:
        cmd.append("--pre")
    cmd.append(DISTRIBUTION)

    proc = _run_process(cmd)
    if proc.returncode != 0:
        # Do not echo pip stderr here: package-index configuration can contain
        # authenticated URLs or other local environment details.
        raise UpdateError("pip could not upgrade residual-agent-harness")

    after = _package_version()
    if after is None:
        raise UpdateError("pip completed but the installed RESIDUAL package could not be identified")

    return {
        "method": "package",
        "status": "updated" if after != before else "current",
        "distribution": DISTRIBUTION,
        "from_version": before,
        "to_version": after,
        "pre": pre,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="residual update",
        description=(
            "Safely update RESIDUAL. Git source checkouts are fast-forwarded only "
            "when clean; installed packages are upgraded with the current Python."
        ),
    )
    parser.add_argument(
        "--method",
        choices=("auto", "source", "package"),
        default="auto",
        help="Update method. auto uses source for Git checkouts, otherwise package.",
    )
    parser.add_argument(
        "--pre",
        action="store_true",
        help="Allow pre-release versions for package updates.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the selected update path without changing files or packages.",
    )
    args = parser.parse_args(argv)

    try:
        checkout = detect_source_checkout()
        method = args.method
        if method == "auto":
            method = "source" if checkout is not None else "package"

        if method == "source":
            if checkout is None:
                raise UpdateError("this RESIDUAL installation is not running from a Git source checkout")
            if args.pre:
                raise UpdateError("--pre applies only to package updates")
            result = update_source(checkout, dry_run=args.dry_run)
        else:
            result = update_package(pre=args.pre, dry_run=args.dry_run)

        print(json.dumps(result, sort_keys=True))
        return 0
    except UpdateError as exc:
        print(f"residual update: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
