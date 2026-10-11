"""Command-line interface for the full WebVM browser acceptance probe.

Browser selection never relaxes the acceptance assertions in browser_smoke.py.
"""
from __future__ import annotations

import argparse
from pathlib import Path


SUPPORTED_BROWSERS = ("chromium", "firefox", "webkit")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Real WebVM acceptance. Cloud failure tests never authenticate or spend money."
    )
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--browser", choices=SUPPORTED_BROWSERS, default="chromium")
    parser.add_argument("--mobile", action="store_true")
    parser.add_argument("--boot-timeout", type=int, default=120)
    parser.add_argument("--expected-sha", required=True)
    return parser.parse_args(argv)
