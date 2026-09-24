from __future__ import annotations

import ast
import pathlib
import tomllib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _package_version() -> str:
    tree = ast.parse((ROOT / "residual" / "__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return node.value.value
            raise AssertionError("residual.__version__ must be a literal string")
    raise AssertionError("residual.__version__ assignment not found")


class VersionMetadataTests(unittest.TestCase):
    def test_package_version_matches_project_metadata(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        self.assertEqual(project["version"], _package_version())


if __name__ == "__main__":
    unittest.main()
