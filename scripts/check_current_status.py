#!/usr/bin/env python3
"""Supplement the pinned traceability checker with active-summary invariants.

Offline, deliberately narrow: this checks README and CURRENT_STATUS against
the local implementation manifest and reviewed closed-reference facts. It is
not a GitHub synchronizer or a general natural-language truth checker. Keep
historical documents intact; new issue dispositions need explicit review here.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ("README.md", "docs/CURRENT_STATUS.md")
FAMILIES = ("M2", "M3", "M4", "EVAL")
# Reviewed at a8082109e01aff9eda72030b837103c09d1393d3, 2026-09-15.
# Sources and the remaining qualification gates: docs/status/INTEGRATION_HANDOFF.md.
CLOSED_REFERENCES = {48: "issue", 63: "issue", 71: "PR"}


def manifest_summary(manifest: dict) -> str:
    rows = manifest["families"]
    statuses = {}
    for family in FAMILIES:
        matches = [row["status"] for row in rows if row["family"] == family]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one manifest row for {family}")
        statuses[family] = matches[0]
    return "Implementation manifest: " + "; ".join(
        f"{family}={statuses[family]}" for family in FAMILIES
    ) + "."


def check_document(text: str, summary: str) -> list[str]:
    errors = []
    if text.splitlines().count(summary) != 1:
        errors.append(f"include exactly one manifest summary line: {summary}")
    if "`residual/eval_frozen/`" not in text:
        errors.append("name the canonical frozen apparatus: `residual/eval_frozen/`")
    # Canonical wording makes historical state explicit instead of trying to
    # guess whether an arbitrary mention asserts that a closed item is open.
    normalized = re.sub(r"[*`]", "", text)
    normalized = re.sub(r"\s+", " ", normalized)
    for number, kind in CLOSED_REFERENCES.items():
        reference = rf"#{number}\b"
        for match in re.finditer(reference, normalized):
            before = normalized[:match.start()]
            if not before.endswith(f"closed {kind} "):
                errors.append(f"refer to #{number} explicitly as 'closed {kind} #{number}'")
        if re.search(rf"\bclose\s+(?:(?:closed\s+)?(?:issue|PR)\s+)?{reference}", normalized, re.I):
            errors.append(f"do not request closure of already closed #{number}")
        if re.search(rf"{reference}\s+(?:still\s+)?(?:tracks|needs|remains open|must be closed)\b", normalized, re.I):
            errors.append(f"do not assign active work to closed #{number}")
    if re.search(r"(?:M2|M3|M4|EVAL)[^\n]*\bnot_started\b", text) and "=not_started" not in summary:
        errors.append("obsolete not_started claim conflicts with the current manifest")
    return errors


def check(root: Path) -> list[str]:
    try:
        summary = manifest_summary(yaml.safe_load(
            (root / "implementation-status.yaml").read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        return [f"implementation manifest unavailable/invalid: {exc}"]
    errors = []
    for path in DOCUMENTS:
        try:
            text = (root / path).read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{path}: unavailable: {exc}")
            continue
        errors.extend(f"{path}: {error}" for error in check_document(text, summary))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    errors = check(parser.parse_args(argv).root)
    print("\n".join(errors) if errors else "PASS: active status summaries match reviewed invariants")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
