from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import yaml
    from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode
except Exception:  # pragma: no cover - exercised by runtime BLOCKED handling
    yaml = None
    MappingNode = Node = ScalarNode = SequenceNode = object

SCHEMA = "residual.github-action-pin-audit.v2"
PIN_RE = re.compile(r"^[0-9a-fA-F]{40}$")


@dataclass(frozen=True)
class UseReference:
    path: str
    line: int
    target: str


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    target: str
    reason: str


class WorkflowParseError(RuntimeError):
    pass


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


def _walk_uses(node: Node, path: Path, root: Path, output: list[UseReference]) -> None:
    """Traverse the YAML syntax tree and collect every structural uses: scalar.

    A syntax-tree walk avoids the false-PASS class caused by line-oriented regex
    parsing: inline mappings, quoted keys, folded scalars, and aliases are all
    interpreted as YAML rather than guessed from source text.
    """
    if isinstance(node, MappingNode):
        seen_keys: set[str] = set()
        for key_node, value_node in node.value:
            if isinstance(key_node, ScalarNode):
                key = str(key_node.value)
                if key in seen_keys:
                    raise WorkflowParseError(
                        f"duplicate mapping key {key!r} at line {key_node.start_mark.line + 1}"
                    )
                seen_keys.add(key)
                if key == "uses":
                    if not isinstance(value_node, ScalarNode):
                        raise WorkflowParseError(
                            f"uses must be a scalar at line {value_node.start_mark.line + 1}"
                        )
                    target = str(value_node.value).strip()
                    output.append(
                        UseReference(
                            str(path.relative_to(root)),
                            value_node.start_mark.line + 1,
                            target,
                        )
                    )
            _walk_uses(value_node, path, root, output)
    elif isinstance(node, SequenceNode):
        for child in node.value:
            _walk_uses(child, path, root, output)


def scan_workflow_uses(root: Path) -> tuple[list[UseReference], int]:
    workflows = root / ".github" / "workflows"
    if not workflows.is_dir():
        raise WorkflowParseError(".github/workflows is missing")
    if yaml is None:
        raise WorkflowParseError("PyYAML is unavailable")

    try:
        paths = sorted([*workflows.glob("*.yml"), *workflows.glob("*.yaml")])
    except OSError as exc:
        raise WorkflowParseError(f"unable to enumerate workflows: {exc.__class__.__name__}") from exc

    references: list[UseReference] = []
    files_scanned = 0
    for path in paths:
        files_scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise WorkflowParseError(
                f"unable to read workflow {path.name}: {exc.__class__.__name__}"
            ) from exc
        try:
            document = yaml.compose(text, Loader=yaml.BaseLoader)
        except yaml.YAMLError as exc:
            mark = getattr(exc, "problem_mark", None)
            suffix = f" at line {mark.line + 1}" if mark is not None else ""
            raise WorkflowParseError(f"invalid workflow YAML {path.name}{suffix}") from exc
        if document is not None:
            _walk_uses(document, path, root, references)
    return references, files_scanned


def audit(root: Path) -> dict:
    findings: list[Finding] = []
    external_uses = 0
    try:
        references, files_scanned = scan_workflow_uses(root)
    except WorkflowParseError as exc:
        return _report("BLOCKED", str(exc))

    for reference in references:
        target = reference.target
        if target.startswith("./") or target.startswith("docker://"):
            continue

        external_uses += 1
        if "@" not in target:
            findings.append(
                Finding(reference.path, reference.line, target, "external action/workflow has no ref")
            )
            continue

        _, ref = target.rsplit("@", 1)
        if not PIN_RE.fullmatch(ref):
            findings.append(
                Finding(
                    reference.path,
                    reference.line,
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
