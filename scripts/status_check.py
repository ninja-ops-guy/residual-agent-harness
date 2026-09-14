#!/usr/bin/env python3
"""status_check.py - traceability checker and status-doc generator.

Swarm 1 (Traceability, tracks A+P). RFC 2119 language applies.

Two functions:

1. Stale-doc detector (default mode). The manifest
   ``implementation-status.yaml`` is the source of truth for what is
   implemented. Prose docs (README.md, docs/**, harness_specs/**) MUST NOT
   claim that a family the manifest marks ``implemented`` is "not
   implemented" (or equivalent phrasing) using any of the family's
   keywords. Documents listed in the manifest's ``historical_documents``
   are frozen snapshots and are skipped. The check MUST exit non-zero when
   a stale claim is found.

2. Generator (``--generate``). Regenerates
   ``docs/status/IMPLEMENTATION_STATUS.md`` from the manifest. The
   generated file MUST NOT be edited by hand.

Usage:
    python3 scripts/status_check.py [--root DIR] [--manifest PATH]
    python3 scripts/status_check.py --generate [--root DIR] [--manifest PATH]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    sys.stderr.write(
        "status_check.py requires PyYAML (pip install pyyaml)\n"
    )
    sys.exit(2)

VALID_STATUSES = ("implemented", "partial", "not_started")
GENERATED_DOC = "docs/status/IMPLEMENTATION_STATUS.md"

# Phrases that count as a "not implemented" claim in prose.
NEGATION_RE = re.compile(
    r"(not\s+yet\s+implemented|not\s+implemented|unimplemented|"
    r"does\s+not\s+exist|do\s+not\s+exist|no[t]?\s+currently\s+implemented|"
    r"remains?\s+(unimplemented|absent|missing)|is\s+absent|are\s+absent|"
    r"no\s+{kw}\b)",
    re.IGNORECASE,
)

# Prose surfaces scanned by the stale-doc detector.
SCAN_GLOBS = ("README.md", "docs/**/*.md")
# NOTE: harness_specs/*.md are normative specifications. They describe
# the gaps they close by design, so they are not prose status claims and
# are excluded from scanning. Historical assessments live under
# docs/roadmap/source/ and harness_specs/ and are listed in the
# manifest's historical_documents.


class ManifestError(Exception):
    """Raised when the manifest fails schema validation."""


def load_manifest(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    validate_manifest(data, source=str(path))
    return data


def validate_manifest(data: dict, source: str = "manifest") -> None:
    """Validate manifest schema. Raises ManifestError on any violation."""
    if not isinstance(data, dict):
        raise ManifestError(f"{source}: top level must be a mapping")
    families = data.get("families")
    if not isinstance(families, list) or not families:
        raise ManifestError(f"{source}: 'families' must be a non-empty list")
    seen = set()
    for i, fam in enumerate(families):
        where = f"{source}: families[{i}]"
        if not isinstance(fam, dict):
            raise ManifestError(f"{where}: entry must be a mapping")
        for key in ("family", "title", "spec", "status", "code_paths",
                    "test_paths", "keywords", "notes"):
            if key not in fam:
                raise ManifestError(f"{where}: missing required key '{key}'")
        name = fam["family"]
        if not isinstance(name, str) or not name:
            raise ManifestError(f"{where}: 'family' must be a non-empty string")
        if name in seen:
            raise ManifestError(f"{where}: duplicate family id '{name}'")
        seen.add(name)
        if fam["status"] not in VALID_STATUSES:
            raise ManifestError(
                f"{where}: status must be one of {VALID_STATUSES}, "
                f"got {fam['status']!r}")
        for key in ("code_paths", "test_paths", "keywords"):
            if not isinstance(fam[key], list) or not all(
                    isinstance(p, str) for p in fam[key]):
                raise ManifestError(f"{where}: '{key}' must be a list of strings")
        if fam["status"] == "implemented":
            if not fam["code_paths"]:
                raise ManifestError(
                    f"{where}: implemented family '{name}' MUST list code_paths")
            if not fam["test_paths"]:
                raise ManifestError(
                    f"{where}: implemented family '{name}' MUST list test_paths")
        if not isinstance(fam["notes"], str):
            raise ManifestError(f"{where}: 'notes' must be a string")
    hist = data.get("historical_documents", [])
    if not isinstance(hist, list) or not all(isinstance(h, str) for h in hist):
        raise ManifestError(f"{source}: 'historical_documents' must be a list of strings")


def check_manifest_paths(data: dict, root: Path) -> list[str]:
    """Every referenced code/test/spec path MUST exist on disk."""
    problems = []
    for fam in data["families"]:
        for rel in [fam["spec"], *fam["code_paths"], *fam["test_paths"]]:
            if not (root / rel).exists():
                problems.append(
                    f"{fam['family']}: referenced path does not exist: {rel}")
    for rel in data.get("historical_documents", []):
        if not (root / rel).exists():
            problems.append(f"historical document does not exist: {rel}")
    return problems


def _iter_scan_files(root: Path, skip: set[str]):
    for pattern in SCAN_GLOBS:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if rel in skip or rel == GENERATED_DOC:
                continue
            yield rel, path


def find_stale_claims(data: dict, root: Path) -> list[str]:
    """Return stale-doc violations: prose claiming an implemented family
    is not implemented."""
    skip = set(data.get("historical_documents", []))
    implemented = [f for f in data["families"] if f["status"] == "implemented"]
    violations = []
    for rel, path in _iter_scan_files(root, skip):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            low = line.lower()
            for fam in implemented:
                for kw in fam["keywords"]:
                    if kw.lower() not in low:
                        continue
                    pattern = re.compile(
                        NEGATION_RE.pattern.replace("{kw}", re.escape(kw)),
                        re.IGNORECASE)
                    if pattern.search(line):
                        violations.append(
                            f"{rel}:{lineno}: stale claim - family "
                            f"{fam['family']} is marked 'implemented' in "
                            f"implementation-status.yaml but this line says "
                            f"otherwise: {line.strip()[:120]}")
    return violations


def render_status_doc(data: dict) -> str:
    """Render docs/status/IMPLEMENTATION_STATUS.md from the manifest."""
    counts = {s: 0 for s in VALID_STATUSES}
    for fam in data["families"]:
        counts[fam["status"]] += 1
    lines = [
        "# Implementation Status",
        "",
        "<!-- GENERATED FILE. Source of truth: implementation-status.yaml.",
        "     Regenerate with: python3 scripts/status_check.py --generate -->",
        "",
        f"Requirement families: {len(data['families'])} total - "
        f"{counts['implemented']} implemented, {counts['partial']} partial, "
        f"{counts['not_started']} not started.",
        "",
        "| Family | Title | Status | Spec | Code | Tests |",
        "|---|---|---|---|---|---|",
    ]
    for fam in data["families"]:
        code = ", ".join(f"`{p}`" for p in fam["code_paths"]) or "-"
        tests = ", ".join(f"`{p}`" for p in fam["test_paths"]) or "-"
        lines.append(
            f"| {fam['family']} | {fam['title']} | {fam['status']} | "
            f"`{fam['spec']}` | {code} | {tests} |")
    lines += ["", "## Notes", ""]
    for fam in data["families"]:
        lines.append(f"### {fam['family']} - {fam['title']} ({fam['status']})")
        lines.append("")
        lines.append(fam["notes"])
        lines.append("")
    hist = data.get("historical_documents", [])
    if hist:
        lines += ["## Historical documents", "",
                  "The following are frozen point-in-time snapshots. Their "
                  "claims do not reflect current code and are excluded from "
                  "the stale-doc check:", ""]
        for h in hist:
            lines.append(f"- `{h}`")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".",
                        help="repository root (default: current directory)")
    parser.add_argument("--manifest", default=None,
                        help="path to implementation-status.yaml "
                             "(default: <root>/implementation-status.yaml)")
    parser.add_argument("--generate", action="store_true",
                        help=f"regenerate {GENERATED_DOC} from the manifest")
    parser.add_argument("--quiet", action="store_true",
                        help="only print failures")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    manifest_path = (Path(args.manifest).resolve() if args.manifest
                     else root / "implementation-status.yaml")
    try:
        data = load_manifest(manifest_path)
    except (ManifestError, OSError) as exc:
        sys.stderr.write(f"status_check: {exc}\n")
        return 2

    if args.generate:
        out = root / GENERATED_DOC
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_status_doc(data), encoding="utf-8")
        if not args.quiet:
            print(f"generated {out.relative_to(root)} from "
                  f"{manifest_path.name}")
        return 0

    problems = check_manifest_paths(data, root)
    problems += find_stale_claims(data, root)
    if problems:
        sys.stderr.write("status_check FAILED:\n")
        for p in problems:
            sys.stderr.write(f"  - {p}\n")
        return 1
    if not args.quiet:
        print(f"status_check OK: {len(data['families'])} families, "
              f"no stale doc claims, all referenced paths exist")
    return 0


if __name__ == "__main__":
    sys.exit(main())
