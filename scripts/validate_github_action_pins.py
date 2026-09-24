from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

SCHEMA = "residual.github-action-pin-audit.v1"
PIN_RE = re.compile(r"^[0-9a-fA-F]{40}$")
USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*(.+?)\s*$")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    target: str
    reason: str


def _parse_target(raw: str) -> str:
    value = raw.split(" #", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


def _report(
    status: str,
    reason: str,
    *,
    files_scanned: int = 0,
    external_uses: int = 0,
    findings: list[Finding] | None = None,
) -> dict:
    return {
        "schema": SCHEMA,
        "status": status,
        "execution_claim": "VALIDATION_ONLY",
        "reason": reason,
        "files_scanned": files_scanned,
        "external_uses": external_uses,
        "violations": [asdict(finding) for finding in (findings or [])],
    }


def audit(root: Path) -> dict:
    workflows = root / ".github" / "workflows"
    findings: list[Finding] = []
    files_scanned = 0
    external_uses = 0

    if not workflows.is_dir():
        return _report("BLOCKED", ".github/workflows is missing")

    try:
        paths = sorted([*workflows.glob("*.yml"), *workflows.glob("*.yaml")])
    except OSError as exc:
        return _report("BLOCKED", f"unable to enumerate workflows: {exc.__class__.__name__}")

    for path in paths:
        files_scanned += 1
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            return _report(
                "BLOCKED",
                f"unable to read workflow {path.name}: {exc.__class__.__name__}",
                files_scanned=files_scanned,
                external_uses=external_uses,
                findings=findings,
            )

        for lineno, line in enumerate(lines, 1):
            match = USES_RE.match(line)
            if not match:
                continue
            target = _parse_target(match.group(1))
            if target.startswith("./") or target.startswith("docker://"):
                continue

            external_uses += 1
            if "@" not in target:
                findings.append(
                    Finding(
                        str(path.relative_to(root)),
                        lineno,
                        target,
                        "external action/workflow has no ref",
                    )
                )
                continue

            _, ref = target.rsplit("@", 1)
            if not PIN_RE.fullmatch(ref):
                findings.append(
                    Finding(
                        str(path.relative_to(root)),
                        lineno,
                        target,
                        "external action/workflow ref is not an immutable 40-hex commit SHA",
                    )
                )

    return _report(
        "PASS" if not findings else "BLOCKED",
        (
            "all external workflow dependencies are commit-pinned"
            if not findings
            else "floating external workflow dependencies detected"
        ),
        files_scanned=files_scanned,
        external_uses=external_uses,
        findings=findings,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed when GitHub Actions workflows use mutable external refs."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (default: script parent repository)",
    )
    parser.add_argument("--output", type=Path, help="optional JSON report destination")
    args = parser.parse_args(argv)

    report = audit(args.root.resolve())
    rendered = json.dumps(report, sort_keys=True, indent=2) + "\n"
    if args.output:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        except OSError as exc:
            print(
                json.dumps(
                    _report("BLOCKED", f"unable to write report: {exc.__class__.__name__}"),
                    sort_keys=True,
                    indent=2,
                )
            )
            return 2
    print(rendered, end="")
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
