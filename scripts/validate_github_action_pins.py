from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml
from yaml.events import AliasEvent
from yaml.nodes import MappingNode, ScalarNode, SequenceNode

SCHEMA = "residual.github-action-pin-audit.v2"
PIN_RE = re.compile(r"^[0-9a-fA-F]{40}$")
SAFE_TAGS = {
    "tag:yaml.org,2002:map",
    "tag:yaml.org,2002:seq",
    "tag:yaml.org,2002:str",
}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    target: str
    reason: str


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


def _line(node) -> int:
    return int(getattr(getattr(node, "start_mark", None), "line", 0)) + 1


def _scalar_key(node) -> str | None:
    if isinstance(node, ScalarNode):
        return str(node.value)
    return None


def _validate_node(node, path: Path, findings: list[Finding], seen: set[int]) -> None:
    # compose() is deliberately used instead of load(): no arbitrary Python
    # object construction occurs. Reject aliases/merges/custom tags so the
    # audit semantics stay simple and deterministic.
    if id(node) in seen:
        findings.append(Finding(str(path), _line(node), "", "YAML aliases are unsupported by the pin auditor"))
        return
    seen.add(id(node))

    if getattr(node, "tag", None) not in SAFE_TAGS:
        findings.append(
            Finding(str(path), _line(node), "", f"unsupported YAML tag: {getattr(node, 'tag', None)}")
        )
        return

    if isinstance(node, MappingNode):
        keys: set[str] = set()
        for key_node, value_node in node.value:
            key = _scalar_key(key_node)
            if key is None:
                findings.append(Finding(str(path), _line(key_node), "", "workflow mapping key must be a string"))
                continue
            if key == "<<":
                findings.append(Finding(str(path), _line(key_node), "", "YAML merge keys are unsupported by the pin auditor"))
                continue
            if key in keys:
                findings.append(Finding(str(path), _line(key_node), key, "duplicate YAML mapping key"))
                continue
            keys.add(key)
            _validate_node(value_node, path, findings, seen)
    elif isinstance(node, SequenceNode):
        for value_node in node.value:
            _validate_node(value_node, path, findings, seen)


def _iter_uses(node):
    if isinstance(node, MappingNode):
        for key_node, value_node in node.value:
            if _scalar_key(key_node) == "uses":
                yield value_node
            yield from _iter_uses(value_node)
    elif isinstance(node, SequenceNode):
        for value_node in node.value:
            yield from _iter_uses(value_node)


def parse_workflow(path: Path):
    text = path.read_text(encoding="utf-8")
    if len(text.encode("utf-8")) > 2_000_000:
        raise ValueError("workflow exceeds 2 MB pin-audit bound")

    # Explicitly reject aliases/anchors before compose() folds aliases into
    # shared node identities.
    for event in yaml.parse(text, Loader=yaml.BaseLoader):
        if isinstance(event, AliasEvent) or getattr(event, "anchor", None):
            raise ValueError("YAML aliases/anchors are unsupported by the pin auditor")

    root = yaml.compose(text, Loader=yaml.BaseLoader)
    if root is None:
        raise ValueError("workflow YAML is empty")

    structural_findings: list[Finding] = []
    _validate_node(root, path, structural_findings, set())
    if structural_findings:
        return root, structural_findings
    return root, []


def external_uses(path: Path):
    root, structural_findings = parse_workflow(path)
    if structural_findings:
        return [], structural_findings

    values: list[tuple[int, str]] = []
    findings: list[Finding] = []
    for value_node in _iter_uses(root):
        if not isinstance(value_node, ScalarNode) or value_node.tag != "tag:yaml.org,2002:str":
            findings.append(
                Finding(str(path), _line(value_node), "", "uses value must be a scalar string")
            )
            continue
        target = str(value_node.value).strip()
        if target.startswith("./"):
            continue
        values.append((_line(value_node), target))
    return values, findings


def audit(root: Path) -> dict:
    workflows = root / ".github" / "workflows"
    findings: list[Finding] = []
    files_scanned = 0
    external_count = 0

    if not workflows.is_dir():
        return _report("BLOCKED", ".github/workflows is missing")

    actions = root / ".github" / "actions"
    try:
        paths = [
            *workflows.glob("*.yml"),
            *workflows.glob("*.yaml"),
        ]
        if actions.is_dir():
            paths.extend(actions.glob("**/action.yml"))
            paths.extend(actions.glob("**/action.yaml"))
        paths = sorted(set(paths))
    except OSError as exc:
        return _report("BLOCKED", f"unable to enumerate workflow/action files: {exc.__class__.__name__}")

    for path in paths:
        files_scanned += 1
        rel = path.relative_to(root)
        try:
            uses, structural_findings = external_uses(path)
        except (OSError, UnicodeError, yaml.YAMLError, ValueError) as exc:
            return _report(
                "BLOCKED",
                f"unable to structurally parse workflow {path.name}: {exc}",
                files_scanned=files_scanned,
                external_uses=external_count,
                findings=findings,
            )

        for finding in structural_findings:
            findings.append(
                Finding(str(rel), finding.line, finding.target, finding.reason)
            )

        for lineno, target in uses:
            external_count += 1
            if target.startswith("docker://"):
                image = target[len("docker://"):]
                if "@sha256:" not in image:
                    findings.append(
                        Finding(str(rel), lineno, target, "docker action image is not pinned by sha256 digest")
                    )
                else:
                    _, digest = image.rsplit("@sha256:", 1)
                    if not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
                        findings.append(
                            Finding(str(rel), lineno, target, "docker action image digest is not 64-hex SHA-256")
                        )
                continue
            if "@" not in target:
                findings.append(
                    Finding(str(rel), lineno, target, "external action/workflow has no ref")
                )
                continue

            _, ref = target.rsplit("@", 1)
            if not PIN_RE.fullmatch(ref):
                findings.append(
                    Finding(
                        str(rel),
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
            else "floating or structurally invalid workflow dependencies detected"
        ),
        files_scanned=files_scanned,
        external_uses=external_count,
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
