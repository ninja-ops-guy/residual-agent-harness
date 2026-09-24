#!/usr/bin/env python3
"""Check that manifest-included Python code does not import local code outside the license scope.

This is a static import-boundary check. It does not prove runtime completeness,
ownership, license validity, optional dynamic-import closure, or commercial fitness.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "open-source" / "open-source-manifest.json"


def git_files() -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        capture_output=True,
        check=True,
    )
    return [p.decode("utf-8") for p in proc.stdout.split(b"\0") if p]


def covered(path: str, roots: list[str]) -> bool:
    return any(path == root or path.startswith(root.rstrip("/") + "/") for root in roots)


def module_for(path: str) -> str | None:
    if not path.endswith(".py"):
        return None
    parts = path[:-3].split("/")
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else None


def path_for_module(module: str, modules: dict[str, str]) -> str | None:
    current = module
    while current:
        if current in modules:
            return modules[current]
        current = current.rpartition(".")[0]
    return None


def resolve_from(current_module: str, is_package: bool, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""
    package = current_module if is_package else current_module.rpartition(".")[0]
    parts = package.split(".") if package else []
    up = node.level - 1
    if up > len(parts):
        return ""
    base = parts[: len(parts) - up]
    if node.module:
        base.extend(node.module.split("."))
    return ".".join(base)


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    include = [str(p).strip("/") for p in data["include"]]
    exclude = [str(p).strip("/") for p in data["exclude"]]
    files = git_files()

    modules: dict[str, str] = {}
    for path in files:
        module = module_for(path)
        if module:
            modules[module] = path

    included_python = [p for p in files if p.endswith(".py") and covered(p, include)]
    findings: set[tuple[str, int, str, str, str]] = set()
    parse_errors: list[tuple[str, str]] = []

    for path in included_python:
        module = module_for(path)
        if not module:
            continue
        is_package = path.endswith("/__init__.py")
        try:
            tree = ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)
        except (OSError, UnicodeError, SyntaxError) as error:
            parse_errors.append((path, str(error)))
            continue

        for node in ast.walk(tree):
            targets: list[str] = []
            if isinstance(node, ast.Import):
                targets.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = resolve_from(module, is_package, node)
                if base:
                    targets.append(base)
                    # "from . import x" and package re-exports may refer to a local submodule.
                    for alias in node.names:
                        if alias.name != "*":
                            candidate = base + "." + alias.name
                            if candidate in modules:
                                targets.append(candidate)
            else:
                continue

            for target in targets:
                dep_path = path_for_module(target, modules)
                if not dep_path or covered(dep_path, include):
                    continue
                classification = "RESERVED" if covered(dep_path, exclude) else "OUTSIDE_OPEN_CORE"
                findings.add((path, getattr(node, "lineno", 0), target, dep_path, classification))

    if parse_errors:
        print("OPEN-CORE IMPORT CLOSURE: FAIL")
        for path, error in parse_errors:
            print(f"- PARSE_ERROR {path}: {error}")
        return 1

    if findings:
        print("OPEN-CORE IMPORT CLOSURE: FAIL")
        for source, line, module, dep_path, classification in sorted(findings):
            print(f"- {classification} {source}:{line} -> {module} ({dep_path})")
        print(f"missing local import edges: {len(findings)}")
        return 1

    print("OPEN-CORE IMPORT CLOSURE: PASS")
    print(f"included Python files checked: {len(included_python)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
