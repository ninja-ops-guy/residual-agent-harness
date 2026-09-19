import ast
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]


def source_files():
    return [
        path
        for path in PACKAGE.glob("*.py")
        if path.name != "__init__.py"
    ]


def test_prototype_has_no_external_io_or_process_imports():
    forbidden_roots = {
        "subprocess", "socket", "requests", "httpx", "urllib", "aiohttp",
        "multiprocessing", "paramiko", "boto3",
    }
    violations = []
    for path in source_files():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in forbidden_roots:
                        violations.append((path.name, alias.name))
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in forbidden_roots:
                    violations.append((path.name, node.module))
    assert violations == []


def test_prototype_does_not_import_production_authority_modules():
    forbidden_prefixes = (
        "residual.factory",
        "residual.providers",
        "residual.runtime",
        "residual.integrator",
        "residual.verifier",
    )
    violations = []
    for path in source_files():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(forbidden_prefixes):
                        violations.append((path.name, alias.name))
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith(forbidden_prefixes):
                    violations.append((path.name, node.module))
    assert violations == []
