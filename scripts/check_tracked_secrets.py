#!/usr/bin/env python3
"""Fail CI if tracked source contains obvious credential material."""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

FORBIDDEN_TRACKED_NAMES = {
    ".env", ".envrc", ".netrc", ".npmrc", ".pypirc",
}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
PATTERNS = {
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "openai_key": re.compile(rb"\bsk-(?:proj-|cp-)?[A-Za-z0-9_-]{40,}\b"),
    "anthropic_key": re.compile(rb"\bsk-ant-[A-Za-z0-9_-]{30,}\b"),
    "github_pat": re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    "github_token": re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "slack_token": re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "google_api_key": re.compile(rb"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "aws_access_key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
}

# Deliberate synthetic strings below threshold remain useful in unit tests.
ALLOW_MARKER = b"residual-secret-scan: allow"


def tracked_files() -> list[Path]:
    raw = subprocess.check_output(["git", "ls-files", "-z"])
    return [Path(p.decode("utf-8")) for p in raw.split(b"\0") if p]


def scan(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if path.name in FORBIDDEN_TRACKED_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append(f"{path}: forbidden credential-bearing filename/type is tracked")
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8192]:
            continue
        scan_data = b"\n".join(
            line for line in data.splitlines() if ALLOW_MARKER not in line
        )
        for name, pattern in PATTERNS.items():
            if pattern.search(scan_data):
                findings.append(f"{path}: matched {name}")
    return findings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    findings = scan(tracked_files())
    if findings:
        print("Tracked-secret scan FAILED:")
        for finding in findings:
            print(" -", finding)
        return 1
    print("Tracked-secret scan PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
