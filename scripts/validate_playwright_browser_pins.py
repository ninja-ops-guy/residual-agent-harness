#!/usr/bin/env python3
"""Validate installed Playwright browser revisions against docs/v1/V1_PLAYWRIGHT_BROWSER_PIN_SET.json.

The pin set records the browser revisions that Playwright's own browsers.json
driver manifest resolves for each pinned package version. An arbitrary
installed Chromium does NOT qualify v1: the installed playwright package must
carry a browsers.json whose revisions match this pin set.

Checks:
  1. node_modules/playwright-core/browsers.json == browser_revisions["playwright-core-1.58.0"]
     for the browsers v1 lanes actually launch (chromium, chromium-headless-shell,
     firefox, webkit, ffmpeg).
  2. If the Python 'playwright' package is importable, its driver browsers.json must
     match browser_revisions["playwright-python-1.55.0"] for chromium /
     chromium-headless-shell / ffmpeg.

Exit 0 = pass, 1 = mismatch/missing required install.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN_SET = ROOT / "docs" / "v1" / "V1_PLAYWRIGHT_BROWSER_PIN_SET.json"

# Browsers actually launched by v1 lanes (tip-of-tree/beta entries excluded).
NODE_BROWSERS = ["chromium", "chromium-headless-shell", "firefox", "webkit", "ffmpeg"]
PY_BROWSERS = ["chromium", "chromium-headless-shell", "ffmpeg"]


def fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


def revisions_from(browsers_json: Path) -> dict[str, str]:
    data = json.loads(browsers_json.read_text(encoding="utf-8"))
    return {b["name"]: str(b["revision"]) for b in data["browsers"]}


def check(label: str, actual: dict[str, str], expected: dict[str, str], names: list[str]) -> list[str]:
    problems = []
    for name in names:
        want = expected.get(name)
        got = actual.get(name)
        if want is None:
            problems.append(f"{label}: pin set has no entry for {name!r}")
        elif got != want:
            problems.append(f"{label}: {name} revision {got!r} != pinned {want!r}")
    return problems


def main() -> int:
    pins = json.loads(PIN_SET.read_text(encoding="utf-8"))["browser_revisions"]
    problems: list[str] = []

    node_manifest = ROOT / "node_modules" / "playwright-core" / "browsers.json"
    if not node_manifest.is_file():
        problems.append("node_modules/playwright-core/browsers.json not found (run npm ci first)")
    else:
        actual = revisions_from(node_manifest)
        pkg = ROOT / "node_modules" / "playwright-core" / "package.json"
        version = json.loads(pkg.read_text(encoding="utf-8"))["version"] if pkg.is_file() else "?"
        if version != "1.58.0":
            problems.append(f"installed playwright-core version {version!r} != pinned '1.58.0'")
        problems += check("node", actual, pins["playwright-core-1.58.0"], NODE_BROWSERS)

    try:
        import playwright  # type: ignore
        import os

        py_manifest = Path(os.path.dirname(playwright.__file__)) / "driver" / "package" / "browsers.json"
        if not py_manifest.is_file():
            problems.append("python playwright driver browsers.json not found")
        else:
            actual = revisions_from(py_manifest)
            problems += check("python", actual, pins["playwright-python-1.55.0"], PY_BROWSERS)
    except ImportError:
        # Python playwright is only needed by pages.yml lanes; not fatal elsewhere.
        print("note: python 'playwright' package not installed; skipping python pin check")

    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        return 1
    print("PASS: installed Playwright browser revisions match docs/v1/V1_PLAYWRIGHT_BROWSER_PIN_SET.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
